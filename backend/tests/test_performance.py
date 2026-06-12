import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_settings_default(client):
    resp = client.get("/api/performance/settings")
    assert resp.status_code == 200
    d = resp.json()
    assert "streak_rule" in d
    assert d["streak_rule"]["logic"] in ("AND", "OR")


def test_save_settings(client):
    rule = {"conditions": [{"type": "tasks_done", "op": "gte", "value": 1}], "logic": "AND"}
    resp = client.post("/api/performance/settings", json={"streak_rule": rule})
    assert resp.status_code == 200
    assert resp.json()["streak_rule"]["logic"] == "AND"


def test_summary_empty_db(client):
    resp = client.get("/api/performance/summary")
    assert resp.status_code == 200
    d = resp.json()
    assert d["streak"] == 0
    assert d["tasks_done"] == 0
    assert d["eda_done"] == 0
    assert d["kpi_logs"] == 0
    assert isinstance(d["wip_avg_progress"], float)
    assert len(d["calendar"]) == 30


def test_summary_calendar_structure(client):
    resp = client.get("/api/performance/summary")
    cal = resp.json()["calendar"]
    assert len(cal) == 30
    for day in cal:
        assert "date" in day
        assert day["status"] in ("hit", "partial", "miss")


def test_summary_counts_done_tasks(client):
    client.post("/api/tasks", json={"title": "Done today", "status": "done"})
    resp = client.get("/api/performance/summary")
    assert resp.json()["tasks_done"] >= 1
