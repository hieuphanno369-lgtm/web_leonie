"""
scheduler.py — Chạy nền, gửi Discord reminder theo lịch.
Chạy: python scheduler.py

Giữ cửa sổ này mở (hoặc chạy ngầm).
Giờ nhắc nhở cấu hình trong .env:
  REMINDER_TIME=08:00
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os
import time
import schedule
from datetime import date
from dotenv import load_dotenv, find_dotenv
from rich.console import Console

from modules.task_manager import get_active_tasks, deactivate_expired
from modules.discord_notifier import send_all_reminders, send_email_digest, send_deadline_alert
from modules.email_digest import run_digest
from modules.style_learner import learn_from_sent

load_dotenv(find_dotenv(), encoding='utf-8')

REMINDER_TIME = os.getenv("REMINDER_TIME", "08:00")

console = Console()


def run_reminders(label: str) -> None:
    today = date.today().isoformat()
    console.print(f"\n[cyan][{today} {label}][/cyan] Đang chạy reminder…")

    archived, renewed = deactivate_expired()
    if archived:
        console.print(f"  ♻️  Đã archive {archived} task hết hạn.")
    if renewed:
        console.print(f"  🔄 Đã gia hạn {renewed} task định kỳ.")

    tasks = get_active_tasks()
    console.print(f"  📋 {len(tasks)} task active.")
    send_all_reminders(tasks)


def run_deadline_alert() -> None:
    today = date.today().isoformat()
    console.print(f"\n[cyan][{today}][/cyan] Đang kiểm tra deadline sắp tới…")
    try:
        from modules.task_manager import get_active_tasks
        tasks = get_active_tasks()
        send_deadline_alert(tasks)
        console.print("  ✅ Đã gửi deadline alert.")
    except Exception as e:
        console.print(f"  ❌ Deadline alert lỗi: {e}")


def run_email_digest() -> None:
    today = date.today().isoformat()
    console.print(f"\n[cyan][{today} 08:00][/cyan] Đang chạy Email Digest…")
    try:
        classified = run_digest(hours=24)
        total = sum(len(v) for v in classified.values())
        console.print(f"  📧 Tìm thấy {total} email mới")
        console.print(f"     🔴 Urgent: {len(classified['urgent'])}")
        console.print(f"     🟡 Normal: {len(classified['normal'])}")
        console.print(f"     🟢 FYI:    {len(classified['fyi'])}")
        send_email_digest(classified)
        console.print("  ✅ Đã gửi Discord digest.")
    except Exception as e:
        console.print(f"  ❌ Email digest lỗi: {e}")


def run_style_relearn() -> None:
    today = date.today().isoformat()
    console.print(f"\n[cyan][{today}][/cyan] Đang re-learn phong cách viết email…")
    try:
        from modules.outlook_reader import get_sent_emails
        sent = get_sent_emails(limit=300)
        summary = learn_from_sent(sent)
        console.print(f"  ✅ Đã học từ {len(sent)} email. Style: {summary[:80]}…")
    except Exception as e:
        console.print(f"  ❌ Style re-learn lỗi: {e}")


def setup_schedule() -> None:
    schedule.every().day.at(REMINDER_TIME).do(run_reminders, label=REMINDER_TIME)

    EMAIL_DIGEST_TIME  = os.getenv("EMAIL_DIGEST_TIME", "08:00")
    DEADLINE_ALERT_TIME = os.getenv("DEADLINE_ALERT_TIME", "08:30")

    schedule.every().day.at(EMAIL_DIGEST_TIME).do(run_email_digest)
    schedule.every().day.at(DEADLINE_ALERT_TIME).do(run_deadline_alert)
    schedule.every().sunday.at("07:00").do(run_style_relearn)

    console.print(f"[bold green]🕐 Scheduler đang chạy.[/bold green]")
    console.print(f"   Reminder lúc:       [yellow]{REMINDER_TIME}[/yellow] hàng ngày")
    console.print(f"   Email digest lúc:   [yellow]{EMAIL_DIGEST_TIME}[/yellow] hàng ngày")
    console.print(f"   Deadline alert lúc: [yellow]{DEADLINE_ALERT_TIME}[/yellow] hàng ngày")
    console.print(f"   Style re-learn:     [yellow]Chủ nhật 07:00[/yellow]")
    console.print("   Nhấn [red]Ctrl+C[/red] để dừng.\n")


def send_startup_notify() -> None:
    """Gửi Discord thông báo scheduler đã khởi động."""
    import requests
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return
    from datetime import datetime
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    payload = {
        "embeds": [{
            "title": "🟢 Scheduler đã khởi động",
            "description": (
                f"**Task Tracker** đang chạy lúc **{now}**\n\n"
                f"⏰ Reminder: **{REMINDER_TIME}** hàng ngày\n"
                f"📧 Email digest: **{os.getenv('EMAIL_DIGEST_TIME', '08:00')}** hàng ngày"
            ),
            "color": 3066993,  # xanh lá
        }]
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    setup_schedule()
    send_startup_notify()
    while True:
        schedule.run_pending()
        time.sleep(30)
