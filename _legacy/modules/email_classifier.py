import os
import re
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), encoding='utf-8')

USER_EMAIL = os.getenv("USER_EMAIL", "user@example.com").lower()
USER_NAME  = os.getenv("USER_NAME", "Test User")
BOSS_EMAIL = os.getenv("BOSS_EMAIL", "").lower()

# VIP senders — always classified as urgent regardless of content
# Can be extended via VIP_SENDERS env var (comma-separated)
_VIP_DEFAULT = {
    "colleague1@example.com",   # Data Manager
    "colleague2@example.com",   # Trưởng bộ phận Ops
}
_vip_env = {e.strip().lower() for e in os.getenv("VIP_SENDERS", "").split(",") if e.strip()}
VIP_SENDERS: set[str] = _VIP_DEFAULT | _vip_env
if BOSS_EMAIL:
    VIP_SENDERS.add(BOSS_EMAIL)

URGENT_KEYWORDS = [
    "urgent", "gấp", "khẩn", "asap", "cần ngay", "[urgent]",
    "deadline hôm nay", "quan trọng", "ngay bây giờ", "cần gấp",
    "khẩn cấp", "immediately", "ngay", "lập tức",
]
NORMAL_KEYWORDS = [
    "deadline", "cần confirm", "vui lòng", "nhờ anh", "nhờ chị",
    "phản hồi", "xác nhận", "please", "kindly", "nhờ", "confirm",
    "cần check", "cần review",
]


def _normalize(text: str) -> str:
    return text.lower()


def _score_email(email: dict) -> int:
    score = 0
    to_field   = _normalize(email.get("to", ""))
    cc_field   = _normalize(email.get("cc", ""))
    body       = _normalize(email.get("body", ""))
    subject    = _normalize(email.get("subject", ""))
    full_text  = f"{subject} {body}"
    user_email = USER_EMAIL
    user_name  = _normalize(USER_NAME)

    # @mention trong body
    if f"@{user_name}" in body or f"@phan trung hiếu" in body or f"@phan trung hieu" in body:
        score += 2

    # Direct To (không phải CC)
    if user_email in to_field:
        score += 2
    elif user_email in cc_field:
        score += 1

    # Keyword scoring
    for kw in URGENT_KEYWORDS:
        if kw in full_text:
            score += 3
            break  # chỉ cộng 1 lần cho urgent

    for kw in NORMAL_KEYWORDS:
        if kw in full_text:
            score += 1
            break  # chỉ cộng 1 lần cho normal

    return score


def classify_priority(email: dict, ai_classify_fn) -> str:
    """
    Phân loại email theo 4 bước.
    ai_classify_fn: callable(email) -> "urgent"|"normal"|"fyi", hoặc None để skip AI
    """
    # Bước 1: VIP sender → always urgent
    if email.get("sender_email", "").lower() in VIP_SENDERS:
        return "urgent"

    # Bước 2-3: Score
    score = _score_email(email)
    if score >= 4:
        return "urgent"
    if score >= 1:
        return "normal"

    # Bước 4: AI judgment
    if ai_classify_fn is not None:
        try:
            result = ai_classify_fn(email)
            if result in ("urgent", "normal", "fyi"):
                return result
        except Exception:
            pass

    return "fyi"
