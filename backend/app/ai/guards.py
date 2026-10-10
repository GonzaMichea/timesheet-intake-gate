"""Controles en código sobre lo que dice la IA: nada llega al analista sin pasar por aquí (R11.5–R11.7)."""
import re

from backend.app.ai.models import CauseOut, MappingOut, RemediationOut

REF_PATTERN = re.compile(r"\b[A-Z]{2,4}\d?-\d{3}\b")


class InvalidAiOutput(Exception):
    """La respuesta cita hallazgos que no existen; se descarta completa."""


def _unknown_refs(refs: list[str], text: str, valid: set[str]) -> set[str]:
    """Códigos de hallazgo citados que no existen, ya sea en la lista de referencias o escritos en el texto."""
    return (set(refs) | set(REF_PATTERN.findall(text))) - valid


def guard_mapping(output: MappingOut, unknown: set[str], missing: set[str], min_conf: float) -> dict:
    kept, discarded = [], 0
    for s in output.suggestions:
        # Se descartan destinos que no son columnas requeridas faltantes, o columnas que no existen en el archivo (R11.7)
        if s.source_column not in unknown or s.target_column not in missing:
            discarded += 1
            continue
        kept.append({**s.model_dump(), "needs_review": s.confidence < min_conf})
    return {"suggestions": kept, "discarded": discarded}


def guard_cause(output: CauseOut, valid: set[str], min_conf: float) -> dict:
    statements, discarded = [], 0
    for s in output.statements:
        if _unknown_refs(s.finding_refs, s.text, valid):
            discarded += 1  # cita un hallazgo inexistente: se descarta la afirmación (R11.5)
            continue
        statements.append({**s.model_dump(), "needs_review": s.confidence < min_conf,
                           "unsupported": len(s.finding_refs) == 0})
    if output.statements and not statements:
        raise InvalidAiOutput("Todas las afirmaciones de la IA citaban hallazgos inexistentes.")
    return {"statements": statements, "discarded": discarded}


def guard_remediation(output: RemediationOut, valid: set[str], min_conf: float) -> dict:
    if _unknown_refs(output.finding_refs, f"{output.subject} {output.body}", valid):
        raise InvalidAiOutput("El borrador de la IA citaba hallazgos inexistentes.")
    return {**output.model_dump(), "needs_review": output.confidence < min_conf,
            "unsupported": len(output.finding_refs) == 0}
