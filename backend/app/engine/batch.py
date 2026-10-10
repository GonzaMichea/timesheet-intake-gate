"""Validación de un lote completo: nombres (D01–D03) y orquestación por archivo."""
import re

from backend.app.contract.loader import Contract, Master
from backend.app.engine.disposition import decide
from backend.app.engine.models import BatchResult, FileResult, Finding, InputFile
from backend.app.engine.validate import validate_file

BLOCKING = {"BLOCK", "QUARANTINE"}


def _finding(contract: Contract, filename: str, code: str, rule_id: str, evidence: dict) -> Finding:
    return Finding(
        file=filename,
        code=code,
        severity=contract.severities[code],
        rule_id=rule_id,
        rule_text=contract.rule_texts[rule_id],
        evidence=evidence,
    )


def _entry(kind, filename, site, findings, contract, row_count=0, headers=None, prefix="") -> FileResult:
    for number, finding in enumerate(findings, start=1):
        finding.ref = f"{prefix}-{number:03d}"
    return FileResult(
        kind=kind, filename=filename, site=site, row_count=row_count, headers=headers or [],
        findings=findings, disposition=decide(findings, row_count, contract),
    )


def validate_batch(period: str, files: list[InputFile], contract: Contract, master: Master,
                   mappings: dict[str, dict[str, str]] | None = None) -> BatchResult:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
        raise ValueError("El período debe tener formato YYYY-MM")
    mappings = mappings or {}
    yyyymm = period.replace("-", "")
    pattern = re.compile(contract.file_name_pattern)

    assigned: dict[str, tuple[InputFile, str]] = {}
    unexpected: list[tuple[InputFile, str, str]] = []
    for file in sorted(files, key=lambda f: f.name):
        match = pattern.match(file.name)
        if not match or match.group("site") not in contract.sites:
            unexpected.append((file, "D02.bad_name", "nombre fuera de patrón"))
        elif match.group("site") in assigned:
            unexpected.append((file, "D02.duplicate_site", "sede duplicada"))
        else:
            assigned[match.group("site")] = (file, match.group("yyyymm"))

    entries: list[FileResult] = []
    for site in contract.sites:
        expected_name = f"TS_{site}_{yyyymm}.csv|.xlsx"
        if site not in assigned:
            finding = _finding(contract, expected_name, "D01", "D01.missing_file",
                               {"found": "sin archivo", "expected": expected_name})
            entries.append(_entry("missing", None, site, [finding], contract, prefix=site))
            continue
        file, file_period = assigned[site]
        if file_period != yyyymm:
            finding = _finding(contract, file.name, "D03", "D03.period_mismatch",
                               {"found": file_period, "expected": yyyymm})
            entries.append(_entry("site_file", file.name, site, [finding], contract, prefix=site))
            continue
        findings, row_count, headers = validate_file(
            file.name, file.content, period, contract, master, mappings.get(file.name))
        entries.append(_entry("site_file", file.name, site, findings, contract, row_count, headers, site))

    for number, (file, rule_id, reason) in enumerate(unexpected, start=1):
        finding = _finding(contract, file.name, "D02", rule_id,
                           {"found": file.name, "expected": "TS_{SEDE}_{YYYYMM}.csv|.xlsx", "motivo": reason})
        entries.append(_entry("unexpected", file.name, None, [finding], contract, prefix=f"EXT{number}"))

    ready = all(e.disposition.value not in BLOCKING for e in entries)
    return BatchResult(period=period, entries=entries, ready_for_load=ready)
