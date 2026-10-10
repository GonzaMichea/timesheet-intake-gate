"""Única puerta hacia la API de Anthropic. Si algo falla, lanza AiUnavailable con un motivo en español."""
import json
import os
import re
import time
from dataclasses import dataclass


class AiUnavailable(Exception):
    """La IA no se pudo usar. El mensaje es corto y apto para mostrar al analista (sin trazas)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Completion:
    text: str
    model: str
    latency_ms: int


# Los modelos de la familia 5 aceptan `effort`; con "low" la respuesta es rápida y barata para esta tarea
_EFFORT_MODELS = re.compile(r"^claude-(fable|opus|sonnet|haiku)-5")


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def complete(system: str, user: str, schema: dict, timeout_s: float, max_tokens: int = 2048) -> Completion:
    """Pide una respuesta JSON que cumpla `schema` (salida estructurada, sin tool_choice forzado)."""
    # Se exige la variable explícita: el SDK también leería credenciales guardadas del equipo (R12.1)
    if not is_configured():
        raise AiUnavailable("No hay una clave de IA configurada (ANTHROPIC_API_KEY).")
    model = os.environ.get("LLM_MODEL", "").strip()
    if not model:
        raise AiUnavailable("No se configuró el modelo de IA (LLM_MODEL).")

    import anthropic  # se importa aquí para que el resto de la app funcione aunque falte el paquete

    config: dict = {"format": {"type": "json_schema", "schema": schema}}
    if _EFFORT_MODELS.match(model):
        config["effort"] = "low"
    client = anthropic.Anthropic(timeout=timeout_s, max_retries=0)
    started = time.perf_counter()
    try:
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], output_config=config,
        )
    except anthropic.APITimeoutError as error:
        raise AiUnavailable(f"La IA tardó más de {timeout_s:g} segundos en responder.") from error
    except anthropic.RateLimitError as error:
        raise AiUnavailable("La IA está recibiendo demasiadas solicitudes. Inténtalo en un minuto.") from error
    except anthropic.AuthenticationError as error:
        raise AiUnavailable("La clave de IA no es válida.") from error
    except anthropic.APIConnectionError as error:
        raise AiUnavailable("No se pudo conectar con el servicio de IA.") from error
    except anthropic.APIStatusError as error:
        raise AiUnavailable(f"El servicio de IA respondió con un error ({error.status_code}).") from error

    if response.stop_reason == "refusal":
        raise AiUnavailable("La IA declinó responder a esta solicitud.")
    text = next((block.text for block in response.content if block.type == "text"), "")
    return Completion(text=text, model=response.model, latency_ms=round((time.perf_counter() - started) * 1000))


def parse_json(text: str) -> dict:
    """JSON de la respuesta; ValueError si no es un objeto JSON válido."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("la respuesta no es un objeto JSON")
    return data
