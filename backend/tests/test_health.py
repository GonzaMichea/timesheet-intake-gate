from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_reports_versions(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["pandas"]
    assert body["db"] == "no_configurada"


def test_health_db_error_hides_details(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://tig_api:x@127.0.0.1:1/postgres")
    body = TestClient(app).get("/api/health").json()
    assert body["db"] == "error"
