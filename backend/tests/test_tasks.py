import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


# ── List ─────────────────────────────────────────────────────────────────────

def test_list_empty(client):
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_created_tasks(client):
    client.post("/api/tasks", json={"title": "A"})
    client.post("/api/tasks", json={"title": "B"})
    assert len(client.get("/api/tasks").json()) == 2


def test_list_filter_by_status(client):
    client.post("/api/tasks", json={"title": "Todo task",  "status": "todo"})
    client.post("/api/tasks", json={"title": "Done task",  "status": "done"})
    data = client.get("/api/tasks?status=todo").json()
    assert len(data) == 1
    assert data[0]["title"] == "Todo task"


# ── Create ───────────────────────────────────────────────────────────────────

def test_create_minimal(client):
    resp = client.post("/api/tasks", json={"title": "Do something"})
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"]    == "Do something"
    assert d["status"]   == "todo"
    assert d["priority"] == "medium"
    assert d["id"]


def test_create_full(client):
    resp = client.post("/api/tasks", json={
        "title": "Full task", "status": "in_progress", "priority": "high",
        "due_date": "2026-05-20", "recurring": "daily", "notes": "note",
    })
    assert resp.status_code == 201
    d = resp.json()
    assert d["status"]    == "in_progress"
    assert d["due_date"]  == "2026-05-20"
    assert d["recurring"] == "daily"
    assert d["notes"]     == "note"


# ── Get by ID ────────────────────────────────────────────────────────────────

def test_get_task(client):
    created = client.post("/api/tasks", json={"title": "Get me"}).json()
    resp = client.get(f"/api/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_task_not_found(client):
    assert client.get("/api/tasks/does-not-exist").status_code == 404


# ── Patch ────────────────────────────────────────────────────────────────────

def test_patch_status(client):
    created = client.post("/api/tasks", json={"title": "Patch me"}).json()
    resp = client.patch(f"/api/tasks/{created['id']}", json={"status": "done"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["status"] == "done"
    assert d["title"]  == "Patch me"          # other fields unchanged


def test_patch_not_found(client):
    assert client.patch("/api/tasks/x", json={"status": "done"}).status_code == 404


def test_patch_empty_body_returns_task(client):
    created = client.post("/api/tasks", json={"title": "No change"}).json()
    resp = client.patch(f"/api/tasks/{created['id']}", json={})
    assert resp.status_code == 200
    assert resp.json()["title"] == "No change"


# ── Delete ───────────────────────────────────────────────────────────────────

def test_delete_task(client):
    created = client.post("/api/tasks", json={"title": "Delete me"}).json()
    resp = client.delete(f"/api/tasks/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/tasks/{created['id']}").status_code == 404


def test_delete_not_found(client):
    assert client.delete("/api/tasks/does-not-exist").status_code == 404
