import platform

import openpyxl
from fastapi import FastAPI

from backend.app.db.session import check_database
from backend.app.errors import install_handlers
from backend.app.routes.api import router

app = FastAPI(title="Timesheet Intake Gate API")
install_handlers(app)
app.include_router(router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "db": check_database(),
        "python": platform.python_version(),
        "openpyxl": openpyxl.__version__,
    }
