"""
outlook_reader.py — Đọc email từ folder EmailQueue (sync từ OneDrive qua Power Automate).

Flow: Outlook → Power Automate → OneDrive/EmailQueue/*.json → Python đọc & xóa
"""

import os
import json
import re
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), encoding='utf-8')

USER_EMAIL = os.getenv("USER_EMAIL", "user@example.com")
USER_NAME  = os.getenv("USER_NAME", "Test User")

# Folder chứa file email do Power Automate ghi vào (sync từ OneDrive)
EMAIL_QUEUE_PATH = os.getenv(
    "EMAIL_QUEUE_PATH",
    r"C:\Users\user\OneDrive\EmailQueue"
)


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _read_queue_files() -> list[dict]:
    """Đọc tất cả file .json trong EmailQueue, trả về list email."""
    emails = []
    if not os.path.isdir(EMAIL_QUEUE_PATH):
        return emails

    for fname in os.listdir(EMAIL_QUEUE_PATH):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(EMAIL_QUEUE_PATH, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Chuẩn hoá các field
            body = data.get("body", "")
            body = _strip_html(body)[:2000]

            received_raw = data.get("received_time", "")
            try:
                received_dt  = datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
                received_str = received_dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
            except Exception:
                received_str = datetime.utcnow().isoformat()

            emails.append({
                "entry_id":     data.get("entry_id", fname),
                "subject":      data.get("subject", ""),
                "sender_name":  data.get("sender_name", ""),
                "sender_email": data.get("sender_email", "").lower(),
                "to":           data.get("to", ""),
                "cc":           data.get("cc", ""),
                "body":         body,
                "received_time": received_str,
                "folder":       "Inbox",
                "_source_file": fpath,   # để xóa sau khi xử lý
            })
        except Exception:
            continue

    return emails


def get_queue_status() -> dict:
    """Trả về thông tin chẩn đoán nguồn email cho UI."""
    queue_path   = EMAIL_QUEUE_PATH
    queue_exists = os.path.isdir(queue_path)
    queue_files  = len([f for f in os.listdir(queue_path) if f.endswith(".json")]) if queue_exists else 0

    win32_available = False
    try:
        import win32com.client  # noqa: F401
        win32_available = True
    except ImportError:
        pass

    # Source priority: queue nếu có file, win32com nếu queue rỗng
    if queue_files > 0:
        source = "queue"
    elif win32_available:
        source = "win32com"
    else:
        source = "queue"

    return {
        "source":          source,
        "queue_path":      queue_path,
        "queue_files":     queue_files,
        "queue_exists":    queue_exists,
        "win32_available": win32_available,
    }


def _read_via_win32com(hours: int = 48) -> list[dict]:
    """
    Đọc email trực tiếp từ Outlook Inbox qua win32com.
    Ưu tiên kết nối vào Outlook đang chạy (GetActiveObject) trước khi tạo mới.
    Không dùng Restrict filter (format AM/PM phụ thuộc locale).
    Iterate toàn bộ inbox (tối đa 500 items), lọc theo ngày thủ công.
    Raise exception để caller có thể hiển thị lỗi.
    """
    import pythoncom
    import win32com.client
    from datetime import datetime, timedelta

    # COM phải được init trên mỗi thread (Streamlit chạy callback trong thread riêng)
    pythoncom.CoInitialize()
    cutoff = datetime.now() - timedelta(hours=hours)
    emails: list[dict] = []

    # Dùng Outlook đang chạy trước (đã được user trust), fallback sang Dispatch
    try:
        outlook = win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        outlook = win32com.client.Dispatch("Outlook.Application")

    ns    = outlook.GetNamespace("MAPI")
    inbox = ns.GetDefaultFolder(6)   # olFolderInbox = 6

    items = inbox.Items
    items.Sort("[ReceivedTime]", True)   # newest first

    try:
        for i, item in enumerate(items):
            if i >= 500 or len(emails) >= 150:
                break
            try:
                # Lấy class (43 = MailItem). Bỏ qua meeting requests, tasks...
                if getattr(item, "Class", 43) != 43:
                    continue

                raw = item.ReceivedTime
                received_dt = datetime(
                    raw.year, raw.month, raw.day,
                    raw.hour, raw.minute, raw.second,
                )

                # Items đã sort newest-first → gặp cũ hơn cutoff là hết
                if received_dt < cutoff:
                    break

                body = _strip_html(item.Body or "")[:2000]
                emails.append({
                    "entry_id":      item.EntryID,
                    "subject":       item.Subject or "",
                    "sender_name":   item.SenderName or "",
                    "sender_email":  (item.SenderEmailAddress or "").lower(),
                    "to":            item.To or "",
                    "cc":            item.CC or "",
                    "body":          body,
                    "received_time": received_dt.isoformat(),
                    "folder":        "Inbox",
                    "_source_file":  None,
                })
            except Exception:
                continue
    finally:
        pythoncom.CoUninitialize()

    return emails


def _read_via_win32com_safe(hours: int = 48) -> tuple[list[dict], str]:
    """Wrapper trả về (emails, error_msg). error_msg rỗng nếu thành công."""
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return [], "pywin32 chưa được cài đặt"
    try:
        return _read_via_win32com(hours), ""
    except Exception as e:
        return [], str(e)


def get_recent_emails(hours: int = 48) -> list[dict]:
    """
    Lấy email gần đây:
    1. Power Automate queue (EmailQueue/*.json) — nếu có file
    2. win32com trực tiếp từ Outlook Inbox     — fallback khi queue rỗng
    Raise exception nếu win32com thất bại (để UI hiển thị lỗi cụ thể).
    """
    queue = _read_queue_files()
    if queue:
        return queue
    # Queue rỗng → đọc thẳng từ Outlook (có thể raise)
    return _read_via_win32com(hours)


def mark_processed(email: dict) -> None:
    """Xóa file JSON sau khi đã xử lý xong email."""
    fpath = email.get("_source_file")
    if fpath and os.path.exists(fpath):
        try:
            os.remove(fpath)
        except Exception:
            pass


def get_sent_emails(limit: int = 300) -> list[dict]:
    """Sent emails — chưa hỗ trợ qua Power Automate, trả về rỗng."""
    return []
