import json
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = Path(__file__).parent.parent / "data" / "email_history.json"
RETENTION_DAYS = 30


def _load() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict]) -> None:
    HISTORY_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _purge_old_entries() -> None:
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat()
    entries = [e for e in _load() if e.get("processed_at", "") >= cutoff]
    _save(entries)


def is_processed(entry_id: str) -> bool:
    return any(e["entry_id"] == entry_id for e in _load())


def save_entry(email: dict) -> None:
    _purge_old_entries()
    entries = _load()
    entries.append({
        "entry_id": email["entry_id"],
        "subject": email["subject"],
        "sender_name": email["sender_name"],
        "received_time": email["received_time"],
        "priority": email.get("priority", "fyi"),
        "processed_at": datetime.now().isoformat(),
    })
    _save(entries)
