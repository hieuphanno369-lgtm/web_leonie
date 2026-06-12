import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open

import modules.email_history as eh


def _make_entry(entry_id: str, days_ago: int = 0) -> dict:
    dt = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {
        "entry_id": entry_id,
        "subject": f"Test {entry_id}",
        "sender_name": "Test Sender",
        "received_time": "2026-05-04T08:00:00",
        "priority": "normal",
        "processed_at": dt,
    }


def test_is_processed_true(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    entry = _make_entry("id-001")
    (tmp_path / "history.json").write_text(json.dumps([entry]), encoding="utf-8")
    assert eh.is_processed("id-001") is True


def test_is_processed_false(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")
    assert eh.is_processed("id-999") is False


def test_save_entry_appends(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")
    email = {
        "entry_id": "id-001",
        "subject": "Hello",
        "sender_name": "Boss",
        "received_time": "2026-05-04T08:00:00",
        "priority": "urgent",
    }
    eh.save_entry(email)
    data = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["entry_id"] == "id-001"
    assert "processed_at" in data[0]


def test_purge_old_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    entries = [
        _make_entry("old-1", days_ago=35),
        _make_entry("old-2", days_ago=31),
        _make_entry("new-1", days_ago=5),
    ]
    (tmp_path / "history.json").write_text(json.dumps(entries), encoding="utf-8")
    eh._purge_old_entries()
    data = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["entry_id"] == "new-1"
