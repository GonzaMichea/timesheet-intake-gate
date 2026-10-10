"""Prueba la API contra la base real (DATABASE_URL de .env.local) sin dejar datos.

Todo ocurre dentro de una transacción que se deshace al final: la auditoría es de solo
inserción y no se podría borrar después. Uso: python scripts/smoke_db.py
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if "DATABASE_URL" not in os.environ:
    match = re.search(r"^DATABASE_URL=(.*)$", (ROOT / ".env.local").read_text(encoding="utf-8-sig"), re.M)
    os.environ["DATABASE_URL"] = match.group(1).strip()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.app.db.session import get_db, get_engine  # noqa: E402
from backend.app.main import app  # noqa: E402

BATCH = ROOT / "datasets" / "batch_01_old_template"


def main() -> int:
    connection = get_engine().connect()
    outer = connection.begin()

    def override():
        # Cada commit del servicio es un savepoint; la transacción externa nunca se confirma
        with Session(connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    try:
        files = [("files", (p.name, p.read_bytes())) for p in BATCH.iterdir() if p.suffix != ".json"]
        created = client.post("/api/batches", data={"period": "2026-09", "actor": "Prueba humo"}, files=files)
        assert created.status_code == 201, created.text
        batch = created.json()
        print("lote creado:", batch["id"], "| archivos:", len(batch["entries"]), "| apto:", batch["ready_for_load"])

        queue = client.get(f"/api/batches/{batch['id']}/review").json()["pending"]
        horas = next(r for r in queue if r["source_column"] == "Horas Extra")
        accepted = client.post(f"/api/mappings/{horas['id']}/accept",
                               json={"actor": "Prueba humo", "target_column": "overtime_hours"})
        assert accepted.status_code == 200, accepted.text
        file_id = accepted.json()["id"]

        override = client.post(f"/api/files/{file_id}/override", json={
            "actor": "Prueba humo", "disposition": "LOAD", "justification": "Prueba de humo, se deshace al terminar."})
        assert override.status_code == 200, override.text
        audit = client.get(f"/api/batches/{batch['id']}/audit").json()
        print("auditoría:", [a["action"] for a in audit])
        assert [a["action"] for a in audit] == ["mapping_accepted", "override_created"]
        print("historial incluye el lote:", any(b["id"] == batch["id"] for b in client.get("/api/batches").json()))
        print("RESULTADO: OK")
        return 0
    finally:
        app.dependency_overrides.clear()
        outer.rollback()
        connection.close()
        print("transacción deshecha: no quedó ningún dato")


if __name__ == "__main__":
    sys.exit(main())
