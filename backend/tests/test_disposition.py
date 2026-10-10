"""Un test por cada regla de disposición y el borde del umbral (R16.2)."""
from backend.tests.helpers import HEADERS, run_scl, valid_rows


def test_block_with_any_blocker():
    rows = valid_rows()
    rows[0]["regular_hours"] = "x"
    e = run_scl(rows)
    assert (e.disposition.value, e.disposition.rule_id) == ("BLOCK", "RULE_BLOCK")


def test_quarantine_above_threshold():
    rows = valid_rows()
    rows[0]["shift_code"] = rows[1]["shift_code"] = "NOCHE"  # 2 de 50 = 4 %
    e = run_scl(rows)
    assert (e.disposition.value, e.disposition.rule_id) == ("QUARANTINE", "RULE_QUARANTINE")
    assert e.disposition.explanation == "4,0 % de filas con ERROR > 2,0 %"


def test_exactly_at_threshold_is_not_quarantine():
    rows = valid_rows()
    rows[0]["shift_code"] = "NOCHE"  # 1 de 50 = 2 % exacto
    e = run_scl(rows)
    assert (e.disposition.value, e.disposition.rule_id) == ("LOAD_WITH_WARNINGS", "RULE_WARN")


def test_load_with_warnings_only_warnings():
    rows = [dict(r, Notas="x") for r in valid_rows()]
    e = run_scl(rows, HEADERS + ["Notas"])
    assert e.disposition.value == "LOAD_WITH_WARNINGS"


def test_load_without_findings():
    e = run_scl(valid_rows())
    assert (e.disposition.value, e.disposition.rule_id) == ("LOAD", "RULE_LOAD")
