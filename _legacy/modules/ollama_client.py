import os
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), encoding='utf-8')

OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _build_prompt(task_name: str, category_label: str, deadline: str, note: str, obsidian_context: str) -> str:
    context_block = (
        f"\n\nTài liệu liên quan từ vault Obsidian:\n{obsidian_context}\n"
        if obsidian_context
        and "(không tìm" not in obsidian_context
        and "(vault" not in obsidian_context
        else ""
    )
    return (
        f"Task: '{task_name}'. Mức độ: {category_label}. Deadline: {deadline}. Ghi chú: {note}."
        f"{context_block}"
        "Liệt kê đúng 2-3 việc cần làm nhất để hoàn thành task này. "
        "Quy tắc BẮT BUỘC: chỉ trả lời bằng các dòng ✅, mỗi dòng dưới 12 từ tiếng Việt, "
        "không tiêu đề, không giải thích, không ngày tháng, không đánh số. "
        "Ví dụ đúng:\n✅ Truy vấn dữ liệu trên Fabric\n✅ Tính tổng theo định nghĩa chuẩn\n✅ Gửi kết quả qua email"
    )


def _ollama_available() -> bool:
    try:
        requests.get(OLLAMA_BASE_URL, timeout=3)
        return True
    except Exception:
        return False


def _generate_via_ollama(prompt: str) -> str:
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


def _generate_via_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_checklist(
    task_name: str,
    category_label: str,
    deadline: str,
    note: str,
    obsidian_context: str = "",
) -> str:
    """Sinh checklist 2-3 bước. Thử Ollama trước, fallback sang Claude API."""
    prompt = _build_prompt(task_name, category_label, deadline, note, obsidian_context)

    if _ollama_available():
        try:
            return _generate_via_ollama(prompt)
        except Exception:
            pass  # fall through to Claude API

    if ANTHROPIC_API_KEY:
        try:
            return _generate_via_claude(prompt)
        except Exception:
            return ""

    return ""
