"""
discord_notifier.py — Gửi thông báo Discord theo định dạng đồng bộ với CHOOPER web.
Icons dùng Unicode giống sidebar/cards: ⬡ ◈ ◆ ◇ ⚡ ⏱ ⬢ ◉
"""
import os
import requests
from datetime import date, datetime, timedelta
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), encoding="utf-8")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Colors (đồng bộ với PRIORITY_COLORS trong app.py) ──────────────────────
COLOR_HIGH   = 16722005  # #ff2d55 → high
COLOR_MEDIUM = 16621322  # #ff9f0a → medium
COLOR_LOW    = 3199320   # #30d158 → low
COLOR_ADHOC  = 6608639   # #64d2ff → ad-hoc
COLOR_GREEN  = 5763719   # confirm / success
COLOR_YELLOW = 15844367  # reminder / warning
COLOR_RED    = 15548997  # urgent / overdue
COLOR_ORANGE = 15105570  # normal email
COLOR_TEAL   = 1752220   # fyi / info

PRIORITY_COLORS = {
    "high":   COLOR_HIGH,
    "medium": COLOR_MEDIUM,
    "low":    COLOR_LOW,
    "ad-hoc": COLOR_ADHOC,
}

PRIORITY_ICONS = {
    "high":   "◈ High",
    "medium": "◆ Medium",
    "low":    "◇ Low",
    "ad-hoc": "⚡ Ad-hoc",
}

RECUR_LABELS = {
    None:      "—",
    "monthly": "↺ Hằng tháng",
    "yearly":  "↻ Hằng năm",
}

_MAX_EMBED_CHARS = 3800
APP_FOOTER = "⬡ CHOOPER"


def _post(payload: dict) -> bool:
    if not DISCORD_WEBHOOK_URL:
        print("⚠  DISCORD_WEBHOOK_URL chưa cấu hình trong .env")
        return False
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"⚠  Discord gửi thất bại: {e}")
        return False


# ── Task notifications ──────────────────────────────────────────────────────

def send_confirm(task: dict) -> bool:
    """Xác nhận tạo task mới — không kèm checklist AI."""
    color     = PRIORITY_COLORS.get(task.get("category_raw", "low"), COLOR_GREEN)
    priority  = PRIORITY_ICONS.get(task.get("category_raw", "low"), "◇ Low")
    recur     = RECUR_LABELS.get(task.get("recur"), "—")
    note      = task.get("note", "(không có)")
    if note == "(none)":
        note = "(không có)"
    tags_raw  = task.get("tags", [])
    tags_line = "  ".join(f"`{t}`" for t in tags_raw) if tags_raw else "—"

    fields = [
        {"name": "◈  Mức độ",   "value": priority,              "inline": True},
        {"name": "⏱  Deadline", "value": f"`{task['deadline']}`", "inline": True},
        {"name": "↺  Lặp lại",  "value": recur,                  "inline": True},
        {"name": "//  Ghi chú",  "value": note,                   "inline": False},
    ]
    if tags_raw:
        fields.append({"name": "#  Tags", "value": tags_line, "inline": False})

    payload = {
        "embeds": [{
            "title":       ">>  Task mới đã tạo",
            "description": f"### {task['task_name']}",
            "color":       color,
            "fields":      fields,
            "footer":      {"text": f"{APP_FOOTER}  ·  {task.get('created_at', date.today().isoformat())}"},
        }]
    }
    return _post(payload)


def send_reminder(task: dict) -> bool:
    """Reminder hằng ngày cho một task."""
    today     = date.today()
    deadline  = task.get("deadline", "9999-99-99")
    try:
        days_left = (date.fromisoformat(deadline) - today).days
    except Exception:
        days_left = 99

    if days_left < 0:
        urgency = f"[!]  Trễ {-days_left} ngày"
        color   = COLOR_RED
    elif days_left == 0:
        urgency = "[~]  Deadline hôm nay"
        color   = COLOR_YELLOW
    elif days_left <= 2:
        urgency = f"[~]  Còn {days_left} ngày"
        color   = COLOR_YELLOW
    else:
        urgency = f"[ok]  Còn {days_left} ngày"
        color   = PRIORITY_COLORS.get(task.get("category_raw", "low"), COLOR_LOW)

    priority = PRIORITY_ICONS.get(task.get("category_raw", "low"), "◇ Low")
    recur    = RECUR_LABELS.get(task.get("recur"), "—")
    note     = task.get("note", "(không có)")
    if note == "(none)":
        note = "(không có)"
    tags_raw  = task.get("tags", [])
    tags_line = "  ".join(f"`{t}`" for t in tags_raw) if tags_raw else "—"

    fields = [
        {"name": "◈  Mức độ",    "value": priority,               "inline": True},
        {"name": "⏱  Deadline",  "value": f"`{deadline}`",         "inline": True},
        {"name": "◉  Trạng thái","value": f"`{urgency}`",          "inline": True},
        {"name": "↺  Lặp lại",   "value": recur,                   "inline": True},
        {"name": "//  Ghi chú",  "value": note,                    "inline": False},
    ]
    if tags_raw:
        fields.append({"name": "#  Tags", "value": tags_line, "inline": False})

    payload = {
        "embeds": [{
            "title":       f"▸  {task['task_name']}",
            "color":       color,
            "fields":      fields,
            "footer":      {"text": f"{APP_FOOTER}  ·  Reminder {today.isoformat()}"},
        }]
    }
    return _post(payload)


def send_all_reminders(tasks: list[dict]) -> None:
    if not tasks:
        print("📭  Không có task active.")
        return
    for task in tasks:
        ok = send_reminder(task)
        print(f"  {'✅' if ok else '❌'}  {task['task_name']}")


def send_deadline_alert(tasks: list[dict]) -> None:
    """Alert cho task due today / tomorrow."""
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    today_s, tomorrow_s = today.isoformat(), tomorrow.isoformat()

    due_today    = [t for t in tasks if t.get("deadline") == today_s]
    due_tomorrow = [t for t in tasks if t.get("deadline") == tomorrow_s]

    if not due_today and not due_tomorrow:
        return

    lines = []
    if due_today:
        lines.append(f"**[!]  DUE TODAY — {len(due_today)} task**")
        for t in due_today:
            p = PRIORITY_ICONS.get(t.get("category_raw", "low"), "◇")
            lines.append(f"  ▸  **{t['task_name']}**  ·  {p}")
    if due_tomorrow:
        lines.append(f"\n**[~]  DUE TOMORROW — {len(due_tomorrow)} task**")
        for t in due_tomorrow:
            p = PRIORITY_ICONS.get(t.get("category_raw", "low"), "◇")
            lines.append(f"  ▹  {t['task_name']}  ·  {p}")

    color = COLOR_RED if due_today else COLOR_YELLOW
    _post({
        "embeds": [{
            "title":       "⏱  Deadline Alert",
            "description": "\n".join(lines),
            "color":       color,
            "footer":      {"text": f"{APP_FOOTER}  ·  {today_s}"},
        }]
    })


# ── Email digest ────────────────────────────────────────────────────────────

_PRIORITY_CONFIG = {
    "urgent": ("[!]  URGENT", COLOR_RED),
    "normal": ("[~]  NORMAL", COLOR_ORANGE),
    "fyi":    ("[i]  FYI",    COLOR_TEAL),
}


def _format_email_block(email: dict) -> str:
    replies  = email.get("replies", [])
    reply_ln = "  ".join(f"`{i+1}. {r}`" for i, r in enumerate(replies[:3]))
    summary  = email.get("summary", "")[:200]
    subj     = email.get("subject", "")[:80]
    sender   = email.get("sender_name", "?")
    return (
        f"**{sender}** — {subj}\n"
        f"📝 {summary}\n"
        + (f"💬 {reply_ln}" if reply_ln else "")
    )


def send_email_digest(classified: dict) -> None:
    now   = datetime.now().strftime("%d/%m/%Y  %H:%M")
    total = sum(len(v) for v in classified.values())

    if total == 0:
        _post({"embeds": [{
            "title":       f">>  Email Digest — {now}",
            "description": "[ ok ]  Không có email mới hôm nay.",
            "color":       COLOR_TEAL,
            "footer":      {"text": APP_FOOTER},
        }]})
        return

    sections = []
    for priority in ("urgent", "normal", "fyi"):
        emails = classified.get(priority, [])
        if not emails:
            continue
        label, _ = _PRIORITY_CONFIG[priority]
        header   = f"**{label}  ({len(emails)} emails)**"
        blocks   = [_format_email_block(e) for e in emails]
        sections.append((header, blocks))

    current_desc   = f">> **Email Digest — {now}**\n{'─' * 28}\n\n"
    embeds_to_send = []

    for header, blocks in sections:
        section_text = f"{header}\n" + "\n\n".join(f"┌ {b}" for b in blocks) + "\n\n"
        if len(current_desc) + len(section_text) > _MAX_EMBED_CHARS:
            embeds_to_send.append(current_desc.strip())
            current_desc = section_text
        else:
            current_desc += section_text

    if current_desc.strip():
        embeds_to_send.append(current_desc.strip())

    top_color = COLOR_RED if classified.get("urgent") else (
        COLOR_ORANGE if classified.get("normal") else COLOR_TEAL
    )

    for i, desc in enumerate(embeds_to_send):
        _post({
            "embeds": [{
                "description": desc,
                "color":       top_color if i == 0 else COLOR_TEAL,
                "footer":      {"text": f"{APP_FOOTER}  ·  {i+1}/{len(embeds_to_send)}"},
            }]
        })
