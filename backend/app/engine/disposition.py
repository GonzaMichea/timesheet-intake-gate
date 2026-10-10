"""Disposición por archivo: 100 % determinística, con reglas del contrato (R7)."""
from backend.app.contract.loader import Contract
from backend.app.engine.models import Disposition, Finding


def _pct_text(value: float) -> str:
    return f"{value * 100:.1f}".replace(".", ",")


def _error_row_pct(open_findings: list[Finding], row_count: int, contract: Contract) -> float:
    errors = [f for f in open_findings if f.severity == "ERROR"]
    if any(f.code in contract.file_level_full_impact for f in errors):
        return 1.0
    rows = {r for f in errors for r in f.affected_rows}
    if not rows:
        return 1.0 if errors else 0.0
    return len(rows) / row_count if row_count else 1.0


def decide(findings: list[Finding], row_count: int, contract: Contract) -> Disposition:
    open_findings = [f for f in findings if f.status == "open"]
    for rule in contract.disposition_rules:
        when = rule.when
        if when.always:
            return Disposition(value=rule.disposition, rule_id=rule.id, explanation="Sin hallazgos")
        if when.any_open and open_findings:
            return Disposition(
                value=rule.disposition,
                rule_id=rule.id,
                explanation=f"{len(open_findings)} hallazgo(s) abierto(s), sin superar el umbral de cuarentena",
            )
        if when.severity and when.min_open:
            count = sum(1 for f in open_findings if f.severity == when.severity)
            if count >= when.min_open:
                return Disposition(
                    value=rule.disposition,
                    rule_id=rule.id,
                    explanation=f"{count} hallazgo(s) {when.severity} abierto(s)",
                )
        if when.severity and when.row_pct_gt:
            threshold = getattr(contract.thresholds, when.row_pct_gt)
            pct = _error_row_pct(open_findings, row_count, contract)
            has_errors = any(f.severity == when.severity for f in open_findings)
            # Se compara con tolerancia para que exactamente el umbral no cuente como "mayor"
            if has_errors and round(pct - threshold, 9) > 0:
                return Disposition(
                    value=rule.disposition,
                    rule_id=rule.id,
                    explanation=f"{_pct_text(pct)} % de filas con {when.severity} > {_pct_text(threshold)} %",
                )
    raise ValueError("Las reglas de disposición del contrato no cubren todos los casos")
