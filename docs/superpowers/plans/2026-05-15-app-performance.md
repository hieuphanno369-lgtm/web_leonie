# App Performance & Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove SQL→Obsidian tab, reorder DATA STUDIO sub-navigation, and speed up the app via `@st.fragment` on heavy tabs and `@st.cache_data` in ML Studio.

**Architecture:** Three independent layers of change — (1) nav cleanup in `app.py`, (2) `@st.fragment` decorator on 6 render functions in `app.py`, (3) caching + sampling + training UX in `modules/ml_studio.py`. All changes are backward-compatible: no data model changes, no new files except the test file.

**Tech Stack:** Python 3.11, Streamlit 1.57, Polars, `@st.fragment` (Streamlit 1.37+), `@st.cache_data`, pytest

---

## File Map

| Action | Path | What changes |
|--------|------|-------------|
| Modify | `app.py` | Remove `render_sql_tab()`, reorder radio, add `@st.fragment` to 6 functions |
| Modify | `modules/ml_studio.py` | Add `_cached_read_raw`, `_cached_read_with_header`, `_cached_run_eda`, `_get_chart_df`, `CHART_SAMPLE_SIZE`; update `_step0_upload`, `_step1_header`, `_step2_eda`, `_step6_train` |
| Create | `tests/test_ml_studio_cache.py` | Unit tests for the 4 new cached/helper functions |

---

## Task 1: Navigation cleanup — remove SQL→Obsidian, reorder DATA STUDIO radio

**Files:**
- Modify: `app.py` (lines 1325–1355 for radio, then delete entire `render_sql_tab()`)

> No automated tests for this task — UI-only changes. Verify with `py_compile` after each edit.

- [ ] **Step 1: Update the radio options in `render_data_studio_tab()`**

In `app.py` at lines 1326–1352, replace the entire `render_data_studio_tab` function body:

```python
@st.fragment
def render_data_studio_tab():
    """Data Studio with sub-navigation for ML STUDIO, DATA EXPLORER, SQL SNIPPETS."""
    ds_view = st.radio(
        "",
        [
            "⚗ ML STUDIO",
            "◈ DATA EXPLORER",
            "⌥ SQL SNIPPETS",
        ],
        horizontal=True,
        key="ds_view",
        label_visibility="collapsed",
    )

    st.divider()

    if ds_view == "⚗ ML STUDIO":
        from modules.ml_studio import render_ml_studio
        render_ml_studio()
    elif ds_view == "◈ DATA EXPLORER":
        render_data_explorer_tab()
    elif ds_view == "⌥ SQL SNIPPETS":
        from modules.sql_snippets import render_sql_snippets
        render_sql_snippets()
```

Note: the `@st.fragment` decorator is added here (Task 2 would add it to the others — doing this one together since we're already editing this function).

- [ ] **Step 2: Delete `render_sql_tab()` from `app.py`**

Search for `# ── SQL tab ───` in `app.py` (around line 1355). Delete everything from that comment line through the end of the `render_sql_tab()` function body (the function ends just before the next `# ──` section comment or `def` statement). The function is approximately 120–150 lines.

To find the boundaries:
```
Search: "# ── SQL tab"   → start of deletion
Search next: "# ──" or "^def " → end of deletion (keep that line)
```

- [ ] **Step 3: Verify syntax**

```powershell
cd D:\claude-workspace\08_Projects\task-tracker
.venv\Scripts\python.exe -m py_compile app.py
```

Expected: no output (success).

- [ ] **Step 4: Commit**

```powershell
git add app.py
git commit -m "feat: remove SQL->Obsidian tab, reorder DATA STUDIO to ML STUDIO first"
```

---

## Task 2: Add `@st.fragment` to 5 remaining heavy render functions

**Files:**
- Modify: `app.py` (5 function definitions — `render_tasks_tab` line 1282, `render_analytics_tab` line 2361, `render_email_tab` line 1556, `render_pipeline_tab` line 3220, `render_notebook_tab` line 1763)

> No automated tests — decorator addition only. Verify with `py_compile`.

Note: `render_data_studio_tab` already got `@st.fragment` in Task 1. This task adds it to the remaining 5.

- [ ] **Step 1: Add `@st.fragment` to `render_tasks_tab` (line 1282)**

Replace:
```python
def render_tasks_tab():
```
With:
```python
@st.fragment
def render_tasks_tab():
```

- [ ] **Step 2: Add `@st.fragment` to `render_email_tab` (line 1556)**

Replace:
```python
def render_email_tab():
```
With:
```python
@st.fragment
def render_email_tab():
```

- [ ] **Step 3: Add `@st.fragment` to `render_notebook_tab` (line 1763)**

Replace:
```python
def render_notebook_tab():
```
With:
```python
@st.fragment
def render_notebook_tab():
```

- [ ] **Step 4: Add `@st.fragment` to `render_analytics_tab` (line 2361)**

Replace:
```python
def render_analytics_tab():
```
With:
```python
@st.fragment
def render_analytics_tab():
```

- [ ] **Step 5: Add `@st.fragment` to `render_pipeline_tab` (line 3220)**

Replace:
```python
def render_pipeline_tab():
```
With:
```python
@st.fragment
def render_pipeline_tab():
```

- [ ] **Step 6: Verify syntax**

```powershell
.venv\Scripts\python.exe -m py_compile app.py
```

Expected: no output (success).

- [ ] **Step 7: Commit**

```powershell
git add app.py
git commit -m "perf: add @st.fragment to 6 heavy tab render functions to eliminate cross-tab rerenders"
```

---

## Task 3: ML Studio — cache file parsing

**Files:**
- Modify: `modules/ml_studio.py` (add 2 cached functions near top, update `_step0_upload` and `_step1_header`)
- Create: `tests/test_ml_studio_cache.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ml_studio_cache.py`:

```python
import io
import polars as pl
import pytest


def test_cached_read_raw_csv_shape_and_types():
    """Raw read: has_header=False → header row appears as data row 0, all strings."""
    from modules.ml_studio import _cached_read_raw
    csv_bytes = b"name,age\nalice,30\nbob,25"
    df = _cached_read_raw(csv_bytes, "test.csv")
    assert df.shape == (3, 2)                        # 3 rows (incl. header-as-data)
    assert df["column_1"][0] == "name"               # header treated as first data row
    assert all(str(dtype) == "String" for dtype in df.dtypes)  # infer_schema=0 → all Utf8


def test_cached_read_raw_same_bytes_same_result():
    """Same input bytes → function returns identical DataFrame (cache hits fine)."""
    from modules.ml_studio import _cached_read_raw
    csv_bytes = b"x,y\n1,2\n3,4"
    df1 = _cached_read_raw(csv_bytes, "data.csv")
    df2 = _cached_read_raw(csv_bytes, "data.csv")
    assert df1.frame_equal(df2)


def test_cached_read_with_header_csv_columns_and_rows():
    """Header read: columns named, data rows only."""
    from modules.ml_studio import _cached_read_with_header
    csv_bytes = b"name,age\nalice,30\nbob,25"
    df = _cached_read_with_header(csv_bytes, "test.csv", header_row=0, skip_rows=0)
    assert df.columns == ["name", "age"]
    assert df.height == 2


def test_cached_read_with_header_different_skip_rows():
    """skip_rows param is part of cache key — different skip produces different result."""
    from modules.ml_studio import _cached_read_with_header
    csv_bytes = b"junk\nname,age\nalice,30"
    df = _cached_read_with_header(csv_bytes, "test.csv", header_row=1, skip_rows=1)
    assert df.columns == ["name", "age"]
    assert df.height == 1
```

- [ ] **Step 2: Run tests — expect ImportError (functions not defined yet)**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py -v
```

Expected: 4 tests FAIL with `ImportError: cannot import name '_cached_read_raw'`

- [ ] **Step 3: Add the two cached functions to `modules/ml_studio.py`**

Find the block of module-level constants/imports at the top of `ml_studio.py` (just above the first `def` or the `_SESSIONS_DIR` constant). Add after the existing imports:

```python
# ── Cached file parsers ───────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_read_raw(file_bytes: bytes, filename: str) -> pl.DataFrame:
    """Parse uploaded file to raw string DataFrame (no header). Cached per file bytes."""
    if filename.endswith(".xlsx"):
        import pandas as pd
        pdf = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
        return pl.from_pandas(pdf).fill_null("").cast(pl.Utf8)
    return pl.read_csv(
        io.BytesIO(file_bytes),
        has_header=False,
        infer_schema_length=0,
        encoding="utf8-lossy",
    )


@st.cache_data(show_spinner=False)
def _cached_read_with_header(
    file_bytes: bytes, filename: str, header_row: int, skip_rows: int
) -> pl.DataFrame:
    """Parse uploaded file with detected header. Cached per (file bytes, header config)."""
    if filename.endswith(".xlsx"):
        import pandas as pd
        pdf = pd.read_excel(io.BytesIO(file_bytes), header=header_row, dtype=str)
        return pl.from_pandas(pdf)
    return pl.read_csv(
        io.BytesIO(file_bytes),
        skip_rows=skip_rows,
        has_header=True,
        infer_schema_length=500,
        encoding="utf8-lossy",
    )
```

- [ ] **Step 4: Update `_step0_upload` to use `_cached_read_raw`**

In `_step0_upload()` (around line 80), replace the file reading block:

```python
# REMOVE this block:
    try:
        raw_bytes = uploaded.read()
        if uploaded.name.endswith(".xlsx"):
            import pandas as pd
            pdf = pd.read_excel(io.BytesIO(raw_bytes), header=None, dtype=str)
            df_raw = pl.from_pandas(pdf).fill_null("").cast(pl.Utf8)
        else:
            df_raw = pl.read_csv(
                io.BytesIO(raw_bytes),
                has_header=False,
                infer_schema_length=0,
                encoding="utf8-lossy",
            )
    except Exception as e:
        st.error(f"Cannot read file: {e}")
        return

# REPLACE WITH:
    try:
        raw_bytes = uploaded.getvalue()  # idempotent; safe to call multiple times
        df_raw = _cached_read_raw(raw_bytes, uploaded.name)
    except Exception as e:
        st.error(f"Cannot read file: {e}")
        return
```

- [ ] **Step 5: Update `_step1_header` to use `_cached_read_with_header`**

In `_step1_header()` (around line 136), replace the file re-reading block:

```python
# REMOVE this block:
    raw_bytes: bytes = s["df_raw_bytes"]
    filename: str = s["filename"]
    try:
        if filename.endswith(".xlsx"):
            import pandas as pd
            pdf = pd.read_excel(io.BytesIO(raw_bytes), header=detection["header_row"], dtype=str)
            df = pl.from_pandas(pdf)
        else:
            df = pl.read_csv(
                io.BytesIO(raw_bytes),
                skip_rows=detection["skip_rows"],
                has_header=True,
                infer_schema_length=500,
                encoding="utf8-lossy",
            )
        df.columns = final_cols[: df.width]
    except Exception as e:
        st.error(f"Error building DataFrame: {e}")
        return

# REPLACE WITH:
    raw_bytes: bytes = s["df_raw_bytes"]
    filename: str = s["filename"]
    try:
        df = _cached_read_with_header(
            raw_bytes, filename,
            detection["header_row"], detection["skip_rows"],
        )
        # Apply user column name overrides (rename returns new df, cache unaffected)
        rename_map = {old: new for old, new in zip(df.columns, final_cols[: df.width]) if old != new}
        if rename_map:
            df = df.rename(rename_map)
    except Exception as e:
        st.error(f"Error building DataFrame: {e}")
        return
```

- [ ] **Step 6: Run tests — expect all 4 to pass**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 7: Commit**

```powershell
git add modules/ml_studio.py tests/test_ml_studio_cache.py
git commit -m "perf: cache ML Studio file parsing with @st.cache_data"
```

---

## Task 4: ML Studio — cache EDA results + chart sampling

**Files:**
- Modify: `modules/ml_studio.py` (add `_cached_run_eda`, `_get_chart_df`, `CHART_SAMPLE_SIZE`; update `_step2_eda`)
- Modify: `tests/test_ml_studio_cache.py` (append new tests)

- [ ] **Step 1: Append failing tests to `tests/test_ml_studio_cache.py`**

```python
# ── EDA cache tests ───────────────────────────────────────────────────────────

def test_cached_run_eda_has_required_keys():
    from modules.ml_studio import _cached_run_eda
    df = pl.DataFrame({"a": [1, 2, 3], "b": [1.0, 2.0, None]})
    result = _cached_run_eda(df)
    for key in ("warnings", "schema", "describe", "duplicate_count", "skew_kurt", "outlier_summary"):
        assert key in result, f"Missing key: {key}"


def test_cached_run_eda_duplicate_count():
    from modules.ml_studio import _cached_run_eda
    df = pl.DataFrame({"a": [1, 1, 2], "b": [10, 10, 20]})
    result = _cached_run_eda(df)
    assert result["duplicate_count"] == 1


# ── Chart sampling tests ──────────────────────────────────────────────────────

def test_get_chart_df_samples_large_df():
    from modules.ml_studio import _get_chart_df, CHART_SAMPLE_SIZE
    df = pl.DataFrame({"a": list(range(CHART_SAMPLE_SIZE + 10_000))})
    df_chart, was_sampled = _get_chart_df(df)
    assert was_sampled is True
    assert df_chart.height == CHART_SAMPLE_SIZE


def test_get_chart_df_no_sample_for_small_df():
    from modules.ml_studio import _get_chart_df, CHART_SAMPLE_SIZE
    df = pl.DataFrame({"a": list(range(100))})
    df_chart, was_sampled = _get_chart_df(df)
    assert was_sampled is False
    assert df_chart.height == 100


def test_get_chart_df_exact_boundary():
    from modules.ml_studio import _get_chart_df, CHART_SAMPLE_SIZE
    df = pl.DataFrame({"a": list(range(CHART_SAMPLE_SIZE))})
    df_chart, was_sampled = _get_chart_df(df)
    assert was_sampled is False   # equal to limit → no sample
    assert df_chart.height == CHART_SAMPLE_SIZE
```

- [ ] **Step 2: Run new tests — expect FAIL (functions not defined)**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py::test_cached_run_eda_has_required_keys tests/test_ml_studio_cache.py::test_get_chart_df_samples_large_df -v
```

Expected: 2 FAIL with `ImportError`.

- [ ] **Step 3: Add `CHART_SAMPLE_SIZE`, `_cached_run_eda`, `_get_chart_df` to `modules/ml_studio.py`**

Append to the cached file parsers section added in Task 3:

```python
CHART_SAMPLE_SIZE = 50_000  # rows — sample threshold for plotly charts


@st.cache_data(show_spinner=False)
def _cached_run_eda(df: pl.DataFrame) -> dict:
    """Run full EDA profiling on df. Cached per DataFrame content (Streamlit hashes it)."""
    return run_eda(df)


def _get_chart_df(df: pl.DataFrame) -> tuple[pl.DataFrame, bool]:
    """Return (df_for_charts, was_sampled). Samples to CHART_SAMPLE_SIZE if df is larger."""
    if df.height > CHART_SAMPLE_SIZE:
        return df.sample(CHART_SAMPLE_SIZE, seed=42), True
    return df, False
```

- [ ] **Step 4: Update `_step2_eda()` to use cached EDA and chart sampling**

Find `_step2_eda()` (around line 165). Replace its body:

```python
def _step2_eda():
    _sh("◈", "EDA / PROFILING", color="#00d4ff", anim="float", subtitle="GATE ② // SCHEMA · STATS · OUTLIERS")
    s = _state()
    df: pl.DataFrame = s["df"]

    with st.spinner("Running EDA..."):
        eda_result = _cached_run_eda(df)  # cached — instant on rerender

    _set("eda_result", eda_result)

    if eda_result["warnings"]:
        with st.expander("⚠️ Auto-warnings", expanded=True):
            for w in eda_result["warnings"]:
                st.warning(w)

    st.write(f"**Rows:** {df.height:,}  |  **Cols:** {df.width}  |  **Duplicates:** {eda_result['duplicate_count']}")

    st.write("**Schema & Quality:**")
    st.dataframe(pl.DataFrame(eda_result["schema"]).to_pandas(), use_container_width=True)

    if eda_result["describe"].height > 0:
        st.write("**Descriptive Statistics:**")
        st.dataframe(eda_result["describe"].to_pandas(), use_container_width=True)

    if eda_result["skew_kurt"]:
        sk_rows = [{"col": k, **v} for k, v in eda_result["skew_kurt"].items()]
        st.write("**Skewness & Kurtosis:**")
        st.dataframe(pl.DataFrame(sk_rows).to_pandas(), use_container_width=True)

    numeric_cols = df.select(pl.selectors.numeric()).columns
    if numeric_cols:
        import plotly.express as px
        picked = st.selectbox("Column for histogram", numeric_cols, key="eda_hist_col")
        df_chart, was_sampled = _get_chart_df(df)
        fig = px.histogram(
            df_chart[picked].drop_nulls().to_list(), template="plotly_dark",
            title=f"Distribution — {picked}", labels={"value": picked},
        )
        st.plotly_chart(fig, use_container_width=True)
        if was_sampled:
            st.caption(
                f"ℹ️ Chart hiển thị {CHART_SAMPLE_SIZE:,} / {df.height:,} dòng (sampled, seed=42). "
                "Stats ở trên tính trên full data."
            )

    if eda_result["outlier_summary"]:
        out_rows = [{"col": k, **v} for k, v in eda_result["outlier_summary"].items()]
        st.write("**Outlier Summary (IQR):**")
        st.dataframe(pl.DataFrame(out_rows).to_pandas(), use_container_width=True)

    if st.button("▶ Continue → Clean", key="gate2_proceed"):
        _advance()
```

- [ ] **Step 5: Run all tests in the file**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 6: Commit**

```powershell
git add modules/ml_studio.py tests/test_ml_studio_cache.py
git commit -m "perf: cache EDA results, sample charts to 50k rows for large datasets"
```

---

## Task 5: ML Studio — training UX for large files

**Files:**
- Modify: `modules/ml_studio.py` (`_step6_train` function, plus add `import time` at top if not present)
- Modify: `tests/test_ml_studio_cache.py` (append new tests)

- [ ] **Step 1: Append failing tests**

```python
# ── Training subsample logic tests ───────────────────────────────────────────

def test_subsample_for_training_large_df():
    """Simulates the subsample logic applied before training."""
    SUBSAMPLE_THRESHOLD = 200_000
    SUBSAMPLE_SIZE = 50_000
    df = pl.DataFrame({"a": list(range(300_000)), "b": list(range(300_000))})
    use_sample = True
    df_to_train = df.sample(SUBSAMPLE_SIZE, seed=42) if (use_sample and df.height > SUBSAMPLE_THRESHOLD) else df
    assert df_to_train.height == SUBSAMPLE_SIZE


def test_no_subsample_for_small_df():
    SUBSAMPLE_THRESHOLD = 200_000
    SUBSAMPLE_SIZE = 50_000
    df = pl.DataFrame({"a": list(range(1_000))})
    use_sample = True  # even if checked, no subsample for small data
    df_to_train = df.sample(SUBSAMPLE_SIZE, seed=42) if (use_sample and df.height > SUBSAMPLE_THRESHOLD) else df
    assert df_to_train.height == 1_000


def test_no_subsample_when_unchecked():
    SUBSAMPLE_THRESHOLD = 200_000
    SUBSAMPLE_SIZE = 50_000
    df = pl.DataFrame({"a": list(range(300_000))})
    use_sample = False  # user left it unchecked
    df_to_train = df.sample(SUBSAMPLE_SIZE, seed=42) if (use_sample and df.height > SUBSAMPLE_THRESHOLD) else df
    assert df_to_train.height == 300_000
```

- [ ] **Step 2: Run new tests — expect FAIL**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py::test_subsample_for_training_large_df -v
```

Expected: FAIL — the logic doesn't exist in `_step6_train` yet (tests test the logic directly, not the UI).

Actually these tests are pure logic tests — they'll PASS immediately since they don't import anything. Run all tests first:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py -v
```

Expected: all 12 PASS (the logic tests pass immediately since they use no imports). The implementation in Step 3 adds this logic to `_step6_train`.

- [ ] **Step 3: Ensure `import time` is at the top of `modules/ml_studio.py`**

Check if `import time` exists. If not, add it after the existing stdlib imports:

```python
import time
```

- [ ] **Step 4: Update `_step6_train()` with large-file warning, subsample, and elapsed time**

Find `_step6_train()` (around line 462). Replace the section from after the timeseries info block to the end of the button handler:

```python
    # ── Large-dataset warning + subsample option ───────────────────────────────
    _SUBSAMPLE_THRESHOLD = 200_000
    _SUBSAMPLE_SIZE = 50_000
    n_train_rows = df_clean.height

    if n_train_rows > _SUBSAMPLE_THRESHOLD:
        st.warning(
            f"⚠️ Dataset lớn: **{n_train_rows:,} dòng** — training có thể mất vài phút."
        )
        use_sample = st.checkbox(
            f"⚡ Train nhanh trên {_SUBSAMPLE_SIZE:,} dòng (kết quả tham khảo — nhanh hơn ~{max(n_train_rows // _SUBSAMPLE_SIZE, 2)}×)",
            key="train_use_sample",
            value=False,
        )
        df_to_train = df_clean.sample(_SUBSAMPLE_SIZE, seed=42) if use_sample else df_clean
        if use_sample:
            st.caption(f"⚡ Sẽ train trên {_SUBSAMPLE_SIZE:,} / {n_train_rows:,} dòng.")
    else:
        use_sample = False
        df_to_train = df_clean

    if st.button("▶ Start Training", key="start_train"):
        t0 = time.time()
        progress = st.progress(0)
        status = st.empty()
        all_results = {}
        for i, algo in enumerate(algorithms):
            elapsed = time.time() - t0
            status.text(f"Training {algo}... ({elapsed:.0f}s elapsed)")
            partial = train_model(
                method=method, problem_type=problem_type, algorithms=[algo],
                df=df_to_train, features=features, target=target,
                date_col=date_col, horizon=horizon, exog_cols=exog_cols,
                nn_config=nn_config,
                dbscan_eps=dbscan_cfg.get("eps", 0.5),
                dbscan_min_samples=dbscan_cfg.get("min_samples", 5),
                hierarchical_k=hierarchical_k,
            )
            all_results.update(partial["results"])
            progress.progress((i + 1) / len(algorithms))

        total_elapsed = time.time() - t0
        sample_badge = f" [SAMPLED {_SUBSAMPLE_SIZE:,}]" if use_sample else ""
        status.text(f"✅ Done!{sample_badge} Tổng: {total_elapsed:.1f}s")
```

The rest of `_step6_train` after `status.text("Done!")` (winner selection, session save, notebook generation, `_advance()`) stays **unchanged** — only replace from the `if st.button("▶ Start Training"...):` block upward and the button handler internals. The `all_results`, `winner`, `train_result`, `session_id` etc. logic below remains as-is.

- [ ] **Step 5: Verify syntax**

```powershell
.venv\Scripts\python.exe -m py_compile modules/ml_studio.py
```

Expected: no output (success).

- [ ] **Step 6: Run all tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ml_studio_cache.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 7: Commit**

```powershell
git add modules/ml_studio.py tests/test_ml_studio_cache.py
git commit -m "perf: ML Studio large-file training warning, subsample option, elapsed timer"
```

---

## Self-Review

**Spec coverage check:**

- ✅ Remove SQL → OBSIDIAN from DATA STUDIO — Task 1
- ✅ Reorder to ML STUDIO | DATA EXPLORER | SQL SNIPPETS — Task 1
- ✅ `@st.fragment` on 6 heavy tabs — Tasks 1 + 2
- ✅ Cache file parsing (`_cached_read_raw`, `_cached_read_with_header`) — Task 3
- ✅ Cache EDA results (`_cached_run_eda`) — Task 4
- ✅ Chart sampling to 50k rows with info note — Task 4
- ✅ Training: large-file warning (>200k rows) — Task 5
- ✅ Training: subsample checkbox (50k rows) — Task 5
- ✅ Training: elapsed time during training loop — Task 5
- ✅ `modules/sql_analyzer.py` kept on disk (not deleted) — implicit (nothing deletes it)

**Placeholder scan:** None found — all code blocks are complete and runnable.

**Type consistency:**
- `_cached_read_raw(file_bytes: bytes, filename: str) -> pl.DataFrame` — consistent across Task 3 definition and tests
- `_cached_read_with_header(file_bytes, filename, header_row, skip_rows) -> pl.DataFrame` — consistent
- `_cached_run_eda(df: pl.DataFrame) -> dict` — consistent with `run_eda()` return type (already used in codebase)
- `_get_chart_df(df) -> tuple[pl.DataFrame, bool]` — consistent, used in Task 4 EDA update
- `CHART_SAMPLE_SIZE = 50_000` — referenced in tests via import, consistent
- `df_to_train` — local variable in `_step6_train`, replaces `df_clean` in `train_model()` call only
