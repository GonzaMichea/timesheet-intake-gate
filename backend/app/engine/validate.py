"""Validación del contenido de un archivo de sede: D04–D12. Funciones puras."""
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher

from backend.app.contract.loader import Contract, Master
from backend.app.engine.ingest import IngestError, Table, read_table
from backend.app.engine.models import Finding

SAMPLE_SIZE = 5
PROFILE_SIZE = 50


def norm_header(header: str) -> str:
    return header.strip().lower()


def norm_key(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", plain.lower())


def parse_decimal(value: str) -> Decimal | None:
    if re.fullmatch(r"-?\d+([.,]\d+)?", value):
        return Decimal(value.replace(",", "."))
    return None


def parse_date(value: str, formats: list[str]) -> date | None:
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _type_ok(spec, value: str, contract: Contract) -> bool:
    if spec.type == "decimal":
        return parse_decimal(value) is not None
    if spec.type == "date":
        return parse_date(value, contract.date_formats) is not None
    if spec.type == "str" and spec.pattern:
        return re.fullmatch(spec.pattern, value) is not None
    return True


def _equivalence_score(unknown: str, required: str, values: list[str], contract: Contract) -> float:
    """Puntaje 0–1: alias del contrato, similitud del nombre y perfil de valores (R4.3)."""
    aliases = {norm_key(a) for a in contract.aliases.get(required, [])}
    if norm_key(unknown) in aliases:
        return 1.0
    name_sim = SequenceMatcher(None, norm_key(unknown), norm_key(required)).ratio()
    sample = [v for v in values if v][:PROFILE_SIZE]
    spec = contract.columns[required]
    fit = sum(_type_ok(spec, v, contract) for v in sample) / len(sample) if sample else 0.0
    return round(0.6 * name_sim + 0.4 * fit, 3)


class _Collector:
    def __init__(self, filename: str, table: Table | None, contract: Contract):
        self.filename = filename
        self.contract = contract
        self.findings: list[Finding] = []
        self.rows = dict(zip(table.row_nums, table.records)) if table else {}

    def add(self, code, rule_id, column=None, rows=(), evidence=None, severity=None, status="open"):
        rows = sorted(rows)
        self.findings.append(
            Finding(
                file=self.filename,
                code=code,
                severity=severity or self.contract.severities[code],
                column=column,
                rule_id=rule_id,
                rule_text=self.contract.rule_texts.get(rule_id, self.contract.code_descriptions[code]),
                affected_count=len(rows),
                affected_rows=rows,
                sample_rows=[{"row": r, **self.rows[r]} for r in rows[:SAMPLE_SIZE]],
                evidence=evidence or {},
                status=status,
            )
        )


def _structure(table: Table, contract: Contract, mapping: dict[str, str], out: _Collector):
    """D04, D05, D06. Devuelve required -> encabezado real."""
    header_for: dict[str, str] = {}
    applied: list[tuple[str, str]] = []
    for header in table.headers:
        name = norm_header(header)
        if name in contract.columns and name not in header_for:
            header_for[name] = header
    mapping_n = {norm_header(k): v for k, v in mapping.items()}
    unknown: list[str] = []
    for header in table.headers:
        if header in header_for.values():
            continue
        target = mapping_n.get(norm_header(header))
        if target in contract.columns and target not in header_for:
            header_for[target] = header
            applied.append((header, target))
        else:
            unknown.append(header)

    missing = [c for c in contract.columns if c not in header_for]
    pairs = []
    for header in unknown:
        values = [r.get(header, "").strip() for r in table.records]
        for required in missing:
            pairs.append((_equivalence_score(header, required, values, contract), header, required))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))
    candidates: dict[str, tuple[str, float]] = {}
    for score, header, required in pairs:
        if score < contract.thresholds.d05_min_score:
            break
        if header in candidates or required in {c for c, _ in candidates.values()}:
            continue
        candidates[header] = (required, score)

    for column in missing:
        out.add("D04", "D04.missing_column", column, evidence={"found": "ausente", "expected": column})
    for header, target in applied:
        out.add("D05", "D05.renamed_column", header, status="resolved_by_mapping",
                evidence={"found": header, "expected": target, "mapped": True})
    for header in unknown:
        if header in candidates:
            required, score = candidates[header]
            out.add("D05", "D05.renamed_column", header,
                    evidence={"found": header, "expected": required, "candidate": required, "score": score})
        else:
            out.add("D06", "D06.extra_column", header,
                    evidence={"found": header, "expected": "columna no especificada en el contrato"})
    return header_for


def _bad_sample(values: dict[int, str], rows) -> list[str]:
    return [values[r] if values[r] else "(vacío)" for r in sorted(rows)[:3]]


def _content(table: Table, header_for: dict[str, str], period: str, contract: Contract,
             master: Master, out: _Collector):
    thresholds = contract.thresholds
    raw = {c: {rn: rec.get(h, "").strip() for rn, rec in zip(table.row_nums, table.records)}
           for c, h in header_for.items()}
    total = len(table.row_nums)
    invalid: dict[str, set[int]] = {c: set() for c in raw}

    # D07: tipo inválido o nulo en columna no nullable (R5.1–R5.3)
    for column, values in raw.items():
        spec = contract.columns[column]
        bad, nulls = [], 0
        for rn, value in values.items():
            if value == "":
                if spec.approval or spec.nullable:
                    continue
                nulls += 1
                bad.append(rn)
            elif not _type_ok(spec, value, contract):
                bad.append(rn)
        invalid[column] = set(bad)
        if bad:
            severity = spec.d07_severity
            if total and nulls / total > thresholds.max_null_pct:
                severity = "BLOCKER"
            out.add("D07", "D07.invalid_type", column, bad, severity=severity,
                    evidence={"found": _bad_sample(values, bad), "expected": f"tipo {spec.type}"})

    good = {c: {rn: v for rn, v in vals.items() if v and rn not in invalid[c]} for c, vals in raw.items()}

    if "employee_id" in good and "work_date" in good:  # D08
        seen: dict[tuple, int] = {}
        dups: dict[int, int] = {}
        for rn in table.row_nums:
            if rn in good["employee_id"] and rn in good["work_date"]:
                key = (good["employee_id"][rn], parse_date(good["work_date"][rn], contract.date_formats))
                if key in seen:
                    dups[rn] = seen[key]
                else:
                    seen[key] = rn
        if dups:
            out.add("D08", "D08.duplicate_key", None, dups,
                    evidence={"found": f"{len(dups)} fila(s) repetida(s)",
                              "expected": "una fila por empleado y fecha",
                              "first_occurrence": {str(r): f for r, f in list(dups.items())[:5]}})

    if "work_date" in good:  # D09
        outside = [rn for rn, v in good["work_date"].items()
                   if parse_date(v, contract.date_formats).strftime("%Y-%m") != period]
        if outside:
            out.add("D09", "D09.date_out_of_period", "work_date", outside,
                    evidence={"found": _bad_sample(good["work_date"], outside), "expected": f"fechas dentro de {period}"})

    ranges = {"regular_hours": "D10.regular_range", "overtime_hours": "D10.overtime_range"}
    for column, rule in ranges.items():  # D10: rangos
        if column in good:
            spec = contract.columns[column]
            lo, hi = Decimal(str(spec.min)), Decimal(str(spec.max))
            out_of_range = [rn for rn, v in good[column].items() if not lo <= parse_decimal(v) <= hi]
            if out_of_range:
                out.add("D10", rule, column, out_of_range,
                        evidence={"found": _bad_sample(good[column], out_of_range), "expected": f"entre {lo} y {hi}"})
    if "regular_hours" in good and "overtime_hours" in good:  # D10: total diario
        limit = Decimal(str(thresholds.max_daily_total))
        over = [rn for rn in good["regular_hours"]
                if rn in good["overtime_hours"]
                and parse_decimal(good["regular_hours"][rn]) + parse_decimal(good["overtime_hours"][rn]) > limit]
        if over:
            totals = [str(parse_decimal(good["regular_hours"][r]) + parse_decimal(good["overtime_hours"][r]))
                      for r in over[:3]]
            out.add("D10", "D10.daily_total", None, over,
                    evidence={"found": totals, "expected": f"total diario ≤ {limit}"})

    for column in ("shift_code", "absence_code"):  # D11
        if column in good:
            catalog = contract.catalogs[contract.columns[column].catalog]
            unknown = [rn for rn, v in good[column].items() if v not in catalog]
            if unknown:
                out.add("D11", "D11.unknown_catalog", column, unknown,
                        evidence={"found": _bad_sample(good[column], unknown), "expected": catalog})

    if "employee_id" in good:  # D12: maestro
        absent = [rn for rn, v in good["employee_id"].items() if v not in master.employees]
        inactive = [rn for rn, v in good["employee_id"].items()
                    if v in master.employees and not master.employees[v].active]
        if absent:
            out.add("D12", "D12.unknown_employee", "employee_id", absent,
                    evidence={"found": _bad_sample(good["employee_id"], absent), "expected": "empleado en el maestro"})
        if inactive:
            out.add("D12", "D12.inactive_employee", "employee_id", inactive,
                    evidence={"found": _bad_sample(good["employee_id"], inactive), "expected": "empleado activo"})
    for column, spec in contract.columns.items():  # D12: aprobación
        if spec.approval and column in raw:
            empty = [rn for rn, v in raw[column].items() if v == ""]
            if empty:
                severity = "BLOCKER" if total and len(empty) / total > thresholds.max_null_pct else None
                out.add("D12", "D12.missing_approval", column, empty, severity=severity,
                        evidence={"found": "(vacío)", "expected": "valor de aprobación"})


def validate_file(name: str, content: bytes, period: str, contract: Contract, master: Master,
                  mapping: dict[str, str] | None = None) -> tuple[list[Finding], int, list[str]]:
    """Devuelve (hallazgos, cantidad de filas, encabezados)."""
    try:
        table = read_table(name, content)
    except IngestError:
        out = _Collector(name, None, contract)
        for column in contract.columns:
            out.add("D04", "D04.missing_column", column,
                    evidence={"found": "archivo ilegible o sin encabezados", "expected": column})
        return _sorted(out.findings), 0, []
    out = _Collector(name, table, contract)
    header_for = _structure(table, contract, mapping or {}, out)
    _content(table, header_for, period, contract, master, out)
    return _sorted(out.findings), len(table.row_nums), table.headers


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (f.code, f.column or "", f.affected_rows[0] if f.affected_rows else 0, f.rule_id))
