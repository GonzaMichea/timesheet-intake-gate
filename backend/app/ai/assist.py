"""Asistencia de IA para un archivo. Solo lee hallazgos ya calculados: nunca los cambia (R7.4)."""
import json
from dataclasses import dataclass

from pydantic import ValidationError

from backend.app.ai import client, guards, payload
from backend.app.ai.models import MODELS, SCHEMAS
from backend.app.contract.loader import Contract, Master
from backend.app.engine.batch import assign_refs
from backend.app.engine.ingest import IngestError, read_table
from backend.app.engine.validate import validate_file

KINDS = ("mapping", "cause", "remediation")

SYSTEM = {
    "mapping": (
        "Eres un asistente que revisa hojas de tiempo mensuales que alimentan la nómina de una empresa. "
        "Para cada columna desconocida del archivo, decide si equivale a una de las columnas requeridas que faltan. "
        "Usa solo los encabezados, las columnas requeridas y los valores de muestra entregados. "
        "Si ninguna columna requerida corresponde, responde target_column null. "
        "La confianza (0 a 1) debe ser honesta: usa menos de 0,7 si dudas. "
        "Justifica en una frase breve, en español, citando los valores que viste."
    ),
    "cause": (
        "Eres un asistente que revisa hojas de tiempo mensuales de una empresa. Explica en español, con frases breves y "
        "sin jerga técnica, qué pudo haber pasado en la sede para que el archivo tenga estos hallazgos. "
        "Cada afirmación debe citar en finding_refs los códigos de hallazgo (por ejemplo SCL-001) que la respaldan, "
        "y solo puedes usar códigos que aparezcan en la lista entregada. "
        "Si una afirmación no se apoya en ningún hallazgo, deja finding_refs vacío. "
        "No decidas si el archivo se carga o no: eso lo decide el sistema. Confianza de 0 a 1, honesta."
    ),
    "remediation": (
        "Eres un asistente que redacta mensajes para el responsable de una sede, en español, con tono cordial y claro. "
        "El mensaje pide corregir y reenviar el archivo de horas del mes e incluye los hallazgos concretos: "
        "código del hallazgo, columna, filas y valores encontrados frente a los esperados. "
        "Solo puedes mencionar códigos de hallazgo de la lista entregada y debes listarlos en finding_refs. "
        "No prometas plazos ni decidas si el archivo se carga. Confianza de 0 a 1, honesta."
    ),
}
MAX_TOKENS = {"mapping": 2048, "cause": 2048, "remediation": 3072}


@dataclass
class AiOutcome:
    status: str  # ok | no_disponible | invalido
    model: str | None = None
    latency_ms: int | None = None
    payload: dict | None = None
    reason: str | None = None


def _unavailable(reason: str) -> AiOutcome:
    return AiOutcome(status="no_disponible", reason=reason)


def run(kind: str, filename: str, site: str | None, content: bytes, period: str, contract: Contract,
        master: Master, mapping: dict[str, str]) -> AiOutcome:
    """Genera la asistencia de un tipo para un archivo; cualquier problema termina en un estado, no en una excepción."""
    findings, _, _ = validate_file(filename, content, period, contract, master, mapping)
    assign_refs(findings, site or "EXT")
    open_findings = [f for f in findings if f.status == "open"]
    try:
        table = read_table(filename, content)
    except IngestError:
        return _unavailable("El archivo no se pudo leer, no hay datos que enviar a la IA.")

    required = list(contract.columns)
    if kind == "mapping":
        missing = {f.column for f in open_findings if f.code == "D04"}
        unknown = {f.column for f in open_findings if f.code in ("D05", "D06")}
        if not unknown:
            return _unavailable("No hay columnas desconocidas por sugerir.")
        if not missing:
            return _unavailable("Ya no faltan columnas requeridas en este archivo.")
        data = payload.mapping_payload(filename, site, period, table, required, findings)
    else:
        if not open_findings:
            return _unavailable("El archivo no tiene hallazgos abiertos.")
        data = payload.diagnosis_payload(filename, site, period, table, required, open_findings)

    try:
        completion = client.complete(
            SYSTEM[kind], json.dumps(data, ensure_ascii=False), SCHEMAS[kind],
            timeout_s=contract.thresholds.ai_timeout_s, max_tokens=MAX_TOKENS[kind])
    except client.AiUnavailable as error:
        return _unavailable(error.reason)

    meta = {"model": completion.model, "latency_ms": completion.latency_ms}
    min_conf = contract.thresholds.ai_min_confidence
    try:
        output = MODELS[kind].model_validate(client.parse_json(completion.text))
        if kind == "mapping":
            result = guards.guard_mapping(output, unknown, missing, min_conf)
        elif kind == "cause":
            result = guards.guard_cause(output, {f.ref for f in open_findings}, min_conf)
        else:
            result = guards.guard_remediation(output, {f.ref for f in open_findings}, min_conf)
    except (ValueError, ValidationError):
        return AiOutcome(status="invalido", reason="La respuesta de la IA no tenía el formato esperado.", **meta)
    except guards.InvalidAiOutput as error:
        return AiOutcome(status="invalido", reason=str(error), **meta)
    return AiOutcome(status="ok", payload=result, **meta)
