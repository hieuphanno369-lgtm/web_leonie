import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_empty(client):
    assert client.get("/api/kpi").json() == []


def test_create_da_output(client):
    resp = client.post("/api/kpi", json={
        "metric": "Queries viết", "value": 12, "date": "2026-05-18",
        "category": "da_output"
    })
    assert resp.status_code == 201
    d = resp.json()
    assert d["metric"] == "Queries viết"
    assert d["value"] == 12.0
    assert d["category"] == "da_output"
    assert d["id"]


def test_create_business(client):
    resp = client.post("/api/kpi", json={
        "metric": "GMV ColosBaby", "value": 12400000000,
        "date": "2026-05-18", "category": "business"
    })
    assert resp.status_code == 201
    assert resp.json()["category"] == "business"


def test_invalid_category(client):
    resp = client.post("/api/kpi", json={
        "metric": "X", "value": 1, "date": "2026-05-18",
        "category": "invalid"
    })
    assert resp.status_code == 422


def test_filter_by_category(client):
    client.post("/api/kpi", json={"metric": "A", "value": 1, "date": "2026-05-18", "category": "da_output"})
    client.post("/api/kpi", json={"metric": "B", "value": 2, "date": "2026-05-18", "category": "business"})
    result = client.get("/api/kpi?category=business").json()
    assert len(result) == 1
    assert result[0]["metric"] == "B"


def test_filter_by_metric(client):
    client.post("/api/kpi", json={"metric": "Queries", "value": 5, "date": "2026-05-17", "category": "da_output"})
    client.post("/api/kpi", json={"metric": "Queries", "value": 8, "date": "2026-05-18", "category": "da_output"})
    client.post("/api/kpi", json={"metric": "GMV", "value": 1e9, "date": "2026-05-18", "category": "business"})
    result = client.get("/api/kpi?metric=Queries").json()
    assert len(result) == 2


def test_list_metrics(client):
    client.post("/api/kpi", json={"metric": "Queries", "value": 5, "date": "2026-05-18", "category": "da_output"})
    client.post("/api/kpi", json={"metric": "GMV", "value": 1e9, "date": "2026-05-18", "category": "business"})
    result = client.get("/api/kpi/metrics").json()
    assert set(result) == {"Queries", "GMV"}


def test_delete_kpi(client):
    created = client.post("/api/kpi", json={"metric": "X", "value": 1, "date": "2026-05-18", "category": "da_output"}).json()
    assert client.delete(f"/api/kpi/{created['id']}").status_code == 204
    assert client.get("/api/kpi").json() == []


def test_delete_not_found(client):
    assert client.delete("/api/kpi/does-not-exist").status_code == 404
