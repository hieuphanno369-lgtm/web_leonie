# Outlook Email Tracker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tích hợp module theo dõi email Outlook vào task-tracker: đọc email qua win32com, phân loại 🔴🟡🟢, tóm tắt bằng AI (Claude → Ollama → rule-based), gợi ý 3 reply theo phong cách người dùng, gửi Discord digest lúc 8:00 sáng.

**Architecture:** Module mới nằm trong `modules/`, chia thành 7 file với trách nhiệm rõ ràng. Orchestrator `email_digest.py` kết nối tất cả. Scheduler hiện tại được mở rộng thêm 2 jobs: digest 8:00 sáng và re-learn phong cách hàng tuần.

**Tech Stack:** Python 3.11+, pywin32 (win32com), anthropic SDK, schedule, requests, python-dotenv, rich

---

## File Map

| File | Trạng thái | Trách nhiệm |
|------|-----------|-------------|
| `modules/email_history.py` | Tạo mới | Lưu/đọc email đã xử lý, tránh duplicate, 30-day retention |
| `modules/outlook_reader.py` | Tạo mới | Kết nối Outlook qua win32com, đọc tất cả folders |
| `modules/email_classifier.py` | Tạo mới | Phân loại 🔴🟡🟢 theo 4 bước: VIP → mention → keyword → AI |
| `modules/ai_client.py` | Tạo mới | Claude API → Ollama fallback → rule fallback (tóm tắt + classify) |
| `modules/style_learner.py` | Tạo mới | Phân tích Sent Items → lưu style_profile.json |
| `modules/reply_suggester.py` | Tạo mới | Generate 3 reply options theo style profile |
| `modules/email_digest.py` | Tạo mới | Orchestrator: kết nối toàn bộ pipeline |
| `modules/discord_notifier.py` | Sửa thêm | Thêm `send_email_digest()` |
| `scheduler.py` | Sửa thêm | Thêm job 8:00 AM digest + Chủ nhật 7:00 AM re-learn |
| `requirements.txt` | Sửa thêm | Thêm `pywin32` |
| `.env.example` | Sửa thêm | Thêm 5 biến mới |
| `data/email_history.json` | Tạo mới (auto) | Tự tạo khi chạy lần đầu |
| `data/style_profile.json` | Tạo mới (auto) | Tự tạo sau style-learn |
| `tests/test_email_history.py` | Tạo mới | Unit tests |
| `tests/test_email_classifier.py` | Tạo mới | Unit tests |
| `tests/test_ai_client.py` | Tạo mới | Unit tests |
| `tests/test_email_digest.py` | Tạo mới | Integration tests (mocked) |

---

## Data Structures

```python
# Email raw (dict) — output của outlook_reader
{
    "entry_id": str,       # Outlook EntryID, dùng làm unique key
    "subject": str,
    "sender_name": str,
    "sender_email": str,
    "to": str,             # raw To field string
    "cc": str,             # raw CC field string
    "body": str,           # plain text, tối đa 2000 ký tự đầu
    "received_time": str,  # ISO 8601, e.g. "2026-05-04T08:00:00"
    "folder": str,         # tên folder, e.g. "Inbox"
}

# Classified email (dict) — output của pipeline
{
    **email_raw,
    "priority": str,       # "urgent" | "normal" | "fyi"
    "summary": str,        # AI summary tiếng Việt
    "replies": list[str],  # 3 reply options (có thể [] nếu AI fail)
}

# History entry (dict) — lưu vào email_history.json
{
    "entry_id": str,
    "subject": str,
    "sender_name": str,
    "received_time": str,
    "priority": str,
    "processed_at": str,   # ISO 8601
}

# Style profile (dict) — lưu vào style_profile.json
{
    "learned_at": str,     # ISO 8601
    "email_count": int,
    "style_summary": str,  # đoạn văn mô tả phong cách viết
}
```

---

## Task 1: Setup — requirements, .env, tests folder

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Create: `tests/__init__.py`
- Create: `data/email_history.json` (empty init)

- [ ] **Step 1: Thêm pywin32 vào requirements.txt**

Mở `requirements.txt`, thêm vào cuối:
```
pywin32>=306
```

- [ ] **Step 2: Cài pywin32**

```bash
.venv\Scripts\pip install pywin32>=306
```
Expected output: `Successfully installed pywin32-...`

- [ ] **Step 3: Cập nhật .env.example**

Thêm vào cuối file `.env.example`:
```env
# Outlook Email Tracker
USER_NAME=Test User
USER_EMAIL=user@example.com
BOSS_EMAIL=boss@example.com
EMAIL_DIGEST_TIME=08:00
STYLE_RELEARN_DAY=sunday
```

- [ ] **Step 4: Thêm các biến trên vào file `.env` thật** (copy từ .env.example, điền đúng BOSS_EMAIL)

- [ ] **Step 5: Tạo thư mục tests**

```bash
mkdir tests
echo "" > tests/__init__.py
```

- [ ] **Step 6: Init email_history.json rỗng**

```bash
echo "[]" > data/email_history.json
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example tests/__init__.py data/email_history.json
git commit -m "chore: add pywin32 dep and email tracker env template"
```

---

## Task 2: email_history.py — JSON store với 30-day retention

**Files:**
- Create: `modules/email_history.py`
- Create: `tests/test_email_history.py`

- [ ] **Step 1: Viết test trước**

Tạo file `tests/test_email_history.py`:
```python
import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open

# Patch HISTORY_FILE trước khi import module
import modules.email_history as eh


def _make_entry(entry_id: str, days_ago: int = 0) -> dict:
    dt = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {
        "entry_id": entry_id,
        "subject": f"Test {entry_id}",
        "sender_name": "Test Sender",
        "received_time": "2026-05-04T08:00:00",
        "priority": "normal",
        "processed_at": dt,
    }


def test_is_processed_true(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    entry = _make_entry("id-001")
    (tmp_path / "history.json").write_text(json.dumps([entry]), encoding="utf-8")
    assert eh.is_processed("id-001") is True


def test_is_processed_false(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")
    assert eh.is_processed("id-999") is False


def test_save_entry_appends(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")
    email = {
        "entry_id": "id-001",
        "subject": "Hello",
        "sender_name": "Boss",
        "received_time": "2026-05-04T08:00:00",
        "priority": "urgent",
    }
    eh.save_entry(email)
    data = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["entry_id"] == "id-001"
    assert "processed_at" in data[0]


def test_purge_old_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "HISTORY_FILE", tmp_path / "history.json")
    entries = [
        _make_entry("old-1", days_ago=35),
        _make_entry("old-2", days_ago=31),
        _make_entry("new-1", days_ago=5),
    ]
    (tmp_path / "history.json").write_text(json.dumps(entries), encoding="utf-8")
    eh._purge_old_entries()
    data = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["entry_id"] == "new-1"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

```bash
.venv\Scripts\pytest tests/test_email_history.py -v
```
Expected: `ModuleNotFoundError` hoặc `AttributeError` (module chưa có)

- [ ] **Step 3: Implement email_history.py**

Tạo `modules/email_history.py`:
```python
import json
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = Path(__file__).parent.parent / "data" / "email_history.json"
RETENTION_DAYS = 30


def _load() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict]) -> None:
    HISTORY_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _purge_old_entries() -> None:
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat()
    entries = [e for e in _load() if e.get("processed_at", "") >= cutoff]
    _save(entries)


def is_processed(entry_id: str) -> bool:
    return any(e["entry_id"] == entry_id for e in _load())


def save_entry(email: dict) -> None:
    _purge_old_entries()
    entries = _load()
    entries.append({
        "entry_id": email["entry_id"],
        "subject": email["subject"],
        "sender_name": email["sender_name"],
        "received_time": email["received_time"],
        "priority": email.get("priority", "fyi"),
        "processed_at": datetime.now().isoformat(),
    })
    _save(entries)
```

- [ ] **Step 4: Chạy test lại**

```bash
.venv\Scripts\pytest tests/test_email_history.py -v
```
Expected: tất cả PASS

- [ ] **Step 5: Commit**

```bash
git add modules/email_history.py tests/test_email_history.py
git commit -m "feat: add email_history module with 30-day retention"
```

---

## Task 3: outlook_reader.py — Đọc Outlook qua win32com

**Files:**
- Create: `modules/outlook_reader.py`

> Note: win32com chỉ chạy được khi Outlook đang mở và trên Windows. Không test unit được — module này được test thủ công hoặc integration test.

- [ ] **Step 1: Tạo modules/outlook_reader.py**

```python
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

USER_EMAIL = os.getenv("USER_EMAIL", "user@example.com")
USER_NAME  = os.getenv("USER_NAME", "Test User")


def _get_outlook():
    import win32com.client
    return win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")


def _folder_emails(folder, since: datetime) -> list[dict]:
    """Đệ quy lấy email từ folder và tất cả subfolders."""
    emails = []
    try:
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        for item in items:
            try:
                if item.Class != 43:  # 43 = olMail
                    continue
                received = item.ReceivedTime
                # win32com trả về aware datetime — convert sang naive
                if hasattr(received, "replace"):
                    received_naive = received.replace(tzinfo=None)
                else:
                    received_naive = received
                if received_naive < since:
                    break
                emails.append({
                    "entry_id": item.EntryID,
                    "subject": item.Subject or "",
                    "sender_name": item.SenderName or "",
                    "sender_email": (item.SenderEmailAddress or "").lower(),
                    "to": item.To or "",
                    "cc": item.CC or "",
                    "body": (item.Body or "")[:2000],
                    "received_time": received_naive.isoformat(),
                    "folder": folder.Name,
                })
            except Exception:
                continue
    except Exception:
        pass

    for i in range(folder.Folders.Count):
        try:
            subfolder = folder.Folders.Item(i + 1)
            emails.extend(_folder_emails(subfolder, since))
        except Exception:
            continue
    return emails


def get_recent_emails(hours: int = 24) -> list[dict]:
    """Lấy tất cả email trong N giờ gần nhất từ mọi folder (trừ Sent Items)."""
    since = datetime.now() - timedelta(hours=hours)
    mapi = _get_outlook()
    all_emails = []
    for i in range(mapi.Folders.Count):
        try:
            account_folder = mapi.Folders.Item(i + 1)
            for j in range(account_folder.Folders.Count):
                try:
                    folder = account_folder.Folders.Item(j + 1)
                    if "Sent" in folder.Name or "Đã gửi" in folder.Name:
                        continue
                    all_emails.extend(_folder_emails(folder, since))
                except Exception:
                    continue
        except Exception:
            continue
    # Dedup theo entry_id
    seen = set()
    unique = []
    for e in all_emails:
        if e["entry_id"] not in seen:
            seen.add(e["entry_id"])
            unique.append(e)
    return unique


def get_sent_emails(limit: int = 300) -> list[dict]:
    """Lấy N email gần nhất từ Sent Items để học phong cách viết."""
    mapi = _get_outlook()
    sent_emails = []
    for i in range(mapi.Folders.Count):
        try:
            account_folder = mapi.Folders.Item(i + 1)
            for j in range(account_folder.Folders.Count):
                try:
                    folder = account_folder.Folders.Item(j + 1)
                    if "Sent" not in folder.Name and "Đã gửi" not in folder.Name:
                        continue
                    items = folder.Items
                    items.Sort("[SentOn]", True)
                    count = 0
                    for item in items:
                        if count >= limit:
                            break
                        try:
                            if item.Class != 43:
                                continue
                            sent_emails.append({
                                "subject": item.Subject or "",
                                "body": (item.Body or "")[:1500],
                                "sent_time": item.SentOn.replace(tzinfo=None).isoformat(),
                            })
                            count += 1
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            continue
    return sent_emails[:limit]
```

- [ ] **Step 2: Test thủ công** — Mở Outlook, sau đó chạy:

```bash
.venv\Scripts\python -c "from modules.outlook_reader import get_recent_emails; emails = get_recent_emails(24); print(f'Found {len(emails)} emails'); print(emails[0] if emails else 'none')"
```
Expected: In ra số lượng email và preview email đầu tiên.

- [ ] **Step 3: Commit**

```bash
git add modules/outlook_reader.py
git commit -m "feat: add outlook_reader module via win32com"
```

---

## Task 4: email_classifier.py — Phân loại 🔴🟡🟢

**Files:**
- Create: `modules/email_classifier.py`
- Create: `tests/test_email_classifier.py`

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_email_classifier.py`:
```python
import pytest
from modules.email_classifier import classify_priority, _score_email

SAMPLE_EMAIL = {
    "entry_id": "test-001",
    "subject": "Báo cáo tháng 4",
    "sender_name": "Nguyễn Văn A",
    "sender_email": "alice@example.com",
    "to": "Test User <user@example.com>; Nguyen B",
    "cc": "",
    "body": "Dear anh Hiếu, nhờ anh xác nhận báo cáo.",
    "received_time": "2026-05-04T08:00:00",
    "folder": "Inbox",
}


def test_boss_email_always_urgent(monkeypatch):
    monkeypatch.setenv("BOSS_EMAIL", "boss@example.com")
    import importlib, modules.email_classifier as ec
    importlib.reload(ec)
    email = {**SAMPLE_EMAIL, "sender_email": "boss@example.com"}
    assert ec.classify_priority(email, ai_classify_fn=None) == "urgent"


def test_urgent_keyword_in_subject():
    email = {**SAMPLE_EMAIL, "subject": "[URGENT] Cần xử lý ngay"}
    score = _score_email(email)
    assert score >= 4


def test_direct_to_recipient_increases_score():
    email = {**SAMPLE_EMAIL, "to": "user@example.com"}
    score = _score_email(email)
    assert score >= 2


def test_cc_only_low_score():
    email = {**SAMPLE_EMAIL, "to": "someone@example.com", "cc": "user@example.com"}
    score = _score_email(email)
    assert score == 1  # chỉ CC


def test_mention_in_body_increases_score():
    email = {**SAMPLE_EMAIL, "body": "Nhờ @Test User xác nhận giúp em nhé."}
    score = _score_email(email)
    assert score >= 2


def test_no_mention_no_keywords_returns_fyi():
    email = {
        **SAMPLE_EMAIL,
        "subject": "FYI thông báo lịch",
        "to": "all@example.com",
        "cc": "",
        "body": "FYI: đính kèm lịch họp tháng 5.",
        "sender_email": "hr@example.com",
    }
    result = classify_priority(email, ai_classify_fn=lambda e: "fyi")
    assert result == "fyi"


def test_score_3_returns_normal():
    email = {**SAMPLE_EMAIL, "subject": "Nhờ anh xác nhận deadline"}
    # to match → +2, "deadline" keyword → +1 = 3 → normal
    result = classify_priority(email, ai_classify_fn=None)
    assert result == "normal"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

```bash
.venv\Scripts\pytest tests/test_email_classifier.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement email_classifier.py**

Tạo `modules/email_classifier.py`:
```python
import os
import re
from dotenv import load_dotenv

load_dotenv()

USER_EMAIL = os.getenv("USER_EMAIL", "user@example.com").lower()
USER_NAME  = os.getenv("USER_NAME", "Test User")
BOSS_EMAIL = os.getenv("BOSS_EMAIL", "").lower()

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
    # Bước 1: VIP sender
    if BOSS_EMAIL and email.get("sender_email", "").lower() == BOSS_EMAIL:
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
```

- [ ] **Step 4: Chạy test**

```bash
.venv\Scripts\pytest tests/test_email_classifier.py -v
```
Expected: tất cả PASS

- [ ] **Step 5: Commit**

```bash
git add modules/email_classifier.py tests/test_email_classifier.py
git commit -m "feat: add email_classifier with 4-step priority scoring"
```

---

## Task 5: ai_client.py — Claude → Ollama → Rule fallback

**Files:**
- Create: `modules/ai_client.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_ai_client.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from modules.ai_client import summarize_email, classify_email_ai

SAMPLE_EMAIL = {
    "subject": "Nhờ xác nhận biên bản",
    "sender_name": "Quỳnh Như",
    "body": "Dear anh Hiếu, nhờ anh xác nhận biên bản nghiệm thu tháng 4.",
    "received_time": "2026-05-04T08:00:00",
}


def test_summarize_returns_string_on_claude_success():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Quỳnh Như nhờ anh Hiếu xác nhận biên bản nghiệm thu tháng 4/2026.")]
    )
    with patch("modules.ai_client._get_claude_client", return_value=mock_client):
        result = summarize_email(SAMPLE_EMAIL, priority="normal")
    assert isinstance(result, str)
    assert len(result) > 10


def test_summarize_falls_back_to_rule_when_claude_fails():
    with patch("modules.ai_client._get_claude_client", side_effect=Exception("API Error")):
        with patch("modules.ai_client._ollama_available", return_value=False):
            result = summarize_email(SAMPLE_EMAIL, priority="normal")
    assert "Quỳnh Như" in result or "Nhờ xác nhận biên bản" in result


def test_classify_email_ai_returns_valid_priority():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="normal")]
    )
    with patch("modules.ai_client._get_claude_client", return_value=mock_client):
        result = classify_email_ai(SAMPLE_EMAIL)
    assert result in ("urgent", "normal", "fyi")


def test_classify_email_ai_defaults_fyi_on_error():
    with patch("modules.ai_client._get_claude_client", side_effect=Exception("fail")):
        with patch("modules.ai_client._ollama_available", return_value=False):
            result = classify_email_ai(SAMPLE_EMAIL)
    assert result == "fyi"
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

```bash
.venv\Scripts\pytest tests/test_ai_client.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement ai_client.py**

Tạo `modules/ai_client.py`:
```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3")

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
    """Claude → Ollama → raise exception."""
    if ANTHROPIC_API_KEY:
        try:
            return _call_claude(prompt, max_tokens)
        except Exception:
            pass
    if _ollama_available():
        try:
            return _call_ollama(prompt)
        except Exception:
            pass
    raise RuntimeError("Không có AI nào khả dụng")


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
```

- [ ] **Step 4: Chạy test**

```bash
.venv\Scripts\pytest tests/test_ai_client.py -v
```
Expected: tất cả PASS

- [ ] **Step 5: Commit**

```bash
git add modules/ai_client.py tests/test_ai_client.py
git commit -m "feat: add ai_client with Claude->Ollama->rule fallback chain"
```

---

## Task 6: style_learner.py — Học phong cách từ Sent Items

**Files:**
- Create: `modules/style_learner.py`

- [ ] **Step 1: Tạo modules/style_learner.py**

```python
import json
import random
from datetime import datetime
from pathlib import Path
from modules.ai_client import _call_ai

STYLE_FILE = Path(__file__).parent.parent / "data" / "style_profile.json"
SAMPLE_SIZE = 20  # gửi tối đa 20 email mẫu cho AI phân tích


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

    # Sample ngẫu nhiên để tránh prompt quá dài
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
```

- [ ] **Step 2: Test thủ công** (Outlook phải đang mở):

```bash
.venv\Scripts\python -c "
from modules.outlook_reader import get_sent_emails
from modules.style_learner import learn_from_sent
sent = get_sent_emails(limit=50)
print(f'Got {len(sent)} sent emails')
summary = learn_from_sent(sent)
print('Style summary:', summary[:200])
"
```
Expected: In ra style summary và tạo file `data/style_profile.json`.

- [ ] **Step 3: Commit**

```bash
git add modules/style_learner.py
git commit -m "feat: add style_learner to build writing profile from Sent Items"
```

---

## Task 7: reply_suggester.py — Generate 3 reply options

**Files:**
- Create: `modules/reply_suggester.py`
- Create: `tests/test_reply_suggester.py` (mocked)

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_reply_suggester.py`:
```python
import pytest
from unittest.mock import patch
from modules.reply_suggester import suggest_replies

SAMPLE_EMAIL = {
    "subject": "Nhờ xác nhận biên bản nghiệm thu",
    "sender_name": "Quỳnh Như",
    "body": "Dear anh Hiếu, nhờ anh xác nhận.",
    "priority": "normal",
}

STYLE = "Phong cách lịch sự, ngắn gọn, dùng 'Em' và 'Anh/Chị', kết thúc bằng 'Trân trọng'."


def test_suggest_replies_returns_3_options():
    with patch("modules.reply_suggester._call_ai", return_value="Option 1\nOption 2\nOption 3"):
        result = suggest_replies(SAMPLE_EMAIL, style_summary=STYLE)
    assert len(result) == 3


def test_suggest_replies_fallback_on_error():
    with patch("modules.reply_suggester._call_ai", side_effect=Exception("fail")):
        result = suggest_replies(SAMPLE_EMAIL, style_summary=STYLE)
    assert len(result) == 3
    assert all(isinstance(r, str) for r in result)


def test_suggest_replies_empty_style():
    with patch("modules.reply_suggester._call_ai", return_value="A\nB\nC"):
        result = suggest_replies(SAMPLE_EMAIL, style_summary="")
    assert len(result) == 3
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

```bash
.venv\Scripts\pytest tests/test_reply_suggester.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement reply_suggester.py**

Tạo `modules/reply_suggester.py`:
```python
from modules.ai_client import _call_ai

_FALLBACK_REPLIES = [
    "Em đã nhận, sẽ xử lý và phản hồi sớm ạ.",
    "Dạ em đang xem xét, sẽ update ngay khi có kết quả.",
    "Anh/Chị có thể cung cấp thêm thông tin để em hỗ trợ tốt hơn không ạ?",
]


def suggest_replies(email: dict, style_summary: str) -> list[str]:
    """
    Trả về list 3 reply options (string). Fallback về default nếu AI fail.
    """
    style_block = f"\nPhong cách viết của bạn: {style_summary}" if style_summary else ""
    prompt = (
        f"Gợi ý 3 câu trả lời ngắn (mỗi câu 1-2 câu) cho email bên dưới bằng tiếng Việt.{style_block}\n"
        "Mỗi option theo hướng khác nhau: 1) xác nhận/đồng ý, 2) đang xử lý/cần thời gian, 3) cần thêm thông tin.\n"
        "Định dạng: mỗi option trên 1 dòng riêng, không đánh số, không bullet.\n\n"
        f"Từ: {email['sender_name']}\n"
        f"Tiêu đề: {email['subject']}\n"
        f"Nội dung: {email.get('body', '')[:300]}"
    )
    try:
        raw = _call_ai(prompt, max_tokens=200)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if len(lines) >= 3:
            return lines[:3]
        # Nếu AI trả về ít hơn 3 dòng, pad bằng fallback
        while len(lines) < 3:
            lines.append(_FALLBACK_REPLIES[len(lines)])
        return lines
    except Exception:
        return list(_FALLBACK_REPLIES)
```

- [ ] **Step 4: Chạy test**

```bash
.venv\Scripts\pytest tests/test_reply_suggester.py -v
```
Expected: tất cả PASS

- [ ] **Step 5: Commit**

```bash
git add modules/reply_suggester.py tests/test_reply_suggester.py
git commit -m "feat: add reply_suggester with 3-option generation and fallback"
```

---

## Task 8: email_digest.py — Orchestrator pipeline

**Files:**
- Create: `modules/email_digest.py`
- Create: `tests/test_email_digest.py`

- [ ] **Step 1: Viết test trước**

Tạo `tests/test_email_digest.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from modules.email_digest import run_digest

MOCK_EMAILS = [
    {
        "entry_id": "id-001",
        "subject": "[URGENT] Lỗi hệ thống",
        "sender_name": "Nguyễn Thị Huỳnh Cúc",
        "sender_email": "boss@example.com",
        "to": "user@example.com",
        "cc": "",
        "body": "Anh Hiếu ơi, hệ thống bị lỗi cần xử lý ngay.",
        "received_time": "2026-05-04T07:00:00",
        "folder": "Inbox",
    },
    {
        "entry_id": "id-002",
        "subject": "Thông báo lịch họp",
        "sender_name": "Trần Lan Phương",
        "sender_email": "carol@example.com",
        "to": "all@example.com",
        "cc": "user@example.com",
        "body": "FYI: Lịch họp tuần tới.",
        "received_time": "2026-05-04T06:00:00",
        "folder": "Inbox",
    },
]


def test_run_digest_returns_classified_list():
    with patch("modules.email_digest.get_recent_emails", return_value=MOCK_EMAILS), \
         patch("modules.email_digest.is_processed", return_value=False), \
         patch("modules.email_digest.summarize_email", return_value="Tóm tắt test."), \
         patch("modules.email_digest.suggest_replies", return_value=["R1", "R2", "R3"]), \
         patch("modules.email_digest.save_entry"), \
         patch("modules.email_digest.load_style_profile", return_value=""):
        results = run_digest()

    assert isinstance(results, dict)
    assert "urgent" in results
    assert "normal" in results
    assert "fyi" in results
    total = sum(len(v) for v in results.values())
    assert total == 2


def test_run_digest_skips_processed_emails():
    with patch("modules.email_digest.get_recent_emails", return_value=MOCK_EMAILS), \
         patch("modules.email_digest.is_processed", return_value=True), \
         patch("modules.email_digest.save_entry"):
        results = run_digest()
    total = sum(len(v) for v in results.values())
    assert total == 0
```

- [ ] **Step 2: Chạy test để xác nhận FAIL**

```bash
.venv\Scripts\pytest tests/test_email_digest.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement email_digest.py**

Tạo `modules/email_digest.py`:
```python
from modules.outlook_reader import get_recent_emails
from modules.email_history import is_processed, save_entry
from modules.email_classifier import classify_priority
from modules.ai_client import summarize_email, classify_email_ai
from modules.style_learner import load_style_profile
from modules.reply_suggester import suggest_replies


def run_digest(hours: int = 24) -> dict:
    """
    Chạy full pipeline. Trả về dict phân loại:
    {"urgent": [...], "normal": [...], "fyi": [...]}
    Mỗi item là classified email dict với summary và replies.
    """
    style_summary = load_style_profile()
    raw_emails = get_recent_emails(hours=hours)

    results = {"urgent": [], "normal": [], "fyi": []}

    for email in raw_emails:
        if is_processed(email["entry_id"]):
            continue

        priority = classify_priority(email, ai_classify_fn=classify_email_ai)
        summary  = summarize_email(email, priority=priority)
        replies  = suggest_replies(email, style_summary=style_summary)

        classified = {
            **email,
            "priority": priority,
            "summary": summary,
            "replies": replies,
        }
        results[priority].append(classified)
        save_entry(classified)

    return results
```

- [ ] **Step 4: Chạy test**

```bash
.venv\Scripts\pytest tests/test_email_digest.py -v
```
Expected: tất cả PASS

- [ ] **Step 5: Commit**

```bash
git add modules/email_digest.py tests/test_email_digest.py
git commit -m "feat: add email_digest orchestrator pipeline"
```

---

## Task 9: Mở rộng discord_notifier.py — send_email_digest()

**Files:**
- Modify: `modules/discord_notifier.py`

- [ ] **Step 1: Thêm constants và hàm vào discord_notifier.py**

Mở `modules/discord_notifier.py`, thêm vào cuối file:
```python
COLOR_RED    = 15548997   # urgent
COLOR_ORANGE = 15105570   # normal
COLOR_TEAL   = 1752220    # fyi

_PRIORITY_CONFIG = {
    "urgent": ("🔴 URGENT", COLOR_RED),
    "normal": ("🟡 NORMAL", COLOR_ORANGE),
    "fyi":    ("🟢 FYI",    COLOR_TEAL),
}

_MAX_EMBED_CHARS = 3800  # buffer dưới 4096 của Discord


def _format_email_block(email: dict) -> str:
    replies = email.get("replies", [])
    reply_line = "  ".join(f"`{i+1}. {r}`" for i, r in enumerate(replies[:3]))
    summary = email.get("summary", "")[:200]
    block = (
        f"**{email['sender_name']}** — {email['subject'][:80]}\n"
        f"📝 {summary}\n"
        f"💬 {reply_line}"
    )
    return block


def send_email_digest(classified: dict) -> None:
    """
    classified: {"urgent": [...], "normal": [...], "fyi": [...]}
    Gửi 1 hoặc nhiều Discord embeds nếu content quá dài.
    """
    from datetime import datetime
    import locale
    now = datetime.now().strftime("%d/%m/%Y | %H:%M")

    total = sum(len(v) for v in classified.values())
    if total == 0:
        _post({
            "embeds": [{
                "title": f"📬 Email Digest — {now}",
                "description": "✅ Không có email mới liên quan đến bạn hôm nay.",
                "color": COLOR_TEAL,
                "footer": {"text": "Task Tracker — Email Monitor"},
            }]
        })
        return

    # Xây dựng description theo từng priority tier
    sections = []
    for priority in ("urgent", "normal", "fyi"):
        emails = classified.get(priority, [])
        if not emails:
            continue
        label, _ = _PRIORITY_CONFIG[priority]
        header = f"**{label} ({len(emails)} emails)**"
        blocks = [_format_email_block(e) for e in emails]
        sections.append((header, blocks))

    # Gộp thành 1 description, split nếu quá dài
    current_desc = f"📬 **Email Digest — {now}**\n{'━' * 30}\n\n"
    embeds_to_send = []

    for header, blocks in sections:
        section_text = f"{header}\n" + "\n\n".join(f"┌ {b}" for b in blocks) + "\n\n"
        if len(current_desc) + len(section_text) > _MAX_EMBED_CHARS:
            # Flush current embed, start new
            embeds_to_send.append(current_desc.strip())
            current_desc = section_text
        else:
            current_desc += section_text

    if current_desc.strip():
        embeds_to_send.append(current_desc.strip())

    # Xác định color từ highest priority
    if classified.get("urgent"):
        top_color = COLOR_RED
    elif classified.get("normal"):
        top_color = COLOR_ORANGE
    else:
        top_color = COLOR_TEAL

    for i, desc in enumerate(embeds_to_send):
        payload = {
            "embeds": [{
                "description": desc,
                "color": top_color if i == 0 else COLOR_TEAL,
                "footer": {"text": f"Task Tracker — Email Monitor • {i+1}/{len(embeds_to_send)}"},
            }]
        }
        _post(payload)
```

- [ ] **Step 2: Test thủ công** (không cần Outlook, dùng mock data):

```bash
.venv\Scripts\python -c "
from modules.discord_notifier import send_email_digest
mock = {
    'urgent': [{'sender_name': 'Sếp Cúc', 'subject': '[URGENT] Cần xử lý ngay', 'summary': 'Sếp yêu cầu xử lý lỗi hệ thống trước 10h.', 'replies': ['Em đang xử lý ạ.', 'Dạ em sẽ update ngay.', 'Em cần thêm thông tin ạ.']}],
    'normal': [],
    'fyi': [{'sender_name': 'HR', 'subject': 'Thông báo lịch nghỉ lễ', 'summary': 'Công ty thông báo lịch nghỉ 30/4-1/5.', 'replies': ['Đã nhận.', 'Cảm ơn.', 'OK.']}],
}
send_email_digest(mock)
print('Discord sent!')
"
```
Expected: Discord nhận được embed với format đúng.

- [ ] **Step 3: Commit**

```bash
git add modules/discord_notifier.py
git commit -m "feat: add send_email_digest to discord_notifier"
```

---

## Task 10: Mở rộng scheduler.py — Email digest job + weekly re-learn

**Files:**
- Modify: `scheduler.py`

- [ ] **Step 1: Mở scheduler.py, thêm import và 2 hàm mới**

Thêm vào phần import (sau `from modules.discord_notifier import send_all_reminders`):
```python
from modules.email_digest import run_digest
from modules.style_learner import learn_from_sent
from modules.discord_notifier import send_email_digest
```

- [ ] **Step 2: Thêm hàm run_email_digest vào scheduler.py**

Thêm sau hàm `run_reminders`:
```python
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
```

- [ ] **Step 3: Thêm 2 job mới vào hàm setup_schedule()**

Tìm dòng:
```python
    schedule.every().day.at(REMINDER_TIME_1).do(run_reminders, label=REMINDER_TIME_1)
    schedule.every().day.at(REMINDER_TIME_2).do(run_reminders, label=REMINDER_TIME_2)
```

Thêm vào ngay sau:
```python
    EMAIL_DIGEST_TIME = os.getenv("EMAIL_DIGEST_TIME", "08:00")
    schedule.every().day.at(EMAIL_DIGEST_TIME).do(run_email_digest)
    schedule.every().sunday.at("07:00").do(run_style_relearn)

    console.print(f"   Email digest lúc: [yellow]{EMAIL_DIGEST_TIME}[/yellow] hàng ngày")
    console.print(f"   Style re-learn: [yellow]Chủ nhật 07:00[/yellow]")
```

- [ ] **Step 4: Test scheduler chạy được**

```bash
.venv\Scripts\python -c "
import schedule, time, os
os.environ['EMAIL_DIGEST_TIME'] = '00:00'
from scheduler import setup_schedule
setup_schedule()
print('Scheduler OK — jobs:', len(schedule.jobs))
"
```
Expected: In ra `Scheduler OK — jobs: 4` (2 reminder cũ + 2 email mới)

- [ ] **Step 5: Commit**

```bash
git add scheduler.py
git commit -m "feat: add email digest and style re-learn jobs to scheduler"
```

---

## Task 11: First Run & Smoke Test

- [ ] **Step 1: Chạy toàn bộ test suite**

```bash
.venv\Scripts\pytest tests/ -v
```
Expected: tất cả PASS (trừ `test_email_digest.py` nếu cần Outlook thật)

- [ ] **Step 2: Style-learn lần đầu** (Outlook phải đang mở)

```bash
.venv\Scripts\python -c "
from modules.outlook_reader import get_sent_emails
from modules.style_learner import learn_from_sent
sent = get_sent_emails(300)
print(f'Sent emails found: {len(sent)}')
summary = learn_from_sent(sent)
print('Done! Style summary:')
print(summary)
"
```
Expected: Tạo `data/style_profile.json` với style_summary.

- [ ] **Step 3: Dry run digest** (không gửi Discord)

```bash
.venv\Scripts\python -c "
from modules.email_digest import run_digest
results = run_digest(hours=48)
for priority, emails in results.items():
    print(f'{priority}: {len(emails)} emails')
    for e in emails[:2]:
        print(f'  - {e[\"sender_name\"]}: {e[\"subject\"][:50]}')
        print(f'    Summary: {e[\"summary\"][:100]}')
        print(f'    Replies: {e[\"replies\"]}')
"
```
Expected: In ra danh sách email phân loại với summary và replies.

- [ ] **Step 4: Full test gửi Discord**

```bash
.venv\Scripts\python -c "
from modules.email_digest import run_digest
from modules.discord_notifier import send_email_digest
results = run_digest(hours=48)
send_email_digest(results)
print('Done!')
"
```
Expected: Discord nhận được embed digest đúng format.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: outlook email tracker fully integrated into task-tracker"
```

---

## Self-Review — Spec Coverage Check

| Spec requirement | Task |
|---|---|
| Đọc Outlook qua win32com | Task 3 |
| Detect @mention + To trực tiếp + tên/email trong body | Task 4 |
| 3 mức ưu tiên 🔴🟡🟢 | Task 4 |
| VIP sender (sếp) → auto Urgent | Task 4 |
| Keywords + AI classify | Task 4, 5 |
| Tóm tắt tiếng Việt (Claude → Ollama → rule) | Task 5 |
| Học phong cách từ 200-500 Sent emails | Task 6 |
| 3 reply options trong Discord embed | Task 7 |
| 1 Discord message duy nhất (với split nếu quá dài) | Task 9 |
| 8:00 AM daily digest | Task 10 |
| Weekly re-learn Chủ nhật | Task 10 |
| JSON history, 30-day retention, no duplicate | Task 2 |
| Tích hợp vào task-tracker hiện tại | Task 9, 10 |
| Error handling khi Outlook không mở / AI fail | Task 3, 5, 10 |
| user@example.com, tên Test User | Task 1 (.env) |
