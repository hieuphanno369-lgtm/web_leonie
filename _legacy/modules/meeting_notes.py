"""Meeting notes CRUD — stores in data/meeting_notes.json."""
import json
import uuid
from pathlib import Path
from datetime import datetime

NOTES_FILE = Path("data/meeting_notes.json")


def load_notes() -> list[dict]:
    if not NOTES_FILE.exists():
        return []
    try:
        return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(notes: list[dict]) -> None:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTES_FILE.write_text(
        json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_note(
    title: str,
    date: str,
    attendees: str,
    agenda: str,
    decisions: str,
    action_items: list[dict],
) -> dict:
    """
    action_items: [{"task": str, "owner": str, "due": str}, ...]
    """
    notes = load_notes()
    note = {
        "id":           str(uuid.uuid4())[:8],
        "title":        title,
        "date":         date or datetime.now().strftime("%Y-%m-%d"),
        "attendees":    attendees,
        "agenda":       agenda,
        "decisions":    decisions,
        "action_items": action_items,
        "created_at":   datetime.now().isoformat(),
    }
    notes.insert(0, note)
    _save(notes)
    return note


def update_note(nid: str, **fields) -> None:
    notes = load_notes()
    for n in notes:
        if n["id"] == nid:
            n.update(fields)
    _save(notes)


def delete_note(nid: str) -> None:
    _save([n for n in load_notes() if n["id"] != nid])


def export_markdown(note: dict) -> str:
    lines = [
        f"# {note['title']}",
        f"**Date:** {note['date']}",
        f"**Attendees:** {note['attendees']}",
        "",
        "## Agenda",
        note.get("agenda", ""),
        "",
        "## Decisions",
        note.get("decisions", ""),
        "",
        "## Action Items",
    ]
    for item in note.get("action_items", []):
        lines.append(f"- [ ] {item.get('task','')} — **{item.get('owner','')}** (due {item.get('due','')})")
    return "\n".join(lines)
