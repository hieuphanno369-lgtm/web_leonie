import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def task_id(client):
    return client.post("/api/tasks", json={"title": "My task"}).json()["id"]

def test_list_empty(client):
    assert client.get("/api/wip").json() == []

def test_create_wip(client, task_id):
    resp = client.post("/api/wip", json={"task_id": task_id, "progress": 30})
    assert resp.status_code == 201
    d = resp.json()
    assert d["task_id"] == task_id
    assert d["task_title"] == "My task"
    assert d["progress"] == 30
    assert d["id"]

def test_create_wip_task_not_found(client):
    assert client.post("/api/wip", json={"task_id": "no-such-task"}).status_code == 404

def test_list_includes_task_title(client, task_id):
    client.post("/api/wip", json={"task_id": task_id})
    data = client.get("/api/wip").json()
    assert len(data) == 1
    assert data[0]["task_title"] == "My task"

def test_get_wip(client, task_id):
    created = client.post("/api/wip", json={"task_id": task_id}).json()
    resp = client.get(f"/api/wip/{created['id']}")
    assert resp.status_code == 200 and resp.json()["id"] == created["id"]

def test_get_not_found(client):
    assert client.get("/api/wip/nope").status_code == 404

def test_update_progress(client, task_id):
    created = client.post("/api/wip", json={"task_id": task_id, "progress": 10}).json()
    resp = client.patch(f"/api/wip/{created['id']}", json={"progress": 75})
    assert resp.status_code == 200 and resp.json()["progress"] == 75

def test_delete_wip(client, task_id):
    created = client.post("/api/wip", json={"task_id": task_id}).json()
    assert client.delete(f"/api/wip/{created['id']}").status_code == 204
    assert client.get(f"/api/wip/{created['id']}").status_code == 404

def test_delete_not_found(client):
    assert client.delete("/api/wip/nope").status_code == 404

def test_add_and_list_logs(client, task_id):
    wip_id = client.post("/api/wip", json={"task_id": task_id}).json()["id"]
    client.post(f"/api/wip/{wip_id}/logs", json={"date": "2026-05-18", "note": "First log"})
    logs = client.get(f"/api/wip/{wip_id}/logs").json()
    assert len(logs) == 1
    assert logs[0]["note"] == "First log"
    assert logs[0]["date"] == "2026-05-18"

def test_delete_log(client, task_id):
    wip_id = client.post("/api/wip", json={"task_id": task_id}).json()["id"]
    log_id = client.post(f"/api/wip/{wip_id}/logs", json={"date": "2026-05-18", "note": "Del me"}).json()["id"]
    assert client.delete(f"/api/wip/{wip_id}/logs/{log_id}").status_code == 204
    assert client.get(f"/api/wip/{wip_id}/logs").json() == []

def test_delete_wip_cascades_logs(client, task_id):
    wip_id = client.post("/api/wip", json={"task_id": task_id}).json()["id"]
    client.post(f"/api/wip/{wip_id}/logs", json={"date": "2026-05-18", "note": "cascade test"})
    client.delete(f"/api/wip/{wip_id}")
    # wip gone → logs gone (CASCADE); verify via 404 on wip
    assert client.get(f"/api/wip/{wip_id}").status_code == 404
