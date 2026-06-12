import os
import requests
from dotenv import load_dotenv, find_dotenv, dotenv_values

_dotenv_path = find_dotenv()
load_dotenv(_dotenv_path, encoding='utf-8')
_dotenv_raw = dotenv_values(_dotenv_path, encoding='utf-8')

def _env(key: str, default: str = "") -> str:
    """Read env var, falling back to .env file directly if env var is empty string."""
    val = os.getenv(key, "")
    return val if val else _dotenv_raw.get(key, default)

ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
OLLAMA_BASE_URL   = _env("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL      = _env("OLLAMA_MODEL", "llama3")

_SUMMARY_LENGTH = {
    "urgent": "2 câu đầy đủ",
    "normal": "1 câu ngắn gọn",
    "fyi":    "1 câu rất ngắn",
}


def _get_claude_client():
    import anthropic
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY chưa được cấu hình")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _ollama_available() -> bool:
    try:
        requests.get(OLLAMA_BASE_URL, timeout=3)
        return True
    except Exception:
        return False


def _call_claude(prompt: str, max_tokens: int = 200) -> str:
    client = _get_claude_client()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _call_ai(prompt: str, max_tokens: int = 200) -> str:
    """Claude (priority) → Ollama fallback → raise with details."""
    claude_err = ollama_err = None

    if ANTHROPIC_API_KEY:
        try:
            return _call_claude(prompt, max_tokens)
        except Exception as e:
            claude_err = str(e)

    if _ollama_available():
        try:
            return _call_ollama(prompt)
        except Exception as e:
            ollama_err = str(e)

    details = []
    if claude_err:
        details.append(f"Claude: {claude_err}")
    if ollama_err:
        details.append(f"Ollama: {ollama_err}")
    if not ANTHROPIC_API_KEY and not _ollama_available():
        details.append("Chưa cấu hình ANTHROPIC_API_KEY và Ollama không chạy")

    raise RuntimeError("Không có AI nào khả dụng" + (f" ({'; '.join(details)})" if details else ""))


def _rule_summary(email: dict) -> str:
    return f"{email['sender_name']} — {email['subject']}"


def summarize_email(email: dict, priority: str) -> str:
    """Tóm tắt email bằng tiếng Việt. Fallback về rule-based nếu AI fail."""
    length = _SUMMARY_LENGTH.get(priority, "1 câu")
    prompt = (
        f"Tóm tắt email sau bằng tiếng Việt trong {length}. "
        f"Chỉ nêu nội dung chính, không giải thích, không tiêu đề.\n\n"
        f"Từ: {email['sender_name']}\n"
        f"Tiêu đề: {email['subject']}\n"
        f"Nội dung: {email.get('body', '')[:500]}"
    )
    try:
        return _call_ai(prompt, max_tokens=150)
    except Exception:
        return _rule_summary(email)


def call_ai(prompt: str, max_tokens: int = 200) -> str:
    """Public wrapper around _call_ai for use by other modules."""
    return _call_ai(prompt, max_tokens)


def classify_email_ai(email: dict) -> str:
    """Dùng AI để phân loại email khi keyword scoring không rõ ràng."""
    prompt = (
        "Phân loại email này theo 1 trong 3 mức: urgent, normal, fyi.\n"
        "Chỉ trả về đúng 1 từ: urgent, normal, hoặc fyi. Không giải thích.\n\n"
        f"Tiêu đề: {email['subject']}\n"
        f"Nội dung: {email.get('body', '')[:300]}"
    )
    try:
        raw = _call_ai(prompt, max_tokens=10).lower().strip()
        for level in ("urgent", "normal", "fyi"):
            if level in raw:
                return level
        return "fyi"
    except Exception:
        return "fyi"
