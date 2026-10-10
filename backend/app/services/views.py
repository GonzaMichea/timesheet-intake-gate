"""Convierte filas de la base de datos en las respuestas de la API."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import models as m
from backend.app.errors import ApiError
from backend.app.schemas import (
    BatchSummary, DefectBrief, FileDetail, FileSummary, FindingOut, MappingReviewOut, OverrideOut,
    SeverityCounts,
)
from backend.app.services.contract_store import bundle_from_texts

RANK = {"LOAD": 0, "LOAD_WITH_WARNINGS": 1, "QUARANTINE": 2, "BLOCK": 3}
BLOCKING = {"QUARANTINE", "BLOCK"}


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:  # SQLite devuelve fechas sin zona; siempre se guardan en UTC
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def get_batch(db: Session, batch_id: str) -> m.Batch:
    try:
        batch = db.get(m.Batch, uuid.UUID(batch_id))
    except ValueError:
        batch = None
    if batch is None:
        raise ApiError(404, "lote_no_encontrado", "No se encontró el lote pedido.")
    return batch


def get_file(db: Session, file_id: str) -> m.BatchFile:
    try:
        file = db.get(m.BatchFile, uuid.UUID(file_id))
    except ValueError:
        file = None
    if file is None:
        raise ApiError(404, "archivo_no_encontrado", "No se encontró el archivo pedido.")
    return file


def overrides_of(db: Session, file_id) -> list[m.Override]:
    return list(db.scalars(select(m.Override).where(m.Override.file_id == file_id)
                           .order_by(m.Override.created_at, m.Override.id)))


def active_override(db: Session, file_id) -> m.Override | None:
    history = overrides_of(db, file_id)
    return history[-1] if history and history[-1].disposition else None


def final_disposition(db: Session, file: m.BatchFile) -> str:
    override = active_override(db, file.id)
    return override.disposition if override else file.computed_disposition


def counts_of(findings: list[m.Finding]) -> SeverityCounts:
    counts = SeverityCounts()
    for f in findings:
        if f.status == "open":
            setattr(counts, f.severity, getattr(counts, f.severity) + 1)
    return counts


def findings_of(db: Session, file_id) -> list[m.Finding]:
    return list(db.scalars(select(m.Finding).where(m.Finding.file_id == file_id)
                           .order_by(m.Finding.ref)))


SEVERITY_RANK = {"WARNING": 1, "ERROR": 2, "BLOCKER": 3}
RIBBON_CHAR = {1: "W", 2: "E", 3: "B"}


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value[:3])
    return str(value)


def defects_of(findings: list[m.Finding], descriptions: dict[str, str]) -> list[DefectBrief]:
    """Agrupa los hallazgos abiertos por código, del más grave al menos grave."""
    groups: dict[str, list[m.Finding]] = {}
    for f in findings:
        if f.status == "open":
            groups.setdefault(f.code, []).append(f)
    briefs = []
    for code, items in groups.items():
        first = items[0]
        briefs.append(DefectBrief(
            code=code, description=descriptions[code],
            severity=max((f.severity for f in items), key=SEVERITY_RANK.__getitem__),
            columns=list(dict.fromkeys(f.column_name for f in items if f.column_name)),
            rows=len({r for f in items for r in f.affected_rows}),
            found=_text(first.evidence.get("found")), expected=_text(first.evidence.get("expected")),
        ))
    return sorted(briefs, key=lambda b: (-SEVERITY_RANK[b.severity], b.code))


def ribbon_of(findings: list[m.Finding], row_count: int) -> str:
    """Cinta de filas: la severidad más alta de cada fila (numeración Excel: fila 2 = posición 0)."""
    worst: dict[int, int] = {}
    for f in findings:
        if f.status == "open":
            for row in f.affected_rows:
                worst[row] = max(worst.get(row, 0), SEVERITY_RANK[f.severity])
    length = max([row_count, *(row - 1 for row in worst)])
    return "".join(RIBBON_CHAR.get(worst.get(i + 2, 0), ".") for i in range(length))


def file_summary(db: Session, file: m.BatchFile) -> FileSummary:
    batch = db.get(m.Batch, file.batch_id)
    descriptions = bundle_from_texts(batch.contract_yaml, batch.master_csv).contract.code_descriptions
    findings = findings_of(db, file.id)
    override = active_override(db, file.id)
    permissive = bool(override and RANK[override.disposition] < RANK[file.computed_disposition])
    changed = bool(override and override.computed_disposition
                   and override.computed_disposition != file.computed_disposition)
    return FileSummary(
        id=str(file.id), batch_id=str(file.batch_id), kind=file.kind, filename=file.filename, site=file.site,
        row_count=file.row_count or 0, computed_disposition=file.computed_disposition,
        final_disposition=override.disposition if override else file.computed_disposition,
        disposition_rule=file.disposition_rule, disposition_explanation=file.disposition_explanation,
        override_active=override is not None, permissive_override=permissive,
        calculated_changed_after_override=changed, counts=counts_of(findings),
        defects=defects_of(findings, descriptions), ribbon=ribbon_of(findings, file.row_count or 0),
    )


def compute_ready(db: Session, batch_id) -> bool:
    files = db.scalars(select(m.BatchFile).where(m.BatchFile.batch_id == batch_id))
    return all(final_disposition(db, f) not in BLOCKING for f in files)


def review_out(review: m.MappingReview, file: m.BatchFile) -> MappingReviewOut:
    return MappingReviewOut(
        id=str(review.id), file_id=str(file.id), filename=file.filename, site=file.site,
        source_column=review.source_column, candidate_column=review.candidate_column,
        candidate_score=float(review.candidate_score) if review.candidate_score is not None else None,
        status=review.status, chosen_column=review.chosen_column, decided_by=review.decided_by,
        decided_at=iso(review.decided_at),
    )


def batch_files(db: Session, batch_id) -> list[m.BatchFile]:
    """Sedes en el orden del contrato; después, los archivos fuera de patrón por nombre."""
    batch = db.get(m.Batch, batch_id)
    sites = bundle_from_texts(batch.contract_yaml, batch.master_csv).contract.sites
    files = db.scalars(select(m.BatchFile).where(m.BatchFile.batch_id == batch_id))
    return sorted(files, key=lambda f: (sites.index(f.site) if f.site in sites else len(sites), f.filename or ""))


def batch_summary(db: Session, batch: m.Batch) -> BatchSummary:
    entries = [file_summary(db, f) for f in batch_files(db, batch.id)]
    totals = SeverityCounts()
    for entry in entries:
        for severity in ("BLOCKER", "ERROR", "WARNING"):
            setattr(totals, severity, getattr(totals, severity) + getattr(entry.counts, severity))
    return BatchSummary(
        id=str(batch.id), period=batch.period, analyst_name=batch.analyst_name, created_at=iso(batch.created_at),
        processing_ms=batch.processing_ms, contract_hash=batch.contract_hash,
        ready_for_load=batch.ready_for_load, totals=totals, entries=entries,
    )


def file_detail(db: Session, file: m.BatchFile) -> FileDetail:
    batch = db.get(m.Batch, file.batch_id)
    contract = bundle_from_texts(batch.contract_yaml, batch.master_csv).contract
    findings = findings_of(db, file.id)
    reviews = db.scalars(select(m.MappingReview).where(m.MappingReview.file_id == file.id)
                         .order_by(m.MappingReview.source_column))
    missing = sorted({f.column_name for f in findings if f.code == "D04" and f.status == "open"})
    return FileDetail(
        **file_summary(db, file).model_dump(), period=batch.period,
        findings=[FindingOut(
            id=str(f.id), ref=f.ref, code=f.code, code_description=contract.code_descriptions[f.code],
            severity=f.severity, column=f.column_name, rule_id=f.rule_id, rule_text=f.rule_text,
            affected_count=f.affected_count, affected_rows=f.affected_rows, sample_rows=f.sample_rows,
            evidence=f.evidence, status=f.status) for f in findings],
        mappings=[review_out(r, file) for r in reviews],
        overrides=[OverrideOut(id=str(o.id), disposition=o.disposition, justification=o.justification,
                               actor=o.actor, created_at=iso(o.created_at),
                               computed_disposition=o.computed_disposition)
                   for o in overrides_of(db, file.id)],
        missing_columns=missing, required_columns=list(contract.columns),
    )
