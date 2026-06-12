# Dictionary → Full HTML/CSS Knowledge Wiki

**Date:** 2026-05-16
**Status:** Approved for implementation

---

## Goal

Replace the current Streamlit-component-based Dictionary tab with a fully self-contained HTML/CSS/JS wiki rendered via `st.components.v1.html()`. The entire Dictionary — all categories — renders inside a single iframe. No Streamlit widgets inside the Dictionary.

---

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Layout | 3-Column Wiki | Category tree → method list → detail panel; scales to many methods |
| Integration | `st.components.v1.html()` | 100% HTML/CSS freedom, decoupled from Streamlit session state |
| Scope | All Dictionary categories | Consistent UX — App Guide, Stats, ML, Reference all in one iframe |
| Detail panel style | Structured Cards | Grid of info cards (Khi nào dùng / Fields / Output / Điều kiện / FMCG Case / Business Value) — scannable |
| Content source | Python dict in `dictionary_data.py` | Easier to edit than embedded JS; Python injects into HTML template at render time |
| Language | Vietnamese (VN) primary | EN fallback label kept for future; toggle removed from iframe (handled by app.py if needed) |

---

## Architecture

```
app.py
  └── render_dictionary_tab()          ← signature unchanged

modules/dictionary.py                  ← full rewrite
  ├── build_wiki_html(sections) → str  ← assembles HTML string with JS data injected
  └── render_dictionary_tab()          ← calls st.components.v1.html(build_wiki_html(...), height=900, scrolling=False)

modules/dictionary_data.py             ← NEW: single source of truth for all wiki content
  └── SECTIONS: list[dict]             ← ordered list of section dicts (see schema below)

docs/dictionary/content/vn/*.md        ← existing App Guide .md files; Python reads + injects as HTML
docs/superpowers/specs/                ← this file
```

### Section schema (`dictionary_data.py`)

```python
{
  "id": "anova",                        # unique slug, used as JS key
  "title": "One-Way ANOVA",
  "category": "stat",                   # "guide" | "stat" | "ml" | "ref"
  "group": "Kiểm định tham số",         # sub-group label inside category
  "tags": ["parametric", "≥3 nhóm"],
  "icon": "📊",
  "subtitle": "So sánh nhiều nhóm độc lập",
  # Structured Cards fields:
  "when_to_use": "...",
  "fields": "...",
  "output": "...",
  "conditions": "...",
  "fmcg_case": "...",
  "fmcg_result": "...",
  "business_value": "...",
  # Optional — for App Guide sections only:
  "md_file": "01_data_studio",          # if set, Python reads docs/dictionary/content/vn/{md_file}.md
}
```

---

## 3-Column Layout

```
┌─────────────┬──────────────────┬──────────────────────────────────────────┐
│ Col 1       │ Col 2            │ Col 3                                    │
│ Category    │ Method List      │ Detail Panel                             │
│ Tree        │ (changes on      │ (changes on method click)                │
│ (sticky)    │ category click)  │                                          │
│             │                  │ [Icon] Title          [tag][tag]         │
│ 📋 App Guide│ · Welcome        │ ┌─────────────┬──────────────────┐       │
│ 📊 Stat     │ · ANOVA          │ │⏱ Khi nào   │ 🗂 Fields cần   │       │
│   Tests     │ · T-test         │ │  dùng       │                  │       │
│ 🤖 ML       │ · Chi-square     │ ├─────────────┼──────────────────┤       │
│   Predict   │ · Correlation    │ │📈 Output    │ ⚠️ Điều kiện    │       │
│ 📚 Reference│ · ...            │ └─────────────┴──────────────────┘       │
│             │                  │ 🏭 FMCG Case — VitaDairy                 │
│             │                  │    [scenario + kết quả mẫu]              │
│             │                  │ 💡 Business Value                        │
└─────────────┴──────────────────┴──────────────────────────────────────────┘
```

**Column widths:** 18% / 22% / 60%

---

## Content Map

### 📋 App Guide (group: existing sections)
Reads from existing `docs/dictionary/content/vn/*.md` files via Python, renders as HTML prose in the detail panel (not structured cards — these sections are narrative guides).

| ID | Title | Source |
|----|-------|--------|
| `00_welcome` | Welcome | `00_welcome.md` |
| `02_tasks` | Tasks | `02_tasks.md` |
| `03_performance` | Performance | `03_performance.md` |
| `04_email` | Email | `04_email.md` |
| `05_focus` | Focus | `05_focus.md` |
| `06_pipeline` | Pipeline | `06_pipeline.md` |
| `07_notebook` | Notebook | `07_notebook.md` |
| `08_config` | Config | `08_config.md` |

> Note: `01_data_studio` and `01c_ml_studio` overview content is folded into the ML Predict category header. `01b_sql_obsidian` and `01d_snippets` are kept as-is.

---

### 📊 Kiểm định thống kê

These are wiki reference entries — they document methods for the planned `modules/ml_pipeline/statistical_tests.py` (currently stub, referenced in `ml_studio.py:1087`).

**Group: Tham số (Parametric)**

| ID | Title | Key use case |
|----|-------|-------------|
| `ttest_ind` | T-test độc lập | So sánh 2 nhóm: HCM vs HN |
| `ttest_paired` | T-test cặp đôi | Trước vs sau campaign |
| `anova_oneway` | One-Way ANOVA | GMV của ≥3 region |
| `anova_twoway` | Two-Way ANOVA | Brand × Region interaction |
| `pearson` | Pearson Correlation | GMV vs chi phí quảng cáo |

**Group: Phi tham số (Non-parametric)**

| ID | Title | Key use case |
|----|-------|-------------|
| `mannwhitney` | Mann-Whitney U | So sánh 2 nhóm, data lệch |
| `kruskal` | Kruskal-Wallis | ≥3 nhóm, không chuẩn |
| `chi_square` | Chi-square | Tỉ lệ mua theo nhóm khách |
| `spearman` | Spearman Correlation | Rank correlation, outlier nhiều |

Each entry uses the Structured Cards detail panel with FMCG case from VitaDairy domain (ColosBaby, Calokid, region/channel/GMV fields).

---

### 🤖 ML Dự đoán

Documents algorithms already implemented in `modules/ml_pipeline/`.

**Group: Supervised**

| ID | Algo | Trainer |
|----|------|---------|
| `xgboost` | XGBoost | `supervised_trainer.py` |
| `random_forest` | Random Forest | `supervised_trainer.py` |
| `svm` | SVM | `supervised_trainer.py` |
| `mlp` | MLP Neural Network | `supervised_trainer.py` |

**Group: Time Series**

| ID | Algo | Trainer |
|----|------|---------|
| `sarimax` | SARIMAX | `timeseries_trainer.py` |
| `exp_smoothing` | Exponential Smoothing | `timeseries_trainer.py` |
| `prophet` | Prophet | `timeseries_trainer.py` |

**Group: Clustering**

| ID | Algo | Trainer |
|----|------|---------|
| `kmeans` | KMeans | `unsupervised_trainer.py` |
| `dbscan` | DBSCAN | `unsupervised_trainer.py` |
| `hierarchical` | Hierarchical | `unsupervised_trainer.py` |

Each entry uses Structured Cards: Khi nào dùng / Fields cần / Output / Điều kiện / FMCG Case / Business Value.

---

### 📚 Reference

| ID | Title | Source |
|----|-------|--------|
| `90_glossary` | Glossary | `90_glossary.md` |
| `91_shortcuts` | Shortcuts & Tips | `91_shortcuts.md` |

---

## HTML/CSS/JS Implementation

### Rendering pipeline

```python
# modules/dictionary.py

def build_wiki_html(sections: list[dict], md_contents: dict[str, str]) -> str:
    """
    sections     — from dictionary_data.SECTIONS
    md_contents  — {md_file_id: html_string} for App Guide .md files
    Returns complete HTML document string.
    """
    js_data = json.dumps({"sections": sections, "md": md_contents})
    return HTML_TEMPLATE.replace("__WIKI_DATA__", js_data)

def render_dictionary_tab() -> None:
    from modules.dictionary_data import SECTIONS
    md_contents = _load_md_files(SECTIONS)
    html = build_wiki_html(SECTIONS, md_contents)
    # height=900 fills the tab area; inner columns scroll independently via CSS overflow-y:auto
    st.components.v1.html(html, height=900, scrolling=False)
```

### HTML template structure

```
<!DOCTYPE html>
<html>
<head>
  <style> /* all CSS inline — dark theme matching app */ </style>
</head>
<body>
  <div id="app">
    <div id="search-bar">...</div>
    <div id="main">
      <nav id="col-tree">...</nav>
      <nav id="col-list">...</nav>
      <main id="col-detail">...</main>
    </div>
  </div>
  <script>
    const WIKI = __WIKI_DATA__;   // injected by Python
    // navigation logic, search, render functions
  </script>
</body>
</html>
```

### JS behaviour (no external dependencies)

- `selectCategory(cat)` — filters `WIKI.sections` by category, renders col-list
- `selectSection(id)` — renders detail panel for that section id
- `search(query)` — filters by title + tags, highlights matches, updates col-list
- URL hash sync: `#section-id` so browser back/forward works within iframe (optional — implement only if trivial)
- App Guide sections render `.md` content (pre-converted to HTML by Python's `markdown` lib — already in requirements via `streamlit`)
- Stat/ML sections render Structured Cards from data fields

### CSS design tokens (match existing app)

```css
--bg-0: #0d1117;     /* page background */
--bg-1: #161b22;     /* card background */
--bg-2: #21262d;     /* border / divider */
--text-0: #e6edf3;   /* primary text */
--text-1: #c9d1d9;   /* body text */
--text-2: #8b949e;   /* secondary text */
--accent: #00d4ff;   /* active / highlight */
--green: #3fb950;    /* business value */
--orange: #e6862a;   /* warning */
--font-mono: 'JetBrains Mono', monospace;
```

---

## Files Changed

| File | Action | Notes |
|------|--------|-------|
| `modules/dictionary.py` | Full rewrite | Renders `st.components.v1.html()` |
| `modules/dictionary_data.py` | Create | All wiki content as Python list of dicts |
| `app.py` | No change | `render_dictionary_tab()` signature unchanged |
| `docs/dictionary/content/vn/*.md` | Read-only | Existing files loaded by Python, not modified |
| `tests/test_dictionary.py` | Update | Tests for `build_wiki_html()`, `_filter_sections()` equivalents |

---

## Out of Scope

- `modules/ml_pipeline/statistical_tests.py` — separate task; Dictionary only documents the methods
- EN translation of new stat/ML content — VN only for now
- Streamlit session state sync from iframe — not needed; wiki is read-only reference
- Dark/light theme toggle — dark only, matches app
