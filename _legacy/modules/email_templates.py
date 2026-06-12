"""Email template CRUD — stores in data/email_templates.json."""
import json
import uuid
from pathlib import Path
from datetime import datetime

TEMPLATES_FILE = Path("data/email_templates.json")
CATEGORIES = ["General", "Follow-up", "Report", "Data", "Support"]


def load_templates() -> list[dict]:
    if not TEMPLATES_FILE.exists():
        _seed()
    try:
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(templates: list[dict]) -> None:
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_template(name: str, subject: str, body: str, category: str = "General") -> dict:
    templates = load_templates()
    t = {
        "id":         str(uuid.uuid4())[:8],
        "name":       name,
        "subject":    subject,
        "body":       body,
        "category":   category,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    templates.append(t)
    _save(templates)
    return t


def delete_template(tid: str) -> None:
    _save([t for t in load_templates() if t["id"] != tid])


def _seed() -> None:
    seeds = [
        {
            "id": "tmpl001",
            "name": "Xác nhận đã nhận",
            "subject": "Re: {subject}",
            "body": (
                "Chào {sender_name},\n\n"
                "Em đã nhận được email và sẽ xem xét sớm nhất có thể.\n\n"
                "Trân trọng,\nHiếu"
            ),
            "category": "General",
            "created_at": "2026-05-08",
        },
        {
            "id": "tmpl002",
            "name": "Follow-up chờ phản hồi",
            "subject": "Follow-up: {subject}",
            "body": (
                "Chào {sender_name},\n\n"
                "Em muốn follow-up về email trước liên quan đến {subject}. "
                "Anh/chị có thể cho em biết tiến độ không ạ?\n\n"
                "Trân trọng,\nHiếu"
            ),
            "category": "Follow-up",
            "created_at": "2026-05-08",
        },
        {
            "id": "tmpl003",
            "name": "Báo cáo hoàn thành",
            "subject": "Completed: {task_name}",
            "body": (
                "Chào team,\n\n"
                "Em đã hoàn thành {task_name}.\n\n"
                "Kết quả:\n- \n\n"
                "Vui lòng review và feedback nếu cần.\n\n"
                "Trân trọng,\nHiếu"
            ),
            "category": "Report",
            "created_at": "2026-05-08",
        },
        {
            "id": "tmpl004",
            "name": "Gửi data / báo cáo",
            "subject": "Data: {report_name} — {date}",
            "body": (
                "Chào {recipient},\n\n"
                "Em gửi {report_name} theo yêu cầu.\n\n"
                "File đính kèm: {filename}\n"
                "Period: {period}\n\n"
                "Vui lòng liên hệ nếu cần thêm thông tin.\n\n"
                "Trân trọng,\nHiếu"
            ),
            "category": "Data",
            "created_at": "2026-05-08",
        },
        {
            "id": "tmpl005",
            "name": "Nhờ hỗ trợ / escalation",
            "subject": "Cần hỗ trợ: {subject}",
            "body": (
                "Chào anh/chị,\n\n"
                "Em cần nhờ hỗ trợ về vấn đề sau:\n\n"
                "{description}\n\n"
                "Mong nhận được phản hồi sớm.\n\n"
                "Trân trọng,\nHiếu"
            ),
            "category": "Support",
            "created_at": "2026-05-08",
        },
        {
            "id": "tmpl006",
            "name": "Cảm ơn và xác nhận",
            "subject": "Thank you — {subject}",
            "body": (
                "Chào {sender_name},\n\n"
                "Cảm ơn anh/chị đã phản hồi.\n\n"
                "Em đã ghi nhận và sẽ tiến hành {action} trong thời gian sớm nhất.\n\n"
                "Trân trọng,\nHiếu"
            ),
            "category": "General",
            "created_at": "2026-05-08",
        },
    ]
    _save(seeds)
