"""API de lotes, mapeos, overrides y auditoría, sobre SQLite en memoria (R16.6)."""
import io
import zipfile

from backend.tests.helpers import ROOT, clean_files

OLD_TEMPLATE = ROOT / "datasets" / "batch_01_old_template"


def post_batch(client, files, period="2026-09", actor="Ana Analista"):
    return client.post("/api/batches", data={"period": period, "actor": actor},
                       files=[("files", (name, content)) for name, content in files.items()])


def old_template_files():
    return {p.name: p.read_bytes() for p in OLD_TEMPLATE.iterdir() if p.suffix != ".json"}


def scl(client, batch):
    return next(e for e in batch["entries"] if e["site"] == "SCL")


def create_old(client):
    response = post_batch(client, old_template_files())
    assert response.status_code == 201, response.text
    return response.json()


def pending(client, batch_id):
    return {r["source_column"]: r for r in client.get(f"/api/batches/{batch_id}/review").json()["pending"]}


def test_clean_batch_is_ready_and_has_no_ai(client):
    batch = post_batch(client, clean_files()).json()
    assert batch["ready_for_load"] is True
    assert {e["final_disposition"] for e in batch["entries"]} == {"LOAD"}
    assert batch["processing_ms"] is not None and len(batch["contract_hash"]) == 64
    detail = client.get(f"/api/files/{batch['entries'][0]['id']}").json()
    assert detail["findings"] == [] and detail["ai"] == {}  # la app funciona sin IA (R12.1)


def test_invalid_requests_return_spanish_errors(client):
    for kwargs, code in [
        ({"files": clean_files(), "period": "2026-13"}, "periodo_invalido"),
        ({"files": {}}, "sin_archivos"),
        ({"files": clean_files(), "actor": " "}, "falta_analista"),
    ]:
        response = post_batch(client, **kwargs)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == code and response.json()["error"]["message"]
    assert client.get("/api/batches").json() == []  # no se creó ningún lote


def test_zip_and_corrupt_zip(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in old_template_files().items():
            archive.writestr(f"lote/{name}", content)
    assert post_batch(client, {"lote.zip": buffer.getvalue()}).status_code == 201
    bad = post_batch(client, {"malo.zip": b"no es zip"})
    assert bad.status_code == 400 and "dañado" in bad.json()["error"]["message"]


def test_batch_with_defects_blocks_and_queues_mappings(client):
    batch = create_old(client)
    assert batch["ready_for_load"] is False
    assert scl(client, batch)["computed_disposition"] == "BLOCK"
    vap = next(e for e in batch["entries"] if e["site"] == "VAP")
    assert vap["kind"] == "missing" and vap["final_disposition"] == "BLOCK"
    queue = pending(client, batch["id"])
    assert set(queue) == {"Horas Extra", "Centro Costo", "Notas"}
    assert queue["Horas Extra"]["candidate_column"] == "overtime_hours" and queue["Notas"]["candidate_column"] is None
    assert client.get("/api/batches").json()[0]["id"] == batch["id"]


def test_accept_mapping_revalidates_recalculates_and_audits(client):
    batch = create_old(client)
    queue = pending(client, batch["id"])
    first = client.post(f"/api/mappings/{queue['Horas Extra']['id']}/accept",
                        json={"actor": "Ana Analista", "target_column": "overtime_hours"})
    assert first.status_code == 200
    detail = first.json()
    assert detail["computed_disposition"] == "BLOCK"  # todavía falta cost_center
    resolved = [f for f in detail["findings"] if f["code"] == "D05" and f["column"] == "Horas Extra"]
    assert resolved[0]["status"] == "resolved_by_mapping"
    assert detail["missing_columns"] == ["cost_center"]

    second = client.post(f"/api/mappings/{queue['Centro Costo']['id']}/accept",
                         json={"actor": "Ana Analista", "target_column": "cost_center"}).json()
    assert second["computed_disposition"] == "LOAD_WITH_WARNINGS" and second["missing_columns"] == []
    audit = client.get(f"/api/batches/{batch['id']}/audit").json()
    assert [a["action"] for a in audit] == ["mapping_accepted", "mapping_accepted"]
    assert audit[1]["before"]["computed"] == "BLOCK" and audit[1]["after"]["computed"] == "LOAD_WITH_WARNINGS"
    assert audit[0]["actor"] == "Ana Analista"
    again = client.post(f"/api/mappings/{queue['Horas Extra']['id']}/accept",
                        json={"actor": "x", "target_column": "overtime_hours"})
    assert again.status_code == 409


def test_accept_mapping_rejects_invalid_target(client):
    batch = create_old(client)
    queue = pending(client, batch["id"])
    response = client.post(f"/api/mappings/{queue['Notas']['id']}/accept",
                           json={"actor": "Ana", "target_column": "work_date"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "destino_invalido"


def test_reject_mapping_keeps_findings_open(client):
    batch = create_old(client)
    queue = pending(client, batch["id"])
    detail = client.post(f"/api/mappings/{queue['Notas']['id']}/reject", json={"actor": "Ana"}).json()
    assert next(r for r in detail["mappings"] if r["source_column"] == "Notas")["status"] == "rejected"
    assert any(f["code"] == "D06" and f["status"] == "open" for f in detail["findings"])
    assert "Notas" not in pending(client, batch["id"])
    assert client.get(f"/api/batches/{batch['id']}/audit").json()[0]["action"] == "mapping_rejected"


def test_override_requires_justification_and_marks_permissive(client):
    batch = create_old(client)
    file_id = scl(client, batch)["id"]
    short = client.post(f"/api/files/{file_id}/override",
                        json={"actor": "Ana", "disposition": "LOAD", "justification": "porque sí"})
    assert short.status_code == 400 and short.json()["error"]["code"] == "justificacion_corta"
    assert client.get(f"/api/batches/{batch['id']}/audit").json() == []

    ok = client.post(f"/api/files/{file_id}/override", json={
        "actor": "Ana", "disposition": "LOAD", "justification": "La sede reenviará el archivo corregido."}).json()
    assert ok["computed_disposition"] == "BLOCK" and ok["final_disposition"] == "LOAD"
    assert ok["override_active"] and ok["permissive_override"]
    audit = client.get(f"/api/batches/{batch['id']}/audit").json()
    assert audit[0]["action"] == "override_created" and audit[0]["justification"].startswith("La sede")
    assert audit[0]["before"]["final"] == "BLOCK" and audit[0]["after"]["final"] == "LOAD"


def test_override_survives_revalidation_and_flags_change(client):
    batch = create_old(client)
    file_id = scl(client, batch)["id"]
    client.post(f"/api/files/{file_id}/override", json={
        "actor": "Ana", "disposition": "QUARANTINE", "justification": "Se revisa manualmente con la sede."})
    queue = pending(client, batch["id"])
    for column, target in [("Horas Extra", "overtime_hours"), ("Centro Costo", "cost_center")]:
        detail = client.post(f"/api/mappings/{queue[column]['id']}/accept",
                             json={"actor": "Ana", "target_column": target}).json()
    assert detail["computed_disposition"] == "LOAD_WITH_WARNINGS"
    assert detail["final_disposition"] == "QUARANTINE" and detail["calculated_changed_after_override"] is True
    assert detail["permissive_override"] is False


def test_withdraw_override_and_ready_for_load(client):
    batch = create_old(client)
    ids = [e["id"] for e in batch["entries"]]
    for file_id in ids:  # relajar todo para que el lote quede apto
        client.post(f"/api/files/{file_id}/override", json={
            "actor": "Ana", "disposition": "LOAD", "justification": "Aprobado por la jefatura de nómina."})
    assert client.get(f"/api/batches/{batch['id']}").json()["ready_for_load"] is True
    no_override = client.post(f"/api/files/{ids[0]}/override/withdraw",
                              json={"actor": "Ana", "justification": "ya no corresponde el permiso"}).json()
    assert no_override["override_active"] is False and no_override["final_disposition"] == no_override["computed_disposition"]
    assert client.get(f"/api/batches/{batch['id']}").json()["ready_for_load"] is False
    again = client.post(f"/api/files/{ids[0]}/override/withdraw",
                        json={"actor": "Ana", "justification": "ya no corresponde el permiso"})
    assert again.status_code == 409


def test_audit_log_has_no_edit_or_delete_endpoints(client):
    batch = create_old(client)
    url = f"/api/batches/{batch['id']}/audit"
    assert client.put(url).status_code == 405 and client.delete(url).status_code == 405
    assert client.post(url).status_code == 405


def test_not_found_and_metrics(client):
    assert client.get("/api/files/no-existe").status_code == 404
    assert client.get("/api/batches/00000000-0000-0000-0000-000000000000").json()["error"]["code"] == "lote_no_encontrado"
    assert client.get("/api/metrics").json()["summary"]["detection"] >= 0.95
    assert client.get("/api/contract").json()["sites"] == ["SCL", "VAP", "CCP", "ANF"]
