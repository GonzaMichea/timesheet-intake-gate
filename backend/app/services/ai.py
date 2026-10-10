"""Guarda cada resultado de IA con modelo, latencia y estado (R11.10)."""
from sqlalchemy.orm import Session

from backend.app.ai import assist
from backend.app.db import models as m
from backend.app.errors import ApiError
from backend.app.services.contract_store import bundle_from_texts
from backend.app.services.views import get_file


def generate(db: Session, file_id: str, kind: str) -> m.AiResult:
    if kind not in assist.KINDS:
        raise ApiError(404, "tipo_ia_invalido", "Ese tipo de asistencia de IA no existe.")
    file = get_file(db, file_id)
    if file.kind != "site_file" or file.content is None:
        outcome = assist.AiOutcome(status="no_disponible", reason="Este archivo no tiene contenido que analizar.")
    else:
        batch = db.get(m.Batch, file.batch_id)
        bundle = bundle_from_texts(batch.contract_yaml, batch.master_csv)
        outcome = assist.run(kind, file.filename, file.site, file.content, batch.period, bundle.contract,
                             bundle.master, file.applied_mapping)
    result = m.AiResult(file_id=file.id, kind=kind, status=outcome.status, model=outcome.model,
                        latency_ms=outcome.latency_ms, payload=outcome.payload, reason=outcome.reason)
    db.add(result)
    db.commit()
    return result
