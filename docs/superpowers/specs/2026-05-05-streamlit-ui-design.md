# Streamlit Web UI — Task Tracker

**Date:** 2026-05-05  
**Stack:** Python · Streamlit · existing modules (no new dependencies except streamlit)

---

## Goal

Add a `app.py` Streamlit single-page web UI accessible at `http://localhost:8501` that wraps all existing CLI functionality into a dark-theme dashboard. No backend changes — the UI calls existing module functions directly.

---

## Architecture

```
app.py                  ← Streamlit entry point
modules/
  task_manager.py       ← CRUD (unchanged)
  ai_client.py          ← _call_ai(), summarize_email() (unchanged)
  discord_notifier.py   ← send_all_reminders(), send_confirm() (unchanged)
  email_digest.py       ← run_digest() (unchanged)
data/
  tasks.json            ← JSON storage (unchanged)
```

`app.py` imports directly from `modules/`. No new API layer, no database changes.

---

## UI Structure

### Tab 1 — Tasks

**Stats row (4 columns):**
- Quá hạn (deadline < today, active=True) — màu đỏ
- Đang làm (active=True, deadline >= today) — màu cam
- Hoàn thành (active=False, có trường deadline) — màu xanh lá
- Hôm nay (deadline == today) — màu xanh dương

**Action bar:**
- Nút `+ Thêm task` → mở `st.expander` form bên dưới
- Nút `🔔 Gửi Discord` → gọi `send_all_reminders(get_active_tasks())`
- `st.text_input` tìm kiếm lọc theo tên task
- `st.selectbox` lọc theo priority

**Form thêm task (trong expander):**
- task_name (text_input)
- category (selectbox: HIGH / MEDIUM / LOW / AD-HOC)
- start_date, end_date (date_input)
- note (text_area, optional)
- recur (selectbox: Không / Hằng tháng / Hằng năm)
- Submit → `add_task()` → `send_confirm()` → `st.rerun()`

**Task cards nhóm theo priority (HIGH → MEDIUM → LOW → AD-HOC):**

Mỗi nhóm dùng `st.expander` (mặc định mở với HIGH/MEDIUM, đóng với LOW/AD-HOC).  
Mỗi task hiển thị:
- Tên task + deadline + badge priority
- Màu border-left theo priority (CSS inject)
- Nút `✏️ Sửa` → inline expander form edit
- Nút `✅ Done` → `update_task(id, {"active": False})` → `st.rerun()`
- Nút `🗑️ Xóa` → `delete_task(id)` → `st.rerun()`

**Edit form (inline expander):** tương tự add form, pre-filled với giá trị hiện tại.

---

### Tab 2 — AI Tools

**Section 1: Email Digest**
- Mô tả ngắn + nút `▶ Tạo digest hôm nay`
- Khi click → `run_digest()` (blocking, hiện spinner)
- Kết quả hiển thị theo 3 nhóm: URGENT / NORMAL / FYI
- Mỗi email: sender, subject, summary, gợi ý reply
- Nút `📤 Gửi Discord` → `send_email_digest(results)`

**Section 2: AI Checklist**
- `st.selectbox` chọn task từ danh sách active
- Nút `🤖 Tạo checklist` → gọi `generate_checklist(task_name)` (thêm hàm public mới vào `ai_client.py`)
- Kết quả hiển thị dạng checkbox list
- Nút `💾 Lưu vào task` → `update_task(id, {"checklist": result})`

---

### Tab 3 — Cài đặt

Read-only display các biến .env hiện tại (ẩn key, chỉ hiện trạng thái configured/not configured):
- ANTHROPIC_API_KEY
- DISCORD_WEBHOOK_URL
- OUTLOOK_* configs
- OLLAMA_BASE_URL

---

## Dark Theme

Inject CSS qua `st.markdown()` với `unsafe_allow_html=True`:
- Background: `#0e1117`
- Card background: `#1a1a2e`
- Sidebar/header: `#262730`
- HIGH: border `#ff4b4b`
- MEDIUM: border `#ffa500`
- LOW: border `#00c853`
- AD-HOC: border `#89b4fa`

---

## Data Flow

```
app.py
  ├── Tab Tasks
  │     ├── load_tasks() → filter/group → render cards
  │     ├── add_task() + send_confirm() on submit
  │     ├── update_task() on edit/done
  │     └── send_all_reminders() on Discord button
  ├── Tab AI Tools
  │     ├── run_digest() → send_email_digest()
  │     └── generate_checklist(task_name) → update_task(checklist)
  └── Tab Settings
        └── os.getenv() read-only display
```

---

## Dependencies

Add to `requirements.txt`:
```
streamlit>=1.35.0
```

Run command:
```bash
streamlit run app.py
```

---

## Out of Scope

- Authentication / multi-user
- Real-time updates (auto-refresh)
- Deploy to cloud
- Obsidian integration in UI (CLI-only)
