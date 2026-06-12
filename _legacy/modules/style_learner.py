import json
import random
from datetime import datetime
from pathlib import Path
from modules.ai_client import _call_ai

STYLE_FILE = Path(__file__).parent.parent / "data" / "style_profile.json"
SAMPLE_SIZE = 20


def load_style_profile() -> str:
    """Trả về style_summary string, hoặc chuỗi rỗng nếu chưa có."""
    if not STYLE_FILE.exists():
        return ""
    try:
        data = json.loads(STYLE_FILE.read_text(encoding="utf-8"))
        return data.get("style_summary", "")
    except Exception:
        return ""


def learn_from_sent(sent_emails: list[dict]) -> str:
    """
    Nhận danh sách sent emails, phân tích phong cách, lưu style_profile.json.
    Trả về style_summary string.
    """
    if not sent_emails:
        return ""

    sample = random.sample(sent_emails, min(SAMPLE_SIZE, len(sent_emails)))
    emails_text = "\n---\n".join(
        f"Tiêu đề: {e['subject']}\nNội dung: {e['body'][:400]}"
        for e in sample
    )

    prompt = (
        "Phân tích phong cách viết email của người này dựa trên các email mẫu bên dưới.\n"
        "Tóm tắt trong 3-5 câu tiếng Việt về: cách mở đầu, cách kết thúc, "
        "mức độ formal/informal, từ xưng hô thường dùng, độ dài câu.\n"
        "Chỉ mô tả phong cách, không nhận xét chất lượng.\n\n"
        f"{emails_text}"
    )

    try:
        style_summary = _call_ai(prompt, max_tokens=300)
    except Exception:
        style_summary = "Phong cách viết chuyên nghiệp, lịch sự, ngắn gọn bằng tiếng Việt."

    profile = {
        "learned_at": datetime.now().isoformat(),
        "email_count": len(sent_emails),
        "style_summary": style_summary,
    }
    STYLE_FILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return style_summary
