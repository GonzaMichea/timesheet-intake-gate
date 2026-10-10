from typing import Any, Literal

from pydantic import BaseModel

Severity = Literal["BLOCKER", "ERROR", "WARNING"]
DispositionValue = Literal["LOAD", "LOAD_WITH_WARNINGS", "QUARANTINE", "BLOCK"]


class InputFile(BaseModel):
    name: str
    content: bytes


class Finding(BaseModel):
    ref: str = ""
    file: str
    code: str
    severity: Severity
    column: str | None = None
    rule_id: str
    rule_text: str
    affected_count: int = 0
    affected_rows: list[int] = []
    sample_rows: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}
    status: Literal["open", "resolved_by_mapping"] = "open"


class Disposition(BaseModel):
    value: DispositionValue
    rule_id: str
    explanation: str


class FileResult(BaseModel):
    kind: Literal["site_file", "unexpected", "missing"]
    filename: str | None
    site: str | None
    row_count: int = 0
    headers: list[str] = []
    findings: list[Finding] = []
    disposition: Disposition


class BatchResult(BaseModel):
    period: str
    entries: list[FileResult]
    ready_for_load: bool
