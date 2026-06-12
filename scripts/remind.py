"""
remind.py — Gửi Discord reminder cho tất cả task active.
Chạy bởi Windows Task Scheduler, không cần terminal mở.
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo import đúng thư mục dù chạy từ đâu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from modules.task_manager import get_active_tasks, deactivate_expired
from modules.discord_notifier import send_all_reminders

if __name__ == "__main__":
    log_path = os.path.join(BASE_DIR, "data", "remind.log")
    try:
        deactivate_expired()
        tasks = get_active_tasks()
        send_all_reminders(tasks)
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"{datetime.now():%Y-%m-%d %H:%M} OK — {len(tasks)} task(s)\n")
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"{datetime.now():%Y-%m-%d %H:%M} ERROR — {e}\n")
