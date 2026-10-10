"""Formato de las respuestas de la IA: modelos pydantic (validación) y esquemas JSON (salida estructurada)."""
from pydantic import BaseModel, Field


class MappingSuggestion(BaseModel):
    source_column: str
    target_column: str | None
    confidence: float = Field(ge=0, le=1)
    justification: str


class MappingOut(BaseModel):
    suggestions: list[MappingSuggestion]


class Statement(BaseModel):
    text: str
    finding_refs: list[str]
    confidence: float = Field(ge=0, le=1)


class CauseOut(BaseModel):
    statements: list[Statement]


class RemediationOut(BaseModel):
    subject: str
    body: str
    finding_refs: list[str]
    confidence: float = Field(ge=0, le=1)


_STRING = {"type": "string"}
_REFS = {"type": "array", "items": _STRING}
_NUMBER = {"type": "number"}


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


# Los rangos (0 a 1) no van en el esquema JSON: los valida pydantic después de recibir la respuesta
SCHEMAS = {
    "mapping": _object({"suggestions": {"type": "array", "items": _object({
        "source_column": _STRING,
        "target_column": {"anyOf": [_STRING, {"type": "null"}]},
        "confidence": _NUMBER,
        "justification": _STRING,
    })}}),
    "cause": _object({"statements": {"type": "array", "items": _object({
        "text": _STRING, "finding_refs": _REFS, "confidence": _NUMBER,
    })}}),
    "remediation": _object({
        "subject": _STRING, "body": _STRING, "finding_refs": _REFS, "confidence": _NUMBER,
    }),
}

MODELS = {"mapping": MappingOut, "cause": CauseOut, "remediation": RemediationOut}
