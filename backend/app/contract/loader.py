import csv
import hashlib
import io
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator

Severity = Literal["BLOCKER", "ERROR", "WARNING"]
DispositionValue = Literal["LOAD", "LOAD_WITH_WARNINGS", "QUARANTINE", "BLOCK"]
CODES = [f"D{i:02d}" for i in range(1, 13)]


class ContractError(Exception):
    """El contrato o el maestro no cumplen su esquema (R1.3)."""


class ColumnSpec(BaseModel):
    type: Literal["str", "date", "decimal", "catalog"]
    pattern: str | None = None
    min: float | None = None
    max: float | None = None
    nullable: bool = False
    catalog: str | None = None
    d07_severity: Severity = "ERROR"
    approval: bool = False

    @field_validator("pattern")
    @classmethod
    def pattern_compiles(cls, value):
        if value is not None:
            re.compile(value)
        return value


class Thresholds(BaseModel):
    max_null_pct: float
    max_daily_total: float
    quarantine_error_row_pct: float
    d05_min_score: float
    ai_min_confidence: float
    ai_timeout_s: int
    max_upload_mb: float


class DispositionWhen(BaseModel):
    severity: Severity | None = None
    min_open: int | None = None
    row_pct_gt: str | None = None  # nombre de un umbral
    any_open: bool = False
    always: bool = False


class DispositionRule(BaseModel):
    id: str
    disposition: DispositionValue
    when: DispositionWhen


class Contract(BaseModel):
    version: int
    sites: list[str]
    file_name_pattern: str
    date_formats: list[str]
    columns: dict[str, ColumnSpec]
    catalogs: dict[str, list[str]]
    aliases: dict[str, list[str]] = {}
    thresholds: Thresholds
    severities: dict[str, Severity]
    file_level_full_impact: list[str] = []
    disposition_rules: list[DispositionRule]
    code_descriptions: dict[str, str]
    rule_texts: dict[str, str]

    @field_validator("file_name_pattern")
    @classmethod
    def name_pattern_valid(cls, value):
        compiled = re.compile(value)
        if not {"site", "yyyymm"} <= set(compiled.groupindex):
            raise ValueError("debe tener los grupos nombrados 'site' y 'yyyymm'")
        return value

    @model_validator(mode="after")
    def cross_checks(self):
        for name, spec in self.columns.items():
            if spec.type == "catalog" and spec.catalog not in self.catalogs:
                raise ValueError(f"columns.{name}: el catálogo '{spec.catalog}' no existe")
        missing = [c for c in CODES if c not in self.severities]
        if missing:
            raise ValueError(f"severities: faltan los códigos {missing}")
        for rule in self.disposition_rules:
            key = rule.when.row_pct_gt
            if key is not None and not hasattr(self.thresholds, key):
                raise ValueError(f"disposition_rules.{rule.id}: umbral '{key}' no existe")
        return self


class Employee(BaseModel):
    site: str
    active: bool


class Master(BaseModel):
    employees: dict[str, Employee]


def _format_errors(error: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors())


def parse_contract(text: str) -> Contract:
    try:
        return Contract.model_validate(yaml.safe_load(text))
    except (ValidationError, yaml.YAMLError, re.error) as error:
        detail = _format_errors(error) if isinstance(error, ValidationError) else str(error)
        raise ContractError(f"Contrato inválido: {detail}") from error


def parse_master(text: str) -> Master:
    employees: dict[str, Employee] = {}
    reader = csv.DictReader(io.StringIO(text))
    if set(reader.fieldnames or []) != {"employee_id", "site", "active"}:
        raise ContractError("Maestro inválido: columnas esperadas employee_id, site, active")
    for line, row in enumerate(reader, start=2):
        active = row["active"].strip().lower()
        if active not in {"true", "false", "1", "0", "si", "no"}:
            raise ContractError(f"Maestro inválido: fila {line}, campo active='{row['active']}'")
        employees[row["employee_id"].strip()] = Employee(
            site=row["site"].strip(), active=active in {"true", "1", "si"}
        )
    return Master(employees=employees)


def contract_hash(contract_text: str, master_text: str) -> str:
    return hashlib.sha256((contract_text + "\n--\n" + master_text).encode("utf-8")).hexdigest()


def load_contract(path: str | Path) -> Contract:
    return parse_contract(Path(path).read_text(encoding="utf-8"))


def load_master(path: str | Path) -> Master:
    return parse_master(Path(path).read_text(encoding="utf-8"))
