"""El dataset sintético es reproducible y cubre D01–D12 (R14, R15)."""
import hashlib
import json
import subprocess
import sys

from backend.tests.helpers import ROOT

CODES = [f"D{i:02d}" for i in range(1, 13)]
DATASETS = ROOT / "datasets"


def digest(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def generate(out, seed=42):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_dataset.py"),
                    "--seed", str(seed), "--out", str(out)], check=True, capture_output=True)


def test_same_seed_gives_identical_files(tmp_path):
    generate(tmp_path / "a")
    generate(tmp_path / "b")
    assert digest(tmp_path / "a") == digest(tmp_path / "b")
    assert digest(tmp_path / "a") == digest(DATASETS)  # lo versionado coincide con la seed 42


def test_different_seed_changes_data(tmp_path):
    generate(tmp_path / "c", seed=7)
    assert digest(tmp_path / "c") != digest(DATASETS)


def test_every_defect_code_appears_in_at_least_two_batches():
    batches_by_code = {code: set() for code in CODES}
    for path in DATASETS.glob("batch_*/ground_truth.json"):
        truth = json.loads(path.read_text(encoding="utf-8"))
        for defect in truth["defects"]:
            batches_by_code[defect["code"]].add(truth["batch"])
    assert {c for c, b in batches_by_code.items() if len(b) < 2} == set()


def test_master_has_60_employees_with_inactive_ones():
    lines = (ROOT / "spec" / "employee_master.csv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(lines) == 60
    assert sum(line.endswith("false") for line in lines) == 8


def test_clean_batch_ground_truth_is_empty():
    truth = json.loads((DATASETS / "batch_00_clean" / "ground_truth.json").read_text(encoding="utf-8"))
    assert truth["defects"] == [] and {f["expected_disposition"] for f in truth["files"]} == {"LOAD"}


def test_evaluate_meets_definition_of_done():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "evaluate.py")],
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout[-800:]
