"""Crear un lote: ingesta, validación con el motor y guardado (R2)."""
import re
import time

from sqlalchemy.orm import Session

from backend.app.db import models as m
from backend.app.engine.batch import validate_batch
from backend.app.engine.ingest import IngestError, check_total_size, expand_inputs
from backend.app.engine.models import Finding as EngineFinding
from backend.app.errors import ApiError
from backend.app.services.contract_store import current_bundle
from backend.app.services.views import compute_ready


def clean_actor(actor: str) -> str:
    """R10.3: toda acción necesita el nombre del analista."""
    actor = (actor or "").strip()
    if not actor:
        raise ApiError(400, "falta_analista", "Falta el nombre del analista. Ingrésalo para continuar.")
    return actor


def finding_row(file_id, f: EngineFinding) -> m.Finding:
    return m.Finding(
        file_id=file_id, ref=f.ref, code=f.code, severity=f.severity, column_name=f.column,
        rule_id=f.rule_id, rule_text=f.rule_text, affected_count=f.affected_count,
        affected_rows=f.affected_rows, sample_rows=f.sample_rows, evidence=f.evidence, status=f.status,
    )


def review_rows(file_id, findings: list[EngineFinding]) -> list[m.MappingReview]:
    """Una revisión pendiente por cada columna desconocida (D05 con candidata, o D06)."""
    return [
        m.MappingReview(file_id=file_id, source_column=f.column, candidate_column=f.evidence.get("candidate"),
                        candidate_score=f.evidence.get("score"))
        for f in findings if f.code in ("D05", "D06") and f.status == "open"
    ]


def create_batch(db: Session, period: str, actor: str, uploads: list[tuple[str, bytes]]) -> m.Batch:
    actor = clean_actor(actor)
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period or ""):
        raise ApiError(400, "periodo_invalido", "El período debe tener el formato AAAA-MM, por ejemplo 2026-09.")
    if not uploads:
        raise ApiError(400, "sin_archivos", "Sube al menos un archivo (.csv, .xlsx o .zip) para validar.")
    bundle = current_bundle()
    try:
        check_total_size(uploads, bundle.contract.thresholds.max_upload_mb)
        files = expand_inputs(uploads)
    except IngestError as error:
        raise ApiError(400, "carga_invalida", str(error)) from error
    if not files:
        raise ApiError(400, "sin_archivos", "El .zip no contiene archivos para validar.")

    started = time.perf_counter()
    result = validate_batch(period, files, bundle.contract, bundle.master)
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    batch = m.Batch(
        period=period, analyst_name=actor, contract_yaml=bundle.contract_text, master_csv=bundle.master_text,
        contract_hash=bundle.hash, processing_ms=elapsed_ms, ready_for_load=result.ready_for_load,
    )
    db.add(batch)
    db.flush()
    contents = {f.name: f.content for f in files}
    for entry in result.entries:
        file = m.BatchFile(
            batch_id=batch.id, kind=entry.kind, filename=entry.filename, site=entry.site,
            content=contents.get(entry.filename) if entry.filename else None, row_count=entry.row_count,
            applied_mapping={}, computed_disposition=entry.disposition.value,
            disposition_rule=entry.disposition.rule_id, disposition_explanation=entry.disposition.explanation,
        )
        db.add(file)
        db.flush()
        db.add_all(finding_row(file.id, f) for f in entry.findings)
        db.add_all(review_rows(file.id, entry.findings))
    db.flush()
    batch.ready_for_load = compute_ready(db, batch.id)
    db.commit()
    return batch
