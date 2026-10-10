"""Acciones humanas: mapeos y overrides. Todas quedan en la auditoría (R8–R10)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend.app.db import models as m
from backend.app.engine.batch import assign_refs
from backend.app.engine.disposition import decide
from backend.app.engine.validate import norm_header, validate_file
from backend.app.errors import ApiError
from backend.app.services.batches import clean_actor, finding_row, review_rows
from backend.app.services.contract_store import bundle_from_texts
from backend.app.services.views import (
    RANK, active_override, compute_ready, counts_of, final_disposition, findings_of, get_file,
)

DISPOSITIONS = set(RANK)
MIN_JUSTIFICATION = 20


def snapshot(db: Session, file: m.BatchFile) -> dict:
    return {"computed": file.computed_disposition, "final": final_disposition(db, file),
            "counts": counts_of(findings_of(db, file.id)).model_dump()}


def audit(db: Session, file: m.BatchFile, actor: str, action: str, entity_type: str, entity_id,
          before, after, justification: str | None = None) -> None:
    # Se guarda el nombre de la sede dentro del registro para poder mostrarlo sin consultar otras tablas
    where = {"file": file.site or file.filename}
    db.add(m.AuditLog(batch_id=file.batch_id, actor=actor, action=action, entity_type=entity_type,
                      entity_id=str(entity_id), before={**before, **where}, after={**after, **where},
                      justification=justification))


def check_justification(text: str) -> str:
    text = (text or "").strip()
    if len(text) < MIN_JUSTIFICATION:
        raise ApiError(400, "justificacion_corta",
                       f"La justificación debe tener al menos {MIN_JUSTIFICATION} caracteres.")
    return text


def _review(db: Session, review_id: str) -> tuple[m.MappingReview, m.BatchFile]:
    try:
        review = db.get(m.MappingReview, uuid.UUID(review_id))
    except ValueError:
        review = None
    if review is None:
        raise ApiError(404, "mapeo_no_encontrado", "No se encontró la sugerencia de mapeo.")
    if review.status != "pending":
        raise ApiError(409, "mapeo_resuelto", "Esta sugerencia ya fue resuelta.")
    return review, db.get(m.BatchFile, review.file_id)


def _finish(db: Session, file: m.BatchFile) -> None:
    db.flush()
    db.execute(update(m.Batch).where(m.Batch.id == file.batch_id).values(ready_for_load=compute_ready(db, file.batch_id)))
    db.commit()


def revalidate(db: Session, file: m.BatchFile) -> None:
    """Revalida el archivo con la copia del contrato del lote y reemplaza sus hallazgos (R8.3)."""
    batch = db.get(m.Batch, file.batch_id)
    bundle = bundle_from_texts(batch.contract_yaml, batch.master_csv)
    findings, row_count, _ = validate_file(file.filename, file.content, batch.period, bundle.contract,
                                           bundle.master, file.applied_mapping)
    assign_refs(findings, file.site)
    disposition = decide(findings, row_count, bundle.contract)
    db.execute(delete(m.Finding).where(m.Finding.file_id == file.id))
    db.add_all(finding_row(file.id, f) for f in findings)
    file.row_count, file.computed_disposition = row_count, disposition.value
    file.disposition_rule, file.disposition_explanation = disposition.rule_id, disposition.explanation
    # Revisiones: las columnas nuevas se agregan y las pendientes actualizan su candidata
    existing = {r.source_column: r for r in db.scalars(select(m.MappingReview).where(m.MappingReview.file_id == file.id))}
    for fresh in review_rows(file.id, findings):
        current = existing.get(fresh.source_column)
        if current is None:
            db.add(fresh)
        elif current.status == "pending":
            current.candidate_column, current.candidate_score = fresh.candidate_column, fresh.candidate_score
    # Los textos de IA citaban hallazgos que ya no existen (D-10)
    db.execute(update(m.AiResult).where(m.AiResult.file_id == file.id).values(is_stale=True))


def accept_mapping(db: Session, review_id: str, actor: str, target_column: str) -> m.BatchFile:
    actor = clean_actor(actor)
    review, file = _review(db, review_id)
    batch = db.get(m.Batch, file.batch_id)
    contract = bundle_from_texts(batch.contract_yaml, batch.master_csv).contract
    missing = {f.column_name for f in findings_of(db, file.id) if f.code == "D04" and f.status == "open"}
    if target_column not in contract.columns or target_column not in missing:
        raise ApiError(400, "destino_invalido", "El destino debe ser una columna requerida que falta en este archivo.")
    before = snapshot(db, file)
    file.applied_mapping = {**file.applied_mapping, norm_header(review.source_column): target_column}
    review.status, review.chosen_column = "accepted", target_column
    review.decided_by, review.decided_at = actor, datetime.now(timezone.utc)
    revalidate(db, file)
    db.flush()
    audit(db, file, actor, "mapping_accepted", "mapping", review.id,
          {**before, "column": review.source_column}, {**snapshot(db, file), "target": target_column})
    _finish(db, file)
    return file


def reject_mapping(db: Session, review_id: str, actor: str) -> m.BatchFile:
    actor = clean_actor(actor)
    review, file = _review(db, review_id)
    review.status, review.decided_by, review.decided_at = "rejected", actor, datetime.now(timezone.utc)
    audit(db, file, actor, "mapping_rejected", "mapping", review.id,
          {"status": "pending", "column": review.source_column}, {"status": "rejected"})
    _finish(db, file)
    return file


def create_override(db: Session, file_id: str, actor: str, disposition: str, justification: str) -> m.BatchFile:
    actor, justification = clean_actor(actor), check_justification(justification)
    if disposition not in DISPOSITIONS:
        raise ApiError(400, "disposicion_invalida", "La disposición debe ser LOAD, LOAD_WITH_WARNINGS, QUARANTINE o BLOCK.")
    file = get_file(db, file_id)
    before = snapshot(db, file)
    db.add(m.Override(file_id=file.id, disposition=disposition, justification=justification, actor=actor,
                      computed_disposition=file.computed_disposition))
    db.flush()
    audit(db, file, actor, "override_created", "file", file.id, before, snapshot(db, file), justification)
    _finish(db, file)
    return file


def withdraw_override(db: Session, file_id: str, actor: str, justification: str) -> m.BatchFile:
    actor, justification = clean_actor(actor), check_justification(justification)
    file = get_file(db, file_id)
    if active_override(db, file.id) is None:
        raise ApiError(409, "sin_override", "Este archivo no tiene un override activo.")
    before = snapshot(db, file)
    db.add(m.Override(file_id=file.id, disposition=None, justification=justification, actor=actor,
                      computed_disposition=file.computed_disposition))
    db.flush()
    audit(db, file, actor, "override_withdrawn", "file", file.id, before, snapshot(db, file), justification)
    _finish(db, file)
    return file
