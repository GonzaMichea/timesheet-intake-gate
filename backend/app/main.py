import platform

import openpyxl
import pandas
from fastapi import FastAPI

app = FastAPI(title="Timesheet Intake Gate API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "python": platform.python_version(),
        "pandas": pandas.__version__,
        "openpyxl": openpyxl.__version__,
    }
