"""Qué se le envía a la IA: solo metadatos y muestras pequeñas, nunca el archivo completo (R11.3)."""
from backend.app.engine.ingest import Table
from backend.app.engine.models import Finding

MAX_SAMPLE = 5  # filas de muestra, o valores por columna, como máximo


def findings_payload(findings: list[Finding]) -> list[dict]:
    return [
        {"ref": f.ref, "code": f.code, "severity": f.severity, "column": f.column,
         "affected_count": f.affected_count, "evidence": f.evidence}
        for f in findings
    ]


def _header(filename: str, site: str | None, period: str, table: Table, required: list[str]) -> dict:
    return {"file": filename, "site": site, "period": period, "headers": table.headers, "required_columns": required}


def diagnosis_payload(filename, site, period, table: Table, required: list[str], findings: list[Finding]) -> dict:
    """Para la causa probable y el mensaje a la sede."""
    return {
        **_header(filename, site, period, table, required),
        "findings": findings_payload(findings),
        "sample_rows": table.records[:MAX_SAMPLE],
    }


def mapping_payload(filename, site, period, table: Table, required: list[str], findings: list[Finding]) -> dict:
    """Para sugerir equivalencias: columnas desconocidas con hasta 5 valores de muestra cada una."""
    missing = [f.column for f in findings if f.code == "D04" and f.status == "open"]
    unknown = []
    for finding in findings:
        if finding.code in ("D05", "D06") and finding.status == "open":
            values = [r.get(finding.column, "") for r in table.records if r.get(finding.column, "").strip()]
            unknown.append({
                "column": finding.column, "ref": finding.ref, "sample_values": values[:MAX_SAMPLE],
                "deterministic_candidate": finding.evidence.get("candidate"),
            })
    return {**_header(filename, site, period, table, required), "missing_required_columns": missing,
            "unknown_columns": unknown}
