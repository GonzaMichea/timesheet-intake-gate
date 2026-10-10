"""Un test por cada defecto D01–D12, más archivo limpio y determinismo (R16.1)."""
from backend.tests.helpers import (
    HEADERS, MASTER, clean_files, entry, find, run, run_scl, to_csv, valid_rows,
)


def test_clean_batch_has_no_findings():
    result = run(clean_files())
    assert all(e.findings == [] for e in result.entries)
    assert all(e.disposition.value == "LOAD" for e in result.entries)
    assert result.ready_for_load is True


def test_d01_missing_expected_file():
    files = clean_files()
    del files["TS_VAP_202609.csv"]
    vap = entry(run(files), "VAP")
    assert vap.kind == "missing"
    [finding] = find(vap, "D01")
    assert finding.severity == "BLOCKER"
    assert finding.evidence["expected"] == "TS_VAP_202609.csv|.xlsx"
    assert vap.disposition.value == "BLOCK"


def test_d02_unexpected_or_bad_name():
    files = clean_files()
    files["resumen.csv"] = b"x"
    files["ts_scl_202609.csv"] = b"x"  # el prefijo en minúsculas no calza
    result = run(files)
    unexpected = [e for e in result.entries if e.kind == "unexpected"]
    assert len(unexpected) == 2
    assert all(find(e, "D02")[0].rule_id == "D02.bad_name" for e in unexpected)
    assert all(e.disposition.value == "QUARANTINE" for e in unexpected)
    assert result.ready_for_load is False


def test_d02_duplicate_site():
    files = clean_files()
    files["TS_SCL_202609.xlsx"] = b"x"  # el .csv va primero en orden alfabético
    result = run(files)
    [dup] = [e for e in result.entries if e.kind == "unexpected"]
    assert dup.filename == "TS_SCL_202609.xlsx"
    assert find(dup, "D02")[0].rule_id == "D02.duplicate_site"
    assert entry(result, "SCL").findings == []


def test_d03_period_mismatch():
    files = clean_files()
    files["TS_VAP_202608.csv"] = files.pop("TS_VAP_202609.csv")
    result = run(files)
    vap = entry(result, "VAP")
    [finding] = vap.findings
    assert finding.code == "D03" and finding.evidence == {"found": "202608", "expected": "202609"}
    assert vap.disposition.value == "BLOCK"
    assert not find(vap, "D01")


def test_d04_missing_required_column():
    headers = [h for h in HEADERS if h != "cost_center"]
    e = run_scl(valid_rows(), headers)
    [finding] = find(e, "D04")
    assert finding.column == "cost_center" and finding.severity == "BLOCKER"
    assert e.disposition.value == "BLOCK"


def test_d04_unreadable_file_marks_all_columns():
    files = clean_files()
    files["TS_SCL_202609.csv"] = b""
    e = entry(run(files), "SCL")
    assert len(find(e, "D04")) == len(HEADERS)
    assert e.disposition.value == "BLOCK"


def renamed_headers():
    return ["Horas Extra" if h == "overtime_hours" else h for h in HEADERS]


def renamed_rows():
    return [{("Horas Extra" if k == "overtime_hours" else k): v for k, v in r.items()} for r in valid_rows()]


def test_d05_renamed_column_detected():
    e = run_scl(renamed_rows(), renamed_headers())
    [d05] = find(e, "D05")
    assert d05.column == "Horas Extra"
    assert d05.evidence["candidate"] == "overtime_hours" and d05.evidence["score"] == 1.0
    assert d05.status == "open" and find(e, "D04", "overtime_hours")


def test_d05_accepted_mapping_resolves_and_revalidates():
    e = run_scl(renamed_rows(), renamed_headers(), mappings={"TS_SCL_202609.csv": {"horas extra": "overtime_hours"}})
    [d05] = find(e, "D05")
    assert d05.status == "resolved_by_mapping"
    assert not find(e, "D04")
    assert e.disposition.value == "LOAD"


def test_d06_extra_column():
    rows = [dict(r, Notas="x") for r in valid_rows()]
    e = run_scl(rows, HEADERS + ["Notas"])
    [d06] = find(e, "D06")
    assert d06.column == "Notas" and d06.severity == "WARNING"
    assert e.disposition.value == "LOAD_WITH_WARNINGS"


def test_d07_text_in_hours_blocks():
    rows = valid_rows()
    rows[4]["regular_hours"] = "ocho"
    e = run_scl(rows)
    [d07] = find(e, "D07", "regular_hours")
    assert d07.severity == "BLOCKER" and d07.affected_rows == [6]
    assert e.disposition.value == "BLOCK"


def test_d07_bad_date_and_no_reevaluation():
    rows = valid_rows()
    rows[0]["work_date"] = "31-31-2026"
    e = run_scl(rows)
    [d07] = find(e, "D07", "work_date")
    assert d07.severity == "ERROR" and d07.affected_rows == [2]
    assert not find(e, "D08") and not find(e, "D09")  # R5.9


def test_d07_nulls_over_threshold_become_blocker():
    rows = valid_rows()
    for row in rows[:10]:
        row["cost_center"] = ""
    e = run_scl(rows)
    assert find(e, "D07", "cost_center")[0].severity == "BLOCKER"


def test_d08_duplicate_rows():
    rows = valid_rows()
    rows.append(dict(rows[1]))
    e = run_scl(rows)
    [d08] = find(e, "D08")
    assert d08.affected_rows == [52] and d08.evidence["first_occurrence"] == {"52": 3}


def test_d09_date_outside_period():
    rows = valid_rows()
    rows[0]["work_date"] = "2026-08-31"
    e = run_scl(rows)
    assert find(e, "D09")[0].affected_rows == [2]


def test_d10_hours_out_of_range():
    rows = valid_rows()
    rows[0]["regular_hours"] = "13"
    rows[1]["overtime_hours"] = "5"
    e = run_scl(rows)
    assert find(e, "D10", rule_id="D10.regular_range")[0].affected_rows == [2]
    assert find(e, "D10", rule_id="D10.overtime_range")[0].affected_rows == [3]


def test_d10_daily_total():
    rows = valid_rows()
    rows[0]["regular_hours"], rows[0]["overtime_hours"] = "12", "3"
    e = run_scl(rows)
    [d10] = find(e, "D10", rule_id="D10.daily_total")
    assert d10.affected_rows == [2] and not find(e, "D10", rule_id="D10.regular_range")


def test_d11_unknown_catalog_value():
    rows = valid_rows()
    rows[0]["shift_code"] = "NOCHE"
    rows[1]["absence_code"] = "XYZ"
    e = run_scl(rows)
    assert find(e, "D11", "shift_code")[0].affected_rows == [2]
    assert find(e, "D11", "absence_code")[0].affected_rows == [3]


def test_d12_unknown_inactive_or_unapproved():
    assert MASTER.employees["E10003"].active is False
    rows = valid_rows()
    rows[0]["employee_id"] = "E99999"
    rows[1]["employee_id"] = "E10003"
    rows[2]["approved_by"] = ""
    e = run_scl(rows)
    assert find(e, "D12", rule_id="D12.unknown_employee")[0].affected_rows == [2]
    assert find(e, "D12", rule_id="D12.inactive_employee")[0].affected_rows == [3]
    assert find(e, "D12", "approved_by")[0].affected_rows == [4]


def test_results_are_deterministic():
    rows = valid_rows()
    rows[0]["shift_code"] = "NOCHE"
    rows[5]["regular_hours"] = "x"
    first = run_scl(rows).model_dump()
    assert first == run_scl(rows).model_dump()
    assert [f.ref for f in run_scl(rows).findings] == ["SCL-001", "SCL-002"]
