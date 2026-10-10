"""La IA apoya, nunca decide: controles, fallos y funcionamiento sin IA (R11, R12, R16.3–R16.5)."""
import json

import pytest

from backend.app.ai import assist, client
from backend.app.engine.ingest import read_table
from backend.tests.helpers import CONTRACT, MASTER, ROOT
from backend.tests.test_api import create_old, pending, scl

OLD = ROOT / "datasets" / "batch_01_old_template"
SCL_FILE = "TS_SCL_202609.csv"


def fake(monkeypatch, response=None, error=None):
    """Reemplaza la llamada a Anthropic. `response` es un dict (se serializa) o un texto; guarda lo recibido."""
    seen = {}

    def complete(system, user, schema, timeout_s, max_tokens=2048):
        seen.update(system=system, user=user, schema=schema)
        if error:
            raise error
        text = response if isinstance(response, str) else json.dumps(response)
        return client.Completion(text=text, model="modelo-simulado", latency_ms=12)

    monkeypatch.setattr(client, "complete", complete)
    return seen


def run_ai(kind, mapping=None):
    return assist.run(kind, SCL_FILE, "SCL", (OLD / SCL_FILE).read_bytes(), "2026-09", CONTRACT, MASTER, mapping or {})


def good_mapping():
    return {"suggestions": [
        {"source_column": "Horas Extra", "target_column": "overtime_hours", "confidence": 0.95, "justification": "valores 0, 1, 2"},
        {"source_column": "Notas", "target_column": None, "confidence": 0.9, "justification": "texto libre"},
        {"source_column": "Centro Costo", "target_column": "cost_center", "confidence": 0.5, "justification": "parece"},
    ]}


def test_without_api_key_ai_is_unavailable_and_nothing_is_called(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(client.AiUnavailable, match="clave"):
        client.complete("s", "u", {}, 5)
    outcome = run_ai("cause")
    assert outcome.status == "no_disponible" and "clave" in outcome.reason and outcome.payload is None


def test_missing_model_is_unavailable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(client.AiUnavailable, match="LLM_MODEL"):
        client.complete("s", "u", {}, 5)


def test_api_failure_and_invalid_json_degrade_gracefully(monkeypatch):
    fake(monkeypatch, error=client.AiUnavailable("La IA tardó más de 30 segundos en responder."))
    assert run_ai("cause").status == "no_disponible"
    for bad in ["esto no es json", "[1, 2]", json.dumps({"statements": "no es una lista"}),
                json.dumps({"statements": [{"text": "x", "finding_refs": [], "confidence": 7}]})]:
        fake(monkeypatch, response=bad)
        outcome = run_ai("cause")
        assert outcome.status == "invalido" and outcome.payload is None


def test_payload_sends_only_small_samples_never_the_whole_file(monkeypatch):
    seen = fake(monkeypatch, response=good_mapping())
    run_ai("mapping")
    sent = json.loads(seen["user"])
    total_rows = len(read_table(SCL_FILE, (OLD / SCL_FILE).read_bytes()).records)
    assert total_rows > 200 and len(seen["user"]) < 8000  # el archivo tiene cientos de filas; no viajan
    assert all(len(c["sample_values"]) <= 5 for c in sent["unknown_columns"])
    seen = fake(monkeypatch, response={"statements": []})
    run_ai("cause")
    assert len(json.loads(seen["user"])["sample_rows"]) <= 5


def test_mapping_guards_discard_invalid_targets_and_flag_low_confidence(monkeypatch):
    fake(monkeypatch, response=good_mapping())
    outcome = run_ai("mapping")
    kept = {s["source_column"]: s for s in outcome.payload["suggestions"]}
    assert outcome.status == "ok" and set(kept) == {"Horas Extra", "Centro Costo"}  # "ninguna" se descarta (R11.7)
    assert outcome.payload["discarded"] == 1
    assert kept["Horas Extra"]["needs_review"] is False and kept["Centro Costo"]["needs_review"] is True
    fake(monkeypatch, response={"suggestions": [
        {"source_column": "Horas Extra", "target_column": "work_date", "confidence": 0.99, "justification": "x"},
        {"source_column": "Inventada", "target_column": "overtime_hours", "confidence": 0.99, "justification": "x"}]})
    assert run_ai("mapping").payload["suggestions"] == []  # destino que ya existe y columna inexistente


def test_cause_guards_drop_nonexistent_refs_and_flag_unsupported(monkeypatch):
    fake(monkeypatch, response={"statements": [
        {"text": "Usaron una plantilla antigua.", "finding_refs": ["SCL-003"], "confidence": 0.9},
        {"text": "Falló una macro (ver SCL-099).", "finding_refs": ["SCL-001"], "confidence": 0.9},
        {"text": "Quizás cambió el sistema.", "finding_refs": [], "confidence": 0.4},
        {"text": "Otra cosa.", "finding_refs": ["SCL-500"], "confidence": 0.9}]})
    outcome = run_ai("cause")
    texts = {s["text"]: s for s in outcome.payload["statements"]}
    assert outcome.status == "ok" and set(texts) == {"Usaron una plantilla antigua.", "Quizás cambió el sistema."}
    assert outcome.payload["discarded"] == 2
    assert texts["Quizás cambió el sistema."]["unsupported"] and texts["Quizás cambió el sistema."]["needs_review"]
    assert not texts["Usaron una plantilla antigua."]["unsupported"]


def test_remediation_with_unknown_refs_is_rejected(monkeypatch):
    draft = {"subject": "Reenvío", "body": "Hola, corrige SCL-001 y SCL-042.", "finding_refs": ["SCL-001"], "confidence": 0.9}
    fake(monkeypatch, response=draft)
    assert run_ai("remediation").status == "invalido"
    draft["body"] = "Hola, corrige SCL-001 y SCL-002."
    fake(monkeypatch, response=draft)
    outcome = run_ai("remediation")
    assert outcome.status == "ok" and outcome.payload["needs_review"] is False


def test_mapping_ai_skips_the_call_when_nothing_to_suggest(monkeypatch):
    seen = fake(monkeypatch, response=good_mapping())
    full = {"horas extra": "overtime_hours", "centro costo": "cost_center"}
    outcome = run_ai("mapping", mapping=full)
    assert outcome.status == "no_disponible" and "user" not in seen  # sin llamada a la IA


def test_endpoint_without_ai_still_gives_complete_findings(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    batch = create_old(client)
    file_id = scl(client, batch)["id"]
    before = client.get(f"/api/files/{file_id}").json()
    result = client.post(f"/api/files/{file_id}/ai/cause").json()
    assert result["status"] == "no_disponible" and result["reason"]
    after = client.get(f"/api/files/{file_id}").json()
    assert after["findings"] == before["findings"] and after["ai"]["cause"]["status"] == "no_disponible"
    assert client.post(f"/api/files/{file_id}/ai/otro").status_code == 404


def test_ai_output_never_changes_dispositions_and_goes_stale_on_revalidation(client, monkeypatch):
    fake(monkeypatch, response=good_mapping())
    batch = create_old(client)
    file_id = scl(client, batch)["id"]
    snapshot = lambda: [(e["computed_disposition"], e["final_disposition"]) for e in client.get(f"/api/batches/{batch['id']}").json()["entries"]]
    before = snapshot()
    stored = client.post(f"/api/files/{file_id}/ai/mapping").json()
    assert stored["status"] == "ok" and stored["model"] == "modelo-simulado" and stored["latency_ms"] == 12
    assert snapshot() == before  # R7.4
    queue = {r["source_column"]: r for r in client.get(f"/api/batches/{batch['id']}/review").json()["pending"]}
    assert queue["Horas Extra"]["ai_suggestion"]["target_column"] == "overtime_hours"
    assert queue["Notas"]["ai_suggestion"] is None
    client.post(f"/api/mappings/{queue['Horas Extra']['id']}/accept", json={"actor": "Ana", "target_column": "overtime_hours"})
    assert "mapping" not in client.get(f"/api/files/{file_id}").json()["ai"]  # obsoleto tras revalidar (D-10)
