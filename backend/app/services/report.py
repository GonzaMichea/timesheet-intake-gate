"""Reporte de calidad del lote: un solo HTML, sin recursos externos, listo para imprimir a PDF (R13.6)."""
from datetime import datetime, timezone
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import models as m
from backend.app.schemas import FileDetail
from backend.app.services.views import batch_files, batch_summary, file_detail, get_batch, overrides_of

DISPOSITION = {"LOAD": "Cargar", "LOAD_WITH_WARNINGS": "Cargar con advertencias", "QUARANTINE": "Cuarentena",
               "BLOCK": "Bloqueado"}
SEVERITY = {"BLOCKER": "Bloqueante", "ERROR": "Error", "WARNING": "Advertencia"}
ACTION = {"mapping_accepted": "Aceptó un mapeo", "mapping_rejected": "Rechazó un mapeo",
          "override_created": "Fijó una disposición", "override_withdrawn": "Retiró un override"}
CSS = """
body{font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:#17212b;margin:0;padding:32px;max-width:1000px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:20px;margin:36px 0 8px;border-bottom:2px solid #17212b;padding-bottom:4px}
h3{font-size:16px;margin:20px 0 6px}table{border-collapse:collapse;width:100%;margin:8px 0}
th,td{text-align:left;padding:4px 8px 4px 0;border-bottom:1px solid #d3dadf;vertical-align:top}th{border-bottom:1px solid #17212b}
.muted{color:#4b5967}.ok{color:#15803d}.bad{color:#b91c1c}.warn{color:#a16207}.q{color:#c2410c}
.tag{display:inline-block;border:2px solid currentColor;padding:1px 8px;font-weight:700;text-transform:uppercase;font-size:12px}
code{font:12px ui-monospace,Consolas,monospace}.ai{border-left:3px solid #4b5967;padding-left:10px;margin:8px 0}
@media print{body{padding:0}h2{break-after:avoid}tr,.ai{break-inside:avoid}}
"""
TONE = {"LOAD": "ok", "LOAD_WITH_WARNINGS": "warn", "QUARANTINE": "q", "BLOCK": "bad"}


def e(value) -> str:
    return escape("" if value is None else str(value))


def when(value: datetime) -> str:
    """Fecha legible en UTC, la misma hora que guarda la auditoría."""
    value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%d-%m-%Y %H:%M UTC")


def seal(disposition: str) -> str:
    return f'<span class="tag {TONE[disposition]}">{e(DISPOSITION[disposition])}</span>'


def _text(value) -> str:
    return ", ".join(map(str, value)) if isinstance(value, list) else str(value if value is not None else "—")


def _rows(rows: list[int]) -> str:
    shown = ", ".join(map(str, rows[:20]))
    return shown + (f" y {len(rows) - 20} más" if len(rows) > 20 else "") if rows else "—"


def _findings(detail: FileDetail) -> str:
    if not detail.findings:
        return "<p>Sin hallazgos: el archivo cumple el contrato.</p>"
    body = "".join(
        f"<tr><td>{e(f.ref)}</td><td>{e(SEVERITY[f.severity])}</td><td>{e(f.code)} {e(f.code_description)}</td>"
        f"<td>{e(f.column or 'Todo el archivo')}</td><td>{e(_rows(f.affected_rows))}</td>"
        f"<td>encontrado: {e(_text(f.evidence.get('found')))}<br>esperado: {e(_text(f.evidence.get('expected')))}</td>"
        f"<td>{e(f.rule_text)}<br><span class='muted'>{e(f.rule_id)}</span>"
        f"{' · resuelto por mapeo' if f.status == 'resolved_by_mapping' else ''}</td></tr>"
        for f in detail.findings)
    return ("<table><thead><tr><th>Código</th><th>Severidad</th><th>Defecto</th><th>Columna</th><th>Filas</th>"
            f"<th>Evidencia</th><th>Regla aplicada</th></tr></thead><tbody>{body}</tbody></table>")


def _ai(detail: FileDetail) -> str:
    parts = []
    cause, draft = detail.ai.get("cause"), detail.ai.get("remediation")
    if cause and cause.status == "ok" and cause.payload:
        items = "".join(
            f"<li>{e(s['text'])} <span class='muted'>({'respaldo: ' + e(', '.join(s['finding_refs'])) if s['finding_refs'] else 'sin respaldo en hallazgos'})</span>"
            f"{' · <b>Requiere revisión humana</b>' if s['needs_review'] else ''}</li>" for s in cause.payload["statements"])
        parts.append(f"<div class='ai'><b>Causa probable</b> <span class='muted'>(IA – no vinculante)</span><ul>{items}</ul></div>")
    if draft and draft.status == "ok" and draft.payload:
        flag = " · <b>Requiere revisión humana</b>" if draft.payload["needs_review"] else ""
        parts.append(f"<div class='ai'><b>Borrador de mensaje a la sede</b> <span class='muted'>(IA – no vinculante)</span>{flag}"
                     f"<p><b>{e(draft.payload['subject'])}</b></p><p style='white-space:pre-wrap'>{e(draft.payload['body'])}</p></div>")
    return "".join(parts)


def _file_section(detail: FileDetail) -> str:
    name = detail.site or detail.filename or "Archivo"
    changed = "<p class='warn'>La disposición calculada cambió después del override.</p>" if detail.calculated_changed_after_override else ""
    final = ""
    if detail.override_active:
        kind = "Override permisivo" if detail.permissive_override else "Override"
        final = f"<p><b>{kind}:</b> disposición final {seal(detail.final_disposition)}</p>{changed}"
    counts = detail.counts
    return (f"<h3>{e(name)} <span class='muted'>{e(detail.filename or 'archivo no recibido')} · {detail.row_count} filas</span></h3>"
            f"<p>Calculada por el código: {seal(detail.computed_disposition)} "
            f"<span class='muted'>{e(detail.disposition_explanation)} ({e(detail.disposition_rule)})</span></p>{final}"
            f"<p class='muted'>Abiertos: {counts.BLOCKER} bloqueantes, {counts.ERROR} errores, {counts.WARNING} advertencias.</p>"
            f"{_findings(detail)}{_ai(detail)}")


def build_report(db: Session, batch_id: str) -> str:
    batch = get_batch(db, batch_id)
    summary = batch_summary(db, batch)
    files = batch_files(db, batch.id)
    details = [file_detail(db, f) for f in files]
    verdict = ("Lote apto para carga", "ok") if summary.ready_for_load else ("Lote no apto para carga", "bad")
    overrides = [(f, o) for f in files for o in overrides_of(db, f.id)]
    override_rows = "".join(
        f"<tr><td>{e(when(o.created_at))}</td><td>{e(f.site or f.filename)}</td><td>{e(o.actor)}</td>"
        f"<td>{e(DISPOSITION[o.disposition] if o.disposition else 'Override retirado')}</td><td>{e(o.justification)}</td></tr>"
        for f, o in sorted(overrides, key=lambda pair: pair[1].created_at))
    audit = db.scalars(select(m.AuditLog).where(m.AuditLog.batch_id == batch.id).order_by(m.AuditLog.created_at, m.AuditLog.id))
    audit_rows = "".join(
        f"<tr><td>{e(when(a.created_at))}</td><td>{e(a.actor)}</td><td>{e(ACTION.get(a.action, a.action))} · {e((a.after or {}).get('file'))}</td>"
        f"<td>{e((a.before or {}).get('final'))} → {e((a.after or {}).get('final'))}</td><td>{e(a.justification)}</td></tr>" for a in audit)
    totals = summary.totals
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reporte de calidad {e(batch.period)}</title><style>{CSS}</style></head><body>
<p class="muted">Timesheet Intake Gate · Reporte de calidad del lote</p>
<h1>Período {e(batch.period)}</h1>
<p class="{verdict[1]}"><b style="font-size:18px">{verdict[0]}</b></p>
<table><tr><th>Validado por</th><td>{e(batch.analyst_name)}</td><th>Fecha</th><td>{e(when(batch.created_at))}</td></tr>
<tr><th>Hash del contrato</th><td colspan="3"><code>{e(batch.contract_hash)}</code></td></tr>
<tr><th>Hallazgos abiertos</th><td colspan="3">{totals.BLOCKER} bloqueantes · {totals.ERROR} errores · {totals.WARNING} advertencias · procesado en {e(batch.processing_ms)} ms</td></tr></table>
<h2>Disposición por archivo</h2>{''.join(_file_section(d) for d in details)}
<h2>Overrides</h2>{('<table><thead><tr><th>Fecha</th><th>Archivo</th><th>Analista</th><th>Disposición</th><th>Justificación</th></tr></thead><tbody>' + override_rows + '</tbody></table>') if override_rows else '<p>No hubo overrides en este lote.</p>'}
<h2>Auditoría</h2>{('<table><thead><tr><th>Fecha</th><th>Analista</th><th>Acción</th><th>Disposición final</th><th>Justificación</th></tr></thead><tbody>' + audit_rows + '</tbody></table>') if audit_rows else '<p>No hubo acciones humanas registradas.</p>'}
<p class="muted" style="margin-top:32px">La disposición de cada archivo la calcula el código con las reglas del contrato y un humano aprueba lo consecuente.
Las secciones marcadas «IA – no vinculante» son apoyo para interpretar y no modifican ninguna decisión.</p>
</body></html>"""
