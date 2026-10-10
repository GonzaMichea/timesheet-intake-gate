"""Corre el motor sobre los lotes sintéticos y lo compara con el ground truth.

Uso: python scripts/evaluate.py [--with-ai]
Escribe reports/evaluation.md y reports/evaluation.json. Sale con código 1 si la detección
global es menor a 95 % o si hay alguna disposición incorrecta (R15.4).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.contract.loader import load_contract, load_master  # noqa: E402
from backend.app.engine.batch import validate_batch  # noqa: E402
from backend.app.engine.models import InputFile  # noqa: E402

CODES = [f"D{i:02d}" for i in range(1, 13)]
MIN_DETECTION = 0.95


def entry_key(entry) -> str:
    return f"MISSING:{entry.site}" if entry.kind == "missing" else entry.filename


def detected_units(result) -> set[tuple]:
    """Unidad = (archivo, código, columna, fila); fila 0 para defectos de archivo o columna."""
    units = set()
    for entry in result.entries:
        for finding in entry.findings:
            if finding.status != "open":
                continue
            for row in finding.affected_rows or [0]:
                units.add((entry_key(entry), finding.code, finding.column or "", row))
    return units


def truth_units(truth) -> set[tuple]:
    return {(d["file"], d["code"], d["column"], row) for d in truth["defects"] for row in d["rows"] or [0]}


def evaluate_batch(folder: Path, contract, master) -> dict:
    truth = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
    files = [InputFile(name=p.name, content=p.read_bytes())
             for p in sorted(folder.iterdir()) if p.name != "ground_truth.json"]
    start = time.perf_counter()
    result = validate_batch(truth["period"], files, contract, master)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    expected, found = truth_units(truth), detected_units(result)
    computed = {entry_key(e): e.disposition.value for e in result.entries}
    wrong = [{"file": f["file"], "expected": f["expected_disposition"], "computed": computed.get(f["file"])}
             for f in truth["files"] if computed.get(f["file"]) != f["expected_disposition"]]
    wrong += [{"file": k, "expected": None, "computed": v}
              for k, v in computed.items() if k not in {f["file"] for f in truth["files"]}]

    targets = {(m["file"], m["column"]): m["target"] for m in truth["mappings"]}
    candidates = [(e.filename, f.column, f.evidence.get("candidate"))
                  for e in result.entries for f in e.findings if f.code == "D05" and f.status == "open"]
    return {
        "batch": truth["batch"], "ms": elapsed_ms, "expected": expected, "found": found,
        "files": len(truth["files"]), "wrong_dispositions": wrong,
        "d05_correct": sum(1 for f, c, cand in candidates if targets.get((f, c)) == cand),
        "d05_total": len(candidates),
        "missed": sorted(expected - found), "false_positives": sorted(found - expected),
    }


def rate(part, whole):
    return None if whole == 0 else part / whole


def pct(value) -> str:
    return "N/A" if value is None else f"{value * 100:.1f} %"


def summarize(results) -> dict:
    by_code = {}
    for code in CODES:
        expected = {(r["batch"], *u) for r in results for u in r["expected"] if u[1] == code}
        found = {(r["batch"], *u) for r in results for u in r["found"] if u[1] == code}
        by_code[code] = {"expected": len(expected), "detected": len(expected & found),
                         "false_positives": len(found - expected)}
    expected_total = sum(len(r["expected"]) for r in results)
    detected_total = sum(len(r["expected"] & r["found"]) for r in results)
    found_total = sum(len(r["found"]) for r in results)
    files_total = sum(r["files"] for r in results)
    wrong = sum(len(r["wrong_dispositions"]) for r in results)
    d05_total = sum(r["d05_total"] for r in results)
    return {
        "by_code": by_code,
        "detection": rate(detected_total, expected_total),
        "false_positive_rate": rate(found_total - detected_total, found_total),
        "disposition_accuracy": rate(files_total - wrong, files_total),
        "wrong_dispositions": wrong,
        "d05_precision": rate(sum(r["d05_correct"] for r in results), d05_total),
        "units": {"expected": expected_total, "detected": detected_total, "found": found_total},
    }


def markdown(results, summary, with_ai) -> str:
    lines = ["# Evaluación del motor sobre lotes sintéticos", "",
             "## Detección por tipo de defecto", "",
             "| Código | Unidades sembradas | Detectadas | Detección | Falsos positivos |",
             "|---|---:|---:|---:|---:|"]
    for code, c in summary["by_code"].items():
        lines.append(f"| {code} | {c['expected']} | {c['detected']} | {pct(rate(c['detected'], c['expected']))} "
                     f"| {c['false_positives']} |")
    ai = "N/A (se mide con `--with-ai`; la IA se integra en el incremento 5)"
    lines += ["", "## Resumen", "", "| Métrica | Resultado |", "|---|---:|",
              f"| Detección global | {pct(summary['detection'])} ({summary['units']['detected']} de {summary['units']['expected']}) |",
              f"| Tasa de falsos positivos | {pct(summary['false_positive_rate'])} |",
              f"| Exactitud de disposición | {pct(summary['disposition_accuracy'])} |",
              f"| Disposiciones incorrectas | {summary['wrong_dispositions']} |",
              f"| Precisión de candidatas D05 (determinística) | {pct(summary['d05_precision'])} |",
              f"| Precisión de mapeos sugeridos por IA | {ai if not with_ai else 'N/A'} |",
              "", "## Tiempo por lote (motor determinístico)", "", "| Lote | Archivos | Tiempo |", "|---|---:|---:|"]
    lines += [f"| {r['batch']} | {r['files']} | {r['ms']} ms |" for r in results]
    problems = [r for r in results if r["missed"] or r["false_positives"] or r["wrong_dispositions"]]
    if problems:
        lines += ["", "## Diferencias contra el ground truth", ""]
        for r in problems:
            lines += [f"- **{r['batch']}**: omitidos {r['missed'][:6]}, falsos positivos {r['false_positives'][:6]}, "
                      f"disposiciones incorrectas {r['wrong_dispositions']}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-ai", action="store_true", help="incluye la precisión de los mapeos de IA")
    parser.add_argument("--datasets", default=str(ROOT / "datasets"))
    args = parser.parse_args()

    contract = load_contract(ROOT / "spec" / "timesheet_spec.yaml")
    master = load_master(ROOT / "spec" / "employee_master.csv")
    folders = sorted(p for p in Path(args.datasets).glob("batch_*") if p.is_dir())
    if not folders:
        print("No hay lotes. Ejecuta primero: python scripts/generate_dataset.py")
        return 2
    results = [evaluate_batch(folder, contract, master) for folder in folders]
    summary = summarize(results)
    text = markdown(results, summary, args.with_ai)
    print(text)

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "evaluation.md").write_text(text, encoding="utf-8")
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "summary": summary,
               "batches": [{k: v for k, v in r.items() if k not in {"expected", "found"}} for r in results]}
    (reports / "evaluation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = summary["detection"] >= MIN_DETECTION and summary["wrong_dispositions"] == 0
    print("RESULTADO:", "CUMPLE" if ok else "NO CUMPLE", "(detección ≥ 95 % y 0 disposiciones incorrectas)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
