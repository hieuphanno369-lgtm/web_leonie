"""
daily_briefing.py — Tạo bản tóm tắt buổi sáng từ tasks + email history.
Rule-based nhanh, AI tùy chọn.
"""
from datetime import date, timedelta
from pathlib import Path
import json


def _load_email_history() -> list[dict]:
    f = Path("data/email_history.json")
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def build_context(tasks: list[dict]) -> dict:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    due_today  = [t for t in tasks if t.get("active") and t.get("deadline") == today]
    overdue    = [t for t in tasks if t.get("active") and t.get("deadline", "9999") < today]
    due_week   = [
        t for t in tasks
        if t.get("active")
        and today < t.get("deadline", "9999")
        <= (date.today() + timedelta(days=7)).isoformat()
    ]

    history = _load_email_history()
    urgent_unread = [
        e for e in history
        if e.get("priority") == "urgent"
        and e.get("processed_at", "") >= yesterday
    ]

    return {
        "today":        today,
        "due_today":    due_today,
        "overdue":      overdue,
        "due_week":     due_week,
        "urgent_emails": urgent_unread,
    }


def rule_based_briefing(ctx: dict) -> str:
    lines = [f"📅 **Briefing — {ctx['today']}**\n"]

    if ctx["overdue"]:
        lines.append(f"🔴 **{len(ctx['overdue'])} task quá hạn:**")
        for t in ctx["overdue"][:5]:
            lines.append(f"  • {t['task_name']} *(deadline: {t['deadline']})*")

    if ctx["due_today"]:
        lines.append(f"\n⏱ **{len(ctx['due_today'])} task hôm nay:**")
        for t in ctx["due_today"]:
            lines.append(f"  • {t['task_name']}")
    else:
        lines.append("\n✅ Không có task deadline hôm nay.")

    if ctx["due_week"]:
        lines.append(f"\n📋 **{len(ctx['due_week'])} task trong tuần:**")
        for t in ctx["due_week"][:5]:
            lines.append(f"  • {t['task_name']} *(due {t['deadline']})*")

    if ctx["urgent_emails"]:
        lines.append(f"\n📧 **{len(ctx['urgent_emails'])} email urgent chưa xử lý:**")
        for e in ctx["urgent_emails"][:3]:
            lines.append(f"  • **{e.get('sender_name','?')}** — {e.get('subject','?')[:50]}")

    return "\n".join(lines)


def ai_briefing(ctx: dict) -> str:
    """AI-generated briefing — fallback về rule_based nếu fail."""
    from modules.ai_client import call_ai

    due_today_text = "\n".join(
        f"- {t['task_name']} [{t['category_label']}]" for t in ctx["due_today"]
    ) or "Không có"

    overdue_text = "\n".join(
        f"- {t['task_name']} (quá hạn {t['deadline']})" for t in ctx["overdue"][:5]
    ) or "Không có"

    email_text = "\n".join(
        f"- {e.get('sender_name','?')}: {e.get('subject','?')}" for e in ctx["urgent_emails"][:3]
    ) or "Không có"

    prompt = (
        f"Bạn là trợ lý làm việc. Hãy tạo briefing buổi sáng ngắn gọn (5-8 dòng) bằng tiếng Việt "
        f"cho ngày {ctx['today']}. Nêu những ưu tiên quan trọng nhất cần làm hôm nay.\n\n"
        f"Tasks hôm nay:\n{due_today_text}\n\n"
        f"Tasks quá hạn:\n{overdue_text}\n\n"
        f"Email urgent gần đây:\n{email_text}\n\n"
        f"Viết ngắn gọn, hành động, không giải thích dài dòng."
    )
    try:
        return call_ai(prompt, max_tokens=250)
    except Exception:
        return rule_based_briefing(ctx)


def generate(tasks: list[dict], use_ai: bool = False) -> str:
    ctx = build_context(tasks)
    if use_ai:
        return ai_briefing(ctx)
    return rule_based_briefing(ctx)
