import platform

import openpyxl
import pandas
from fastapi import FastAPI

from backend.app.db.session import check_database

app = FastAPI(title="Timesheet Intake Gate API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "db": check_database(),
        "python": platform.python_version(),
        "pandas": pandas.__version__,
        "openpyxl": openpyxl.__version__,
    }
