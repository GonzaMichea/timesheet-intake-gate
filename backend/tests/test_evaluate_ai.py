"""evaluate.py --with-ai mide la precisión de los mapeos que sugiere la IA (R15.2)."""
import importlib.util
import json

from backend.app.ai import client
from backend.tests.helpers import CONTRACT, MASTER, ROOT

spec = importlib.util.spec_from_file_location("evaluate_script", ROOT / "scripts" / "evaluate.py")
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)

FOLDER = ROOT / "datasets" / "batch_01_old_template"


def simulate(monkeypatch, suggestions):
    def complete(system, user, schema, timeout_s, max_tokens=2048):
        return client.Completion(text=json.dumps({"suggestions": suggestions}), model="simulado", latency_ms=1)

    monkeypatch.setattr(client, "complete", complete)


def suggestion(source, target):
    return {"source_column": source, "target_column": target, "confidence": 0.9, "justification": "prueba"}


def test_ai_precision_counts_correct_suggestions_only(monkeypatch):
    simulate(monkeypatch, [suggestion("Horas Extra", "overtime_hours"),   # correcta
                           suggestion("Centro Costo", "overtime_hours"),  # destino equivocado
                           suggestion("Notas", None)])                    # "ninguna": no cuenta como sugerencia
    result = evaluate.evaluate_batch(FOLDER, CONTRACT, MASTER, with_ai=True)
    assert result["ai"]["total"] == 2 and result["ai"]["correct"] == 1
    summary = evaluate.summarize([result])
    assert summary["ai"]["precision"] == 0.5
    assert "50.0 %" in evaluate.markdown([result], summary, with_ai=True)


def test_ai_unavailable_is_reported_as_na_and_does_not_change_the_rest(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with_ai = evaluate.evaluate_batch(FOLDER, CONTRACT, MASTER, with_ai=True)
    without = evaluate.evaluate_batch(FOLDER, CONTRACT, MASTER)
    assert with_ai["ai"]["total"] == 0 and with_ai["ai"]["unavailable"]
    assert with_ai["found"] == without["found"] and with_ai["wrong_dispositions"] == without["wrong_dispositions"]
    assert "N/A" in evaluate.markdown([with_ai], evaluate.summarize([with_ai]), with_ai=True)
