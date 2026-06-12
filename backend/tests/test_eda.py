import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

EDA_MIN  = {"title": "EDA T04", "requester": "Alice", "dataset": "SF_ColosBaby"}
EDA_FULL = {
    "title": "Full EDA", "requester": "Bob", "dataset": "SF_Optimum",
    "priority": "high", "status": "in_progress",
    "due_date": "2026-05-25", "notes": "Focus on cohort",
}

def test_list_empty(client):
    assert client.get("/api/eda").json() == []

def test_list_returns_created(client):
    client.post("/api/eda", json=EDA_MIN)
    client.post("/api/eda", json={**EDA_MIN, "title": "EDA 2"})
    assert len(client.get("/api/eda").json()) == 2

def test_list_filter_by_status(client):
    client.post("/api/eda", json={**EDA_MIN, "status": "todo"})
    client.post("/api/eda", json={**EDA_MIN, "title": "Done EDA", "status": "done"})
    data = client.get("/api/eda?status=todo").json()
    assert len(data) == 1 and data[0]["title"] == "EDA T04"

def test_create_minimal(client):
    resp = client.post("/api/eda", json=EDA_MIN)
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"] == "EDA T04"
    assert d["requester"] == "Alice"
    assert d["dataset"] == "SF_ColosBaby"
    assert d["status"] == "todo"
    assert d["priority"] == "medium"
    assert d["id"]

def test_create_full(client):
    d = client.post("/api/eda", json=EDA_FULL).json()
    assert d["priority"] == "high"
    assert d["status"] == "in_progress"
    assert d["due_date"] == "2026-05-25"
    assert d["notes"] == "Focus on cohort"

def test_get_eda(client):
    created = client.post("/api/eda", json=EDA_MIN).json()
    resp = client.get(f"/api/eda/{created['id']}")
    assert resp.status_code == 200 and resp.json()["id"] == created["id"]

def test_get_not_found(client):
    assert client.get("/api/eda/nope").status_code == 404

def test_patch_status(client):
    created = client.post("/api/eda", json=EDA_MIN).json()
    resp = client.patch(f"/api/eda/{created['id']}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["title"] == "EDA T04"

def test_patch_not_found(client):
    assert client.patch("/api/eda/x", json={"status": "done"}).status_code == 404

def test_patch_empty_returns_eda(client):
    created = client.post("/api/eda", json=EDA_MIN).json()
    assert client.patch(f"/api/eda/{created['id']}", json={}).json()["title"] == "EDA T04"

def test_delete(client):
    created = client.post("/api/eda", json=EDA_MIN).json()
    assert client.delete(f"/api/eda/{created['id']}").status_code == 204
    assert client.get(f"/api/eda/{created['id']}").status_code == 404

def test_delete_not_found(client):
    assert client.delete("/api/eda/nope").status_code == 404
