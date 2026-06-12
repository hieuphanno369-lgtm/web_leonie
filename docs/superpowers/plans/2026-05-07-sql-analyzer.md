# SQL Analyzer & Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SQL → Obsidian Note section to the AI Tools tab: paste a SQL query, AI analyzes business intent and generates a YAML-frontmatter Obsidian note, with a separate optimizer that suggests a more performant version of the same query.

**Architecture:** New `modules/sql_analyzer.py` handles all AI calls and file I/O, following the single-responsibility pattern of existing modules. `app.py` gets a new `render_sql_analyzer_section()` function wired into `render_ai_tab()`. Files are saved to `D:\ai_brain\SQL Queries\` with timestamp-slug filenames.

**Tech Stack:** Python 3.11+, Streamlit, Anthropic Claude API / Ollama (via existing `ai_client.py`), `unicodedata` (stdlib), `pathlib` (stdlib)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `modules/ai_client.py` | Modify | Expose `call_ai()` as public wrapper |
| `modules/sql_analyzer.py` | Create | `_slugify`, `build_note_content`, `save_note`, `analyze_query`, `optimize_query` |
| `tests/test_sql_analyzer.py` | Create | Unit tests for all sql_analyzer functions |
| `app.py` | Modify | Add `render_sql_analyzer_section()`, session state keys, call in `render_ai_tab()` |
| `GUIDE.md` | Modify | Add SQL Analyzer & Optimizer section |
| `CLAUDE.md` | Create | Module map for the whole codebase |

---

## Task 1: Expose `call_ai` as public function in `ai_client.py`

**Files:**
- Modify: `modules/ai_client.py`

`sql_analyzer.py` needs to call AI. The existing `_call_ai` in `ai_client.py` is private. Add a public wrapper so modules can import it without relying on a private name.

- [ ] **Step 1: Add the public wrapper at the bottom of `modules/ai_client.py`**

Append after the existing `classify_email_ai` function:

```python
def call_ai(prompt: str, max_tokens: int = 200) -> str:
    """Public wrapper around _call_ai for use by other modules."""
    return _call_ai(prompt, max_tokens)
```

- [ ] **Step 2: Verify the import works**

```powershell
cd D:\assitant_tools\tools_performance\task-tracker\.claude\worktrees\quizzical-golick-f6d1ad
.venv\Scripts\python.exe -c "from modules.ai_client import call_ai; print('ok')"
```
Expected output: `ok`

- [ ] **Step 3: Commit**

```powershell
git add modules/ai_client.py
git commit -m "feat: expose call_ai as public function in ai_client"
```

---

## Task 2: Create `modules/sql_analyzer.py` — pure functions

**Files:**
- Create: `modules/sql_analyzer.py`
- Create: `tests/test_sql_analyzer.py`

These functions have no AI calls and are fully testable in isolation.

- [ ] **Step 1: Write failing tests for `_slugify` and `build_note_content`**

Create `tests/test_sql_analyzer.py`:

```python
import re
from pathlib import Path
import pytest
from modules.sql_analyzer import _slugify, build_note_content, save_note


def test_slugify_basic():
    assert _slugify("doanh thu san pham") == "doanh-thu-san-pham"


def test_slugify_strips_special_chars():
    assert _slugify("Hello, World!") == "hello-world"


def test_slugify_truncates_at_60():
    long_text = "word " * 20
    assert len(_slugify(long_text)) <= 60


def test_slugify_handles_vietnamese_diacritics():
    result = _slugify("Doanh thu sản phẩm")
    assert result == "doanh-thu-san-pham"


def test_build_note_content_has_yaml_frontmatter():
    analysis = {
        "title": "Test Query",
        "description": "What is revenue?",
        "tables": ["orders"],
        "filters": ["status = active"],
        "tags": ["sql", "revenue"],
        "keywords": ["doanh_thu"],
    }
    content = build_note_content(analysis, "SELECT SUM(amount) FROM orders")
    assert content.startswith("---")
    assert "title: Test Query" in content
    assert "tables: ['orders']" in content


def test_build_note_content_includes_sql():
    analysis = {
        "title": "T", "description": "D",
        "tables": [], "filters": [], "tags": [], "keywords": [],
    }
    content = build_note_content(analysis, "SELECT 1")
    assert "SELECT 1" in content


def test_save_note_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.sql_analyzer.SQL_NOTES_DIR", tmp_path)
    analysis = {
        "title": "Test query",
        "description": "Desc",
        "tables": ["orders"],
        "filters": ["status = active"],
        "tags": ["sql"],
        "keywords": ["thu_thap"],
    }
    path = save_note(analysis, "SELECT * FROM orders")
    assert path.exists()
    assert "test-query" in path.name


def test_save_note_filename_has_date_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.sql_analyzer.SQL_NOTES_DIR", tmp_path)
    analysis = {
        "title": "Doanh thu", "description": "",
        "tables": [], "filters": [], "tags": [], "keywords": [],
    }
    path = save_note(analysis, "SELECT 1")
    assert re.match(r"\d{4}-\d{2}-\d{2}_doanh-thu\.md", path.name)
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_sql_analyzer.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'modules.sql_analyzer'`

- [ ] **Step 3: Create `modules/sql_analyzer.py` with pure functions**

```python
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from modules.ai_client import call_ai

VAULT_PATH = Path(r"D:\ai_brain")
SQL_NOTES_DIR = VAULT_PATH / "SQL Queries"


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text[:60]


def build_note_content(analysis: dict, sql: str) -> str:
    today = date.today().isoformat()
    return (
        f"---\n"
        f"title: {analysis.get('title', '')}\n"
        f"date: {today}\n"
        f"tags: {analysis.get('tags', [])}\n"
        f"tables: {analysis.get('tables', [])}\n"
        f"filters: {analysis.get('filters', [])}\n"
        f"keywords: {analysis.get('keywords', [])}\n"
        f"description: \"{analysis.get('description', '')}\"\n"
        f"---\n\n"
        f"## Business Question\n\n"
        f"{analysis.get('description', '')}\n\n"
        f"## SQL Query\n\n"
        f"```sql\n{sql.strip()}\n```\n\n"
        f"## Notes\n\n"
        f"_Tạo tự động bởi Task Tracker SQL Analyzer — {today}_\n"
    )


def save_note(analysis: dict, sql: str) -> Path:
    SQL_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    slug = _slugify(analysis.get("title", "query"))
    path = SQL_NOTES_DIR / f"{today}_{slug}.md"
    path.write_text(build_note_content(analysis, sql), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_sql_analyzer.py -v -k "not analyze and not optimize"
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```powershell
git add modules/sql_analyzer.py tests/test_sql_analyzer.py
git commit -m "feat: add sql_analyzer pure functions (slugify, build_note_content, save_note)"
```

---

## Task 3: Add `analyze_query` and `optimize_query` to `modules/sql_analyzer.py`

**Files:**
- Modify: `modules/sql_analyzer.py`
- Modify: `tests/test_sql_analyzer.py`

- [ ] **Step 1: Add failing tests for `analyze_query` and `optimize_query`**

Append to `tests/test_sql_analyzer.py`:

```python
import json
from unittest.mock import patch


def test_analyze_query_parses_json():
    mock_resp = json.dumps({
        "title": "Doanh thu tháng",
        "description": "Doanh thu từng sản phẩm tháng này là bao nhiêu?",
        "tables": ["orders"],
        "filters": ["month = 5"],
        "tags": ["revenue", "monthly"],
        "keywords": ["doanh_thu"],
    })
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import analyze_query
        result = analyze_query("SELECT SUM(amount) FROM orders WHERE month=5")
    assert result["title"] == "Doanh thu tháng"
    assert result["tables"] == ["orders"]
    assert "description" in result


def test_analyze_query_handles_markdown_wrapped_json():
    inner = '{"title":"T","description":"D","tables":[],"filters":[],"tags":[],"keywords":[]}'
    mock_resp = f"```json\n{inner}\n```"
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import analyze_query
        result = analyze_query("SELECT 1")
    assert result["title"] == "T"


def test_optimize_query_returns_improvements_and_sql():
    mock_resp = json.dumps({
        "improvements": ["Thêm index cho cột month", "Tránh dùng SELECT *"],
        "optimized_sql": "SELECT SUM(amount) FROM orders WHERE month=5",
    })
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import optimize_query
        result = optimize_query("SELECT * FROM orders WHERE month=5")
    assert len(result["improvements"]) == 2
    assert "optimized_sql" in result


def test_optimize_query_handles_markdown_wrapped_json():
    inner = '{"improvements":["Fix"],"optimized_sql":"SELECT 1"}'
    mock_resp = f"```json\n{inner}\n```"
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import optimize_query
        result = optimize_query("SELECT 1")
    assert result["optimized_sql"] == "SELECT 1"
```

- [ ] **Step 2: Run tests — expect FAIL (functions not defined)**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_sql_analyzer.py::test_analyze_query_parses_json -v
```
Expected: `ImportError` or `AttributeError`

- [ ] **Step 3: Add `_parse_json_response`, `analyze_query`, `optimize_query` to `modules/sql_analyzer.py`**

Append to `modules/sql_analyzer.py`:

```python
def _parse_json_response(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw)


def analyze_query(sql: str) -> dict:
    prompt = (
        "Phân tích SQL query sau và trả về JSON với các field:\n"
        "- title: tên ngắn gọn mô tả mục đích query (tiếng Việt, max 60 ký tự)\n"
        "- description: câu hỏi business mà query này trả lời (1 câu, tiếng Việt)\n"
        "- tables: danh sách tên bảng được dùng (array of strings)\n"
        "- filters: danh sách điều kiện WHERE chính (array of strings, dạng 'column = value')\n"
        "- tags: 3-5 từ khóa ngắn liên quan (array of strings, tiếng Anh lowercase)\n"
        "- keywords: 3-5 từ khóa tiếng Việt để link Obsidian graph (array of strings)\n\n"
        "Chỉ trả về JSON, không giải thích thêm.\n\n"
        f"SQL:\n{sql}"
    )
    return _parse_json_response(call_ai(prompt, max_tokens=400))


def optimize_query(sql: str) -> dict:
    prompt = (
        "Tối ưu SQL query sau. Giữ nguyên kết quả output (same columns, same rows).\n"
        "Trả về JSON với:\n"
        "- improvements: danh sách các điểm cải tiến (array of strings, tiếng Việt, mỗi item 1 câu)\n"
        "- optimized_sql: câu query đã tối ưu (string)\n\n"
        "Chỉ trả về JSON, không giải thích thêm.\n\n"
        f"SQL:\n{sql}"
    )
    return _parse_json_response(call_ai(prompt, max_tokens=600))
```

- [ ] **Step 4: Run all sql_analyzer tests — expect all PASS**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_sql_analyzer.py -v
```
Expected: all 11 tests PASS

- [ ] **Step 5: Commit**

```powershell
git add modules/sql_analyzer.py tests/test_sql_analyzer.py
git commit -m "feat: add analyze_query and optimize_query to sql_analyzer"
```

---

## Task 4: Add `render_sql_analyzer_section()` to `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add session state keys for SQL analyzer**

In `app.py`, find the session state initialization block (lines 55–63):

```python
for key, val in [
    ("show_add_form",   False),
    ("editing_task_id", None),
    ("digest_results",  None),
    ("checklist_result", None),
    ("selected_task_id", None),
]:
```

Replace with:

```python
for key, val in [
    ("show_add_form",    False),
    ("editing_task_id",  None),
    ("digest_results",   None),
    ("checklist_result", None),
    ("selected_task_id", None),
    ("sql_analysis",     None),
    ("sql_optimization", None),
]:
```

- [ ] **Step 2: Add the `render_sql_analyzer_section()` function**

Add the following function after `render_ai_checklist_section()` and before `render_ai_tab()` in `app.py`:

```python
def render_sql_analyzer_section():
    st.divider()
    st.subheader("🔍 SQL → Obsidian Note")
    st.caption("Paste SQL query — AI phân tích business intent và gợi ý tối ưu.")

    sql = st.text_area("SQL Query", key="sql_input", placeholder="SELECT ...")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Phân tích", key="btn_analyze", use_container_width=True):
            if not sql.strip():
                st.warning("Vui lòng nhập SQL query.")
            else:
                with st.spinner("AI đang phân tích..."):
                    try:
                        from modules.sql_analyzer import analyze_query
                        st.session_state.sql_analysis = analyze_query(sql)
                    except Exception as e:
                        st.error(f"AI trả về kết quả không hợp lệ, thử lại. ({e})")

    with col2:
        if st.button("⚡ Optimize SQL", key="btn_optimize", use_container_width=True):
            if not sql.strip():
                st.warning("Vui lòng nhập SQL query.")
            else:
                with st.spinner("AI đang tối ưu..."):
                    try:
                        from modules.sql_analyzer import optimize_query
                        st.session_state.sql_optimization = optimize_query(sql)
                    except Exception as e:
                        st.error(f"AI trả về kết quả không hợp lệ, thử lại. ({e})")

    if st.session_state.sql_analysis:
        analysis = st.session_state.sql_analysis
        with st.expander("📄 Preview note", expanded=True):
            title = st.text_input("Title", value=analysis.get("title", ""), key="sql_title")
            tags = st.text_input(
                "Tags (comma-separated)",
                value=", ".join(analysis.get("tags", [])),
                key="sql_tags",
            )
            tables = st.text_input(
                "Tables",
                value=", ".join(analysis.get("tables", [])),
                key="sql_tables",
            )
            description = st.text_area(
                "Business Description",
                value=analysis.get("description", ""),
                key="sql_desc",
            )

            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            tables_list = [t.strip() for t in tables.split(",") if t.strip()]
            preview = {
                **analysis,
                "title": title,
                "tags": tags_list,
                "tables": tables_list,
                "description": description,
            }

            from modules.sql_analyzer import build_note_content
            st.code(build_note_content(preview, sql), language="markdown")

            if st.button("💾 Lưu vào Obsidian", key="btn_save_note", use_container_width=True):
                try:
                    from modules.sql_analyzer import save_note
                    saved_path = save_note(preview, sql)
                    st.success(f"✅ Đã lưu: `{saved_path}`")
                    st.session_state.sql_analysis = None
                except Exception as e:
                    st.error(f"Không thể lưu file: {e}")

    if st.session_state.sql_optimization:
        opt = st.session_state.sql_optimization
        with st.expander("⚡ SQL được tối ưu", expanded=True):
            for point in opt.get("improvements", []):
                st.markdown(f"- {point}")
            st.code(opt.get("optimized_sql", ""), language="sql")
```

- [ ] **Step 3: Call `render_sql_analyzer_section()` inside `render_ai_tab()`**

In `render_ai_tab()`, add a call at the end of the function, after `render_ai_checklist_section()`:

```python
def render_ai_tab():
    st.subheader("📧 Email Digest hôm nay")
    # ... existing code ...
    st.divider()
    render_ai_checklist_section()
    render_sql_analyzer_section()   # ← add this line
```

- [ ] **Step 4: Start the app and verify visually**

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`, go to "🤖 AI Tools" tab, scroll to bottom. Verify:
- "🔍 SQL → Obsidian Note" section appears
- Paste `SELECT product_name, SUM(amount) FROM orders GROUP BY product_name` and click "🔍 Phân tích"
- Preview expander opens with editable fields
- Click "⚡ Optimize SQL" — optimization section appears below

- [ ] **Step 5: Commit**

```powershell
git add app.py
git commit -m "feat: add SQL analyzer section to AI Tools tab"
```

---

## Task 5: Update `GUIDE.md` and create `CLAUDE.md`

**Files:**
- Modify: `GUIDE.md`
- Create: `CLAUDE.md`

- [ ] **Step 1: Add SQL Analyzer section to `GUIDE.md`**

Append to the end of `GUIDE.md`:

```markdown
---

## SQL → Obsidian Note

**Tab:** 🤖 AI Tools → cuộn xuống cuối

### Cách dùng

1. Paste SQL query vào text area
2. Click **🔍 Phân tích** → AI sinh business description, title, tags, tables
3. Xem và chỉnh preview note trong expander
4. Click **💾 Lưu vào Obsidian** → file được lưu tại `D:\ai_brain\SQL Queries\`

### SQL Optimizer

Dùng nút **⚡ Optimize SQL** (độc lập với phân tích) để nhận gợi ý tối ưu query cùng outcome.

### Định dạng file

File lưu dạng `YYYY-MM-DD_slug-title.md` với YAML frontmatter đầy đủ:
`title`, `date`, `tags`, `tables`, `filters`, `keywords`, `description`

Các field `tags` và `keywords` tự động tạo connections trong Obsidian Graph.

### Đổi đường dẫn vault

Mở `modules/sql_analyzer.py`, sửa dòng:

```python
VAULT_PATH = Path(r"D:\ai_brain")
```
```

- [ ] **Step 2: Create `CLAUDE.md`**

Create a new file `CLAUDE.md` at the project root:

```markdown
# Task Tracker — Codebase Guide

## Run

```powershell
.venv\Scripts\Activate.ps1
streamlit run app.py
```

Tests:
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

## Module Map

| File | Responsibility |
|------|----------------|
| `app.py` | Streamlit UI — tabs, forms, session state |
| `app_helpers.py` | Pure functions: stats, grouping, filtering tasks |
| `modules/task_manager.py` | Load/save/update/delete tasks in `data/tasks.json` |
| `modules/deadline.py` | Calculate deadline dates by category |
| `modules/ollama_client.py` | Generate AI checklist (Ollama → Claude fallback) |
| `modules/ai_client.py` | Shared AI call wrapper: Claude API → Ollama fallback |
| `modules/sql_analyzer.py` | SQL → Obsidian note: analyze business intent, optimize query, write .md files |
| `modules/obsidian_client.py` | Read vault files for context (keyword scoring) |
| `modules/discord_notifier.py` | Send task reminders and email digest to Discord |
| `modules/email_digest.py` | Read Outlook emails, classify, summarize |
| `modules/email_classifier.py` | Rule-based + AI email priority classification |
| `modules/reply_suggester.py` | Generate reply options for emails |
| `modules/outlook_reader.py` | Read emails via win32com |
| `modules/email_history.py` | Track sent/skipped email history |
| `modules/style_learner.py` | Learn user reply style from past emails |
| `scheduler.py` | Daily reminders at 09:00 and 13:30 |
| `main.py` | CLI menu (legacy, pre-Streamlit) |
| `add_task.py` | CLI add task (legacy) |

## Key Paths

- Tasks data: `data/tasks.json`
- Obsidian vault: `D:\ai_brain`
- SQL notes output: `D:\ai_brain\SQL Queries\`
- Config: `.env` (see `.env.example`)

## AI Priority

All AI calls: Claude API (`ANTHROPIC_API_KEY`) → Ollama (`OLLAMA_BASE_URL`) → fail gracefully.
```

- [ ] **Step 3: Run full test suite**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 4: Commit**

```powershell
git add GUIDE.md CLAUDE.md
git commit -m "docs: update GUIDE.md with SQL analyzer and create CLAUDE.md module map"
```

---

## Self-Review

**Spec coverage check:**
- ✅ SQL paste + analyze → business questions (Task 3: `analyze_query`)
- ✅ Preview mockup with editable fields (Task 4: UI expander)
- ✅ Save to YAML-frontmatter `.md` (Task 2: `build_note_content`, `save_note`)
- ✅ Obsidian graph keywords via `tags` + `keywords` frontmatter fields (Task 2)
- ✅ `D:\ai_brain\SQL Queries\` auto-created (Task 2: `SQL_NOTES_DIR.mkdir`)
- ✅ Filename: `YYYY-MM-DD_slug.md` (Task 2: `save_note`)
- ✅ SQL Optimizer — separate button, bullet improvements + optimized SQL (Task 3, Task 4)
- ✅ GUIDE.md updated (Task 5)
- ✅ CLAUDE.md created (Task 5)

**Type consistency:**
- `analyze_query` → `dict` consumed by `render_sql_analyzer_section` as `analysis` ✅
- `optimize_query` → `dict` with `improvements: list[str]` and `optimized_sql: str` ✅
- `save_note(analysis, sql)` → `Path` ✅ matches Task 2 definition and Task 4 usage
- `build_note_content(analysis, sql)` → `str` ✅ used in both Task 2 (save_note) and Task 4 (preview)
- `SQL_NOTES_DIR` monkeypatched in tests ✅ matches attribute name in sql_analyzer.py
