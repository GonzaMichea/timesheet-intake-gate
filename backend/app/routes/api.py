"""Endpoints delgados: validan la entrada y llaman a services/ (design §6)."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db import models as m
from backend.app.db.session import get_db
from backend.app.errors import ApiError
from backend.app.schemas import (
    AcceptMapping, Actor, AuditOut, BatchListItem, BatchSummary, FileDetail, OverrideIn, ReviewQueue,
    WithdrawIn,
)
from backend.app.services import actions, batches
from backend.app.services.contract_store import current_bundle
from backend.app.services.views import (
    batch_files, batch_summary, file_detail, file_summary, get_batch, get_file, iso, review_out,
)

router = APIRouter(prefix="/api")
REPORTS = Path(__file__).resolve().parents[3] / "reports"


@router.get("/contract")
def contract_info():
    contract = current_bundle().contract
    return {
        "sites": contract.sites,
        "code_descriptions": contract.code_descriptions,
        "columns": [{"name": n, "type": c.type, "nullable": c.nullable, "approval": c.approval}
                    for n, c in contract.columns.items()],
        "quarantine_error_row_pct": contract.thresholds.quarantine_error_row_pct,
        "ai_min_confidence": contract.thresholds.ai_min_confidence,
        "max_upload_mb": contract.thresholds.max_upload_mb,
    }


@router.post("/batches", status_code=201, response_model=BatchSummary)
async def create_batch(period: str = Form(""), actor: str = Form(""), files: list[UploadFile] = File(default=[]),
                       db: Session = Depends(get_db)):
    uploads = [(f.filename or "sin_nombre", await f.read()) for f in files]
    return batch_summary(db, batches.create_batch(db, period, actor, uploads))


@router.get("/batches", response_model=list[BatchListItem])
def list_batches(db: Session = Depends(get_db)):
    rows = db.scalars(select(m.Batch).order_by(m.Batch.created_at.desc())).all()
    counts = dict(db.execute(select(m.BatchFile.batch_id, func.count()).group_by(m.BatchFile.batch_id)).all())
    return [BatchListItem(id=str(b.id), period=b.period, analyst_name=b.analyst_name, created_at=iso(b.created_at),
                          ready_for_load=b.ready_for_load, file_count=counts.get(b.id, 0)) for b in rows]


@router.get("/batches/{batch_id}", response_model=BatchSummary)
def get_batch_summary(batch_id: str, db: Session = Depends(get_db)):
    return batch_summary(db, get_batch(db, batch_id))


@router.get("/batches/{batch_id}/review", response_model=ReviewQueue)
def review_queue(batch_id: str, db: Session = Depends(get_db)):
    batch = get_batch(db, batch_id)
    files = batch_files(db, batch.id)
    by_id = {f.id: f for f in files}
    pending = db.scalars(select(m.MappingReview).where(m.MappingReview.file_id.in_(by_id), m.MappingReview.status == "pending")
                         .order_by(m.MappingReview.created_at, m.MappingReview.source_column)).all()
    return ReviewQueue(pending=[review_out(r, by_id[r.file_id]) for r in pending],
                       files=[file_summary(db, f) for f in files])


@router.get("/batches/{batch_id}/audit", response_model=list[AuditOut])
def batch_audit(batch_id: str, db: Session = Depends(get_db)):
    batch = get_batch(db, batch_id)
    rows = db.scalars(select(m.AuditLog).where(m.AuditLog.batch_id == batch.id)
                      .order_by(m.AuditLog.created_at, m.AuditLog.id)).all()
    return [AuditOut(id=str(a.id), created_at=iso(a.created_at), actor=a.actor, action=a.action,
                     entity_type=a.entity_type, entity_id=a.entity_id, before=a.before, after=a.after,
                     justification=a.justification) for a in rows]


@router.get("/files/{file_id}", response_model=FileDetail)
def get_file_detail(file_id: str, db: Session = Depends(get_db)):
    return file_detail(db, get_file(db, file_id))


@router.post("/mappings/{review_id}/accept", response_model=FileDetail)
def accept_mapping(review_id: str, body: AcceptMapping, db: Session = Depends(get_db)):
    return file_detail(db, actions.accept_mapping(db, review_id, body.actor, body.target_column))


@router.post("/mappings/{review_id}/reject", response_model=FileDetail)
def reject_mapping(review_id: str, body: Actor, db: Session = Depends(get_db)):
    return file_detail(db, actions.reject_mapping(db, review_id, body.actor))


@router.post("/files/{file_id}/override", response_model=FileDetail)
def create_override(file_id: str, body: OverrideIn, db: Session = Depends(get_db)):
    return file_detail(db, actions.create_override(db, file_id, body.actor, body.disposition, body.justification))


@router.post("/files/{file_id}/override/withdraw", response_model=FileDetail)
def withdraw_override(file_id: str, body: WithdrawIn, db: Session = Depends(get_db)):
    return file_detail(db, actions.withdraw_override(db, file_id, body.actor, body.justification))


@router.get("/metrics")
def metrics():
    path = REPORTS / "evaluation.json"
    if not path.exists():
        raise ApiError(404, "sin_metricas", "Aún no hay resultados de evaluación. Genera los datos con "
                       "'python scripts/generate_dataset.py' y luego ejecuta 'python scripts/evaluate.py'.")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
