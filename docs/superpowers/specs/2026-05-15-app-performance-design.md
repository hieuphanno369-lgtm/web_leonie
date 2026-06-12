# App Performance & Navigation Design Spec
**Date:** 2026-05-15
**Author:** Leonie (VitaDairy DA)
**Status:** Approved by user

---

## Overview

Three coordinated improvements to the Task Tracker Streamlit app:

1. **Navigation cleanup** — Remove SQL → Obsidian from DATA STUDIO, reorder sub-tabs
2. **Tab lag fix** — Apply `@st.fragment` to heavy render functions to prevent full-page reruns
3. **ML Studio performance** — Cache file parsing + EDA results, sample large datasets for charts, improve training UX

---

## Scope

- `app.py` — fragment decorators, tab reorder, SQL→Obsidian removal
- `modules/ml_studio.py` — file cache, EDA cache, chart sampling, training UX
- No changes to: `modules/sql_analyzer.py` (kept on disk, just not imported), any data files, other modules

---

## Section 1: Navigation Cleanup

### DATA STUDIO sub-navigation

**Before:**
```
◈ DATA EXPLORER  |  ⬡ SQL → OBSIDIAN  |  ⚗ ML STUDIO  |  ⌥ SQL SNIPPETS
```

**After:**
```
⚗ ML STUDIO  |  ◈ DATA EXPLORER  |  ⌥ SQL SNIPPETS
```

**Changes:**
- Remove `"⬡ SQL → OBSIDIAN"` from the `st.radio()` options list in `render_data_studio_tab()`
- Remove the `elif ds_view == "⬡ SQL → OBSIDIAN": render_sql_tab()` branch
- Delete `render_sql_tab()` function from `app.py` (~60 lines, around line 1358)
- Delete its `section_header()` call and all SQL→Obsidian UI code
- `modules/sql_analyzer.py` is **not deleted** — left on disk for safety
- Default view becomes `"⚗ ML STUDIO"` (first in list)

---

## Section 2: Tab Lag Fix — `@st.fragment`

### Problem

`st.tabs()` renders all 10 tab functions simultaneously. Every widget interaction anywhere on the page triggers a full rerun of all 10 render functions, even unrelated ones.

### Solution

Apply `@st.fragment` decorator to the 6 heaviest render functions. Interactions inside a fragment only rerun that fragment — other tabs stay idle.

```python
@st.fragment
def render_data_studio_tab():
    ...
```

### Tabs to fragment

| Render Function | Reason |
|----------------|--------|
| `render_data_studio_tab` | ML Studio file I/O, EDA, file uploader |
| `render_notebook_tab` | Project Log, Meeting Notes, AI calls |
| `render_tasks_tab` | JSON I/O, task filtering, session state |
| `render_analytics_tab` | Charts, metric computation |
| `render_email_tab` | Outlook reader, AI classify/summarize |
| `render_pipeline_tab` | Pipeline orchestration logic |

### Tabs NOT fragmented (lightweight)

`render_focus_tab`, `render_dictionary_tab`, `render_ai_agent`, `render_settings_tab`

### Technical notes

- Session state remains global — fragments share the same `st.session_state`
- `st.rerun()` inside a fragment triggers a full-page rerun (e.g., after saving a task)
- `@st.fragment` is stable in Streamlit 1.37+ (current: 1.57 ✓)

---

## Section 3: ML Studio Performance

### 3a. Cache file parsing

**Problem:** Every Streamlit rerender re-reads and re-parses the uploaded file from scratch.

**Fix:** Wrap the file loading logic in a `@st.cache_data` function keyed on file bytes + filename. Streamlit auto-hashes the bytes — if the file hasn't changed, the cached DataFrame is returned instantly.

```python
@st.cache_data(show_spinner=False)
def _cached_load_dataframe(file_bytes: bytes, filename: str) -> pl.DataFrame:
    if filename.endswith(".csv"):
        return pl.read_csv(io.BytesIO(file_bytes))
    elif filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))
    elif filename.endswith(".parquet"):
        return pl.read_parquet(io.BytesIO(file_bytes))
    raise ValueError(f"Unsupported format: {filename}")
```

The cached function lives in `modules/ml_studio.py`. The upload handler passes `uploaded_file.getvalue()` (bytes) and `uploaded_file.name` as cache keys.

### 3b. Cache EDA results

**Problem:** Statistical profiling (describe, null counts, dtype analysis) on 500k rows is slow and re-computed on every rerender.

**Fix:** Wrap EDA computation in a separate `@st.cache_data` function keyed on file bytes + filename. Computed once per file, reused on subsequent reruns.

```python
@st.cache_data(show_spinner=False)
def _cached_eda(file_bytes: bytes, filename: str) -> dict:
    df = _cached_load_dataframe(file_bytes, filename)
    return {
        "shape": df.shape,
        "nulls": df.null_count(),
        "describe": df.describe(),
        "dtypes": {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
    }
```

### 3c. Chart sampling for large datasets

**Rule:** Stats (mean, std, null count, shape, describe) always use **full data** for accuracy. Charts/histograms/scatter plots use a **50k-row random sample** when the dataset exceeds 50k rows.

```python
CHART_SAMPLE_SIZE = 50_000

def _get_chart_df(df: pl.DataFrame) -> tuple[pl.DataFrame, bool]:
    """Returns (df_for_charts, was_sampled)."""
    if len(df) > CHART_SAMPLE_SIZE:
        return df.sample(CHART_SAMPLE_SIZE, seed=42), True
    return df, False
```

When sampled, show an info note below the chart:
```
ℹ️ Chart hiển thị 50,000 / 523,441 dòng (sampled). Stats ở trên tính trên full data.
```

### 3d. Training UX for large files

**Problem:** Training on 500-600k rows can take minutes with no feedback.

**Changes:**
- Show `st.progress()` + elapsed time during training (already partially implemented — enhance to show elapsed seconds updating live)
- Before starting training, display: `"⚠️ Dataset lớn: {N:,} dòng — ước tính ~X giây. Training full data."`
- For datasets > 200k rows: offer a **subsample option** via checkbox before training:
  ```
  ☐ Train nhanh trên 50k dòng (kết quả tham khảo — nhanh hơn ~10x)
  ```
  If checked: subsample to 50k rows, show badge `[SAMPLED 50k]` on results
  If unchecked: train on full data (default)

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Fragment raises exception | Only that tab shows error, others unaffected |
| File format unsupported in cache fn | Raise `ValueError` — caught by ML Studio's existing error handler |
| EDA cache miss (first load) | Show `st.spinner("Đang phân tích...")` while computing |
| Training on full 600k rows | User-visible progress bar + elapsed time; subsample option offered |
| `st.cache_data` memory pressure | Streamlit auto-evicts LRU; no manual handling needed |

---

## Out of Scope

- Changing the 10 main tab icons or labels
- Adding new features to Data Explorer or ML Studio
- Removing `modules/sql_analyzer.py` from disk
- Multi-file upload support
- Persistent caching across app restarts (session cache only)
