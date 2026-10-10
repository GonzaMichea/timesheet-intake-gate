"""Contratos de respuesta de la API. Se reflejan a mano en src/types/api.ts."""
from typing import Any

from pydantic import BaseModel


class FindingOut(BaseModel):
    id: str
    ref: str
    code: str
    code_description: str
    severity: str
    column: str | None
    rule_id: str
    rule_text: str
    affected_count: int
    affected_rows: list[int]
    sample_rows: list[dict[str, Any]]
    evidence: dict[str, Any]
    status: str


class OverrideOut(BaseModel):
    id: str
    disposition: str | None
    justification: str
    actor: str
    created_at: str
    computed_disposition: str | None


class MappingReviewOut(BaseModel):
    id: str
    file_id: str
    filename: str | None
    site: str | None
    source_column: str
    candidate_column: str | None
    candidate_score: float | None
    status: str
    chosen_column: str | None
    decided_by: str | None
    decided_at: str | None


class SeverityCounts(BaseModel):
    BLOCKER: int = 0
    ERROR: int = 0
    WARNING: int = 0


class DefectBrief(BaseModel):
    """Un código de defecto abierto en el archivo, resumido para explicar la disposición."""
    code: str
    description: str
    severity: str
    columns: list[str]
    rows: int
    found: str | None
    expected: str | None


class FileSummary(BaseModel):
    id: str
    batch_id: str
    kind: str
    filename: str | None
    site: str | None
    row_count: int
    computed_disposition: str
    final_disposition: str
    disposition_rule: str | None
    disposition_explanation: str | None
    override_active: bool
    permissive_override: bool
    calculated_changed_after_override: bool
    counts: SeverityCounts
    defects: list[DefectBrief]
    ribbon: str  # un carácter por fila: "." sin hallazgos, W advertencia, E error, B bloqueante


class FileDetail(FileSummary):
    period: str
    findings: list[FindingOut]
    mappings: list[MappingReviewOut]
    overrides: list[OverrideOut]
    missing_columns: list[str]
    required_columns: list[str]
    ai: dict[str, Any] = {}


class BatchListItem(BaseModel):
    id: str
    period: str
    analyst_name: str
    created_at: str
    ready_for_load: bool
    file_count: int


class BatchSummary(BaseModel):
    id: str
    period: str
    analyst_name: str
    created_at: str
    processing_ms: int | None
    contract_hash: str
    ready_for_load: bool
    totals: SeverityCounts
    entries: list[FileSummary]


class ReviewQueue(BaseModel):
    pending: list[MappingReviewOut]
    files: list[FileSummary]


class AuditOut(BaseModel):
    id: str
    created_at: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    justification: str | None


class AcceptMapping(BaseModel):
    actor: str
    target_column: str


class Actor(BaseModel):
    actor: str


class OverrideIn(BaseModel):
    actor: str
    disposition: str
    justification: str


class WithdrawIn(BaseModel):
    actor: str
    justification: str
