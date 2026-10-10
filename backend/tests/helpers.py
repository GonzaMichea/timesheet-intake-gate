import csv
import io
from pathlib import Path

from backend.app.contract.loader import load_contract, load_master
from backend.app.engine.batch import validate_batch
from backend.app.engine.models import InputFile

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = load_contract(ROOT / "spec" / "timesheet_spec.yaml")
MASTER = load_master(ROOT / "spec" / "employee_master.csv")
HEADERS = list(CONTRACT.columns)
PERIOD = "2026-09"
SITE_EMPLOYEES = {
    "SCL": ("E10001", "E10002"),
    "VAP": ("E20001", "E20002"),
    "CCP": ("E30001", "E30002"),
    "ANF": ("E40001", "E40002"),
}


def valid_rows(site="SCL", days=25):
    """2 empleados activos x 25 días = 50 filas sin defectos (1 fila = 2 %)."""
    return [
        {
            "employee_id": emp, "employee_name": f"Persona {emp}", "site": site, "cost_center": "CC100",
            "work_date": f"2026-09-{day:02d}", "shift_code": "DAY", "regular_hours": "8",
            "overtime_hours": "1", "absence_code": "", "approved_by": "Supervisor Demo",
            "approval_date": "2026-10-01",
        }
        for emp in SITE_EMPLOYEES[site]
        for day in range(1, days + 1)
    ]


def to_csv(rows, headers=None, sep=",") -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers or HEADERS, delimiter=sep, lineterminator="\n",
                            extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def clean_files():
    return {f"TS_{s}_202609.csv": to_csv(valid_rows(s)) for s in SITE_EMPLOYEES}


def run(files: dict[str, bytes], mappings=None, period=PERIOD):
    inputs = [InputFile(name=n, content=c) for n, c in files.items()]
    return validate_batch(period, inputs, CONTRACT, MASTER, mappings)


def run_scl(rows, headers=None, mappings=None):
    """Lote completo donde solo SCL se modifica; devuelve la entrada de SCL."""
    files = clean_files()
    files["TS_SCL_202609.csv"] = to_csv(rows, headers)
    return entry(run(files, mappings), "SCL")


def entry(result, site):
    return next(e for e in result.entries if e.site == site)


def find(e, code, column=None, rule_id=None):
    return [f for f in e.findings if f.code == code and (column is None or f.column == column)
            and (rule_id is None or f.rule_id == rule_id)]
