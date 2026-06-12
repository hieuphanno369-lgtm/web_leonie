# Streamlit Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark-theme Streamlit single-page dashboard at `localhost:8501` wrapping the existing task tracker CLI functionality.

**Architecture:** `app.py` is the sole new UI file — it imports directly from existing `modules/`. Pure business logic (stats, grouping, filtering) is extracted to `app_helpers.py` for testability. No changes to existing modules.

**Tech Stack:** Python · Streamlit >= 1.35.0 · existing modules (task_manager, discord_notifier, ollama_client, email_digest, deadline)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `requirements.txt` | Modify | Add streamlit dependency |
| `.streamlit/config.toml` | Create | Dark theme base config |
| `app_helpers.py` | Create | Pure functions: get_stats, group_by_priority, filter_tasks |
| `app.py` | Create | Streamlit UI — all tabs and rendering |
| `tests/test_app_helpers.py` | Create | Unit tests for app_helpers |

---

## Task 1: Add Streamlit Dependency + Dark Theme Config

**Files:**
- Modify: `requirements.txt`
- Create: `.streamlit/config.toml`

- [ ] **Step 1: Add streamlit to requirements.txt**

Open `requirements.txt` and add at the end:
```
streamlit>=1.35.0
```

- [ ] **Step 2: Create .streamlit/config.toml**

```toml
[theme]
base = "dark"
primaryColor = "#ff4b4b"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
font = "sans serif"
```

- [ ] **Step 3: Install and verify**

```bash
cd D:\assitant_tools\tools_performance\task-tracker
pip install streamlit>=1.35.0
python -c "import streamlit; print(streamlit.__version__)"
```

Expected: prints a version >= 1.35.0

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .streamlit/config.toml
git commit -m "feat: add streamlit dependency and dark theme config"
```

---

## Task 2: app_helpers.py — Pure Functions + Tests

**Files:**
- Create: `app_helpers.py`
- Create: `tests/test_app_helpers.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app_helpers.py`:

```python
from datetime import date, timedelta
import pytest
from app_helpers import get_stats, group_by_priority, filter_tasks


def _today():
    return date.today().isoformat()

def _days(n):
    return (date.today() + timedelta(days=n)).isoformat()


def test_get_stats_empty():
    assert get_stats([]) == {"overdue": 0, "active": 0, "done": 0, "today": 0}


def test_get_stats_overdue():
    tasks = [{"active": True, "deadline": _days(-1)}]
    stats = get_stats(tasks)
    assert stats["overdue"] == 1
    assert stats["active"] == 1


def test_get_stats_today():
    tasks = [{"active": True, "deadline": _today()}]
    stats = get_stats(tasks)
    assert stats["today"] == 1
    assert stats["overdue"] == 0


def test_get_stats_done():
    tasks = [{"active": False, "deadline": _days(-5)}]
    stats = get_stats(tasks)
    assert stats["done"] == 1
    assert stats["active"] == 0


def test_get_stats_mixed():
    tasks = [
        {"active": True,  "deadline": _days(-1)},   # overdue
        {"active": True,  "deadline": _today()},     # today
        {"active": True,  "deadline": _days(3)},     # future active
        {"active": False, "deadline": _days(-2)},    # done
    ]
    s = get_stats(tasks)
    assert s["overdue"] == 1
    assert s["today"]   == 1
    assert s["active"]  == 3
    assert s["done"]    == 1


def test_group_by_priority_all_groups():
    tasks = [
        {"category_raw": "high"},
        {"category_raw": "high"},
        {"category_raw": "medium"},
        {"category_raw": "low"},
        {"category_raw": "ad-hoc"},
    ]
    groups = group_by_priority(tasks)
    assert len(groups["high"])   == 2
    assert len(groups["medium"]) == 1
    assert len(groups["low"])    == 1
    assert len(groups["ad-hoc"]) == 1


def test_group_by_priority_unknown_goes_to_low():
    tasks = [{"category_raw": "unknown"}]
    groups = group_by_priority(tasks)
    assert len(groups["low"]) == 1


def test_filter_tasks_by_name_case_insensitive():
    tasks = [
        {"task_name": "Báo cáo Q2", "category_raw": "high"},
        {"task_name": "Review code", "category_raw": "medium"},
    ]
    result = filter_tasks(tasks, "báo cáo", "")
    assert len(result) == 1
    assert result[0]["task_name"] == "Báo cáo Q2"


def test_filter_tasks_by_priority():
    tasks = [
        {"task_name": "T1", "category_raw": "high"},
        {"task_name": "T2", "category_raw": "medium"},
    ]
    result = filter_tasks(tasks, "", "high")
    assert len(result) == 1
    assert result[0]["task_name"] == "T1"


def test_filter_tasks_no_filter_returns_all():
    tasks = [
        {"task_name": "T1", "category_raw": "high"},
        {"task_name": "T2", "category_raw": "medium"},
    ]
    assert len(filter_tasks(tasks, "", "")) == 2


def test_filter_tasks_combined():
    tasks = [
        {"task_name": "Report high", "category_raw": "high"},
        {"task_name": "Report med",  "category_raw": "medium"},
        {"task_name": "Fix bug",     "category_raw": "high"},
    ]
    result = filter_tasks(tasks, "report", "high")
    assert len(result) == 1
    assert result[0]["task_name"] == "Report high"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:\assitant_tools\tools_performance\task-tracker
python -m pytest tests/test_app_helpers.py -v
```

Expected: `ModuleNotFoundError: No module named 'app_helpers'`

- [ ] **Step 3: Create app_helpers.py**

```python
from datetime import date


def get_stats(tasks: list[dict]) -> dict:
    today = date.today().isoformat()
    active = [t for t in tasks if t.get("active")]
    done   = [t for t in tasks if not t.get("active")]
    overdue = [t for t in active if t.get("deadline", "") < today]
    today_tasks = [t for t in active if t.get("deadline", "") == today]
    return {
        "overdue": len(overdue),
        "active":  len(active),
        "done":    len(done),
        "today":   len(today_tasks),
    }


def group_by_priority(tasks: list[dict]) -> dict:
    groups: dict[str, list] = {"high": [], "medium": [], "low": [], "ad-hoc": []}
    for task in tasks:
        key = task.get("category_raw", "low")
        groups[key if key in groups else "low"].append(task)
    return groups


def filter_tasks(tasks: list[dict], query: str, priority: str) -> list[dict]:
    result = tasks
    if query:
        q = query.lower()
        result = [t for t in result if q in t.get("task_name", "").lower()]
    if priority:
        result = [t for t in result if t.get("category_raw") == priority]
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_app_helpers.py -v
```

Expected: all 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app_helpers.py tests/test_app_helpers.py
git commit -m "feat: add app_helpers with stats/grouping/filtering logic"
```

---

## Task 3: app.py Skeleton — Imports, Page Config, CSS, Tab Structure

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create app.py with full skeleton**

```python
import os
import streamlit as st
from datetime import date
from dotenv import load_dotenv

from modules.task_manager import load_tasks, add_task, update_task, delete_task, get_active_tasks
from modules.discord_notifier import send_confirm, send_all_reminders, send_email_digest
from modules.deadline import calculate_deadline, get_label
from modules.ollama_client import generate_checklist
from app_helpers import get_stats, group_by_priority, filter_tasks

load_dotenv()

st.set_page_config(page_title="Task Tracker", page_icon="📋", layout="wide")

PRIORITY_COLORS = {
    "high":   "#ff4b4b",
    "medium": "#ffa500",
    "low":    "#00c853",
    "ad-hoc": "#89b4fa",
}

CATEGORY_OPTIONS = {
    "🔴 High":   "high",
    "🟡 Medium": "medium",
    "🟢 Low":    "low",
    "⚡ Ad-hoc": "ad-hoc",
}

RECUR_OPTIONS = {
    "Không lặp":       None,
    "🔄 Hằng tháng":  "monthly",
    "🔁 Hằng năm":    "yearly",
}

RECUR_REVERSE = {v: k for k, v in RECUR_OPTIONS.items()}

st.markdown("""
<style>
div[data-testid="stMetricValue"] { font-size: 28px !important; }
.task-card-high   { border-left: 3px solid #ff4b4b; background: #1a1a2e; padding: 10px 14px; border-radius: 6px; margin-bottom: 4px; }
.task-card-medium { border-left: 3px solid #ffa500; background: #1a1a2e; padding: 10px 14px; border-radius: 6px; margin-bottom: 4px; }
.task-card-low    { border-left: 3px solid #00c853; background: #1a1a2e; padding: 10px 14px; border-radius: 6px; margin-bottom: 4px; }
.task-card-adhoc  { border-left: 3px solid #89b4fa; background: #1a1a2e; padding: 10px 14px; border-radius: 6px; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

for key, val in [
    ("show_add_form",   False),
    ("editing_task_id", None),
    ("digest_results",  None),
    ("checklist_result", None),
    ("selected_task_id", None),
]:
    if key not in st.session_state:
        st.session_state[key] = val


def main():
    st.title("📋 Task Tracker")

    tab_tasks, tab_ai, tab_settings = st.tabs(["📝 Tasks", "🤖 AI Tools", "⚙️ Cài đặt"])

    with tab_tasks:
        st.write("Tab Tasks — coming in next task")

    with tab_ai:
        st.write("Tab AI Tools — coming in next task")

    with tab_settings:
        st.write("Tab Settings — coming in next task")


main()
```

- [ ] **Step 2: Run the app and verify it starts**

```bash
cd D:\assitant_tools\tools_performance\task-tracker
streamlit run app.py
```

Expected: browser opens at `http://localhost:8501` showing dark page with title "📋 Task Tracker" and 3 empty tabs. No errors in terminal.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add app.py skeleton with dark theme and tab structure"
```

---

## Task 4: Tab Tasks — Stats Row + Action Bar

**Files:**
- Modify: `app.py` — replace `render_tasks_tab` stub

- [ ] **Step 1: Replace the tasks tab content in main()**

Replace the `with tab_tasks:` block in `main()`:

```python
    with tab_tasks:
        render_tasks_tab()
```

Then add these functions before `main()`:

```python
def render_stats(tasks: list[dict]):
    stats = get_stats(tasks)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Quá hạn",    stats["overdue"])
    c2.metric("🟠 Đang làm",   stats["active"])
    c3.metric("🟢 Hoàn thành", stats["done"])
    c4.metric("📅 Hôm nay",    stats["today"])


def render_action_bar() -> tuple[str, str]:
    col_add, col_discord, col_search, col_filter = st.columns([1.2, 1.5, 3, 1.5])
    with col_add:
        if st.button("➕ Thêm task", use_container_width=True):
            st.session_state.show_add_form = not st.session_state.show_add_form
            st.session_state.editing_task_id = None
    with col_discord:
        if st.button("🔔 Gửi Discord", use_container_width=True):
            tasks = get_active_tasks()
            send_all_reminders(tasks)
            st.success(f"Đã gửi {len(tasks)} reminder lên Discord!")
    with col_search:
        query = st.text_input("🔍 Tìm task...", label_visibility="collapsed", placeholder="Tìm kiếm task...")
    with col_filter:
        priority_filter = st.selectbox(
            "Lọc",
            options=["", "high", "medium", "low", "ad-hoc"],
            format_func=lambda x: "Tất cả" if x == "" else get_label(x),
            label_visibility="collapsed",
        )
    return query, priority_filter


def render_tasks_tab():
    all_tasks = load_tasks()
    render_stats(all_tasks)
    st.divider()
    query, priority_filter = render_action_bar()
    st.write("Task list — coming soon")
```

- [ ] **Step 2: Run and verify**

```bash
streamlit run app.py
```

Expected: Tab Tasks shows 4 metric boxes with real counts from `data/tasks.json`, a search input, filter dropdown, and two buttons. No errors.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add stats row and action bar to tasks tab"
```

---

## Task 5: Tab Tasks — Add Task Form

**Files:**
- Modify: `app.py` — add `render_add_form()`, wire into `render_tasks_tab()`

- [ ] **Step 1: Add render_add_form() before main()**

```python
def render_add_form():
    with st.expander("➕ Thêm task mới", expanded=True):
        task_name = st.text_input("Tên task *", key="add_name")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Ngày bắt đầu *", value=date.today(), key="add_start")
        with col2:
            end_date = st.date_input("Ngày kết thúc *", value=date.today(), key="add_end")

        cat_labels = list(CATEGORY_OPTIONS.keys())
        category_display = st.selectbox("Độ ưu tiên *", cat_labels, key="add_cat")
        category = CATEGORY_OPTIONS[category_display]

        note = st.text_area("Ghi chú", key="add_note", placeholder="Không bắt buộc")

        recur_labels = list(RECUR_OPTIONS.keys())
        recur_display = st.selectbox("Lặp lại", recur_labels, key="add_recur")
        recur = RECUR_OPTIONS[recur_display]

        col_submit, col_cancel = st.columns([1, 4])
        with col_submit:
            submitted = st.button("💾 Lưu task", key="add_submit", use_container_width=True)
        with col_cancel:
            if st.button("❌ Hủy", key="add_cancel"):
                st.session_state.show_add_form = False
                st.rerun()

        if submitted:
            if not task_name.strip():
                st.error("Tên task không được để trống.")
                return
            if end_date < start_date:
                st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                return

            deadline = calculate_deadline(end_date.isoformat(), category)
            with st.spinner("Đang tạo AI checklist..."):
                checklist = generate_checklist(
                    task_name, get_label(category), deadline, note or "(none)", ""
                )

            task = {
                "task_name":      task_name.strip(),
                "start_date":     start_date.isoformat(),
                "end_date":       end_date.isoformat(),
                "category_raw":   category,
                "category_label": get_label(category),
                "deadline":       deadline,
                "note":           note.strip() or "(none)",
                "recur":          recur,
                "checklist":      checklist,
            }
            saved = add_task(task)
            send_confirm(saved)
            st.session_state.show_add_form = False
            st.success(f"✅ Đã tạo task: {saved['task_name']}")
            st.rerun()
```

- [ ] **Step 2: Wire render_add_form into render_tasks_tab()**

Replace the `st.write("Task list — coming soon")` line in `render_tasks_tab()` with:

```python
    if st.session_state.show_add_form:
        render_add_form()
    st.write("Task cards — coming in next task")
```

- [ ] **Step 3: Run and test**

```bash
streamlit run app.py
```

Expected: clicking "➕ Thêm task" toggles the add form. Fill in fields and click "💾 Lưu task" — task is saved to `data/tasks.json` and stats update. Discord confirmation sent if configured.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add task creation form with AI checklist generation"
```

---

## Task 6: Tab Tasks — Task Cards Grouped by Priority

**Files:**
- Modify: `app.py` — add `render_task_card()`, `render_priority_group()`, wire into `render_tasks_tab()`

- [ ] **Step 1: Add render_task_card() before main()**

```python
def render_task_card(task: dict):
    raw = task.get("category_raw", "low")
    color = PRIORITY_COLORS.get(raw, "#888")
    today = date.today().isoformat()
    is_overdue = task.get("active") and task.get("deadline", "") < today
    overdue_html = ' <span style="color:#ff4b4b;font-size:11px">⚠️ Quá hạn!</span>' if is_overdue else ""

    st.markdown(
        f'<div style="border-left:3px solid {color};background:#1a1a2e;'
        f'padding:10px 14px;border-radius:6px;margin-bottom:4px;">'
        f'<strong style="color:#fafafa;font-size:14px">{task["task_name"]}</strong>{overdue_html}<br>'
        f'<span style="color:#a0a0b0;font-size:12px">⏰ {task["deadline"]} · {task["category_label"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tid = task["task_id"]
    c1, c2, c3, c4 = st.columns([1, 1, 1, 6])
    with c1:
        if st.button("✅", key=f"done_{tid}", help="Hoàn thành"):
            update_task(tid, {"active": False})
            st.rerun()
    with c2:
        if st.button("✏️", key=f"edit_{tid}", help="Sửa"):
            st.session_state.editing_task_id = tid
            st.session_state.show_add_form = False
            st.rerun()
    with c3:
        if st.button("🗑️", key=f"del_{tid}", help="Xóa"):
            delete_task(tid)
            st.rerun()
```

- [ ] **Step 2: Add render_priority_group() before main()**

```python
PRIORITY_GROUP_CONFIG = [
    ("high",   "🔴 High",   True),
    ("medium", "🟡 Medium", True),
    ("low",    "🟢 Low",    False),
    ("ad-hoc", "⚡ Ad-hoc", False),
]


def render_priority_group(label: str, tasks: list[dict], expanded: bool):
    if not tasks:
        return
    with st.expander(f"{label} ({len(tasks)})", expanded=expanded):
        for task in sorted(tasks, key=lambda t: t.get("deadline", "")):
            render_task_card(task)
            if st.session_state.editing_task_id == task["task_id"]:
                render_edit_form(task)
```

- [ ] **Step 3: Add render_edit_form() placeholder before render_priority_group()**

```python
def render_edit_form(task: dict):
    pass  # implemented in Task 7
```

- [ ] **Step 4: Update render_tasks_tab() to render cards**

Replace the `st.write("Task cards — coming in next task")` line:

```python
    active_tasks = [t for t in all_tasks if t.get("active")]
    filtered = filter_tasks(active_tasks, query, priority_filter)
    groups = group_by_priority(filtered)

    for raw_key, label, expanded in PRIORITY_GROUP_CONFIG:
        render_priority_group(label, groups[raw_key], expanded)
```

- [ ] **Step 5: Run and verify**

```bash
streamlit run app.py
```

Expected: active tasks appear as cards grouped under HIGH/MEDIUM/LOW/AD-HOC expanders. HIGH and MEDIUM expanded by default. Done/Delete buttons work and update the list. Overdue tasks show ⚠️ badge.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: add task cards grouped by priority with done/delete actions"
```

---

## Task 7: Tab Tasks — Edit Task Form

**Files:**
- Modify: `app.py` — implement `render_edit_form()`

- [ ] **Step 1: Replace the render_edit_form() stub**

Find `def render_edit_form(task: dict):` and `pass` and replace the entire function:

```python
def render_edit_form(task: dict):
    tid = task["task_id"]
    with st.container():
        st.markdown("---")
        st.markdown(f"**✏️ Sửa task:** {task['task_name']}")

        task_name = st.text_input("Tên task", value=task["task_name"], key=f"en_{tid}")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Ngày bắt đầu", value=date.fromisoformat(task["start_date"]), key=f"es_{tid}"
            )
        with col2:
            end_date = st.date_input(
                "Ngày kết thúc", value=date.fromisoformat(task["end_date"]), key=f"ee_{tid}"
            )

        cat_labels = list(CATEGORY_OPTIONS.keys())
        cat_index = cat_labels.index(task["category_label"]) if task["category_label"] in cat_labels else 0
        category_display = st.selectbox("Độ ưu tiên", cat_labels, index=cat_index, key=f"ec_{tid}")
        category = CATEGORY_OPTIONS[category_display]

        note = st.text_area("Ghi chú", value=task.get("note", ""), key=f"en2_{tid}")

        recur_labels = list(RECUR_OPTIONS.keys())
        recur_label_current = RECUR_REVERSE.get(task.get("recur"), "Không lặp")
        recur_index = recur_labels.index(recur_label_current)
        recur_display = st.selectbox("Lặp lại", recur_labels, index=recur_index, key=f"er_{tid}")
        recur = RECUR_OPTIONS[recur_display]

        col_save, col_cancel = st.columns([1, 4])
        with col_save:
            if st.button("💾 Lưu", key=f"esave_{tid}", use_container_width=True):
                if not task_name.strip():
                    st.error("Tên task không được để trống.")
                    return
                new_deadline = calculate_deadline(end_date.isoformat(), category)
                update_task(tid, {
                    "task_name":      task_name.strip(),
                    "start_date":     start_date.isoformat(),
                    "end_date":       end_date.isoformat(),
                    "category_raw":   category,
                    "category_label": get_label(category),
                    "deadline":       new_deadline,
                    "note":           note.strip() or "(none)",
                    "recur":          recur,
                })
                st.session_state.editing_task_id = None
                st.rerun()
        with col_cancel:
            if st.button("❌ Hủy", key=f"ecancel_{tid}"):
                st.session_state.editing_task_id = None
                st.rerun()
        st.markdown("---")
```

- [ ] **Step 2: Run and test**

```bash
streamlit run app.py
```

Expected: clicking ✏️ on a task opens the edit form inline below that card, pre-filled with current values. Saving updates the task and closes the form. Cancelling closes without saving.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add inline edit form for tasks"
```

---

## Task 8: Tab AI Tools — Email Digest

**Files:**
- Modify: `app.py` — implement `render_ai_tab()` with digest section

- [ ] **Step 1: Add render_ai_tab() before main()**

```python
def render_ai_tab():
    st.subheader("📧 Email Digest hôm nay")
    st.caption("Đọc email từ Outlook, phân loại và tóm tắt bằng AI.")

    if st.button("▶ Tạo digest", key="run_digest"):
        try:
            from modules.email_digest import run_digest
            with st.spinner("Đang đọc email và tạo digest..."):
                st.session_state.digest_results = run_digest(hours=24)
        except Exception as e:
            st.error(f"Lỗi khi tạo digest: {e}")

    if st.session_state.digest_results is not None:
        results = st.session_state.digest_results
        total = sum(len(v) for v in results.values())

        if total == 0:
            st.info("✅ Không có email mới liên quan hôm nay.")
        else:
            st.success(f"Tìm thấy {total} email mới.")
            if st.button("📤 Gửi digest lên Discord", key="send_digest"):
                send_email_digest(results)
                st.success("Đã gửi digest lên Discord!")

            PRIORITY_LABELS = {"urgent": "🔴 URGENT", "normal": "🟡 NORMAL", "fyi": "🟢 FYI"}
            for level in ("urgent", "normal", "fyi"):
                emails = results.get(level, [])
                if not emails:
                    continue
                with st.expander(f"{PRIORITY_LABELS[level]} ({len(emails)} emails)", expanded=(level == "urgent")):
                    for email in emails:
                        st.markdown(f"**{email.get('sender_name', '?')}** — {email.get('subject', '?')}")
                        st.caption(email.get("summary", ""))
                        replies = email.get("replies", [])
                        if replies:
                            st.markdown("💬 Gợi ý reply: " + " · ".join(f"`{r}`" for r in replies[:3]))
                        st.divider()

    st.divider()
    render_ai_checklist_section()
```

- [ ] **Step 2: Wire render_ai_tab into main()**

Replace `st.write("Tab AI Tools — coming in next task")` in `main()`:

```python
    with tab_ai:
        render_ai_tab()
```

- [ ] **Step 3: Add render_ai_checklist_section() stub before render_ai_tab()**

```python
def render_ai_checklist_section():
    pass  # implemented in Task 9
```

- [ ] **Step 4: Run and verify**

```bash
streamlit run app.py
```

Expected: Tab "AI Tools" shows the digest section. Clicking "▶ Tạo digest" attempts to run (may fail if Outlook not configured — should show error message, not crash). No unhandled exceptions.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: add email digest section to AI Tools tab"
```

---

## Task 9: Tab AI Tools — AI Checklist Generator

**Files:**
- Modify: `app.py` — implement `render_ai_checklist_section()`

- [ ] **Step 1: Replace the render_ai_checklist_section() stub**

```python
def render_ai_checklist_section():
    st.subheader("✅ AI Checklist cho task")
    st.caption("Chọn một task — AI sẽ tạo checklist bước thực hiện.")

    active_tasks = get_active_tasks()
    if not active_tasks:
        st.info("Không có task đang hoạt động.")
        return

    task_options = {t["task_name"]: t for t in active_tasks}
    selected_name = st.selectbox(
        "Chọn task",
        options=list(task_options.keys()),
        key="checklist_task_select",
    )
    selected_task = task_options[selected_name]

    col_gen, col_save = st.columns([1, 1])
    with col_gen:
        if st.button("🤖 Tạo checklist", key="gen_checklist"):
            with st.spinner("AI đang tạo checklist..."):
                try:
                    result = generate_checklist(
                        selected_task["task_name"],
                        selected_task["category_label"],
                        selected_task["deadline"],
                        selected_task.get("note", "(none)"),
                        "",
                    )
                    st.session_state.checklist_result = result
                    st.session_state.selected_task_id = selected_task["task_id"]
                except Exception as e:
                    st.error(f"Lỗi tạo checklist: {e}")

    if st.session_state.checklist_result:
        st.markdown("**Kết quả:**")
        for line in st.session_state.checklist_result.splitlines():
            if line.strip():
                st.markdown(line)

        with col_save:
            if st.button("💾 Lưu vào task", key="save_checklist"):
                update_task(
                    st.session_state.selected_task_id,
                    {"checklist": st.session_state.checklist_result},
                )
                st.session_state.checklist_result = None
                st.success("✅ Đã lưu checklist vào task!")
                st.rerun()
```

- [ ] **Step 2: Run and test**

```bash
streamlit run app.py
```

Expected: "AI Checklist" section appears below digest section. Selecting a task and clicking "🤖 Tạo checklist" generates checklist lines (requires Ollama running or ANTHROPIC_API_KEY set). "💾 Lưu vào task" saves to tasks.json.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add AI checklist generator to AI Tools tab"
```

---

## Task 10: Tab Settings — .env Status Display

**Files:**
- Modify: `app.py` — implement `render_settings_tab()`

- [ ] **Step 1: Add render_settings_tab() before main()**

```python
def render_settings_tab():
    st.subheader("⚙️ Cấu hình hệ thống")
    st.caption("Trạng thái các biến môi trường từ file .env (chỉ xem).")

    def status(key: str, label: str):
        val = os.getenv(key, "")
        icon = "✅" if val else "❌"
        masked = val[:8] + "..." if val and len(val) > 8 else val
        st.markdown(f"{icon} **{label}**: `{masked if val else 'chưa cấu hình'}`")

    st.markdown("#### Integrations")
    status("ANTHROPIC_API_KEY",   "Anthropic API Key")
    status("DISCORD_WEBHOOK_URL", "Discord Webhook")
    status("OBSIDIAN_API_KEY",    "Obsidian API Key")
    status("OBSIDIAN_BASE_URL",   "Obsidian URL")

    st.markdown("#### AI / Local LLM")
    status("OLLAMA_BASE_URL", "Ollama URL")
    status("OLLAMA_MODEL",    "Ollama Model")

    st.markdown("#### Email / Outlook")
    status("USER_EMAIL",       "User Email")
    status("BOSS_EMAIL",       "Boss Email")
    status("EMAIL_QUEUE_PATH", "Email Queue Path")

    st.markdown("#### Reminders")
    t1 = os.getenv("REMINDER_TIME_1", "09:00")
    t2 = os.getenv("REMINDER_TIME_2", "13:30")
    st.markdown(f"🕐 Reminder 1: `{t1}` · Reminder 2: `{t2}`")
    st.info("Để thay đổi cấu hình, chỉnh sửa file `.env` rồi khởi động lại app.")
```

- [ ] **Step 2: Wire into main()**

Replace `st.write("Tab Settings — coming in next task")` in `main()`:

```python
    with tab_settings:
        render_settings_tab()
```

- [ ] **Step 3: Run final check**

```bash
streamlit run app.py
```

Expected: Tab "Cài đặt" shows all env var statuses. Keys are masked (first 8 chars + ...). Missing vars show ❌. App fully functional across all 3 tabs.

- [ ] **Step 4: Final commit**

```bash
git add app.py
git commit -m "feat: add settings tab with env status display"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Single page dark theme dashboard — Tasks 1, 3
- ✅ Stats row (overdue/active/done/today) — Task 4
- ✅ Search + filter — Task 4
- ✅ Cards grouped by priority — Task 6
- ✅ Add task form with AI checklist — Task 5
- ✅ Edit task inline — Task 7
- ✅ Done / Delete actions — Task 6
- ✅ Discord send all reminders button — Task 4
- ✅ Tab AI Tools: email digest — Task 8
- ✅ Tab AI Tools: AI checklist — Task 9
- ✅ Tab Settings: .env read-only display — Task 10

**No placeholders:** all steps have complete code.

**Type consistency:**
- `generate_checklist(task_name, category_label, deadline, note, obsidian_context)` — used consistently across Tasks 5 and 9
- `update_task(task_id, fields)` — used consistently in Tasks 6, 7, 9
- `get_active_tasks()` returns `list[dict]` — used in Tasks 4, 9
- `filter_tasks(tasks, query, priority)` — matches app_helpers signature
