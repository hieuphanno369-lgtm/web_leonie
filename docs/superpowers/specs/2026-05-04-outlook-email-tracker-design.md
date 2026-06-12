# Outlook Email Tracker — Design Spec
**Date:** 2026-05-04
**Project:** task-tracker (integrated module)

---

## Overview

Một module Python tích hợp vào project task-tracker hiện tại, kết nối Outlook Classic (Exchange) qua Windows COM API để:
1. Đọc email từ tất cả folders (Inbox, Sent, subfolders)
2. Phát hiện email có @mention hoặc To trực tiếp đến `user@example.com`
3. Phân loại theo 3 mức độ: 🔴 Urgent / 🟡 Normal / 🟢 FYI
4. Tóm tắt nội dung bằng tiếng Việt (Claude API → Ollama → rule-based)
5. Gợi ý 3 reply options theo phong cách viết đã học từ Sent Items
6. Gửi 1 Discord embed digest lúc 8:00 sáng hàng ngày

---

## User Context

- **User:** Test User
- **Email:** user@example.com
- **Company:** example.com
- **Team:** CRM_Data System Team
- **Boss (VIP sender):** Nguyễn Thị Huỳnh Cúc
- **Outlook:** Classic, kết nối Microsoft Exchange

---

## Architecture

### Cấu trúc thư mục

```
task-tracker/
├── modules/
│   ├── outlook_reader.py      ← Đọc Outlook qua win32com
│   ├── email_classifier.py    ← Phân loại 🔴🟡🟢
│   ├── ai_client.py           ← Claude API → Ollama → rule-based
│   ├── style_learner.py       ← Học phong cách từ Sent Items
│   ├── reply_suggester.py     ← Generate 3 reply options
│   └── email_history.py       ← Lưu/đọc processed emails (JSON, 30 ngày)
├── data/
│   ├── tasks.json             ← (hiện có)
│   ├── email_history.json     ← Email đã xử lý (tránh duplicate)
│   └── style_profile.json     ← Phong cách viết học từ Sent Items
├── scheduler.py               ← Thêm job 8:00 AM daily digest
└── .env                       ← Thêm các biến mới (xem bên dưới)
```

### Data Flow

```
Outlook (win32com)
    → outlook_reader.py       (lấy email mới từ tất cả folders)
    → email_history.py        (lọc email đã xử lý rồi)
    → email_classifier.py     (phân loại 🔴🟡🟢)
    → ai_client.py            (tóm tắt tiếng Việt: Claude → Ollama → rule)
    → reply_suggester.py      (3 reply options theo style)
    → discord_notifier.py     (gửi 1 embed digest)
    → email_history.py        (lưu lại, 30 ngày retention)
```

---

## Module Specs

### `outlook_reader.py`
- Kết nối Outlook Classic qua `win32com.client`
- Đọc tất cả folders: Inbox, Sent Items, và subfolders đệ quy
- Lấy email trong khoảng thời gian: 24h gần nhất (cho daily digest)
- Lấy 200-500 email Sent Items gần nhất cho `style_learner.py`
- Fields cần lấy: `Subject`, `SenderName`, `SenderEmailAddress`, `To`, `CC`, `Body`, `ReceivedTime`, `EntryID`
- `EntryID` dùng làm unique key lưu vào history

### `email_classifier.py`
Phân loại theo 4 bước theo thứ tự ưu tiên:

**Bước 1 — VIP Sender (override):**
- Email từ `BOSS_EMAIL` trong `.env` → 🔴 Urgent ngay

**Bước 2 — @mention / Direct To:**
- `@Test User` trong body → score +2
- `user@example.com` trong To field → score +2
- `user@example.com` chỉ trong CC → score +1

**Bước 3 — Keyword scoring:**
```
🔴 Urgent (+3): "urgent", "gấp", "khẩn", "asap", "cần ngay", "[URGENT]", 
                "deadline hôm nay", "quan trọng", "ngay bây giờ"
🟡 Normal (+1): "deadline", "cần confirm", "vui lòng", "nhờ anh", "nhờ chị",
                "phản hồi", "xác nhận"
🟢 FYI (0):    "fyi", "thông báo", "forward", "tham khảo", "đính kèm"
```

**Bước 4 — AI final judgment:**
- Nếu score không rõ ràng → Claude API (hoặc Ollama) đọc subject + 200 ký tự body → trả về Urgent/Normal/FYI

**Score mapping:**
- Score ≥ 4 → 🔴 Urgent
- Score 1-3 → 🟡 Normal
- Score 0 → 🟢 FYI

### `ai_client.py`
AI provider với fallback chain:
1. **Claude API** (`claude-sonnet-4-6`) — primary
2. **Ollama** (`llama3` hoặc model trong `.env`) — fallback nếu Claude fail
3. **Rule-based** — fallback cuối: trả về subject làm summary, không có reply suggestion

Nhiệm vụ:
- Tóm tắt email bằng tiếng Việt (1-2 câu cho Urgent, 1 câu cho Normal/FYI)
- Phân loại mức độ khi email classifier không chắc chắn

### `style_learner.py`
- Chạy lần đầu khi setup: đọc 200-500 email Sent Items gần nhất
- Phân tích: cách mở đầu, kết thúc, tone (formal/informal), độ dài câu, từ xưng hô
- Lưu `style_profile.json`: summary phong cách để feed vào reply suggestion prompt
- Re-learn tự động mỗi tuần (job trong scheduler.py)

### `reply_suggester.py`
- Input: email gốc + style_profile.json
- Output: 3 reply options ngắn (1-2 câu mỗi option) bằng tiếng Việt
- Dùng Claude API → fallback Ollama
- 3 options theo hướng khác nhau: xác nhận/đang xử lý/cần thêm thông tin

### `email_history.py`
- Lưu vào `data/email_history.json`: `{entryID, subject, sender, received_time, priority, processed_at}`
- Retention: tự động xóa entries cũ hơn 30 ngày
- Check duplicate: skip email có EntryID đã tồn tại trong history

---

## Discord Embed Format

```
📬 Email Digest — [Thứ], DD/MM/YYYY | 8:00 AM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 URGENT (N emails)
┌ [Sender Name] — [Subject]
│ 📝 [AI summary 1-2 câu tiếng Việt]
│ 💬 Reply nhanh:
│   1. "[option 1]"
│   2. "[option 2]"
│   3. "[option 3]"

🟡 NORMAL (N emails)
┌ [Sender Name] — [Subject]
│ 📝 [AI summary 1 câu]
│ 💬 1. "[option 1]"  2. "[option 2]"  3. "[option 3]"

🟢 FYI (N emails)
┌ [Sender Name] — [Subject]
│ 📝 [AI summary 1 câu]
│ 💬 1. "[option 1]"  2. "[option 2]"  3. "[option 3]"
```

---

## Scheduler Integration

Thêm vào `scheduler.py` hiện tại:
- **8:00 AM daily** — chạy email digest (outlook_reader → classifier → AI → Discord)
- **Weekly (Chủ nhật 7:00 AM)** — re-learn style từ Sent Items mới nhất

---

## Environment Variables (thêm vào `.env`)

```env
# Outlook Email Tracker
USER_NAME=Test User
USER_EMAIL=user@example.com
BOSS_EMAIL=boss@example.com  # email sếp — tự động Urgent
EMAIL_DIGEST_TIME=08:00
STYLE_RELEARN_DAY=sunday

# Claude API (primary AI)
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (fallback — đã có)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## Dependencies (thêm vào `requirements.txt`)

```
pywin32          # win32com — đọc Outlook
anthropic        # Claude API
```

---

## Error Handling

- Outlook không mở → log warning, skip digest, không crash scheduler
- Claude API fail → fallback Ollama tự động, không báo lỗi cho user
- Ollama fail → fallback rule-based, Discord embed vẫn gửi nhưng không có AI summary
- Không có email mới → gửi Discord message ngắn "Không có email mới hôm nay ✅"
- Discord webhook fail → log error vào file

---

## Out of Scope

- Tự động gửi reply (chỉ suggest, không gửi)
- Web UI hoặc dashboard
- Push notification mobile
- Multi-account Outlook
