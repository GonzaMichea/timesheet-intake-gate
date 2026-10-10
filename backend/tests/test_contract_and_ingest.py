import io
import zipfile
from datetime import date

import pytest
import yaml
from openpyxl import Workbook

from backend.app.contract.loader import ContractError, contract_hash, parse_contract, parse_master
from backend.app.engine.ingest import IngestError, check_total_size, expand_inputs, read_table
from backend.tests.helpers import HEADERS, ROOT, to_csv, valid_rows

SPEC_TEXT = (ROOT / "spec" / "timesheet_spec.yaml").read_text(encoding="utf-8")
MASTER_TEXT = (ROOT / "spec" / "employee_master.csv").read_text(encoding="utf-8")


def test_contract_loads_and_hash_is_stable():
    assert parse_contract(SPEC_TEXT).sites == ["SCL", "VAP", "CCP", "ANF"]
    assert contract_hash(SPEC_TEXT, MASTER_TEXT) == contract_hash(SPEC_TEXT, MASTER_TEXT)
    assert contract_hash(SPEC_TEXT, MASTER_TEXT) != contract_hash(SPEC_TEXT + " ", MASTER_TEXT)


def test_invalid_contract_names_the_field():
    data = yaml.safe_load(SPEC_TEXT)
    data["thresholds"]["max_null_pct"] = "mucho"
    with pytest.raises(ContractError, match="thresholds.max_null_pct"):
        parse_contract(yaml.safe_dump(data))


def test_invalid_master_is_rejected():
    with pytest.raises(ContractError, match="active"):
        parse_master("employee_id,site,active\nE10001,SCL,quizas\n")


def test_csv_semicolon_and_latin1():
    content = to_csv(valid_rows(days=1), sep=";").replace(b"Persona", "Pérez".encode("latin-1"))
    table = read_table("a.csv", content)
    assert table.headers == HEADERS and table.row_nums == [2, 3]
    assert table.records[0]["employee_name"].startswith("Pérez")


def test_csv_with_bom_and_blank_rows_keep_excel_numbering():
    body = to_csv(valid_rows(days=2)).decode().splitlines()
    text = "\n".join([body[0], body[1], ",,,,,,,,,,", body[2]])
    table = read_table("a.csv", b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert table.headers[0] == "employee_id" and table.row_nums == [2, 4]


def test_xlsx_reads_first_sheet_and_native_dates():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["employee_id", "work_date", "regular_hours"])
    sheet.append(["E10001", date(2026, 9, 1), 8.0])
    buffer = io.BytesIO()
    workbook.save(buffer)
    table = read_table("a.xlsx", buffer.getvalue())
    assert table.records == [{"employee_id": "E10001", "work_date": "2026-09-01", "regular_hours": "8"}]


def test_empty_file_has_no_headers():
    with pytest.raises(IngestError):
        read_table("a.csv", b"")


def test_zip_expands_subfolders_and_skips_junk():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("lote/TS_SCL_202609.csv", "a")
        archive.writestr("__MACOSX/lote/._TS_SCL_202609.csv", "x")
        archive.writestr(".oculto", "x")
        archive.writestr("carpeta/", "")
    names = [f.name for f in expand_inputs([("lote.zip", buffer.getvalue()), ("TS_VAP_202609.csv", b"b")])]
    assert names == ["TS_SCL_202609.csv", "TS_VAP_202609.csv"]


def test_corrupt_zip_and_size_limit():
    with pytest.raises(IngestError, match="dañado"):
        expand_inputs([("malo.zip", b"no es un zip")])
    with pytest.raises(IngestError, match="4 MB"):
        check_total_size([("a.csv", b"x" * (5 * 1024 * 1024))], 4)


def test_engine_does_not_import_ai_or_db():
    """Frontera IA vs. código (R7.4): el motor no puede depender de ai/ ni de db/."""
    for path in (ROOT / "backend" / "app" / "engine").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "app.ai" not in text and "app.db" not in text, path.name
