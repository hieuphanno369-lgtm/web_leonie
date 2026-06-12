"""Generate weekly report from tasks + email history."""
from datetime import datetime, timedelta
from pathlib import Path


def _load_history() -> list[dict]:
    import json
    f = Path("data/email_history.json")
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def generate(days: int = 7) -> dict:
    from modules.task_manager import load_tasks

    today = datetime.now().date()
    cutoff = (today - timedelta(days=days)).isoformat()
    today_str = today.isoformat()

    tasks = load_tasks()

    created_week   = [t for t in tasks if t.get("created_at", "") >= cutoff]
    active_tasks   = [t for t in tasks if t.get("active")]
    overdue_tasks  = [t for t in tasks if t.get("active") and t.get("deadline", "9999") < today_str]
    inactive_tasks = [t for t in tasks if not t.get("active")]

    history = _load_history()
    week_emails = [e for e in history if e.get("processed_at", "") >= cutoff]
    emails_by_priority = {
        "urgent": [e for e in week_emails if e.get("priority") == "urgent"],
        "normal": [e for e in week_emails if e.get("priority") == "normal"],
        "fyi":    [e for e in week_emails if e.get("priority") == "fyi"],
    }

    return {
        "period":          f"{cutoff} → {today_str}",
        "days":            days,
        "tasks_created":   created_week,
        "tasks_active":    active_tasks,
        "tasks_overdue":   overdue_tasks,
        "tasks_archived":  inactive_tasks,
        "emails":          emails_by_priority,
        "generated_at":    datetime.now().isoformat(),
    }


def to_markdown(report: dict) -> str:
    c  = len(report["tasks_created"])
    a  = len(report["tasks_active"])
    o  = len(report["tasks_overdue"])
    ar = len(report["tasks_archived"])
    eu = len(report["emails"]["urgent"])
    en = len(report["emails"]["normal"])
    ef = len(report["emails"]["fyi"])
    et = eu + en + ef

    lines = [
        f"# 📊 Weekly Report",
        f"**Period:** {report['period']}  |  **Generated:** {report['generated_at'][:16]}",
        "",
        "## ✅ Tasks",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Created this week | {c} |",
        f"| Active | {a} |",
        f"| Overdue | {o} |",
        f"| Archived | {ar} |",
    ]

    if report["tasks_overdue"]:
        lines.append("\n### ⚠ Overdue")
        for t in report["tasks_overdue"][:10]:
            lines.append(f"- {t['task_name']} *(deadline: {t['deadline']})*")

    if report["tasks_created"]:
        lines.append("\n### ➕ Created this week")
        for t in report["tasks_created"][:10]:
            lines.append(f"- {t['task_name']} *(due: {t.get('deadline', '—')})*")

    lines += [
        "",
        "## 📧 Emails",
        f"| Priority | Count |",
        f"|----------|-------|",
        f"| 🔴 Urgent | {eu} |",
        f"| 🟡 Normal | {en} |",
        f"| 🟢 FYI | {ef} |",
        f"| **Total** | **{et}** |",
    ]

    if report["emails"]["urgent"]:
        lines.append("\n### 🔴 Urgent emails")
        for e in report["emails"]["urgent"][:5]:
            lines.append(f"- **{e.get('sender_name','?')}** — {e.get('subject','?')[:60]}")

    return "\n".join(lines)
