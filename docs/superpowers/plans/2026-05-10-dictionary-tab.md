# Dictionary Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm tab DICTIONARY vào Chooper app — bản đồ tính năng cho người mới và người dùng cũ, nhấn mạnh Data Studio và ML Studio.

**Architecture:** Index JSON + Markdown Content (Approach B). `index.json` chứa metadata 15 sections để drive search/filter; file `.md` trong `docs/dictionary/content/vn/` chứa nội dung; `modules/dictionary.py` load + render. VN/EN toggle lưu vào `session_state["lang"]` để Phase 2 toàn app dễ dàng.

**Tech Stack:** Streamlit, Python 3.11+, pathlib, json, pytest

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `docs/dictionary/index.json` | Metadata 15 sections (id, title, parent, category, tags) |
| Create | `modules/dictionary.py` | Toàn bộ render logic của tab Dictionary |
| Create | `tests/test_dictionary.py` | Unit tests cho pure functions |
| Create | `docs/dictionary/content/vn/00_welcome.md` | Bản đồ tổng quan |
| Create | `docs/dictionary/content/vn/01_data_studio.md` | Overview Data Studio |
| Create | `docs/dictionary/content/vn/01a_data_explorer.md` | Data Explorer |
| Create | `docs/dictionary/content/vn/01b_sql_obsidian.md` | SQL → Obsidian |
| Create | `docs/dictionary/content/vn/01c_ml_studio.md` | ML Studio (chi tiết nhất) |
| Create | `docs/dictionary/content/vn/01d_snippets.md` | SQL Snippets |
| Create | `docs/dictionary/content/vn/02_tasks.md` | Tasks tab |
| Create | `docs/dictionary/content/vn/03_performance.md` | Performance tab |
| Create | `docs/dictionary/content/vn/04_email.md` | Email tab |
| Create | `docs/dictionary/content/vn/05_focus.md` | Focus tab |
| Create | `docs/dictionary/content/vn/06_pipeline.md` | Pipeline tab |
| Create | `docs/dictionary/content/vn/07_notebook.md` | Notebook tab |
| Create | `docs/dictionary/content/vn/08_config.md` | Config tab |
| Create | `docs/dictionary/content/vn/90_glossary.md` | Thuật ngữ ML |
| Create | `docs/dictionary/content/vn/91_shortcuts.md` | Tips & phím tắt |
| Modify | `app.py` (dòng 2918-2928) | Thêm tab_dict vào st.tabs() |

---

## Task 1: Directory scaffolding + index.json

**Files:**
- Create: `docs/dictionary/index.json`
- Create: `docs/dictionary/content/vn/.gitkeep`
- Create: `docs/dictionary/content/en/.gitkeep`

- [ ] **Step 1: Tạo thư mục**

```bash
mkdir -p docs/dictionary/content/vn
mkdir -p docs/dictionary/content/en
```

- [ ] **Step 2: Tạo `docs/dictionary/index.json`**

```json
{
  "sections": [
    {
      "id": "00_welcome",
      "title": "◈ Welcome",
      "parent": null,
      "category": "core",
      "tags": ["overview", "map", "start", "giới thiệu", "bắt đầu"],
      "pinned": true
    },
    {
      "id": "01_data_studio",
      "title": "◈ Data Studio",
      "parent": null,
      "category": "core",
      "tags": ["data", "studio", "analysis", "root", "phân tích"],
      "pinned": true
    },
    {
      "id": "01a_data_explorer",
      "title": "· Data Explorer",
      "parent": "01_data_studio",
      "category": "core",
      "tags": ["csv", "excel", "parquet", "upload", "eda", "khám phá"],
      "pinned": false
    },
    {
      "id": "01b_sql_obsidian",
      "title": "· SQL → Obsidian",
      "parent": "01_data_studio",
      "category": "core",
      "tags": ["sql", "obsidian", "note", "analyze", "ghi chú"],
      "pinned": false
    },
    {
      "id": "01c_ml_studio",
      "title": "· ⚗ ML Studio",
      "parent": "01_data_studio",
      "category": "ml",
      "tags": ["ml", "forecast", "cluster", "xgboost", "sarimax", "prophet", "kmeans", "random forest", "pipeline", "dự đoán", "phân cụm"],
      "pinned": true
    },
    {
      "id": "01d_snippets",
      "title": "· Snippets",
      "parent": "01_data_studio",
      "category": "core",
      "tags": ["sql", "snippet", "reuse", "đoạn code"],
      "pinned": false
    },
    {
      "id": "02_tasks",
      "title": "⬡ Tasks",
      "parent": null,
      "category": "tools",
      "tags": ["task", "priority", "deadline", "checklist", "công việc"],
      "pinned": false
    },
    {
      "id": "03_performance",
      "title": "◎ Performance",
      "parent": null,
      "category": "tools",
      "tags": ["analytics", "chart", "burndown", "tag", "hiệu suất", "biểu đồ"],
      "pinned": false
    },
    {
      "id": "04_email",
      "title": "◉ Email",
      "parent": null,
      "category": "tools",
      "tags": ["email", "outlook", "digest", "classify", "reply", "phân loại"],
      "pinned": false
    },
    {
      "id": "05_focus",
      "title": "⏱ Focus",
      "parent": null,
      "category": "tools",
      "tags": ["focus", "pomodoro", "timer", "deep work", "tập trung"],
      "pinned": false
    },
    {
      "id": "06_pipeline",
      "title": "◉ Pipeline",
      "parent": null,
      "category": "tools",
      "tags": ["pipeline", "scheduler", "discord", "monitor", "lịch trình"],
      "pinned": false
    },
    {
      "id": "07_notebook",
      "title": "⬡ Notebook",
      "parent": null,
      "category": "tools",
      "tags": ["notebook", "python", "jupyter", "meeting notes", "ghi chú"],
      "pinned": false
    },
    {
      "id": "08_config",
      "title": "⊛ Config",
      "parent": null,
      "category": "tools",
      "tags": ["config", "env", "settings", "api key", "cấu hình"],
      "pinned": false
    },
    {
      "id": "90_glossary",
      "title": "📚 Glossary",
      "parent": null,
      "category": "ml",
      "tags": ["mape", "rmse", "silhouette", "ci", "confidence interval", "overfitting", "feature importance", "thuật ngữ"],
      "pinned": false
    },
    {
      "id": "91_shortcuts",
      "title": "⌨ Shortcuts & Tips",
      "parent": null,
      "category": "tips",
      "tags": ["shortcut", "tip", "keyboard", "trick", "mẹo", "phím tắt"],
      "pinned": false
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add docs/dictionary/
git commit -m "feat: scaffold dictionary directory + index.json (15 sections)"
```

---

## Task 2: Tests cho pure functions

**Files:**
- Create: `tests/test_dictionary.py`

- [ ] **Step 1: Tạo `tests/test_dictionary.py`**

```python
# tests/test_dictionary.py
"""Unit tests for modules/dictionary.py pure functions."""
import json
import pytest
from pathlib import Path


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_INDEX = [
    {
        "id": "00_welcome",
        "title": "◈ Welcome",
        "parent": None,
        "category": "core",
        "tags": ["overview", "map", "start"],
        "pinned": True,
    },
    {
        "id": "01_data_studio",
        "title": "◈ Data Studio",
        "parent": None,
        "category": "core",
        "tags": ["data", "studio", "analysis"],
        "pinned": True,
    },
    {
        "id": "01c_ml_studio",
        "title": "· ⚗ ML Studio",
        "parent": "01_data_studio",
        "category": "ml",
        "tags": ["ml", "forecast", "sarimax", "xgboost"],
        "pinned": True,
    },
    {
        "id": "90_glossary",
        "title": "📚 Glossary",
        "parent": None,
        "category": "ml",
        "tags": ["mape", "rmse", "silhouette"],
        "pinned": False,
    },
    {
        "id": "91_shortcuts",
        "title": "⌨ Shortcuts & Tips",
        "parent": None,
        "category": "tips",
        "tags": ["shortcut", "tip"],
        "pinned": False,
    },
]


# ── Import after fixture definition so missing module gives clear error ────────

from modules.dictionary import _filter_sections, _load_index_from_path


# ── _filter_sections ──────────────────────────────────────────────────────────

def test_filter_no_query_no_category_returns_all():
    result = _filter_sections(SAMPLE_INDEX, "", None)
    assert len(result) == len(SAMPLE_INDEX)


def test_filter_by_title_case_insensitive():
    result = _filter_sections(SAMPLE_INDEX, "welcome", None)
    assert len(result) == 1
    assert result[0]["id"] == "00_welcome"


def test_filter_by_tag():
    result = _filter_sections(SAMPLE_INDEX, "sarimax", None)
    assert len(result) == 1
    assert result[0]["id"] == "01c_ml_studio"


def test_filter_by_category_ml():
    result = _filter_sections(SAMPLE_INDEX, "", "ml")
    ids = [s["id"] for s in result]
    assert "01c_ml_studio" in ids
    assert "90_glossary" in ids
    assert "00_welcome" not in ids


def test_filter_category_and_query_and_logic():
    # "mape" is in glossary (ml category), not in ml_studio
    result = _filter_sections(SAMPLE_INDEX, "mape", "ml")
    assert len(result) == 1
    assert result[0]["id"] == "90_glossary"


def test_filter_query_no_match_returns_empty():
    result = _filter_sections(SAMPLE_INDEX, "xyznotexist", None)
    assert result == []


def test_filter_empty_index_returns_empty():
    result = _filter_sections([], "anything", None)
    assert result == []


def test_filter_preserves_order():
    result = _filter_sections(SAMPLE_INDEX, "", None)
    assert [s["id"] for s in result] == [s["id"] for s in SAMPLE_INDEX]


# ── _load_index_from_path ─────────────────────────────────────────────────────

def test_load_index_from_valid_file(tmp_path):
    index_file = tmp_path / "index.json"
    index_file.write_text(
        json.dumps({"sections": SAMPLE_INDEX}), encoding="utf-8"
    )
    result = _load_index_from_path(index_file)
    assert len(result) == len(SAMPLE_INDEX)
    assert result[0]["id"] == "00_welcome"


def test_load_index_missing_file_returns_empty(tmp_path):
    result = _load_index_from_path(tmp_path / "nonexistent.json")
    assert result == []


def test_load_index_empty_sections(tmp_path):
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps({"sections": []}), encoding="utf-8")
    result = _load_index_from_path(index_file)
    assert result == []
```

- [ ] **Step 2: Chạy test để confirm fail đúng cách**

```bash
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v
```

Expected: `ImportError: cannot import name '_filter_sections' from 'modules.dictionary'` (file chưa tồn tại)

- [ ] **Step 3: Commit test**

```bash
git add tests/test_dictionary.py
git commit -m "test: add failing tests for dictionary pure functions"
```

---

## Task 3: Data layer — `_load_index_from_path` + `_filter_sections`

**Files:**
- Create: `modules/dictionary.py` (skeleton + data layer)

- [ ] **Step 1: Tạo `modules/dictionary.py`**

```python
# modules/dictionary.py
"""
DICTIONARY TAB — App map for new and returning users.
Renders content from docs/dictionary/content/{lang}/{section_id}.md
driven by docs/dictionary/index.json metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_INDEX_PATH = Path("docs/dictionary/index.json")
_CONTENT_BASE = Path("docs/dictionary/content")

CATEGORY_LABELS: dict[str, str] = {
    "core":  "Core",
    "ml":    "ML",
    "tools": "Tools",
    "tips":  "Tips",
}

# IDs that appear above the separator in nav
_SEPARATOR_BEFORE = {"90_glossary"}


# ── Pure functions (testable without Streamlit) ───────────────────────────────

def _load_index_from_path(path: Path) -> list[dict]:
    """Load sections list from a JSON file. Returns [] on missing/invalid file."""
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sections", [])
    except (json.JSONDecodeError, OSError):
        return []


def _filter_sections(
    index: list[dict],
    query: str,
    category: str | None,
) -> list[dict]:
    """
    Filter sections by search query AND category.
    - query: matched against title (case-insensitive) OR any tag
    - category: matched against section's category field; None = all
    Returns a new list preserving original order.
    """
    results = []
    q = query.strip().lower()
    for s in index:
        match_search = (
            not q
            or q in s.get("title", "").lower()
            or any(q in tag.lower() for tag in s.get("tags", []))
        )
        match_category = not category or s.get("category") == category
        if match_search and match_category:
            results.append(s)
    return results
```

- [ ] **Step 2: Chạy test**

```bash
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v
```

Expected: tất cả PASS

- [ ] **Step 3: Commit**

```bash
git add modules/dictionary.py tests/test_dictionary.py
git commit -m "feat: dictionary data layer (_load_index_from_path, _filter_sections) with tests"
```

---

## Task 4: Toolbar — search bar + VN/EN toggle

**Files:**
- Modify: `modules/dictionary.py` (append functions)

- [ ] **Step 1: Thêm `_render_toolbar()` vào `modules/dictionary.py`**

Append sau phần pure functions:

```python
# ── UI helpers ────────────────────────────────────────────────────────────────

def _render_toolbar() -> tuple[str, str]:
    """
    Render search bar + VN/EN toggle button trên cùng 1 row.
    Returns (search_query, current_lang).
    """
    col_search, col_spacer, col_toggle = st.columns([7, 1, 1])

    with col_search:
        query = st.text_input(
            "",
            placeholder="🔍  Tìm trong Dictionary...",
            key="dict_search",
            label_visibility="collapsed",
        )

    with col_toggle:
        lang = st.session_state.get("lang", "vn")
        toggle_label = "🌐 EN" if lang == "vn" else "🌐 VN"
        if st.button(toggle_label, key="dict_lang_toggle", use_container_width=True):
            st.session_state["lang"] = "en" if lang == "vn" else "vn"
            st.rerun()

    return query or "", st.session_state.get("lang", "vn")
```

- [ ] **Step 2: Verify không có syntax error**

```bash
.venv\Scripts\python.exe -c "from modules.dictionary import _render_toolbar; print('OK')"
```

Expected: `OK`

---

## Task 5: Filter chips

**Files:**
- Modify: `modules/dictionary.py` (append)

- [ ] **Step 1: Thêm `_render_filter_chips()` vào `modules/dictionary.py`**

```python
def _render_filter_chips(query: str) -> str | None:
    """
    Render filter chips: Tất cả | Core | ML | Tools | Tips.
    Returns active category string or None (= Tất cả).
    Resets to 'Tất cả' khi user gõ search.
    """
    # Khi search active → reset filter về Tất cả
    if query:
        st.session_state["dict_filter"] = None

    options = ["Tất cả", "Core", "ML", "Tools", "Tips"]
    current = st.session_state.get("dict_filter_label", "Tất cả")

    selected = st.radio(
        "",
        options,
        index=options.index(current) if current in options else 0,
        horizontal=True,
        key="dict_filter_radio",
        label_visibility="collapsed",
    )
    # Map label → category key
    label_to_cat: dict[str, str | None] = {
        "Tất cả": None,
        "Core": "core",
        "ML": "ml",
        "Tools": "tools",
        "Tips": "tips",
    }
    cat = label_to_cat.get(selected)
    st.session_state["dict_filter"] = cat
    st.session_state["dict_filter_label"] = selected
    return cat
```

- [ ] **Step 2: Verify**

```bash
.venv\Scripts\python.exe -c "from modules.dictionary import _render_filter_chips; print('OK')"
```

Expected: `OK`

---

## Task 6: Nav tree

**Files:**
- Modify: `modules/dictionary.py` (append)

- [ ] **Step 1: Thêm CSS helper + `_render_nav()` vào `modules/dictionary.py`**

```python
_NAV_CSS = """
<style>
/* Nav buttons: borderless, left-aligned, dark theme */
section[data-testid="stSidebar"] button,
div[data-testid="stVerticalBlock"] button[kind="secondary"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    text-align: left !important;
    color: #6e7681 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    padding: 3px 8px !important;
    width: 100% !important;
    justify-content: flex-start !important;
}
button[data-dict-active="true"] {
    color: #00d4ff !important;
}
</style>
"""


def _render_nav(sections: list[dict]) -> None:
    """
    Render nav tree trong cột trái.
    - Top-level sections: rendered as buttons
    - Children của 01_data_studio: rendered indented bên dưới khi expanded
    - Separator trước 90_glossary
    Sets st.session_state["dict_section"] khi click.
    """
    st.markdown(_NAV_CSS, unsafe_allow_html=True)

    # Build children map
    children: dict[str, list[dict]] = {}
    for s in sections:
        p = s.get("parent")
        if p:
            children.setdefault(p, []).append(s)

    selected = st.session_state.get("dict_section", "00_welcome")
    expanded: dict[str, bool] = st.session_state.get(
        "dict_expanded", {"01_data_studio": True}
    )

    top_level = [s for s in sections if not s.get("parent")]
    separator_added = False

    for s in top_level:
        sid = s["id"]
        has_children = sid in children
        is_exp = expanded.get(sid, False)

        # Separator trước section bắt đầu bằng "9"
        if sid.startswith("9") and not separator_added:
            st.markdown(
                "<hr style='margin:6px 0 4px;border:none;border-top:1px solid #21262d'>",
                unsafe_allow_html=True,
            )
            separator_added = True

        # Label với arrow nếu có children
        if has_children:
            arrow = "▼" if is_exp else "▶"
            label = f"{arrow}  {s['title']}"
        else:
            label = s["title"]

        # Highlight section đang active
        active_marker = " ●" if sid == selected else ""
        if st.button(
            f"{label}{active_marker}",
            key=f"nav_{sid}",
            use_container_width=True,
        ):
            st.session_state["dict_section"] = sid
            if has_children:
                expanded[sid] = not is_exp
                st.session_state["dict_expanded"] = expanded
            st.rerun()

        # Render children nếu expanded
        if has_children and is_exp:
            for child in children.get(sid, []):
                cid = child["id"]
                active_marker_c = " ●" if cid == selected else ""
                child_label = f"    {child['title']}{active_marker_c}"
                if st.button(child_label, key=f"nav_{cid}", use_container_width=True):
                    st.session_state["dict_section"] = cid
                    st.rerun()
```

- [ ] **Step 2: Verify**

```bash
.venv\Scripts\python.exe -c "from modules.dictionary import _render_nav; print('OK')"
```

Expected: `OK`

---

## Task 7: Content renderer

**Files:**
- Modify: `modules/dictionary.py` (append)

- [ ] **Step 1: Thêm `_render_content()` vào `modules/dictionary.py`**

```python
def _render_content(section_id: str, lang: str) -> None:
    """
    Load và render file docs/dictionary/content/{lang}/{section_id}.md.
    Fallback về 'vn' nếu file EN chưa tồn tại.
    Graceful message nếu file VN cũng chưa có.
    """
    path = _CONTENT_BASE / lang / f"{section_id}.md"

    # Fallback về vn nếu en chưa có
    if not path.exists() and lang == "en":
        path = _CONTENT_BASE / "vn" / f"{section_id}.md"

    if not path.exists():
        st.info(
            f"📝 Nội dung **{section_id}** đang được cập nhật. "
            "Quay lại sau nhé!"
        )
        return

    content = path.read_text(encoding="utf-8")
    st.markdown(content, unsafe_allow_html=False)
```

- [ ] **Step 2: Verify**

```bash
.venv\Scripts\python.exe -c "from modules.dictionary import _render_content; print('OK')"
```

Expected: `OK`

---

## Task 8: Orchestrator — `render_dictionary_tab()`

**Files:**
- Modify: `modules/dictionary.py` (append)

- [ ] **Step 1: Thêm `render_dictionary_tab()` vào `modules/dictionary.py`**

```python
def render_dictionary_tab() -> None:
    """
    Entry point từ app.py.
    Layout: toolbar (top) → filter chips → [nav col | content col]
    """
    # Init session state defaults
    if "dict_section" not in st.session_state:
        st.session_state["dict_section"] = "00_welcome"
    if "dict_expanded" not in st.session_state:
        st.session_state["dict_expanded"] = {"01_data_studio": True}
    if "lang" not in st.session_state:
        st.session_state["lang"] = "vn"

    # ── Toolbar ──────────────────────────────────────────────────────────────
    query, lang = _render_toolbar()

    # ── Filter chips ─────────────────────────────────────────────────────────
    active_category = _render_filter_chips(query)

    # ── Load + filter index ──────────────────────────────────────────────────
    all_sections = _load_index_from_path(_INDEX_PATH)
    visible = _filter_sections(all_sections, query, active_category)

    if not visible:
        st.warning("Không tìm thấy — thử: ml, forecast, task, email, sarimax...")
        return

    # Ensure current section is still visible; fallback to first result
    current = st.session_state["dict_section"]
    visible_ids = {s["id"] for s in visible}
    if current not in visible_ids:
        st.session_state["dict_section"] = visible[0]["id"]
        current = visible[0]["id"]

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── 2-column layout ──────────────────────────────────────────────────────
    col_nav, col_content = st.columns([22, 78])

    with col_nav:
        _render_nav(visible)

    with col_content:
        _render_content(st.session_state["dict_section"], lang)
```

- [ ] **Step 2: Verify full module imports clean**

```bash
.venv\Scripts\python.exe -c "from modules.dictionary import render_dictionary_tab; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Chạy tests**

```bash
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v
```

Expected: tất cả PASS

- [ ] **Step 4: Commit toàn bộ module**

```bash
git add modules/dictionary.py
git commit -m "feat: add modules/dictionary.py with full render pipeline"
```

---

## Task 9: Sửa app.py — thêm tab Dictionary

**Files:**
- Modify: `app.py` dòng 2918–2944

- [ ] **Step 1: Mở `app.py`, tìm đoạn `st.tabs` (~dòng 2918)**

Tìm đoạn:
```python
    (tab_data, tab_tasks, tab_perf, tab_email, tab_focus,
     tab_pipeline, tab_nb, tab_settings) = st.tabs([
        "◈ DATA STUDIO",
        "⬡ TASKS",
        "◎ PERFORMANCE",
        "◉ EMAIL",
        "⏱ FOCUS",
        "◉ PIPELINE",
        "⬡ NOTEBOOK",
        "⊛ CONFIG",
    ])
```

Thay bằng:
```python
    (tab_data, tab_tasks, tab_perf, tab_email, tab_focus,
     tab_pipeline, tab_nb, tab_dict, tab_settings) = st.tabs([
        "◈ DATA STUDIO",
        "⬡ TASKS",
        "◎ PERFORMANCE",
        "◉ EMAIL",
        "⏱ FOCUS",
        "◉ PIPELINE",
        "⬡ NOTEBOOK",
        "◈ DICTIONARY",
        "⊛ CONFIG",
    ])
```

- [ ] **Step 2: Tìm đoạn `with tab_nb:` → thêm `with tab_dict:` sau đó**

Tìm:
```python
    with tab_nb:
        render_notebook_tab()
    with tab_settings:
        render_settings_tab()
```

Thay bằng:
```python
    with tab_nb:
        render_notebook_tab()
    with tab_dict:
        from modules.dictionary import render_dictionary_tab
        render_dictionary_tab()
    with tab_settings:
        render_settings_tab()
```

- [ ] **Step 3: Verify app.py syntax**

```bash
.venv\Scripts\python.exe -c "import ast; ast.parse(open('app.py').read()); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add DICTIONARY tab to app.py (before CONFIG)"
```

---

## Task 10: Content — Welcome + Data Studio overview

**Files:**
- Create: `docs/dictionary/content/vn/00_welcome.md`
- Create: `docs/dictionary/content/vn/01_data_studio.md`
- Create: `docs/dictionary/content/vn/01a_data_explorer.md`
- Create: `docs/dictionary/content/vn/01b_sql_obsidian.md`
- Create: `docs/dictionary/content/vn/01d_snippets.md`

- [ ] **Step 1: Tạo `docs/dictionary/content/vn/00_welcome.md`**

```markdown
# ⬡ Chooper — Bạn đang ở đâu?

> **Chooper** là workspace phân tích dữ liệu cá nhân. 8 khu vực, mỗi khu có vai trò riêng.

## Bạn muốn làm gì?

| Tôi muốn...                              | Vào đây           | Ghi chú                        |
|------------------------------------------|-------------------|--------------------------------|
| Phân tích / dự đoán dữ liệu             | ◈ Data Studio     | Trung tâm của toàn bộ app      |
| Theo dõi công việc hôm nay               | ⬡ Tasks           | Deadline + priority + checklist|
| Xem hiệu suất & báo cáo                 | ◎ Performance     | Chart, burndown, tag breakdown |
| Đọc & phân loại email Outlook            | ◉ Email           | AI tóm tắt + gợi ý reply      |
| Tập trung làm việc, đặt timer            | ⏱ Focus           | Pomodoro 25/5, deep work       |
| Kiểm tra pipeline đang chạy              | ◉ Pipeline        | Scheduler, Discord health      |
| Viết code Python / meeting notes         | ⬡ Notebook        | JupyterLab tích hợp            |
| Xem API key, biến môi trường             | ⊛ Config          | Read-only, chỉnh trong .env    |

---

## ◈ Data Studio là trung tâm

Mọi phân tích đều bắt đầu từ **Data Studio**. Nó có 4 công cụ:

```
Upload data → [Data Explorer]  → hiểu ngay dữ liệu có gì
Write SQL   → [SQL → Obsidian] → phân tích + lưu note
Run ML      → [ML Studio]      → AI dự đoán / phân cụm
Save query  → [Snippets]       → tái sử dụng SQL hay dùng
```

---

## Bắt đầu từ đâu?

**Lần đầu dùng:**
1. Vào **◈ Data Studio** → chọn **⚗ ML Studio**
2. Đọc phần *"ML Studio là gì?"* trong Dictionary này
3. Upload file CSV/Excel → làm theo 8 bước

**Đã dùng rồi, cần tra cứu nhanh:**
- Dùng thanh search phía trên → gõ thuật ngữ (vd: `sarimax`, `mape`, `task`)
- Hoặc chọn filter chip **ML** / **Tools** bên trái
```

- [ ] **Step 2: Tạo `docs/dictionary/content/vn/01_data_studio.md`**

```markdown
# ◈ Data Studio

> Phòng phân tích dữ liệu của bạn. 4 công cụ trong 1 chỗ — từ khám phá đến dự đoán.

## 4 Sub-view

| Sub-view        | Dùng khi nào                                     | Output                          |
|-----------------|--------------------------------------------------|---------------------------------|
| Data Explorer   | Upload file → cần hiểu ngay cấu trúc dữ liệu    | Stats, missing%, correlation    |
| SQL → Obsidian  | Có câu SQL → muốn phân tích + lưu thành note    | File .md trong Obsidian vault   |
| ⚗ ML Studio    | Có data → muốn dự đoán hoặc phân nhóm            | Model + chart + AI insight      |
| Snippets        | Có câu SQL hay dùng lại → muốn lưu trữ          | Thư viện SQL cá nhân            |

## Flow điển hình

```
1. Upload CSV/Excel/Parquet vào Data Explorer
   → Kiểm tra cột, missing values, phân phối

2. Nếu cần viết SQL để lọc/aggregate:
   → Sang SQL → Obsidian → paste SQL → analyze → lưu note

3. Khi đã hiểu data:
   → Sang ML Studio → upload file đã clean → chạy pipeline 8 bước

4. Lưu câu SQL hay dùng:
   → Sang Snippets → thêm snippet → gán tag
```

## Lưu ý

- Data Explorer và ML Studio **không kết nối trực tiếp** — bạn cần export/save file rồi upload lại
- SQL → Obsidian ghi file `.md` vào `D:\ai_brain\SQL Queries\` — cần Obsidian vault được mount
- ML Studio lưu session tại `data/ml_sessions/` — có thể tiếp tục từ bước bất kỳ
```

- [ ] **Step 3: Tạo `docs/dictionary/content/vn/01a_data_explorer.md`**

```markdown
# ⬢ Data Explorer

> Upload file → app tự động phân tích và cho bạn thấy mọi thứ cần biết trước khi làm gì tiếp theo.

## Dùng để làm gì?

Khi bạn có một file dữ liệu mới và chưa biết nó có gì bên trong — Data Explorer là điểm đầu tiên nên ghé.

## Các file được hỗ trợ

| Format  | Extension        |
|---------|------------------|
| CSV     | `.csv`           |
| Excel   | `.xlsx`, `.xls`  |
| Parquet | `.parquet`       |

## 5 tab tự động sau khi upload

| Tab         | Hiển thị gì                                              |
|-------------|----------------------------------------------------------|
| HEAD        | 5 dòng đầu tiên của data                                 |
| DTYPES      | Kiểu dữ liệu từng cột (int, float, string, datetime...)  |
| MISSING     | % missing của từng cột, bar chart trực quan             |
| STATS       | Min, max, mean, median, std của các cột số              |
| CORRELATION | Heatmap tương quan giữa các cột số                      |

## Tips

- Xem **MISSING** trước: cột nào > 30% missing thường nên drop trước khi đưa vào ML
- **CORRELATION** > 0.9 giữa 2 cột → chỉ cần giữ 1 cột (multicollinearity)
- Sau khi hiểu data → chuyển sang **ML Studio** để phân tích sâu hơn
```

- [ ] **Step 4: Tạo `docs/dictionary/content/vn/01b_sql_obsidian.md`**

```markdown
# ⬡ SQL → Obsidian

> Paste câu SQL → app phân tích business intent → optimize → lưu thành note `.md` trong Obsidian vault.

## Dùng để làm gì?

Khi bạn viết SQL để trả lời một câu hỏi business, bạn muốn:
- Biết câu SQL đó **đang hỏi gì** (không phải syntax mà là ý nghĩa)
- Có bản **optimize** chạy nhanh hơn nếu có thể
- **Lưu lại** có thể tìm kiếm sau này trong Obsidian

## Cách dùng

```
1. Paste câu SQL vào text box
2. Nhấn Analyze → app gửi lên Claude AI để phân tích
3. Xem kết quả: business intent, optimization suggestions, tags
4. Điều chỉnh title / tags nếu cần
5. Nhấn Save → file .md được ghi vào D:\ai_brain\SQL Queries\
```

## Output file .md chứa gì?

- Title và business question
- Câu SQL gốc
- Câu SQL đã optimize (nếu có cải thiện)
- Tags để tìm kiếm sau
- Tên tables được dùng
- Ngày lưu

## Lưu ý

- Cần `ANTHROPIC_API_KEY` trong `.env` để phân tích bằng AI
- Nếu không có API key → fallback sang Ollama local
- File được lưu tại `D:\ai_brain\SQL Queries\` — cần path này tồn tại
```

- [ ] **Step 5: Tạo `docs/dictionary/content/vn/01d_snippets.md`**

```markdown
# ◇ SQL Snippets

> Thư viện SQL cá nhân — lưu câu query hay dùng, tìm lại nhanh khi cần.

## Dùng để làm gì?

Thay vì viết lại câu SQL giống nhau mỗi tuần, bạn lưu nó một lần vào Snippets và copy ra khi cần.

## Tính năng

| Tính năng     | Mô tả                                              |
|---------------|----------------------------------------------------|
| Thêm snippet  | Title + SQL content + category tag                 |
| Tìm kiếm      | Search theo title hoặc nội dung SQL                |
| Copy          | 1 click copy SQL ra clipboard                      |
| Xóa           | Xóa snippet không còn dùng                         |
| Categories    | Nhóm snippet theo loại (aggregate, filter, join...) |

## Tips

- Đặt tên snippet rõ ràng: `"Doanh thu theo kênh tháng này"` tốt hơn `"query1"`
- Dùng category để nhóm: `sfdc` (Salesforce), `fabric` (Data warehouse), `common`
- Snippet lưu tại `data/snippets.json` — có thể backup file này
```

- [ ] **Step 6: Commit**

```bash
git add docs/dictionary/content/vn/
git commit -m "feat: add dictionary content - welcome + data studio overview files"
```

---

## Task 11: Content — ML Studio (file quan trọng nhất)

**Files:**
- Create: `docs/dictionary/content/vn/01c_ml_studio.md`

- [ ] **Step 1: Tạo `docs/dictionary/content/vn/01c_ml_studio.md`**

```markdown
# ⚗ ML Studio

> Cho app tự phân tích dữ liệu của bạn — không cần biết code, không cần biết ML.

---

## ML Studio là gì?

Tưởng tượng bạn có một đống số liệu bán hàng từ 2 năm qua.

**ML Studio giống như một người bạn thông minh** — bạn đưa file cho nó, nó tự hỏi *"Dữ liệu này muốn trả lời câu hỏi gì nhỉ?"*, rồi chọn cách phân tích phù hợp và giải thích kết quả bằng tiếng người bình thường.

Bạn không cần biết SARIMAX là gì. Bạn chỉ cần biết: *"Tôi muốn dự đoán doanh số tháng tới."*

---

## Pipeline 8 bước

```
[1] Upload  →  [2] Detect Header  →  [3] EDA  →  [4] Clean
     ↓
[5] Feature Select  →  [6] AI Recommend  →  [7] Train  →  [8] Result + Insight
```

| Bước | Tên               | Bạn làm gì                      | App làm gì                                         |
|------|-------------------|---------------------------------|----------------------------------------------------|
| 1    | Upload            | Kéo file CSV/Excel vào          | Đọc file, detect encoding, load vào bộ nhớ         |
| 2    | Detect Header     | Xác nhận tên cột                | Tự đoán header row, hỏi lại nếu file phức tạp     |
| 3    | EDA               | Xem tổng quan data              | Thống kê, % missing, correlation, phân phối        |
| 4    | Clean             | Chọn cách xử lý giá trị null    | Drop hàng/cột, fill mean/median, hoặc impute       |
| 5    | Feature Select    | Xem cột nào quan trọng nhất     | Tính feature importance, gợi ý bỏ cột thừa        |
| 6    | AI Recommend      | Xác nhận bài toán + thuật toán  | Claude AI đề xuất thuật toán phù hợp + lý do      |
| 7    | Train             | Nhấn Train                      | Chạy model, tính metrics, lưu kết quả             |
| 8    | Result + Insight  | Đọc kết quả                     | Vẽ chart + viết nhận xét bằng ngôn ngữ tự nhiên   |

**Lưu ý quan trọng:** Bạn có thể quay lại bất kỳ bước nào mà không cần upload lại file. Session được lưu tại `data/ml_sessions/`.

---

## Các thuật toán hiện có

### XGBoost — Phân loại & Hồi quy

> **Analogy:** Hỏi ý kiến 500 người bạn khác nhau. Mỗi người nhìn dữ liệu theo một góc độ riêng, rồi cả nhóm bỏ phiếu ra đáp án. Người nào hay sai thì lần sau ít được hỏi hơn — nhờ vậy nhóm ngày càng thông minh hơn.

| | |
|-|-|
| **Dùng khi** | Dự đoán con số (doanh thu, tỉ lệ chuyển đổi) hoặc phân loại (có/không, nhóm A/B/C) |
| **Input cần** | Bảng dữ liệu có **cột mục tiêu** rõ ràng (cột bạn muốn dự đoán) |
| **Output** | Giá trị dự đoán + biểu đồ Feature Importance (cột nào ảnh hưởng nhất) |
| **Điểm mạnh** | Chính xác cao, xử lý tốt missing values, nhanh |
| **Điểm yếu** | Khó giải thích "tại sao" cho từng dự đoán cụ thể |

---

### Random Forest — Phân loại & Hồi quy

> **Analogy:** Giống XGBoost nhưng 500 người bạn đó học **hoàn toàn độc lập** — không ai biết người kia đang học gì. Kết quả đa dạng hơn, ít bị "học vẹt" hơn.

| | |
|-|-|
| **Dùng khi** | Tương tự XGBoost; đặc biệt tốt khi data nhỏ hoặc có nhiều outlier |
| **Input cần** | Bảng dữ liệu có cột mục tiêu |
| **Output** | Giá trị dự đoán + Feature Importance |
| **Khác XGBoost** | Ổn định hơn, ít overfit hơn, nhưng chậm hơn một chút |

---

### SARIMAX — Dự báo chuỗi thời gian

> **Analogy:** Bạn có doanh số 24 tháng. SARIMAX nhìn vào và học 3 thứ: (1) xu hướng tăng/giảm dài hạn, (2) chu kỳ lặp lại theo mùa (tháng 12 luôn cao hơn), (3) yếu tố bên ngoài bạn cung cấp như khuyến mãi hay ngày lễ. Rồi nó nói: *"Tháng sau bạn bán được khoảng X, sai số ±Y"*.

| | |
|-|-|
| **Dùng khi** | Data là chuỗi theo ngày/tuần/tháng **và** có seasonality rõ ràng |
| **Cần tối thiểu** | 24 điểm dữ liệu (24 tháng, hoặc 24 tuần...) |
| **Input cần** | Cột ngày + cột giá trị; optionally: cột exogenous (biến ngoài) |
| **Output** | Đường dự báo (màu cam) + vùng confidence interval (màu mờ xung quanh) |
| **Điểm mạnh** | Xử lý seasonality tốt, có thể tích hợp biến ngoài |
| **Điểm yếu** | Cần ít nhất 24 điểm; data có khoảng trống thì khó |

**Đọc biểu đồ SARIMAX:**
- **Đường xanh** = data thực tế đã có
- **Đường cam** = dự báo
- **Vùng mờ** = confidence interval — thực tế sẽ rơi vào đây với xác suất ~95%

---

### Prophet — Dự báo chuỗi thời gian

> **Analogy:** Giống SARIMAX nhưng dễ tính hơn nhiều — tự xử lý ngày lễ, không cần bạn chỉnh tham số phức tạp. Phù hợp khi data có khoảng trống hoặc những ngày bất thường.

| | |
|-|-|
| **Dùng khi** | Time series có holiday effects, data không đều, hoặc bạn muốn setup nhanh |
| **Input cần** | Cột ngày (tên `ds`) + cột giá trị (tên `y`) |
| **Output** | Đường dự báo + vùng uncertainty + decomposition (trend, seasonality, holidays) |
| **Khác SARIMAX** | Dễ dùng hơn, ít kiểm soát hơn; tốt cho forecast ngắn-trung hạn |

---

### KMeans — Phân cụm (Clustering)

> **Analogy:** Bạn có 1000 khách hàng và không biết nên chia họ thành mấy nhóm. KMeans tự thử nhiều cách chia khác nhau, chấm điểm mỗi cách, rồi báo cho bạn cách nào tự nhiên nhất — không cần bạn nói trước có bao nhiêu nhóm.

| | |
|-|-|
| **Dùng khi** | Muốn segment khách hàng, SKU, vùng địa lý — không có nhãn sẵn |
| **Input cần** | Bảng dữ liệu **không có cột mục tiêu** (unsupervised) |
| **Output** | Biểu đồ scatter màu các cụm + bảng đặc trưng của từng cluster |
| **Điểm mạnh** | Không cần dữ liệu đã được gán nhãn |
| **Điểm yếu** | Kết quả phụ thuộc vào việc chọn số cụm K |

---

## Khi nào dùng thuật toán nào?

| Câu hỏi của bạn                              | Thuật toán gợi ý          |
|----------------------------------------------|---------------------------|
| Tháng tới tôi bán được bao nhiêu?            | SARIMAX hoặc Prophet      |
| Khách hàng này có mua lại không?             | XGBoost hoặc Random Forest|
| Yếu tố nào ảnh hưởng nhất đến doanh thu?    | XGBoost (Feature Importance)|
| Tôi nên chia khách hàng thành mấy nhóm?     | KMeans                    |
| Data có khoảng trống, ngày lễ phức tạp?      | Prophet                   |
| Data nhỏ (<500 dòng), có outlier?            | Random Forest             |

---

## Đọc kết quả — Các chỉ số đánh giá

Xem giải thích chi tiết tại: **📚 Glossary**

| Chỉ số           | Thuật toán dùng          | Nghĩa ngắn gọn                        |
|------------------|--------------------------|---------------------------------------|
| MAPE             | SARIMAX, Prophet         | Sai bao nhiêu % so với thực tế        |
| RMSE             | XGBoost, RF, SARIMAX     | Sai số trung bình (đơn vị gốc)        |
| Silhouette Score | KMeans                   | Các cụm có tách biệt tốt không?       |
| R²               | XGBoost, RF              | Model giải thích được bao % variance  |
| Accuracy / F1    | XGBoost, RF (classification) | Dự đoán đúng bao nhiêu %          |
```

- [ ] **Step 2: Commit**

```bash
git add docs/dictionary/content/vn/01c_ml_studio.md
git commit -m "feat: add ML Studio dictionary content (algorithms, pipeline, decision table)"
```

---

## Task 12: Content — Remaining tabs (02–08)

**Files:**
- Create: `docs/dictionary/content/vn/02_tasks.md` đến `08_config.md`

- [ ] **Step 1: Tạo `docs/dictionary/content/vn/02_tasks.md`**

```markdown
# ⬡ Tasks

> Theo dõi công việc theo priority, deadline, và checklist AI.

## Dùng để làm gì?

Quản lý task hằng ngày: thêm task, gán priority, đặt deadline, đánh dấu hoàn thành.

## Priority levels

| Level   | Màu      | Dùng khi                                     |
|---------|----------|----------------------------------------------|
| ◈ High  | Đỏ       | Deadline hôm nay hoặc blocking người khác     |
| ◆ Medium| Cam      | Cần làm tuần này                             |
| ◇ Low   | Xanh lá  | Backlog, làm khi có thời gian                |
| ⚡Ad-hoc | Xanh nhạt| Phát sinh đột xuất, không có deadline cố định|

## Tính năng chính

- **Global search bar**: lọc task theo tên hoặc tag (`#urgent`, `#sf`)
- **AI Checklist**: với task phức tạp, bấm Generate → AI tạo checklist con
- **Recurring tasks**: lặp hàng tháng hoặc hàng năm
- **Discord reminder**: nhắc nhở qua Discord lúc 09:00 và 13:30

## Tips

- Task overdue sẽ hiển thị badge đỏ trong sidebar
- Bấm vào task để edit inline — không cần mở form mới
- Dùng tag `#sf` cho task liên quan Salesforce để filter nhanh
```

- [ ] **Step 2: Tạo `docs/dictionary/content/vn/03_performance.md`**

```markdown
# ◎ Performance

> Báo cáo trực quan về task đã làm: burndown, phân bố priority, tag analysis.

## Các chart có sẵn

| Chart             | Đọc như thế nào                                          |
|-------------------|----------------------------------------------------------|
| Priority breakdown| Pie chart — tỉ lệ High/Medium/Low/Ad-hoc                |
| Status breakdown  | Done vs Active — đo được bao nhiêu % đã xong           |
| Burndown chart    | Task hoàn thành theo ngày — xu hướng tăng là tốt        |
| Tag analysis      | Tag nào xuất hiện nhiều nhất trong các task của bạn     |

## Dùng khi nào?

- Cuối tuần: xem burndown có đều không hay dồn vào cuối tuần
- Cuối tháng: priority breakdown — nếu High quá nhiều thì đang bị overwhelmed
- Khi muốn biết mình đang dành nhiều thời gian cho loại việc nào (tag analysis)
```

- [ ] **Step 3: Tạo `docs/dictionary/content/vn/04_email.md`**

```markdown
# ◉ Email

> Đọc email Outlook, AI phân loại theo priority, tóm tắt, gợi ý reply.

## Pipeline Email

```
Outlook → Đọc email → Phân loại priority → Tóm tắt → Gợi ý reply → Gửi digest Discord
```

## Các bước

| Bước            | App làm gì                                               |
|-----------------|----------------------------------------------------------|
| Đọc Outlook     | Dùng win32com để đọc inbox (cần Outlook desktop)        |
| Phân loại       | Rule-based + AI → gán priority: Urgent / Normal / FYI   |
| Tóm tắt         | Claude AI tóm tắt nội dung chính 2-3 câu                |
| Gợi ý reply     | 3 phương án reply từ ngắn đến dài                       |
| Digest Discord  | Tổng hợp email quan trọng → gửi vào Discord channel    |

## Lưu ý

- Cần **Outlook desktop** đang mở và đăng nhập
- Cần `ANTHROPIC_API_KEY` cho AI tóm tắt/reply
- Email đã xử lý được lưu vào `data/email_history.json` tránh duplicate
- Style học từ email cũ của bạn để gợi ý reply đúng giọng văn
```

- [ ] **Step 4: Tạo `docs/dictionary/content/vn/05_focus.md`**

```markdown
# ⏱ Focus Timer

> Pomodoro timer — 25 phút làm việc, 5 phút nghỉ. Giữ focus, tránh bị phân tán.

## Cách dùng

1. Nhập tên task đang làm (optional)
2. Nhấn Start → đếm ngược 25 phút
3. Khi hết giờ → app thông báo → nghỉ 5 phút
4. Lặp lại — sau 4 pomodoro thì nghỉ dài 15-30 phút

## Tại sao dùng Pomodoro?

Não người khó tập trung liên tục > 30 phút. Pomodoro chia nhỏ thời gian thành các sprint ngắn — làm cho việc lớn bớt đáng sợ hơn và dễ bắt đầu hơn.

## Tips

- Tắt hết notification trước khi start timer
- Ghi task đang làm vào ô text để nhớ mình đang làm gì sau khi nghỉ
- Nếu bị gián đoạn giữa chừng → nhấn Reset và bắt đầu lại thay vì tiếp tục đếm
```

- [ ] **Step 5: Tạo `docs/dictionary/content/vn/06_pipeline.md`**

```markdown
# ◉ Pipeline Monitor

> Xem trạng thái scheduler, trigger Discord notifications thủ công, kiểm tra sức khỏe hệ thống.

## Scheduler jobs

| Job                  | Giờ chạy   | Làm gì                                      |
|----------------------|------------|---------------------------------------------|
| Morning reminder     | 09:00      | Gửi danh sách task hôm nay lên Discord      |
| Afternoon reminder   | 13:30      | Nhắc task chưa done + task overdue          |

## Tính năng trong tab

- **Manual trigger**: bấm nút để gửi Discord notification ngay lập tức (không chờ schedule)
- **Health check**: xem Discord webhook có hoạt động không
- **Job status**: xem lần cuối job chạy lúc mấy giờ, có lỗi không

## Lưu ý

- Scheduler chạy bằng `scheduler.py` — cần file này đang chạy trong background
- Cần `DISCORD_WEBHOOK_URL` trong `.env`
- Nếu Discord webhook lỗi → check URL trong `.env` trước
```

- [ ] **Step 6: Tạo `docs/dictionary/content/vn/07_notebook.md`**

```markdown
# ⬡ Notebook

> JupyterLab tích hợp trong app — viết Python, chạy code, ghi meeting notes.

## Dùng để làm gì?

- Viết và chạy code Python exploratory mà không cần mở terminal
- Ghi meeting notes với format Markdown
- Thử nhanh một đoạn code trước khi đưa vào module chính

## Stack gợi ý (DA/DS/DE)

| Loại công việc    | Libraries hay dùng                          |
|--------------------|---------------------------------------------|
| Data Analysis      | polars, pandas, plotly                      |
| Machine Learning   | scikit-learn, xgboost, statsmodels          |
| Data Engineering   | dbt, sqlalchemy, pyarrow                    |
| Visualization      | plotly, matplotlib, seaborn                 |

## Tips

- Notebook lưu tại `D:\ai_brain\` (Obsidian vault) — tự động có trong Obsidian
- Dùng magic command `%%time` để đo thời gian chạy từng cell
- Kernel restart nếu memory usage cao (thường sau khi load file lớn)
```

- [ ] **Step 7: Tạo `docs/dictionary/content/vn/08_config.md`**

```markdown
# ⊛ Config

> Xem biến môi trường đang được load từ file `.env`. Chỉ xem — không edit tại đây.

## Các biến quan trọng

| Biến                  | Dùng cho                                      |
|-----------------------|-----------------------------------------------|
| `ANTHROPIC_API_KEY`   | Tất cả tính năng AI (ML insight, email, SQL)  |
| `OLLAMA_BASE_URL`     | Fallback khi không có Claude API              |
| `DISCORD_WEBHOOK_URL` | Gửi reminder và digest lên Discord            |
| `OBSIDIAN_VAULT_PATH` | Đường dẫn Obsidian vault để lưu SQL notes     |

## Cách thay đổi config

```
1. Mở file .env ở root project
2. Sửa giá trị cần thay đổi
3. Restart app: Ctrl+C → streamlit run app.py
```

## Lưu ý bảo mật

- Không commit file `.env` lên git (đã có trong `.gitignore`)
- API key bị lộ → revoke ngay tại console.anthropic.com
- Xem `.env.example` để biết format cần điền
```

- [ ] **Step 8: Commit**

```bash
git add docs/dictionary/content/vn/
git commit -m "feat: add dictionary content for all main tabs (02-08)"
```

---

## Task 13: Content — Glossary + Shortcuts

**Files:**
- Create: `docs/dictionary/content/vn/90_glossary.md`
- Create: `docs/dictionary/content/vn/91_shortcuts.md`

- [ ] **Step 1: Tạo `docs/dictionary/content/vn/90_glossary.md`**

```markdown
# 📚 Glossary — Thuật ngữ hay gặp

> Giải thích ngắn gọn, không dài dòng. Nếu thấy thuật ngữ lạ trong ML Studio → tìm ở đây.

## Chỉ số đánh giá model

| Thuật ngữ              | Nghĩa đơn giản                                                                 | Tốt khi nào          |
|------------------------|--------------------------------------------------------------------------------|----------------------|
| **MAPE**               | Dự đoán sai bao nhiêu % so với thực tế (Mean Absolute Percentage Error)       | Càng thấp càng tốt   |
| **RMSE**               | Sai số trung bình tính bằng đơn vị gốc (Root Mean Squared Error)              | Càng thấp càng tốt   |
| **R²**                 | Model giải thích được bao nhiêu % sự biến động của data (0→1)                 | Càng gần 1 càng tốt  |
| **Accuracy**           | Tỉ lệ dự đoán đúng trên tổng số dự đoán (cho bài toán phân loại)             | Càng cao càng tốt    |
| **F1 Score**           | Cân bằng giữa Precision và Recall — dùng khi data imbalanced                  | Càng gần 1 càng tốt  |
| **Silhouette Score**   | Các cụm KMeans có tách biệt rõ không? (-1→1)                                  | Càng gần 1 càng tốt  |
| **AIC / BIC**          | Điểm đánh giá SARIMAX — model nào fit tốt hơn với ít tham số hơn             | Càng thấp càng tốt   |

## Khái niệm ML

| Thuật ngữ              | Nghĩa đơn giản                                                                  |
|------------------------|---------------------------------------------------------------------------------|
| **Overfitting**        | Model học thuộc data cũ nhưng đoán sai data mới — như học vẹt                  |
| **Feature Importance** | Cột nào ảnh hưởng nhiều nhất đến kết quả dự đoán                               |
| **Confidence Interval**| Vùng dự báo — thực tế sẽ rơi vào đây với xác suất ~95%                        |
| **Seasonality**        | Chu kỳ lặp lại theo mùa/tháng/tuần — VD: tháng 12 luôn cao hơn               |
| **Exogenous variable** | Biến ngoài đưa vào để giúp dự báo tốt hơn — VD: ngày khuyến mãi              |
| **Imputation**         | Tự động điền giá trị cho ô null thay vì xóa cả hàng                           |
| **Cross-validation**   | Kiểm tra model bằng cách chia data ra nhiều phần, test từng phần               |

## Định dạng dữ liệu

| Thuật ngữ    | Nghĩa                                                              |
|--------------|--------------------------------------------------------------------|
| **CSV**      | File text, các giá trị cách nhau bằng dấu phẩy                    |
| **Parquet**  | File nhị phân nén — load nhanh hơn CSV nhiều khi data lớn         |
| **Long format** | Mỗi hàng là 1 observation (ngày × sản phẩm) — ML Studio cần vậy |
| **Wide format** | Mỗi sản phẩm là 1 cột — cần pivot trước khi dùng               |
```

- [ ] **Step 2: Tạo `docs/dictionary/content/vn/91_shortcuts.md`**

```markdown
# ⌨ Shortcuts & Tips

> Các mẹo hay dùng để làm việc nhanh hơn trong Chooper.

## Tips theo tab

### ◈ ML Studio
- Có thể **quay lại bước bất kỳ** mà không cần upload lại — bấm nút bước ở progress bar
- Session được **lưu tự động** — tắt app đi rồi mở lại vẫn còn
- Nếu model chạy sai → thử step 4 (Clean) lại — data chất lượng > thuật toán xịn

### ⬡ Tasks
- Search bar hỗ trợ **filter theo tag**: gõ `#sf` để chỉ xem task Salesforce
- **Click trực tiếp** vào tên task để edit — không cần mở form riêng
- Task recurring: sau khi done → tự tạo task mới cho kỳ tiếp theo

### ⬡ SQL → Obsidian
- **Ctrl+Enter** trong text box SQL để trigger analyze nhanh
- Sau khi analyze, **title và tags** có thể sửa trước khi save
- File lưu vào `D:\ai_brain\SQL Queries\` → tự động index bởi Obsidian

### ⬢ Data Explorer
- **Kéo nhiều file** cùng lúc để so sánh cấu trúc
- Tab **CORRELATION** → giá trị > 0.9 giữa 2 cột = cân nhắc bỏ 1 cột trước khi ML
- Tab **MISSING** → cột > 30% null thường nên drop thay vì impute

### ◉ Email
- Email digest gửi Discord **ngay lập tức** nếu bấm Manual trigger trong Pipeline tab
- Nếu muốn **skip email** mà không gửi → nhấn Skip (lưu vào history, không nhắc lại)

## Phím tắt Streamlit (khi app đang mở)

| Phím          | Tác dụng                                       |
|---------------|------------------------------------------------|
| `R`           | Reload lại app (hard refresh)                  |
| `Ctrl + Enter`| Chạy lại widget hiện tại (text area, code box) |
| `Esc`         | Đóng dropdown / dialog đang mở                 |

## Khi app bị lỗi

```
1. Thử Ctrl+C → streamlit run app.py  (restart app)
2. Nếu lỗi import → .venv\Scripts\python.exe -m pip install -r requirements.txt
3. Nếu AI không respond → kiểm tra ANTHROPIC_API_KEY trong .env
4. Nếu Discord không gửi → kiểm tra DISCORD_WEBHOOK_URL trong .env
```
```

- [ ] **Step 3: Chạy toàn bộ test suite**

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: tất cả PASS, không có regression

- [ ] **Step 4: Verify app syntax**

```bash
.venv\Scripts\python.exe -c "import ast; ast.parse(open('app.py').read()); print('app.py OK')"
.venv\Scripts\python.exe -c "from modules.dictionary import render_dictionary_tab; print('dictionary.py OK')"
```

Expected: cả 2 đều in `OK`

- [ ] **Step 5: Commit final**

```bash
git add docs/dictionary/content/vn/
git commit -m "feat: complete dictionary content (glossary, shortcuts, all 15 sections)"
```

---

## Definition of Done — Checklist

Sau khi xong tất cả tasks, verify:

- [ ] `docs/dictionary/index.json` tồn tại với 15 sections
- [ ] Tất cả 15 file `.md` trong `docs/dictionary/content/vn/` có nội dung
- [ ] `modules/dictionary.py` import clean không lỗi
- [ ] `tests/test_dictionary.py` chạy PASS 100%
- [ ] Tab **◈ DICTIONARY** xuất hiện đúng vị trí (trước ⊛ CONFIG)
- [ ] Search real-time: gõ "sarimax" → filter đúng sections có tags/title match
- [ ] Filter chips: chọn "ML" → chỉ hiện ML Studio + Glossary
- [ ] Nav tree: Data Studio expanded mặc định, click section → load đúng content
- [ ] Toggle VN/EN: button hiển thị, click → section reloads (fallback về vn nếu en chưa có)
- [ ] Khi không tìm thấy section → hiển thị message gợi ý thay vì crash
- [ ] `pytest tests/ -v` toàn bộ PASS (không regression)
