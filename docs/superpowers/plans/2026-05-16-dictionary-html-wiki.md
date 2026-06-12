# Dictionary HTML/CSS Wiki — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit-widget Dictionary tab with a self-contained HTML/CSS/JS 3-column wiki rendered via `st.components.v1.html()`, covering all categories — App Guide, Statistical Tests, ML Prediction, and Reference.

**Architecture:** `dictionary_data.py` holds all wiki content as Python dicts. `dictionary.py` reads that data, loads `.md` files for App Guide sections, assembles them into a single HTML string (injecting data as a JS object), and calls `st.components.v1.html()`. All navigation, search, and rendering runs in JS inside the iframe — no Streamlit widgets.

**Tech Stack:** Python, Streamlit `st.components.v1.html`, vanilla HTML/CSS/JS (no external JS deps), `markdown` package (md→html conversion).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `modules/dictionary_data.py` | **Create** | All wiki content: CATEGORIES list + SECTIONS list of dicts |
| `modules/dictionary.py` | **Full rewrite** | `_md_to_html()`, `_load_md_files()`, `build_wiki_html()`, `render_dictionary_tab()` |
| `tests/test_dictionary.py` | **Update** | Replace old Streamlit-nav tests with new schema + builder tests |
| `pyproject.toml` | **Update** | Add `markdown>=3.6` dependency |

---

## Task 1 — `dictionary_data.py`: schema + App Guide + 2 sample card entries

**Files:**
- Create: `modules/dictionary_data.py`
- Test: `tests/test_dictionary.py`

- [ ] **Step 1.1 — Write failing schema tests**

Replace the full contents of `tests/test_dictionary.py` with:

```python
"""Tests for dictionary_data.py schema and dictionary.py builder."""
import pytest
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

CARD_FIELDS = ("when_to_use", "fields", "output", "conditions", "fmcg_case", "business_value")
GUIDE_CATEGORIES = {"guide", "ref"}


# ── dictionary_data schema ────────────────────────────────────────────────────

def test_no_duplicate_ids():
    from modules.dictionary_data import SECTIONS
    ids = [s["id"] for s in SECTIONS]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"


def test_all_card_sections_have_required_fields():
    from modules.dictionary_data import SECTIONS
    card_sections = [s for s in SECTIONS if not s.get("md_file")]
    for s in card_sections:
        for f in CARD_FIELDS:
            assert f in s and s[f], f"Section '{s['id']}' missing or empty field '{f}'"


def test_all_guide_sections_have_md_file():
    from modules.dictionary_data import SECTIONS
    guide_sections = [s for s in SECTIONS if s.get("category") in GUIDE_CATEGORIES]
    for s in guide_sections:
        assert s.get("md_file"), f"Guide section '{s['id']}' missing 'md_file'"


def test_all_sections_have_required_base_fields():
    from modules.dictionary_data import SECTIONS
    base = ("id", "title", "category", "icon", "group")
    for s in SECTIONS:
        for f in base:
            assert f in s, f"Section '{s.get('id', '?')}' missing base field '{f}'"


def test_categories_match_section_categories():
    from modules.dictionary_data import SECTIONS, CATEGORIES
    cat_ids = {c["id"] for c in CATEGORIES}
    for s in SECTIONS:
        assert s["category"] in cat_ids, \
            f"Section '{s['id']}' has unknown category '{s['category']}'"


# ── dictionary.py builder ─────────────────────────────────────────────────────

def test_md_to_html_converts_heading():
    from modules.dictionary import _md_to_html
    result = _md_to_html("# Hello")
    assert "<h1>" in result
    assert "Hello" in result


def test_md_to_html_converts_table():
    from modules.dictionary import _md_to_html
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = _md_to_html(md)
    assert "<table>" in result


def test_load_md_files_converts_existing_file(tmp_path):
    (tmp_path / "myfile.md").write_text("# Hi\nContent", encoding="utf-8")
    import modules.dictionary as d
    orig = d._CONTENT_DIR
    d._CONTENT_DIR = tmp_path
    try:
        result = d._load_md_files([{"id": "x", "md_file": "myfile"}])
        assert "myfile" in result
        assert "<h1>" in result["myfile"]
    finally:
        d._CONTENT_DIR = orig


def test_load_md_files_skips_sections_without_md_file():
    import modules.dictionary as d
    result = d._load_md_files([{"id": "xgboost"}])  # no md_file key
    assert result == {}


def test_load_md_files_returns_empty_string_for_missing_file(tmp_path):
    import modules.dictionary as d
    orig = d._CONTENT_DIR
    d._CONTENT_DIR = tmp_path
    try:
        result = d._load_md_files([{"id": "x", "md_file": "nonexistent"}])
        assert result["nonexistent"] == ""
    finally:
        d._CONTENT_DIR = orig


def test_build_wiki_html_is_valid_document():
    from modules.dictionary import build_wiki_html
    from modules.dictionary_data import SECTIONS
    html = build_wiki_html(SECTIONS, {})
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "__WIKI_DATA__" not in html


def test_build_wiki_html_injects_section_id():
    from modules.dictionary import build_wiki_html
    from modules.dictionary_data import SECTIONS
    html = build_wiki_html(SECTIONS, {})
    assert SECTIONS[0]["id"] in html


def test_build_wiki_html_injects_md_content():
    from modules.dictionary import build_wiki_html
    from modules.dictionary_data import SECTIONS
    html = build_wiki_html(SECTIONS, {"00_welcome": "<h1>UNIQUE_MARKER</h1>"})
    assert "UNIQUE_MARKER" in html
```

- [ ] **Step 1.2 — Run tests to confirm they all fail**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v 2>&1 | head -40
```

Expected: `ImportError` or `ModuleNotFoundError` for `modules.dictionary_data`.

- [ ] **Step 1.3 — Create `modules/dictionary_data.py`**

```python
# modules/dictionary_data.py
"""Wiki content for the Dictionary HTML/CSS knowledge base."""
from __future__ import annotations

CATEGORIES: list[dict] = [
    {"id": "guide", "label": "App Guide",      "icon": "📋"},
    {"id": "stat",  "label": "Kiểm định TK",   "icon": "📊"},
    {"id": "ml",    "label": "ML Dự đoán",     "icon": "🤖"},
    {"id": "ref",   "label": "Reference",       "icon": "📚"},
]

SECTIONS: list[dict] = [
    # ── App Guide ────────────────────────────────────────────────────────────
    {"id": "00_welcome",   "title": "Welcome",      "category": "guide", "icon": "◈", "group": "", "md_file": "00_welcome"},
    {"id": "02_tasks",     "title": "Tasks",         "category": "guide", "icon": "⬡", "group": "", "md_file": "02_tasks"},
    {"id": "03_performance","title": "Performance",  "category": "guide", "icon": "◎", "group": "", "md_file": "03_performance"},
    {"id": "04_email",     "title": "Email",         "category": "guide", "icon": "◉", "group": "", "md_file": "04_email"},
    {"id": "05_focus",     "title": "Focus",         "category": "guide", "icon": "⏱", "group": "", "md_file": "05_focus"},
    {"id": "06_pipeline",  "title": "Pipeline",      "category": "guide", "icon": "◉", "group": "", "md_file": "06_pipeline"},
    {"id": "07_notebook",  "title": "Notebook",      "category": "guide", "icon": "⬡", "group": "", "md_file": "07_notebook"},
    {"id": "08_config",    "title": "Config",        "category": "guide", "icon": "⊛", "group": "", "md_file": "08_config"},

    # ── Stat Tests — Tham số (Parametric) ───────────────────────────────────
    {
        "id": "anova_oneway",
        "title": "One-Way ANOVA",
        "subtitle": "So sánh nhiều nhóm độc lập",
        "category": "stat",
        "group": "Tham số (Parametric)",
        "icon": "📊",
        "tags": ["parametric", "≥3 nhóm", "F-test"],
        "when_to_use": "So sánh trung bình của ≥ 3 nhóm độc lập. VD: GMV của ColosBaby ở HCM, HN, Đà Nẵng, Cần Thơ có thực sự khác nhau không?",
        "fields": "`region` (≥3 categories), `gmv` (numeric)",
        "output": "F-statistic, p-value, box plot so sánh nhóm, post-hoc Tukey HSD",
        "conditions": "Phân phối chuẩn trong mỗi nhóm. Phương sai bằng nhau (kiểm tra Levene). Mẫu độc lập.",
        "fmcg_case": "ColosBaby Gold T04: HCM (4.2B), HN (3.1B), ĐN (1.8B), CT (1.2B). Kiểm tra xem chênh lệch giữa 4 region có ý nghĩa thống kê không.",
        "fmcg_result": "p = 0.03 → Có sự khác biệt thực sự. Post-hoc: HCM vs CT là cặp chênh lệch lớn nhất.",
        "business_value": "Xác định region nào underperform thực sự (không phải do ngẫu nhiên) để điều chỉnh ngân sách và KPI có cơ sở.",
    },

    # ── ML Dự đoán — Supervised ──────────────────────────────────────────────
    {
        "id": "xgboost",
        "title": "XGBoost",
        "subtitle": "Gradient boosting — Supervised learning",
        "category": "ml",
        "group": "Supervised",
        "icon": "⚡",
        "tags": ["Regression", "Classification", "Supervised"],
        "when_to_use": "Dự đoán giá trị số (GMV tháng tới) hoặc phân loại (khách có churn không). Data dạng bảng với cột mục tiêu rõ ràng.",
        "fields": "`target` (cột dự đoán), feature columns (numeric và categorical đã encode)",
        "output": "Giá trị dự đoán, Feature Importance chart, RMSE/R² (regression) hoặc Accuracy/F1/AUC (classification)",
        "conditions": "Cần cột mục tiêu (supervised). Tốt nhất với ≥ 500 dòng. Categorical phải được encode.",
        "fmcg_case": "Dự đoán GMV ColosBaby tháng T+1 dựa trên lag_gmv_1, lag_gmv_2, region_encoded, channel_encoded, sku_count.",
        "fmcg_result": "RMSE = 0.8B, R² = 0.87 → Model giải thích 87% biến động. Top features: lag_gmv_1 (40%), sku_count (22%).",
        "business_value": "Lập kế hoạch tồn kho và trade spend chính xác hơn. Biết feature nào quan trọng nhất để tập trung cải thiện.",
    },

    # ── Reference ────────────────────────────────────────────────────────────
    {"id": "90_glossary",  "title": "Glossary",         "category": "ref", "icon": "📚", "group": "", "md_file": "90_glossary"},
    {"id": "91_shortcuts", "title": "Shortcuts & Tips",  "category": "ref", "icon": "⌨", "group": "", "md_file": "91_shortcuts"},
]
```

- [ ] **Step 1.4 — Run schema tests (expect partial pass)**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py::test_no_duplicate_ids tests/test_dictionary.py::test_all_card_sections_have_required_fields tests/test_dictionary.py::test_all_guide_sections_have_md_file tests/test_dictionary.py::test_all_sections_have_required_base_fields tests/test_dictionary.py::test_categories_match_section_categories -v
```

Expected: all 5 pass.

- [ ] **Step 1.5 — Commit**

```powershell
git add modules/dictionary_data.py tests/test_dictionary.py
git commit -m "feat: add dictionary_data.py content schema + schema tests"
```

---

## Task 2 — `dictionary.py`: Python utilities + add `markdown` dependency

**Files:**
- Rewrite: `modules/dictionary.py`
- Modify: `pyproject.toml`

- [ ] **Step 2.1 — Add `markdown` to `pyproject.toml`**

In `pyproject.toml`, add to the `dependencies` list (after `matplotlib` line):

```toml
    "markdown>=3.6",
```

Install it:

```powershell
.venv\Scripts\pip.exe install markdown>=3.6
```

- [ ] **Step 2.2 — Rewrite `modules/dictionary.py`** (utilities only — `_HTML_TEMPLATE` is a stub for now)

```python
# modules/dictionary.py
"""
DICTIONARY TAB — Full HTML/CSS/JS wiki via st.components.v1.html().
Content comes from modules/dictionary_data.SECTIONS.
App Guide sections are loaded from docs/dictionary/content/vn/*.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_CONTENT_DIR = Path(__file__).parent.parent / "docs/dictionary/content/vn"

# Placeholder — replaced in Task 3
_HTML_TEMPLATE = "<!DOCTYPE html><html><body>STUB</body></html>"


def _md_to_html(text: str) -> str:
    """Convert Markdown text to HTML string."""
    import markdown
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
    )


def _load_md_files(sections: list[dict]) -> dict[str, str]:
    """
    For each section with a 'md_file' key, read the corresponding .md file
    from _CONTENT_DIR and convert to HTML.
    Returns {md_file_id: html_string}. Missing files → empty string.
    """
    result: dict[str, str] = {}
    for s in sections:
        md_file = s.get("md_file")
        if not md_file:
            continue
        path = _CONTENT_DIR / f"{md_file}.md"
        result[md_file] = _md_to_html(path.read_text(encoding="utf-8")) if path.exists() else ""
    return result


def build_wiki_html(sections: list[dict], md_contents: dict[str, str]) -> str:
    """
    Assemble the full HTML document by injecting sections and md_contents
    into _HTML_TEMPLATE as a JS constant WIKI.
    """
    from modules.dictionary_data import CATEGORIES
    payload = json.dumps(
        {"categories": CATEGORIES, "sections": sections, "md": md_contents},
        ensure_ascii=False,
    )
    return _HTML_TEMPLATE.replace("__WIKI_DATA__", payload)


def render_dictionary_tab() -> None:
    """Entry point from app.py — renders the full wiki iframe."""
    from modules.dictionary_data import SECTIONS
    md_contents = _load_md_files(SECTIONS)
    html = build_wiki_html(SECTIONS, md_contents)
    # height=900: inner columns scroll via CSS overflow-y:auto
    components.html(html, height=900, scrolling=False)
```

- [ ] **Step 2.3 — Run builder tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -k "md_to_html or load_md or build_wiki" -v
```

Expected: all 8 builder tests pass (stub template makes `build_wiki_html` tests pass partially — `__WIKI_DATA__` not in stub, so `test_build_wiki_html_is_valid_document` may fail on `startswith`).

Fix: `test_build_wiki_html_is_valid_document` will fail because stub doesn't start with `<!DOCTYPE`. That's fine — it's a red flag to fix in Task 3.

- [ ] **Step 2.4 — Commit**

```powershell
git add modules/dictionary.py pyproject.toml
git commit -m "feat: add dictionary.py utilities (_md_to_html, _load_md_files, build_wiki_html stub)"
```

---

## Task 3 — Full HTML/CSS/JS template

**Files:**
- Modify: `modules/dictionary.py` (replace `_HTML_TEMPLATE` stub with full template)

- [ ] **Step 3.1 — Replace `_HTML_TEMPLATE` in `modules/dictionary.py`**

Replace the line:
```python
_HTML_TEMPLATE = "<!DOCTYPE html><html><body>STUB</body></html>"
```

With the full template below. Insert it after the `import streamlit.components.v1 as components` line:

```python
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:#0d1117;color:#e6edf3;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px}
#app{display:flex;flex-direction:column;height:100%}
/* Search */
#search-row{display:flex;align-items:center;gap:10px;padding:10px 14px;
  border-bottom:1px solid #21262d;flex-shrink:0}
#search-input{flex:1;background:#161b22;border:1px solid #30363d;border-radius:6px;
  padding:6px 12px;color:#e6edf3;font-size:12px;outline:none;
  font-family:'JetBrains Mono',monospace}
#search-input::placeholder{color:#6e7681}
#search-input:focus{border-color:#00d4ff}
#search-count{font-size:11px;color:#6e7681;font-family:'JetBrains Mono',monospace;
  white-space:nowrap;min-width:60px;text-align:right}
/* Columns */
#main{display:flex;flex:1;overflow:hidden}
#col-tree{width:18%;min-width:130px;border-right:1px solid #21262d;
  overflow-y:auto;padding:12px 6px;flex-shrink:0}
#col-list{width:22%;min-width:150px;border-right:1px solid #21262d;
  overflow-y:auto;padding:10px 6px;flex-shrink:0}
#col-detail{flex:1;overflow-y:auto;padding:20px 24px}
/* Scrollbar */
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:2px}
/* Category buttons */
.cat-btn{display:flex;align-items:center;gap:8px;width:100%;padding:8px 10px;
  background:transparent;border:none;border-radius:6px;cursor:pointer;
  color:#8b949e;font-size:12px;text-align:left;transition:background .15s,color .15s}
.cat-btn:hover{background:rgba(255,255,255,.05);color:#c9d1d9}
.cat-btn.active{background:rgba(0,212,255,.1);color:#00d4ff}
.cat-icon{font-size:15px;flex-shrink:0;width:22px;text-align:center}
.cat-count{margin-left:auto;font-size:10px;background:#21262d;
  padding:1px 7px;border-radius:8px;color:#6e7681}
.cat-btn.active .cat-count{background:rgba(0,212,255,.15);color:#00d4ff}
/* Method list */
.group-label{font-size:9px;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:#6e7681;padding:10px 10px 4px;
  font-family:'JetBrains Mono',monospace}
.method-btn{display:block;width:100%;padding:7px 10px;background:transparent;
  border:none;border-left:2px solid transparent;border-radius:0 5px 5px 0;
  cursor:pointer;text-align:left;transition:background .15s;margin-bottom:1px}
.method-btn:hover{background:rgba(255,255,255,.05)}
.method-btn.active{background:rgba(0,212,255,.08);border-left-color:#00d4ff}
.m-row{display:flex;align-items:center;gap:6px}
.m-icon{font-size:13px;flex-shrink:0}
.m-title{font-size:12px;color:#c9d1d9}
.method-btn.active .m-title{color:#00d4ff}
.m-sub{font-size:10px;color:#6e7681;margin-top:2px;padding-left:19px}
/* Detail — Structured Cards */
.method-heading{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.method-icon-box{width:40px;height:40px;border-radius:8px;
  background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.2);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;flex-shrink:0}
.method-name{font-size:18px;font-weight:700;color:#e6edf3}
.method-subtitle{font-size:12px;color:#8b949e;margin-top:2px}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.tag{font-size:10px;padding:2px 9px;border-radius:10px}
.tag-stat{background:rgba(0,212,255,.1);color:#00d4ff;border:1px solid rgba(0,212,255,.2)}
.tag-ml{background:rgba(63,185,80,.1);color:#3fb950;border:1px solid rgba(63,185,80,.2)}
.tag-cluster{background:rgba(163,113,247,.1);color:#a371f7;border:1px solid rgba(163,113,247,.2)}
.tag-ts{background:rgba(230,134,42,.1);color:#e6862a;border:1px solid rgba(230,134,42,.2)}
.tag-guide{background:rgba(139,148,158,.1);color:#8b949e;border:1px solid rgba(139,148,158,.2)}
.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.info-card{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 12px}
.info-label{font-size:9px;text-transform:uppercase;letter-spacing:.08em;
  color:#6e7681;font-weight:700;margin-bottom:4px;
  font-family:'JetBrains Mono',monospace}
.info-val{font-size:12px;color:#c9d1d9;line-height:1.5}
.info-val code{background:#21262d;padding:1px 5px;border-radius:3px;
  font-family:'JetBrains Mono',monospace;font-size:10px;color:#79c0ff}
.fmcg-block{background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.12);
  border-left:3px solid #00d4ff;border-radius:0 6px 6px 0;
  padding:12px 14px;margin-bottom:10px}
.fmcg-eyebrow{font-size:9px;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;color:#00d4ff;margin-bottom:5px;
  font-family:'JetBrains Mono',monospace}
.fmcg-case{font-size:12px;color:#c9d1d9;line-height:1.6}
.fmcg-result{font-size:11px;color:#8b949e;margin-top:5px;font-style:italic}
.value-block{background:rgba(35,134,54,.07);border:1px solid rgba(35,134,54,.2);
  border-radius:6px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start}
.value-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.value-label{font-size:9px;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;color:#3fb950;margin-bottom:3px;
  font-family:'JetBrains Mono',monospace}
.value-text{font-size:12px;color:#c9d1d9;line-height:1.5}
/* Detail — Prose (App Guide) */
.prose{font-size:13px;line-height:1.7;color:#c9d1d9;max-width:720px}
.prose h1{font-size:20px;color:#e6edf3;margin:0 0 12px;font-weight:700}
.prose h2{font-size:16px;color:#e6edf3;margin:20px 0 8px;font-weight:600}
.prose h3{font-size:14px;color:#e6edf3;margin:16px 0 6px;font-weight:600}
.prose p{margin-bottom:10px}
.prose code{background:#21262d;padding:2px 6px;border-radius:3px;
  font-family:'JetBrains Mono',monospace;font-size:11px;color:#79c0ff}
.prose pre{background:#161b22;border:1px solid #21262d;border-radius:6px;
  padding:14px;overflow-x:auto;margin-bottom:12px}
.prose pre code{background:none;padding:0;font-size:12px;color:#e6edf3}
.prose table{border-collapse:collapse;width:100%;margin-bottom:12px;font-size:12px}
.prose th{text-align:left;padding:6px 10px;border-bottom:2px solid #21262d;
  color:#8b949e;font-size:11px;text-transform:uppercase}
.prose td{padding:6px 10px;border-bottom:1px solid #161b22}
.prose ul,.prose ol{margin:0 0 10px 20px}
.prose li{margin-bottom:4px}
.prose blockquote{border-left:3px solid #30363d;padding-left:12px;
  color:#8b949e;margin-bottom:10px;font-style:italic}
.prose hr{border:none;border-top:1px solid #21262d;margin:16px 0}
.prose a{color:#58a6ff;text-decoration:none}
.prose strong{color:#e6edf3;font-weight:600}
/* Empty state */
.empty-state{display:flex;align-items:center;justify-content:center;
  height:200px;color:#6e7681;font-size:13px;font-style:italic}
</style>
</head>
<body>
<div id="app">
  <div id="search-row">
    <span style="color:#6e7681;font-size:14px">🔍</span>
    <input id="search-input" type="text"
           placeholder="Tìm kiếm... (vd: anova, xgboost, forecast)"
           oninput="onSearch()" autocomplete="off">
    <span id="search-count"></span>
  </div>
  <div id="main">
    <nav id="col-tree"></nav>
    <nav id="col-list"></nav>
    <main id="col-detail"></main>
  </div>
</div>
<script>
const WIKI = __WIKI_DATA__;
let _cat = 'guide', _sid = null;

const TAG_CLASS = {stat:'tag-stat',ml:'tag-ml',cluster:'tag-cluster',
                   ts:'tag-ts',guide:'tag-guide',ref:'tag-guide'};

function init() {
  const first = WIKI.sections.find(s => s.category === _cat);
  if (first) _sid = first.id;
  renderTree(); renderList(); renderDetail();
}

// ── Category tree ──
function renderTree() {
  document.getElementById('col-tree').innerHTML = WIKI.categories.map(c => {
    const n = WIKI.sections.filter(s => s.category === c.id).length;
    return `<button class="cat-btn${c.id===_cat?' active':''}" onclick="selectCat('${c.id}')">
      <span class="cat-icon">${c.icon}</span><span>${c.label}</span>
      <span class="cat-count">${n}</span></button>`;
  }).join('');
}

function selectCat(cat) {
  _cat = cat;
  document.getElementById('search-input').value = '';
  const first = WIKI.sections.find(s => s.category === cat);
  _sid = first ? first.id : null;
  renderTree(); renderList(); renderDetail();
}

// ── Method list ──
function _filtered() {
  const q = document.getElementById('search-input').value.toLowerCase().trim();
  return WIKI.sections.filter(s => {
    if (!q) return s.category === _cat;
    return s.title.toLowerCase().includes(q)
      || (s.tags||[]).some(t => t.toLowerCase().includes(q))
      || (s.subtitle||'').toLowerCase().includes(q);
  });
}

function renderList() {
  const q = document.getElementById('search-input').value.trim();
  const filtered = _filtered();
  document.getElementById('search-count').textContent =
    q ? filtered.length + ' kết quả' : '';

  if (!filtered.length) {
    document.getElementById('col-list').innerHTML =
      '<div class="empty-state">Không tìm thấy</div>';
    return;
  }

  const grouped = {};
  filtered.forEach(s => {
    const key = q
      ? (WIKI.categories.find(c=>c.id===s.category)||{label:s.category}).label
      : (s.group||'');
    (grouped[key] = grouped[key]||[]).push(s);
  });

  let html = '';
  Object.entries(grouped).forEach(([g, secs]) => {
    if (g) html += `<div class="group-label">${g}</div>`;
    secs.forEach(s => {
      html += `<button class="method-btn${s.id===_sid?' active':''}"
        onclick="selectSection('${s.id}')">
        <div class="m-row"><span class="m-icon">${s.icon||'◈'}</span>
          <span class="m-title">${s.title}</span></div>
        ${s.subtitle?`<div class="m-sub">${s.subtitle}</div>`:''}
      </button>`;
    });
  });
  document.getElementById('col-list').innerHTML = html;
}

function selectSection(id) {
  _sid = id;
  const s = WIKI.sections.find(x=>x.id===id);
  if (s && s.category !== _cat) { _cat = s.category; renderTree(); }
  renderList(); renderDetail();
}

function onSearch() {
  renderList();
  const first = _filtered()[0];
  if (first && first.id !== _sid) { _sid = first.id; renderDetail(); }
}

// ── Detail panel ──
function renderDetail() {
  const el = document.getElementById('col-detail');
  if (!_sid) {
    el.innerHTML = '<div class="empty-state">Chọn một mục từ menu bên trái</div>';
    return;
  }
  const s = WIKI.sections.find(x=>x.id===_sid);
  if (!s) { el.innerHTML = ''; return; }
  el.innerHTML = s.md_file ? renderProse(s) : renderCards(s);
  el.scrollTop = 0;
}

function renderCards(s) {
  const tc = TAG_CLASS[s.category]||'tag-stat';
  const tags = (s.tags||[]).map(t=>`<span class="tag ${tc}">${t}</span>`).join('');
  const fieldsHtml = (s.fields||'—').replace(/`([^`]+)`/g,'<code>$1</code>');
  return `<div class="method-heading">
    <div class="method-icon-box">${s.icon||'◈'}</div>
    <div><div class="method-name">${s.title}</div>
      ${s.subtitle?`<div class="method-subtitle">${s.subtitle}</div>`:''}</div>
  </div>
  <div class="tags">${tags}</div>
  <div class="info-grid">
    <div class="info-card"><div class="info-label">⏱ Khi nào dùng</div>
      <div class="info-val">${s.when_to_use||'—'}</div></div>
    <div class="info-card"><div class="info-label">🗂 Fields cần</div>
      <div class="info-val">${fieldsHtml}</div></div>
    <div class="info-card"><div class="info-label">📈 Output</div>
      <div class="info-val">${s.output||'—'}</div></div>
    <div class="info-card"><div class="info-label">⚠️ Điều kiện</div>
      <div class="info-val">${s.conditions||'—'}</div></div>
  </div>
  <div class="fmcg-block">
    <div class="fmcg-eyebrow">🏭 FMCG Case — VitaDairy</div>
    <div class="fmcg-case">${s.fmcg_case||'—'}</div>
    ${s.fmcg_result?`<div class="fmcg-result">→ ${s.fmcg_result}</div>`:''}
  </div>
  <div class="value-block">
    <div class="value-icon">💡</div>
    <div><div class="value-label">Business Value</div>
      <div class="value-text">${s.business_value||'—'}</div></div>
  </div>`;
}

function renderProse(s) {
  const html = WIKI.md[s.md_file]||'<p style="color:#6e7681">Nội dung đang cập nhật...</p>';
  return `<div class="prose">${html}</div>`;
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""
```

- [ ] **Step 3.2 — Run all builder tests — expect all pass now**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -k "build_wiki or md_to_html or load_md" -v
```

Expected: all 8 pass. If `test_build_wiki_html_is_valid_document` still fails, check that `_HTML_TEMPLATE` starts with `<!DOCTYPE html>` and contains no literal `__WIKI_DATA__` after the replace.

- [ ] **Step 3.3 — Commit**

```powershell
git add modules/dictionary.py
git commit -m "feat: add full HTML/CSS/JS template to dictionary.py"
```

---

## Task 4 — Wire up `render_dictionary_tab()` + smoke test

**Files:**
- Already in `modules/dictionary.py` from Task 2

- [ ] **Step 4.1 — Run full test suite to confirm no regressions**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v
```

Expected: all tests pass. (The old `_filter_sections` and `_load_index_from_path` tests will now fail with `ImportError` since those functions were removed. That's expected — they are replaced in the next step.)

- [ ] **Step 4.2 — Remove obsolete test imports**

In `tests/test_dictionary.py`, the line:
```python
from modules.dictionary import _filter_sections, _load_index_from_path
```
No longer exists (those functions were removed in the rewrite). The test file written in Task 1.1 already doesn't import them — confirm there's no leftover import.

Run:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v
```

Expected: all pass.

- [ ] **Step 4.3 — Start app and verify Dictionary tab renders**

```powershell
.venv\Scripts\Activate.ps1; streamlit run app.py
```

Open browser → click **DICTIONARY** tab. Expected: 3-column layout with App Guide category active, "Welcome" section loaded. Category tree shows 4 buttons. Method list shows App Guide items. Detail panel shows the Welcome .md prose.

- [ ] **Step 4.4 — Commit**

```powershell
git add modules/dictionary.py tests/test_dictionary.py
git commit -m "feat: wire up render_dictionary_tab via st.components.v1.html"
```

---

## Task 5 — Populate remaining Stat Tests content (8 more entries)

**Files:**
- Modify: `modules/dictionary_data.py`

- [ ] **Step 5.1 — Add 8 stat test entries to `SECTIONS`**

In `modules/dictionary_data.py`, after the `anova_oneway` dict, add the following entries (still inside `SECTIONS = [...]`):

```python
    {
        "id": "ttest_ind",
        "title": "T-test độc lập",
        "subtitle": "So sánh 2 nhóm độc lập",
        "category": "stat",
        "group": "Tham số (Parametric)",
        "icon": "📐",
        "tags": ["parametric", "2 nhóm", "t-test"],
        "when_to_use": "So sánh trung bình của 2 nhóm độc lập. VD: doanh số/outlet của ColosBaby ở HCM vs HN có thực sự khác nhau không?",
        "fields": "`group` (categorical, 2 giá trị), `value` (numeric)",
        "output": "t-statistic, p-value, confidence interval cho hiệu số, box plot",
        "conditions": "Mỗi nhóm ≥ 30 mẫu (hoặc phân phối chuẩn). Phương sai bằng nhau (kiểm tra Levene). Mẫu độc lập.",
        "fmcg_case": "ColosBaby Gold T04: doanh số trung bình/outlet ở HCM (42M) vs HN (38M). Chênh lệch 4M có ý nghĩa hay chỉ ngẫu nhiên?",
        "fmcg_result": "p = 0.08 → Không đủ bằng chứng. Chênh lệch có thể do ngẫu nhiên — chưa cần điều chỉnh chiến lược.",
        "business_value": "Tránh phân bổ ngân sách dựa trên chênh lệch ngẫu nhiên. Chỉ hành động khi p < 0.05.",
    },
    {
        "id": "ttest_paired",
        "title": "T-test cặp đôi",
        "subtitle": "So sánh trước và sau trên cùng đối tượng",
        "category": "stat",
        "group": "Tham số (Parametric)",
        "icon": "📐",
        "tags": ["parametric", "paired", "before-after"],
        "when_to_use": "So sánh cùng một nhóm đối tượng ở 2 thời điểm (trước/sau). VD: doanh số outlet trước và sau campaign Tết.",
        "fields": "`before` (numeric), `after` (numeric) — cùng subject",
        "output": "t-statistic, p-value, mean difference + CI",
        "conditions": "Hiệu số (after − before) phân phối chuẩn. Cùng nhóm đối tượng đo hai lần.",
        "fmcg_case": "50 outlets chạy campaign Tết ColosBaby. Doanh số T12 (trước): 38M, T01 (sau): 51M. Kiểm tra campaign có thực sự hiệu quả không.",
        "fmcg_result": "p = 0.002 → Campaign có hiệu quả thực sự. Tăng 34% đủ bằng chứng thống kê.",
        "business_value": "Đánh giá ROI campaign có cơ sở khoa học. Biết campaign nào đáng nhân rộng, campaign nào chỉ may mắn.",
    },
    {
        "id": "anova_twoway",
        "title": "Two-Way ANOVA",
        "subtitle": "Tác động của 2 biến + interaction",
        "category": "stat",
        "group": "Tham số (Parametric)",
        "icon": "📊",
        "tags": ["parametric", "interaction", "2 factors"],
        "when_to_use": "Kiểm tra tác động của 2 biến phân loại và interaction giữa chúng. VD: Brand × Channel → GMV có tương tác không?",
        "fields": "`brand` (categorical), `channel` (categorical), `gmv` (numeric)",
        "output": "F-statistic cho từng factor + interaction term, p-value, interaction plot",
        "conditions": "Balanced design (số mẫu đều giữa các ô). Phân phối chuẩn trong từng ô.",
        "fmcg_case": "ColosBaby vs Calokid × Modern Trade vs Traditional Trade. ColosBaby bán tốt hơn ở MT, Calokid tốt hơn ở TT — có interaction thật không?",
        "fmcg_result": "p_interaction = 0.01 → Có interaction. Cần chiến lược khác nhau cho từng cặp brand × channel.",
        "business_value": "Tối ưu phân bổ SKU và trade spend theo cặp brand-channel, không chỉ tối ưu từng chiều riêng lẻ.",
    },
    {
        "id": "pearson",
        "title": "Pearson Correlation",
        "subtitle": "Tương quan tuyến tính giữa 2 biến",
        "category": "stat",
        "group": "Tham số (Parametric)",
        "icon": "📈",
        "tags": ["parametric", "correlation", "linear"],
        "when_to_use": "Đo mức độ tương quan tuyến tính giữa 2 biến liên tục. VD: Chi phí quảng cáo và GMV có tương quan không?",
        "fields": "`var1` (numeric), `var2` (numeric) — cả 2 phân phối gần chuẩn",
        "output": "r (hệ số tương quan, −1 đến 1), p-value, scatter plot với regression line",
        "conditions": "Cả 2 biến phân phối xấp xỉ chuẩn. Quan hệ tuyến tính (kiểm tra scatter plot). Không có outlier cực đoan.",
        "fmcg_case": "12 tháng data ColosBaby: ad_spend vs GMV. r = 0.78, p = 0.003 → Tương quan dương mạnh.",
        "fmcg_result": "Tăng 1% ad spend tương ứng tăng ~0.8% GMV. Nhưng correlation ≠ causation — cần context thêm.",
        "business_value": "Định lượng mối quan hệ giữa investment và revenue. Giúp CFO quyết định có đáng tăng ngân sách quảng cáo không.",
    },
    {
        "id": "mannwhitney",
        "title": "Mann-Whitney U",
        "subtitle": "So sánh 2 nhóm — non-parametric",
        "category": "stat",
        "group": "Phi tham số (Non-parametric)",
        "icon": "📉",
        "tags": ["non-parametric", "2 nhóm", "robust"],
        "when_to_use": "Thay thế T-test độc lập khi data lệch mạnh hoặc không chuẩn. Phù hợp với GMV data có outlier lớn.",
        "fields": "`group` (2 giá trị), `value` (numeric, skewed ok)",
        "output": "U-statistic, p-value, median comparison per group",
        "conditions": "Không cần phân phối chuẩn. Phù hợp với data lệch phải (doanh thu, số đơn). Mẫu độc lập.",
        "fmcg_case": "Doanh thu/outlet ColosBaby vs Calokid ở kênh MT. Data GMV lệch mạnh (vài siêu thị lớn kéo mean lên) → dùng Mann-Whitney thay T-test.",
        "fmcg_result": "p = 0.02 → ColosBaby có median GMV cao hơn Calokid ở MT, có ý nghĩa thống kê.",
        "business_value": "Kết quả đáng tin hơn T-test khi data có outlier. Tránh sai lệch do vài siêu thị lớn bóp méo trung bình.",
    },
    {
        "id": "kruskal",
        "title": "Kruskal-Wallis",
        "subtitle": "So sánh ≥3 nhóm — non-parametric",
        "category": "stat",
        "group": "Phi tham số (Non-parametric)",
        "icon": "📉",
        "tags": ["non-parametric", "≥3 nhóm", "robust"],
        "when_to_use": "Thay thế One-Way ANOVA khi data không chuẩn, có ≥ 3 nhóm. Dùng khi GMV/số đơn lệch mạnh theo region.",
        "fields": "`group` (≥3 categories), `value` (numeric)",
        "output": "H-statistic, p-value, median per group",
        "conditions": "Mẫu độc lập. Không cần phân phối chuẩn. Phù hợp ordinal hoặc data lệch.",
        "fmcg_case": "Số đơn/outlet tại 4 region (HCM, HN, ĐN, CT). Distribution lệch mạnh → Kruskal-Wallis thay ANOVA.",
        "fmcg_result": "p = 0.04 → Có sự khác biệt. Median orders: HCM > HN > ĐN > CT — cần điều tra nguyên nhân CT thấp.",
        "business_value": "Kết luận đáng tin về sự khác biệt giữa regions khi data không đồng đều, không bị ảnh hưởng bởi outlier.",
    },
    {
        "id": "chi_square",
        "title": "Chi-square Test",
        "subtitle": "Kiểm tra liên hệ giữa 2 biến categorical",
        "category": "stat",
        "group": "Phi tham số (Non-parametric)",
        "icon": "🔲",
        "tags": ["non-parametric", "categorical", "chi²"],
        "when_to_use": "Kiểm tra mối liên hệ giữa 2 biến phân loại. VD: Tỉ lệ mua ColosBaby có phụ thuộc vào region không?",
        "fields": "`var1` (categorical), `var2` (categorical) — tạo contingency table",
        "output": "χ² statistic, p-value, contingency table, expected vs observed counts",
        "conditions": "Mỗi ô trong contingency table ≥ 5 mẫu. Mẫu độc lập.",
        "fmcg_case": "Khách hàng mua ColosBaby Gold (Có/Không) × Region (HCM/HN/ĐN). Kiểm tra brand preference có khác theo vùng không.",
        "fmcg_result": "p = 0.001 → Có mối liên hệ. HCM ưa ColosBaby Gold hơn; HN ưa ColosBaby thường → localization strategy.",
        "business_value": "Cơ sở để localize product mix và marketing message theo từng vùng thay vì chiến lược one-size-fits-all.",
    },
    {
        "id": "spearman",
        "title": "Spearman Correlation",
        "subtitle": "Tương quan rank — non-parametric",
        "category": "stat",
        "group": "Phi tham số (Non-parametric)",
        "icon": "📈",
        "tags": ["non-parametric", "correlation", "rank"],
        "when_to_use": "Đo tương quan khi data không chuẩn hoặc có outlier. Dùng rank thay vì giá trị thực — robust hơn Pearson.",
        "fields": "`var1` (numeric), `var2` (numeric)",
        "output": "ρ rho (−1 đến 1), p-value, scatter plot",
        "conditions": "Không cần phân phối chuẩn. Phù hợp khi quan hệ monotonic nhưng không nhất thiết tuyến tính.",
        "fmcg_case": "Rank outlet theo số SKU bày biện vs rank theo doanh thu. Có tương quan giữa shelf diversity và GMV không?",
        "fmcg_result": "ρ = 0.65, p = 0.001 → Tương quan dương trung bình-mạnh. Outlet nhiều SKU hơn → doanh thu cao hơn.",
        "business_value": "Căn cứ định lượng để đẩy KPI shelf execution (sku count, facings) như một driver của doanh thu.",
    },
```

- [ ] **Step 5.2 — Run schema tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py::test_all_card_sections_have_required_fields tests/test_dictionary.py::test_no_duplicate_ids -v
```

Expected: both pass.

- [ ] **Step 5.3 — Commit**

```powershell
git add modules/dictionary_data.py
git commit -m "feat: add all 9 statistical test entries to dictionary_data"
```

---

## Task 6 — Populate remaining ML content (9 more entries)

**Files:**
- Modify: `modules/dictionary_data.py`

- [ ] **Step 6.1 — Add 9 ML entries to `SECTIONS`**

After the `xgboost` dict, add:

```python
    {
        "id": "random_forest",
        "title": "Random Forest",
        "subtitle": "Ensemble of decision trees — Supervised",
        "category": "ml",
        "group": "Supervised",
        "icon": "🌲",
        "tags": ["Regression", "Classification", "Supervised", "Ensemble"],
        "when_to_use": "Tương tự XGBoost nhưng ổn định hơn với data nhỏ hoặc nhiều outlier. Tốt khi cần Feature Importance đáng tin cậy.",
        "fields": "`target` (cột dự đoán), feature columns (numeric + categorical đã encode)",
        "output": "Giá trị dự đoán, Feature Importance, RMSE/R² hoặc Accuracy/F1",
        "conditions": "Supervised. Ít nhạy cảm với outlier hơn XGBoost. Không cần scale features.",
        "fmcg_case": "Phân loại 200 outlets thành High Potential vs Low Potential dựa vào sku_count, visit_freq, region, channel. Dùng RF vì data nhỏ và có outlier.",
        "fmcg_result": "Accuracy = 83%, F1 = 0.81. 15 outlets được identify là High Potential cần ưu tiên.",
        "business_value": "Tập trung nguồn lực sales vào đúng outlet thay vì trải đều. Tăng hiệu suất team field force.",
    },
    {
        "id": "svm",
        "title": "SVM",
        "subtitle": "Support Vector Machine — Supervised",
        "category": "ml",
        "group": "Supervised",
        "icon": "🔷",
        "tags": ["Regression", "Classification", "Supervised"],
        "when_to_use": "Phân loại với data có biên rõ ràng, hoặc khi XGBoost/RF cho kết quả kém. Tốt với data chiều cao (nhiều features).",
        "fields": "`target`, feature columns (cần normalize trước khi train)",
        "output": "Predicted class/value, support vectors, Accuracy/F1 hoặc RMSE",
        "conditions": "Features phải được normalize/scale. Chậm với data lớn (>10K dòng). Kém hơn XGBoost với tabular FMCG data thông thường.",
        "fmcg_case": "Phân loại email phản hồi của trade partner thành Positive/Negative/Neutral dựa vào TF-IDF features từ nội dung email.",
        "fmcg_result": "Accuracy = 79%. Được dùng khi features là text (high-dimensional sparse) — XGBoost không phù hợp.",
        "business_value": "Tự động phân loại feedback từ đối tác trade, giảm thời gian manual review email.",
    },
    {
        "id": "mlp",
        "title": "MLP Neural Network",
        "subtitle": "Multi-Layer Perceptron — Supervised",
        "category": "ml",
        "group": "Supervised",
        "icon": "🧠",
        "tags": ["Regression", "Classification", "Supervised", "Neural Net"],
        "when_to_use": "Khi quan hệ giữa features và target phức tạp, phi tuyến. Dùng sau khi XGBoost/RF đã thử nhưng chưa đủ chính xác.",
        "fields": "`target`, feature columns (cần normalize, không có missing values)",
        "output": "Giá trị dự đoán, loss curve theo epoch, RMSE/R² hoặc Accuracy/F1",
        "conditions": "Cần normalize features. Cần nhiều data hơn (≥1000 dòng). Khó tune, training lâu hơn XGBoost.",
        "fmcg_case": "Dự đoán conversion rate của từng outlet dựa vào 20+ features bao gồm historical behavior, demographics, product mix.",
        "fmcg_result": "R² = 0.79 (so với XGBoost 0.82). XGBoost vẫn tốt hơn — giữ XGBoost (simpler = better).",
        "business_value": "Thử khi model đơn giản hơn không đủ. Nếu không cải thiện so với XGBoost, giữ XGBoost để dễ explain hơn.",
    },
    {
        "id": "sarimax",
        "title": "SARIMAX",
        "subtitle": "Seasonal ARIMA + Exogenous — Time series",
        "category": "ml",
        "group": "Time Series",
        "icon": "📅",
        "tags": ["Time Series", "Forecast", "Seasonal", "Exogenous"],
        "when_to_use": "Dự báo chuỗi thời gian có seasonality rõ (doanh số tăng T12, T01). Có thể thêm biến ngoài như ad_spend, ngày lễ.",
        "fields": "`date` (cột ngày), `value` (cột dự báo), optionally exogenous columns",
        "output": "Forecast line + confidence interval (95%), ACF/PACF plots, AIC/BIC metrics",
        "conditions": "Cần ≥ 24 điểm dữ liệu. Data không có khoảng trống. Seasonality xuất hiện ít nhất 2 chu kỳ.",
        "fmcg_case": "Dự báo GMV ColosBaby 3 tháng tới (T05–T07) từ 24 tháng data. Thêm exog: campaign_spend để model biết khi nào có promotion.",
        "fmcg_result": "MAPE = 8.2%. Forecast T05: 13.4B ± 1.1B (95% CI). Tháng cao nhất T07 do school season.",
        "business_value": "Lập kế hoạch sản xuất và tồn kho chính xác. Finance dùng để set target có cơ sở thay vì % tăng flat hằng năm.",
    },
    {
        "id": "exp_smoothing",
        "title": "Exponential Smoothing",
        "subtitle": "Holt-Winters — Time series đơn giản",
        "category": "ml",
        "group": "Time Series",
        "icon": "📅",
        "tags": ["Time Series", "Forecast", "Simple", "Holt-Winters"],
        "when_to_use": "Dự báo nhanh chuỗi thời gian không cần biến ngoài. Phù hợp weekly planning khi cần kết quả nhanh.",
        "fields": "`date` (cột ngày), `value` (cột dự báo)",
        "output": "Forecast line + confidence band, alpha/beta/gamma parameters",
        "conditions": "Cần ít data hơn SARIMAX (≥12 điểm). Không hỗ trợ exogenous variables.",
        "fmcg_case": "Forecast số đơn hàng Calokid tuần tới từ 52 tuần lịch sử. Cần kết quả nhanh cho weekly operational planning.",
        "fmcg_result": "MAPE = 11.5%. Nhanh hơn SARIMAX 3×. Đủ tốt cho weekly planning — không cần setup ARIMA phức tạp.",
        "business_value": "Planning ngắn hạn (weekly/bi-weekly) nhanh mà không mất công tune ARIMA. Trade-off: ít chính xác hơn SARIMAX 3–4%.",
    },
    {
        "id": "prophet",
        "title": "Prophet",
        "subtitle": "Facebook Prophet — Time series linh hoạt",
        "category": "ml",
        "group": "Time Series",
        "icon": "🔮",
        "tags": ["Time Series", "Forecast", "Holiday", "Flexible"],
        "when_to_use": "Time series có holiday effects mạnh (Tết, 8/3, Trung Thu), data không đều hoặc có khoảng trống, hoặc khi muốn setup nhanh.",
        "fields": "`ds` (date column, tên bắt buộc), `y` (value column, tên bắt buộc)",
        "output": "Forecast + uncertainty interval + decomposition (trend, seasonality, holidays riêng biệt)",
        "conditions": "Column phải đặt tên đúng (ds, y). Tự xử lý missing dates. Không cần test stationarity.",
        "fmcg_case": "Dự báo GMV Calokid cả năm 2026, tích hợp Vietnamese holidays (Tết, 1/6, Trung Thu). Thấy rõ Tết spike +38%.",
        "fmcg_result": "MAPE = 9.8%. Decomposition: Tết +38%, school season (8–9) +22%, baseline trend +5%/năm.",
        "business_value": "Nhìn thấy đóng góp riêng biệt của trend/seasonality/holiday. Budget và tồn kho theo mùa chính xác hơn.",
    },
    {
        "id": "kmeans",
        "title": "KMeans",
        "subtitle": "K-Means Clustering — Unsupervised",
        "category": "ml",
        "group": "Clustering",
        "icon": "🔵",
        "tags": ["Clustering", "Unsupervised", "Segmentation"],
        "when_to_use": "Segment khách hàng, outlet, SKU — khi không có nhãn sẵn. App tự tìm số cụm K tối ưu qua Elbow method.",
        "fields": "Feature columns (numeric, không cần target column)",
        "output": "Cluster labels, silhouette score, scatter plot 2D (PCA), cluster profile table",
        "conditions": "Features phải được normalize. Không có cột mục tiêu. Nhạy cảm với outlier cực đoan.",
        "fmcg_case": "Segment 500 outlets theo avg_gmv, visit_frequency, sku_count, channel. App tìm K=4 tối ưu: Power, Growing, Dormant, New.",
        "fmcg_result": "Silhouette = 0.62 (tốt). Power Outlets (18%): avg GMV 8× nhóm Dormant. 4 nhóm có profile rõ ràng.",
        "business_value": "Personalize chiến lược trade theo segment thay vì uniform. Power Outlets cần VIP treatment; Dormant cần reactivation.",
    },
    {
        "id": "dbscan",
        "title": "DBSCAN",
        "subtitle": "Density-Based Clustering — Anomaly detection",
        "category": "ml",
        "group": "Clustering",
        "icon": "🔴",
        "tags": ["Clustering", "Unsupervised", "Anomaly", "Density"],
        "when_to_use": "Clustering khi không biết số cụm trước, và muốn tự động detect outliers. Outlets được gán label −1 là anomalies.",
        "fields": "Feature columns (numeric)",
        "output": "Cluster labels (−1 = noise/outlier), số cụm tự động, silhouette score, scatter plot",
        "conditions": "Nhạy với epsilon và min_samples parameters. Khó tune hơn KMeans. Tốt khi cụm không có hình cầu.",
        "fmcg_case": "Phát hiện outlets bất thường trong GMV pattern. Label −1 (noise) là candidates để investigate data quality hoặc operations.",
        "fmcg_result": "12 outlets flagged. Sau điều tra: 7 do data entry error, 5 do thực sự có vấn đề phân phối.",
        "business_value": "Phát hiện tự động data issues và outlets cần attention đặc biệt — không cần review thủ công 500+ outlets.",
    },
    {
        "id": "hierarchical",
        "title": "Hierarchical Clustering",
        "subtitle": "Agglomerative — Xem cấu trúc cây phân cấp",
        "category": "ml",
        "group": "Clustering",
        "icon": "🌳",
        "tags": ["Clustering", "Unsupervised", "Dendrogram"],
        "when_to_use": "Clustering khi muốn xem dendrogram (cây phân cấp) để hiểu cấu trúc data. Không cần chỉ định K trước.",
        "fields": "Feature columns (numeric)",
        "output": "Dendrogram, cluster labels, silhouette score, cluster profile table",
        "conditions": "Chậm với data lớn (>5000 dòng). Không thể undo merge — kết quả cố định. Tốt với data nhỏ-vừa.",
        "fmcg_case": "Phân nhóm 50 SKUs ColosBaby theo monthly GMV pattern (24 tháng). Dendrogram cho thấy 3 nhóm tự nhiên: Hero, Support, Tail.",
        "fmcg_result": "3 clusters rõ ràng. Hero (8 SKUs) chiếm 65% GMV. Tail (22 SKUs) chiếm 8% → candidate để rationalize.",
        "business_value": "Portfolio rationalization có cơ sở data. Loại Tail SKUs giảm supply chain complexity mà không ảnh hưởng đáng kể doanh thu.",
    },
```

- [ ] **Step 6.2 — Run all schema tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dictionary.py -v
```

Expected: all tests pass.

- [ ] **Step 6.3 — Verify in app — check ML category**

Start the app and open Dictionary tab → click **ML Dự đoán** → verify all 10 entries appear in the method list grouped by Supervised / Time Series / Clustering. Click each entry and confirm the structured cards render.

- [ ] **Step 6.4 — Commit**

```powershell
git add modules/dictionary_data.py
git commit -m "feat: add all 10 ML prediction entries to dictionary_data"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] All sections in HTML/CSS → `st.components.v1.html()` — Task 4
- [x] 3-column layout — Task 3
- [x] All 4 categories in iframe — Tasks 1, 5, 6
- [x] Structured Cards detail panel — Task 3 (`renderCards` JS)
- [x] App Guide sections from .md files — Task 2 (`_load_md_files`)
- [x] 9 statistical test entries — Task 5
- [x] 10 ML entries — Task 6
- [x] FMCG cases for all card sections — Tasks 5, 6
- [x] `dictionary_data.py` as single content source — Task 1
- [x] `render_dictionary_tab()` signature unchanged — Task 2/4
- [x] `markdown` dependency — Task 2
- [x] Tests updated — Task 1 (new test file)

**Placeholder scan:** None found.

**Type consistency:**
- `build_wiki_html(sections: list[dict], md_contents: dict[str, str])` defined in Task 2, tested in Task 1.1 — consistent.
- `_load_md_files(sections: list[dict]) -> dict[str, str]` — consistent across Tasks 2 and 1.1 tests.
- `SECTIONS` and `CATEGORIES` imported from `modules.dictionary_data` — consistent across all tasks.
- `_CONTENT_DIR` module-level variable used in `_load_md_files` and patched in tests — consistent.
