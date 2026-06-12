import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

WEBHOOK = "https://discord.com/api/webhooks/123/abc"

def test_get_settings_default(client):
    resp = client.get("/api/discord/settings")
    assert resp.status_code == 200
    d = resp.json()
    assert d["webhook_url"] is None
    assert d["rule_overdue"] is True
    assert d["rule_done"] is False

def test_upsert_settings(client):
    resp = client.post("/api/discord/settings", json={"webhook_url": WEBHOOK, "rule_done": True})
    assert resp.status_code == 200
    d = resp.json()
    assert d["webhook_url"] == WEBHOOK
    assert d["rule_done"] is True

def test_send_no_webhook(client):
    resp = client.post("/api/discord/send", json={"message": "hello"})
    assert resp.status_code == 400

def test_send_message(client):
    client.post("/api/discord/settings", json={"webhook_url": WEBHOOK})
    with patch("routers.discord_notify._send_webhook") as mock_send:
        resp = client.post("/api/discord/send", json={"message": "Test msg"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_send.assert_called_once_with(WEBHOOK, "Test msg")

def test_check_no_webhook(client):
    assert client.post("/api/discord/check").status_code == 400

def test_check_overdue_sends_notification(client):
    client.post("/api/discord/settings", json={"webhook_url": WEBHOOK, "rule_overdue": True})
    # Create an overdue task
    client.post("/api/tasks", json={"title": "Old task", "due_date": "2020-01-01", "status": "todo"})
    with patch("routers.discord_notify._send_webhook") as mock_send:
        resp = client.post("/api/discord/check")
        assert resp.status_code == 200
        assert resp.json()["sent"] >= 1
        mock_send.assert_called()

def test_check_no_overdue_sends_nothing(client):
    client.post("/api/discord/settings", json={"webhook_url": WEBHOOK, "rule_overdue": True})
    # No tasks created → nothing to notify
    with patch("routers.discord_notify._send_webhook") as mock_send:
        resp = client.post("/api/discord/check")
        assert resp.json()["sent"] == 0
        mock_send.assert_not_called()

def test_check_updates_last_checked(client):
    client.post("/api/discord/settings", json={"webhook_url": WEBHOOK})
    with patch("routers.discord_notify._send_webhook"):
        client.post("/api/discord/check")
    settings = client.get("/api/discord/settings").json()
    assert settings["last_checked"] is not None
