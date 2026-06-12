import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


# ── helpers ──────────────────────────────────────────────────────────────────

def _note(client, **kwargs):
    body = {"content": "test content", "date": "2026-05-24", **kwargs}
    return client.post("/api/notes", json=body)


# ── List ─────────────────────────────────────────────────────────────────────

def test_list_notes_empty(client):
    resp = client.get("/api/notes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_created_notes(client):
    _note(client)
    _note(client)
    assert len(client.get("/api/notes").json()) == 2


# ── Create ───────────────────────────────────────────────────────────────────

def test_create_note_minimal(client):
    resp = _note(client)
    assert resp.status_code == 201
    d = resp.json()
    assert d["content"] == "test content"
    assert d["date"] == "2026-05-24"
    assert d["title"] is None
    assert d["category"] is None
    assert d["task_id"] is None
    assert d["eda_id"] is None
    assert d["id"]


def test_create_note_full(client):
    resp = _note(client, title="Stand-up", category="daily")
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"] == "Stand-up"
    assert d["category"] == "daily"


def test_create_note_missing_content_422(client):
    resp = client.post("/api/notes", json={"date": "2026-05-24"})
    assert resp.status_code == 422


def test_create_note_missing_date_422(client):
    resp = client.post("/api/notes", json={"content": "hello"})
    assert resp.status_code == 422


# ── FK validation ─────────────────────────────────────────────────────────────

def test_create_note_invalid_task_id_400(client):
    resp = _note(client, task_id="nonexistent-id")
    assert resp.status_code == 400
    assert "task_id" in resp.json()["detail"]


def test_create_note_invalid_eda_id_400(client):
    resp = _note(client, eda_id="nonexistent-id")
    assert resp.status_code == 400
    assert "eda_id" in resp.json()["detail"]


def test_create_note_valid_task_id(client):
    task = client.post("/api/tasks", json={"title": "Linked task"}).json()
    resp = _note(client, task_id=task["id"])
    assert resp.status_code == 201
    assert resp.json()["task_id"] == task["id"]


# ── Filters ───────────────────────────────────────────────────────────────────

def test_filter_by_date_range(client):
    _note(client, date="2026-05-20")
    _note(client, date="2026-05-23")
    _note(client, date="2026-05-25")
    data = client.get("/api/notes?date_from=2026-05-22&date_to=2026-05-24").json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-05-23"


def test_filter_by_category(client):
    _note(client, category="daily")
    _note(client, category="meeting")
    data = client.get("/api/notes?category=daily").json()
    assert len(data) == 1
    assert data[0]["category"] == "daily"


# ── Get / Patch / Delete ──────────────────────────────────────────────────────

def test_get_note(client):
    created = _note(client).json()
    resp = client.get(f"/api/notes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_note_not_found(client):
    assert client.get("/api/notes/does-not-exist").status_code == 404


def test_update_note(client):
    created = _note(client).json()
    resp = client.patch(f"/api/notes/{created['id']}", json={"title": "Updated"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["title"] == "Updated"
    assert d["content"] == "test content"   # unchanged
    assert d["updated"] >= d["created"]


def test_update_note_not_found(client):
    assert client.patch("/api/notes/x", json={"title": "X"}).status_code == 404


def test_delete_note(client):
    created = _note(client).json()
    resp = client.delete(f"/api/notes/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/notes/{created['id']}").status_code == 404


def test_delete_note_not_found(client):
    assert client.delete("/api/notes/does-not-exist").status_code == 404


def test_patch_note_invalid_task_id_400(client):
    created = _note(client).json()
    resp = client.patch(f"/api/notes/{created['id']}", json={"task_id": "nonexistent-id"})
    assert resp.status_code == 400
    assert "task_id" in resp.json()["detail"]
