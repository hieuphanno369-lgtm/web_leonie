# ML Studio Analytics Upgrade (Spec A) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ML Studio analysis trustworthy and time-aware — fix the correlation 500, add a shared time-grain engine powering chart period-comparisons (incl. YoY) and forecast-by-grain, add a column-profile + field-placement suggester, and guard cohort against meaningless (non-recurring) data.

**Architecture:** A new pure-Python analytics package (`backend/analytics/`) holds the time-grain aggregation/comparison math and the cohort-suitability check, unit-tested in isolation. Thin FastAPI endpoints in `backend/routers/ml.py` call into it; the React frontend gains grain/agg/comparison controls and a suggestions panel that consume the new endpoints. No new dependencies.

**Tech Stack:** FastAPI · Polars 1.40 · NumPy · scipy/statsmodels/scikit-learn (existing) · pytest (backend) — React 19 · Vite 6 · TypeScript · recharts · TailwindCSS (frontend, gate = `npm run build`).

---

## Delivery constraints (READ FIRST)

- **Work in the MAIN working tree:** `D:\assitant_tools\tools_performance\08_Projects\leonie` on branch **master**. The dev servers (Vite :5177, uvicorn :8000) read files from there — edits in a worktree never reach the running app. All paths below are relative to that root.
- **Commit locally to master. NEVER `git push`.** Master history contains real secrets; only the orphan `backup-clean` branch is ever pushed (out of scope here).
- **Backend tests:** `cd backend ; uv run pytest -q` (run from `backend/` so `main`, `database`, and the new `analytics` package are importable).
- **Frontend gate:** `cd frontend ; npm run build` (= `tsc -b && vite build`). There is **no** JS unit-test runner — the type-check/build plus a manual smoke is the gate for every frontend step.
- **Restart uvicorn after backend code changes** if `--reload` misses them (it watches `.py`, so usually fine).
- Each commit command includes the required co-author trailer.

## Comparison vocabulary (used throughout)

Comparison keys passed in `comparisons: list[str]`: `"yoy"` (year-over-year same sub-period), `"pop"` (period-over-period / previous bucket), `"rolling"` (trailing moving average), `"cumulative"` (running total, resets each year/quarter/month), `"index100"` (rebase first point = 100, optional), `"share"` (% of grand total, optional). Frontend default selection = `["yoy","pop","rolling","cumulative"]`.

## File Structure

| File | New/Modify | Responsibility |
|------|-----------|----------------|
| `backend/analytics/__init__.py` | Create | Marks `analytics` as a package. |
| `backend/analytics/timegrain.py` | Create | Pure time-grain aggregation + comparison math (Grain/Agg, `truncate_dates`, `aggregate_series`, `suggest_grain`, `add_comparisons`). |
| `backend/analytics/cohort_check.py` | Create | Pure cohort data-suitability check (`check_suitability`). |
| `backend/tests/test_timegrain.py` | Create | Unit tests for the engine. |
| `backend/tests/test_cohort_check.py` | Create | Unit tests for suitability. |
| `backend/tests/test_ml.py` | Modify | Endpoint tests (correlation, timeseries, forecast-grain, profile, cohort gate). |
| `backend/routers/ml.py` | Modify | Fix `/correlation`; add `/timeseries`, `/profile/{id}`; extend `/forecast` (+compare) with grain/agg; gate `/cohort`. |
| `frontend/src/types.ts` | Modify | Add `excluded_columns` to `CorrelationMatrix`; add `TimeseriesResult`, `ProfileColumn`/`ProfileResult`; extend `ForecastResult`. |
| `frontend/src/api/ml.ts` | Modify | Add `runTimeseries`, `fetchProfile`; extend `runForecast` (grain/agg); extend `CohortResult` + `runCohort` (period quarter/year). |
| `frontend/src/components/ml/CorrelationHeatmap.tsx` | Modify | Render an "excluded columns" note. |
| `frontend/src/components/ml/MlChartView.tsx` | Modify | Collapsible "Chuỗi thời gian" panel (grain/agg + YoY/PoP/rolling/cumulative, server-side via `dataset.columns`); "Gợi ý biểu đồ" recipe chips; suitability guard on its inline cohort. |
| `frontend/src/components/ml/MlForecastView.tsx` | Modify | Grain ▾ / Agg ▾ selectors wired into `runForecast`. |
| `frontend/src/components/ml/MlCohortView.tsx` | Modify | Render suitability block when `suitable=false`; period quarter/year. |
| `frontend/src/components/ml/CohortCompareView.tsx` | Modify | Guard panels against `suitable=false` responses. |
| `frontend/src/components/ml/cohortUtils.ts` | Modify | Extend `Period` with `'quarter' \| 'year'`. |

### Intentional deviations from the spec (functionality preserved)

The spec's file list anticipated a `Field-picker | SQL result` **mode toggle** plus two new components (`FieldPicker.tsx`, `RecipeCards.tsx`). This plan delivers the same capability **inline inside `MlChartView.tsx`** instead, because that matches the file's actual structure and is lower-risk (no toggle that hides the existing chart, fewer new files to keep in sync):

- **Charts time-grain + comparisons** → a collapsible **"Chuỗi thời gian"** panel appended below the existing chart (Task 4). The current SQL-result charting stays exactly as-is, so both data sources from the "Cả hai" decision are served: client-side charting of the query result **and** server-side full-dataset aggregation via `/timeseries`. No mode toggle, no `FieldPicker.tsx`.
- **Field-placement suggestions** → **"Gợi ý biểu đồ"** recipe chips rendered at the top of the same scroll container (Task 8), surface-aware (date+metric → time-series panel; ≥2 metrics → correlation; dimension+metric → client pickers when present in the result). No `RecipeCards.tsx`.
- **`index100` / `share` comparisons** are built and tested in the backend engine (Task 2) but the frontend ships only the four primary toggles `yoy/pop/rolling/cumulative`. The spec marks `index100`/`share` **optional**; they remain available server-side and can be surfaced with a small UI addition later.

All five spec components and their user-facing requirements are covered; only the frontend file decomposition differs.

---

## Task 1: Fix `/correlation` (Component 3 — ships first)

The live 500: a constant column → `scipy.pearsonr` returns NaN → Starlette serializes with `allow_nan=False` → HTTP 500. Also per-column independent `drop_nulls()` then `[:n]` slice misaligns rows. Fix: drop constant/all-null columns into `excluded_columns`, compute each pair on pairwise-complete rows, diagonal = 1.0, non-finite → `null`.

**Files:**
- Modify: `backend/routers/ml.py:429-454` (`get_correlation`)
- Test: `backend/tests/test_ml.py` (append)
- Modify: `frontend/src/types.ts:220-223` (`CorrelationMatrix`)
- Modify: `frontend/src/components/ml/CorrelationHeatmap.tsx` (add note)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml.py`:

```python
# ── Correlation matrix endpoint (Component 3) ──────────────────────────────
CORR_CONST_CSV = (
    b"x,y,flag\n"
    b"1,2,1\n2,4,1\n3,6,1\n4,8,1\n5,10,1\n"
)  # x,y perfectly correlated; flag constant -> excluded (used to 500)


def test_correlation_excludes_constant_column(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("corr.csv", io.BytesIO(CORR_CONST_CSV), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{up['file_id']}/correlation")
    assert resp.status_code == 200
    d = resp.json()
    assert "flag" not in d["columns"]
    assert {e["name"] for e in d["excluded_columns"]} == {"flag"}
    assert d["excluded_columns"][0]["reason"] == "constant"
    i = d["columns"].index("x")
    j = d["columns"].index("y")
    assert d["matrix"][i][i] == 1.0
    assert d["matrix"][i][j] == pytest.approx(1.0, abs=0.01)


def test_correlation_handles_nulls_pairwise(client):
    csv = b"a,b\n1,10\n2,\n3,30\n4,40\n,50\n"
    up = client.post(
        "/api/ml/upload",
        files={"file": ("corrn.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{up['file_id']}/correlation")
    assert resp.status_code == 200
    d = resp.json()
    assert d["matrix"][0][0] == 1.0  # diagonal always 1.0


def test_correlation_too_few_varying_columns(client):
    csv = b"k,c\n1,9\n2,9\n3,9\n"  # only k varies; c constant -> <2 usable
    up = client.post(
        "/api/ml/upload",
        files={"file": ("corr1.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{up['file_id']}/correlation")
    assert resp.status_code == 400
```

Confirm `import pytest` is present at the top of `test_ml.py` (add it if missing).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml.py -k correlation -q`
Expected: `test_correlation_excludes_constant_column` FAILS (currently 500), and the constant-handling assertions fail — the old endpoint has no `excluded_columns` key.

- [ ] **Step 3: Replace `get_correlation`**

In `backend/routers/ml.py` replace the whole function (lines 429-454):

```python
@router.get("/{file_id}/correlation")
def get_correlation(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])

    candidates = _numeric_cols(df)[:15]
    excluded: list[dict] = []
    cols: list[str] = []
    for c in candidates:
        s = df[c]
        if s.null_count() == len(s):
            excluded.append({"name": c, "reason": "all_null"})
        elif s.n_unique() <= 1:
            excluded.append({"name": c, "reason": "constant"})
        else:
            cols.append(c)

    if len(cols) < 2:
        raise HTTPException(
            400,
            "Cần ít nhất 2 cột số có biến thiên để tính tương quan "
            f"(đã loại {len(excluded)} cột hằng số/rỗng).",
        )

    matrix: list[list[float | None]] = []
    for c1 in cols:
        row_vals: list[float | None] = []
        for c2 in cols:
            if c1 == c2:
                row_vals.append(1.0)
                continue
            pair = df.select([c1, c2]).drop_nulls()          # pairwise-complete
            if pair.height < 3:
                row_vals.append(None)
                continue
            a = pair[c1].to_numpy()
            b = pair[c2].to_numpy()
            if a.std() == 0 or b.std() == 0:                 # guard NaN from pearsonr
                row_vals.append(None)
                continue
            try:
                r, _ = scipy_stats.pearsonr(a, b)
                row_vals.append(round(float(r), 4) if np.isfinite(r) else None)
            except Exception:
                row_vals.append(None)
        matrix.append(row_vals)

    return {"columns": cols, "matrix": matrix, "excluded_columns": excluded}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml.py -k correlation -q`
Expected: 3 passed.

- [ ] **Step 5: Add `excluded_columns` to the frontend type**

In `frontend/src/types.ts` replace the `CorrelationMatrix` interface (lines 220-223):

```typescript
export interface CorrelationMatrix {
  columns: string[]
  matrix: (number | null)[][]
  excluded_columns?: { name: string; reason: string }[]
}
```

- [ ] **Step 6: Render the excluded-columns note in the heatmap**

In `frontend/src/components/ml/CorrelationHeatmap.tsx`, after the closing of the SVG/grid container (just before the component's final `</div>` return), add:

```tsx
{data.excluded_columns && data.excluded_columns.length > 0 && (
  <p className="text-[10px] text-gray-500 mt-2">
    Đã loại {data.excluded_columns.length} cột không có biến thiên:{' '}
    {data.excluded_columns
      .map(e => `${e.name} (${e.reason === 'constant' ? 'hằng số' : 'rỗng'})`)
      .join(', ')}
  </p>
)}
```

- [ ] **Step 7: Verify the frontend builds**

Run: `cd frontend ; npm run build`
Expected: build succeeds, zero TS errors.

- [ ] **Step 8: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py frontend/src/types.ts frontend/src/components/ml/CorrelationHeatmap.tsx
git commit -m "fix(ml): correlation 500 — drop constant/null cols, pairwise-complete pearson" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Time-grain engine (Component 0 — foundation for Tasks 3 & 5)

Pure functions, no FastAPI/DB. Polars `dt.truncate` grain strings verified on a Date series: `1d` (identity), `1w` (→Monday), `1mo` (→1st), `1q` (→quarter-start), `1y` (→Jan-1).

**Files:**
- Create: `backend/analytics/__init__.py`
- Create: `backend/analytics/timegrain.py`
- Test: `backend/tests/test_timegrain.py`

- [ ] **Step 1: Create the package marker**

Create `backend/analytics/__init__.py`:

```python
"""Pure analytics helpers for ML Studio (no FastAPI / no DB)."""
```

- [ ] **Step 2: Write the failing unit tests**

Create `backend/tests/test_timegrain.py`:

```python
from datetime import date
import polars as pl
from analytics.timegrain import (
    truncate_dates, aggregate_series, suggest_grain, add_comparisons,
)


def _df(rows):
    return pl.DataFrame({"d": [r[0] for r in rows], "v": [r[1] for r in rows]})


def test_truncate_month_and_quarter():
    s = pl.Series("d", [date(2024, 2, 20), date(2024, 11, 5)])
    assert truncate_dates(s, "month").to_list() == [date(2024, 2, 1), date(2024, 11, 1)]
    assert truncate_dates(s, "quarter").to_list() == [date(2024, 1, 1), date(2024, 10, 1)]


def test_aggregate_series_monthly_sum():
    df = _df([
        (date(2024, 1, 5), 10), (date(2024, 1, 20), 20),
        (date(2024, 2, 10), 30), (date(2024, 2, 15), 5),
        (date(2024, 3, 1), 40),
    ])
    out = aggregate_series(df, "d", "v", "month", "sum")
    assert out["labels"] == ["2024-01", "2024-02", "2024-03"]
    assert out["values"] == [30.0, 35.0, 40.0]
    assert out["period_starts"][0] == date(2024, 1, 1)


def test_aggregate_drops_null_dates():
    df = pl.DataFrame({"d": [date(2024, 1, 1), None], "v": [5, 99]})
    out = aggregate_series(df, "d", "v", "month", "sum")
    assert out["values"] == [5.0]


def test_suggest_grain_picks_month_for_two_years():
    g = suggest_grain(date(2022, 1, 1), date(2024, 6, 6))  # ~887 days
    assert g == "month"


def test_suggest_grain_day_for_short_span():
    assert suggest_grain(date(2024, 1, 1), date(2024, 1, 5)) == "day"


def test_add_comparisons_pop_and_yoy():
    starts = [date(2023, 1, 1), date(2023, 2, 1), date(2024, 1, 1), date(2024, 2, 1)]
    vals = [100.0, 200.0, 150.0, 180.0]
    out = add_comparisons(starts, vals, "month", ["pop", "yoy"])
    assert out["pop"]["values"] == [None, 100.0, 200.0, 150.0]
    assert out["yoy"]["values"] == [None, None, 100.0, 200.0]
    assert out["yoy"]["delta_pct"] == [None, None, 50.0, -10.0]


def test_add_comparisons_rolling_and_cumulative():
    starts = [date(2024, m, 1) for m in range(1, 5)]
    vals = [10.0, 20.0, 30.0, 40.0]
    out = add_comparisons(starts, vals, "month", ["rolling", "cumulative"],
                          rolling_window=2, cumulative_reset="year")
    assert out["rolling"]["window"] == 2
    assert out["rolling"]["values"] == [10.0, 15.0, 25.0, 35.0]
    assert out["cumulative"]["values"] == [10.0, 30.0, 60.0, 100.0]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_timegrain.py -q`
Expected: collection error / `ModuleNotFoundError: No module named 'analytics.timegrain'`.

- [ ] **Step 4: Implement the engine**

Create `backend/analytics/timegrain.py`:

```python
"""Time-grain aggregation + period-comparison math for ML Studio.

Pure functions over Polars frames/series — no FastAPI, no DB. Shared by the
/timeseries and /forecast endpoints so comparison math lives in exactly one
place. Callers must pass a date_col that is already a Date/Datetime dtype
(parse upstream with routers.ml._try_parse_dates).
"""
from __future__ import annotations

import math
from datetime import date
from typing import Literal

import polars as pl

Grain = Literal["day", "week", "month", "quarter", "year"]
Agg = Literal["sum", "mean", "count", "n_unique", "min", "max"]

_TRUNC: dict[str, str] = {
    "day": "1d", "week": "1w", "month": "1mo", "quarter": "1q", "year": "1y",
}

_AGG = {
    "sum": lambda c: c.sum(),
    "mean": lambda c: c.mean(),
    "count": lambda c: c.count(),
    "n_unique": lambda c: c.n_unique(),
    "min": lambda c: c.min(),
    "max": lambda c: c.max(),
}


def truncate_dates(dates: pl.Series, grain: Grain) -> pl.Series:
    """Map each date to its period-start (week → ISO Monday)."""
    return dates.dt.truncate(_TRUNC[grain])


def _finite_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _label(d: date, grain: Grain) -> str:
    if grain == "year":
        return f"{d.year}"
    if grain == "quarter":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if grain == "month":
        return f"{d.year}-{d.month:02d}"
    if grain == "week":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return d.isoformat()


def aggregate_series(df: pl.DataFrame, date_col: str, value_col: str,
                     grain: Grain, agg: Agg) -> dict:
    """Truncate date_col to grain, group, aggregate value_col, sort by period.

    Returns {"period_starts": [date], "labels": [str], "values": [float|None]}.
    Rows with a null period (null/unparseable date) are dropped.
    """
    period = truncate_dates(df[date_col], grain).alias("_period")
    work = df.with_columns(period).drop_nulls(subset=["_period"])
    grouped = (
        work.group_by("_period")
        .agg(_AGG[agg](pl.col(value_col)).alias("_value"))
        .sort("_period")
    )
    starts = grouped["_period"].to_list()
    values = [_finite_or_none(v) for v in grouped["_value"].to_list()]
    labels = [_label(d, grain) for d in starts]
    return {"period_starts": starts, "labels": labels, "values": values}


def suggest_grain(period_min: date, period_max: date) -> Grain:
    """Coarsest grain giving ~<=60 buckets; finest fallback = day."""
    span = (period_max - period_min).days
    if span <= 0:
        return "day"
    for grain, approx in (("day", 1), ("week", 7), ("month", 30),
                          ("quarter", 91), ("year", 365)):
        if span / approx <= 60:
            return grain  # type: ignore[return-value]
    return "year"


# ── comparison math ─────────────────────────────────────────────────────────

def _delta_pct(cur, prior):
    if cur is None or prior is None or prior == 0:
        return None
    d = (cur - prior) / prior * 100
    return round(d, 2) if math.isfinite(d) else None


def _period_key(d: date, grain: Grain):
    if grain == "year":
        return date(d.year, 1, 1)
    if grain == "quarter":
        return date(d.year, (d.month - 1) // 3 * 3 + 1, 1)
    if grain == "month":
        return date(d.year, d.month, 1)
    if grain == "day":
        return d
    iso = d.isocalendar()
    return ("W", iso[0], iso[1])


def _prior_year_key(d: date, grain: Grain):
    if grain == "year":
        return date(d.year - 1, 1, 1)
    if grain == "quarter":
        return date(d.year - 1, (d.month - 1) // 3 * 3 + 1, 1)
    if grain == "month":
        return date(d.year - 1, d.month, 1)
    if grain == "day":
        try:
            return date(d.year - 1, d.month, d.day)
        except ValueError:           # Feb 29 → Feb 28
            return date(d.year - 1, d.month, 28)
    iso = d.isocalendar()
    return ("W", iso[0] - 1, iso[1])


def _yoy(period_starts, values, grain):
    index = {_period_key(d, grain): v for d, v in zip(period_starts, values)}
    yoy_vals, deltas = [], []
    for d, v in zip(period_starts, values):
        prior = index.get(_prior_year_key(d, grain))
        yoy_vals.append(prior)
        deltas.append(_delta_pct(v, prior))
    return {"values": yoy_vals, "delta_pct": deltas}


def _pop(values):
    vals, deltas = [], []
    for i, v in enumerate(values):
        prior = values[i - 1] if i > 0 else None
        vals.append(prior)
        deltas.append(_delta_pct(v, prior))
    return {"values": vals, "delta_pct": deltas}


def _rolling(values, window):
    out = []
    for i in range(len(values)):
        chunk = [x for x in values[max(0, i - window + 1):i + 1] if x is not None]
        out.append(round(sum(chunk) / len(chunk), 4) if chunk else None)
    return out


def _reset_key(d: date, reset: str):
    if reset == "month":
        return (d.year, d.month)
    if reset == "quarter":
        return (d.year, (d.month - 1) // 3)
    return d.year


def _cumulative(period_starts, values, reset):
    out, run, cur_key = [], 0.0, None
    for d, v in zip(period_starts, values):
        key = _reset_key(d, reset)
        if key != cur_key:
            cur_key, run = key, 0.0
        if v is not None:
            run += v
        out.append(round(run, 4))
    return out


def _index100(values):
    base = next((v for v in values if v not in (None, 0)), None)
    if base is None:
        return [None] * len(values)
    return [round(v / base * 100, 2) if v is not None else None for v in values]


def _share(values):
    total = sum(v for v in values if v is not None)
    if not total:
        return [None] * len(values)
    return [round(v / total * 100, 2) if v is not None else None for v in values]


def add_comparisons(period_starts: list[date], values: list, grain: Grain,
                    comparisons: list[str], rolling_window: int = 7,
                    cumulative_reset: str = "year") -> dict:
    """Return only the requested comparison keys."""
    out: dict = {}
    if "yoy" in comparisons:
        out["yoy"] = _yoy(period_starts, values, grain)
    if "pop" in comparisons:
        out["pop"] = _pop(values)
    if "rolling" in comparisons:
        out["rolling"] = {"window": rolling_window,
                          "values": _rolling(values, rolling_window)}
    if "cumulative" in comparisons:
        out["cumulative"] = {"reset": cumulative_reset,
                             "values": _cumulative(period_starts, values, cumulative_reset)}
    if "index100" in comparisons:
        out["index100"] = {"values": _index100(values)}
    if "share" in comparisons:
        out["share"] = {"values": _share(values)}
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_timegrain.py -q`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/analytics/__init__.py backend/analytics/timegrain.py backend/tests/test_timegrain.py
git commit -m "feat(ml): add time-grain aggregation + comparison engine" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `POST /api/ml/timeseries` (Component 1 — backend)

Parse date_col, drop null dates, resolve grain (`auto` → `suggest_grain`), aggregate, attach requested comparisons.

**Files:**
- Modify: `backend/routers/ml.py` (add import + `TimeseriesIn` + `run_timeseries`)
- Test: `backend/tests/test_ml.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml.py`:

```python
# ── /timeseries endpoint (Component 1) ─────────────────────────────────────
def test_timeseries_monthly_pop(client):
    csv = (
        b"date,rev\n"
        b"2024-01-05,10\n2024-01-20,20\n"
        b"2024-02-10,30\n2024-02-15,5\n"
        b"2024-03-01,40\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("tsm.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/timeseries", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "rev",
        "grain": "month", "agg": "sum", "comparisons": ["pop"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["grain"] == "month"
    assert d["series"]["labels"] == ["2024-01", "2024-02", "2024-03"]
    assert d["series"]["values"] == [30.0, 35.0, 40.0]
    assert d["comparisons"]["pop"]["values"] == [None, 30.0, 35.0]
    assert "yoy" not in d["comparisons"]   # only requested keys present


def test_timeseries_yoy(client):
    csv = (
        b"date,rev\n"
        b"2023-01-15,100\n2023-02-15,200\n"
        b"2024-01-15,150\n2024-02-15,180\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("tsy.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/timeseries", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "rev",
        "grain": "month", "agg": "sum", "comparisons": ["yoy"],
    })
    d = resp.json()
    assert d["series"]["values"] == [100.0, 200.0, 150.0, 180.0]
    assert d["comparisons"]["yoy"]["values"] == [None, None, 100.0, 200.0]
    assert d["comparisons"]["yoy"]["delta_pct"] == [None, None, 50.0, -10.0]


def test_timeseries_auto_grain_meta(client):
    # ~2.4 years of monthly rows -> auto should pick "month"
    rows = b"date,v\n"
    for y in (2022, 2023, 2024):
        for m in range(1, 13):
            rows += f"{y}-{m:02d}-01,{y + m}\n".encode()
    up = client.post("/api/ml/upload",
                     files={"file": ("tsa.csv", io.BytesIO(rows), "text/csv")}).json()
    resp = client.post("/api/ml/timeseries", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "v",
        "grain": "auto", "agg": "sum",
    })
    d = resp.json()
    assert d["grain"] == "month"
    assert d["meta"]["suggested_grain"] == "month"
    assert d["meta"]["periods"] == 36
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml.py -k timeseries -q`
Expected: 404/422 or assertion errors — endpoint does not exist yet.

- [ ] **Step 3: Add the engine import**

In `backend/routers/ml.py`, immediately after line 17 (`from database import get_connection, UPLOADS_DIR`) add:

```python
from typing import Literal
from analytics.timegrain import aggregate_series, suggest_grain, add_comparisons, Grain, Agg
```

(If `Literal` is already imported elsewhere, keep a single import.)

- [ ] **Step 4: Add `TimeseriesIn` and `run_timeseries`**

In `backend/routers/ml.py`, insert directly **after** the `describe_dataset` function (after line 476, before `class CohortIn`):

```python
class TimeseriesIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    grain: Grain | Literal["auto"] = "auto"
    agg: Agg = "sum"
    comparisons: list[str] = []
    rolling_window: int = 7
    cumulative_reset: Literal["month", "quarter", "year"] = "year"
    group_col: str | None = None


@router.post("/timeseries")
def run_timeseries(body: TimeseriesIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    for col in (body.date_col, body.value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        parsed = _try_parse_dates(df[body.date_col])
    except ValueError as e:
        raise HTTPException(400, f"Không thể parse cột ngày '{body.date_col}': {e}")

    df = df.with_columns(parsed.alias("_d")).drop_nulls(subset=["_d"])
    if df.height == 0:
        raise HTTPException(400, "Không có ngày hợp lệ sau khi parse")

    dmin, dmax = df["_d"].min(), df["_d"].max()
    suggested = suggest_grain(dmin, dmax)
    grain = suggested if body.grain == "auto" else body.grain

    series = aggregate_series(df, "_d", body.value_col, grain, body.agg)
    comps = add_comparisons(
        series["period_starts"], series["values"], grain,
        body.comparisons, body.rolling_window, body.cumulative_reset,
    )

    return {
        "grain": grain,
        "agg": body.agg,
        "date_col": body.date_col,
        "value_col": body.value_col,
        "series": {"labels": series["labels"], "values": series["values"]},
        "comparisons": comps,
        "meta": {
            "rows_used": df.height,
            "periods": len(series["labels"]),
            "span_days": (dmax - dmin).days,
            "suggested_grain": suggested,
        },
    }
```

> `group_col` is accepted in the contract for forward-compat but not used in v1 (single-series). Leave it in the model; do not branch on it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml.py -k timeseries -q`
Expected: 3 passed.

- [ ] **Step 6: Run the full backend suite (no regressions)**

Run: `cd backend ; uv run pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(ml): add /timeseries endpoint (grain + period comparisons)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Charts — collapsible "Chuỗi thời gian" panel (Component 1 — frontend)

Add a collapsible **"Chuỗi thời gian"** panel to the Charts view, matching the existing Cohort / Correlation panel idiom (a header button that expands a body). It calls `/ml/timeseries` server-side using the dataset's full schema (`dataset.columns` + `file_id`) — NOT the current SQL `result` — then renders the aggregated line plus comparison overlays. The existing column-vs-column chart (which plots `result`) is left untouched; the new panel is appended after the Correlation panel.

**Files:**
- Modify: `frontend/src/types.ts` (add `TimeseriesResult`)
- Modify: `frontend/src/api/ml.ts` (add `runTimeseries`)
- Modify: `frontend/src/components/ml/MlChartView.tsx` (collapsible panel)

- [ ] **Step 1: Add the result type**

In `frontend/src/types.ts`, after the `CorrelationMatrix` interface add:

```typescript
export interface TimeseriesResult {
  grain: 'day' | 'week' | 'month' | 'quarter' | 'year'
  agg: string
  date_col: string
  value_col: string
  series: { labels: string[]; values: (number | null)[] }
  comparisons: {
    yoy?: { values: (number | null)[]; delta_pct: (number | null)[] }
    pop?: { values: (number | null)[]; delta_pct: (number | null)[] }
    rolling?: { window: number; values: (number | null)[] }
    cumulative?: { reset: string; values: (number | null)[] }
    index100?: { values: (number | null)[] }
    share?: { values: (number | null)[] }
  }
  meta: { rows_used: number; periods: number; span_days: number; suggested_grain: string }
}
```

- [ ] **Step 2: Add the API client function**

In `frontend/src/api/ml.ts`, add `TimeseriesResult` to the type import (line 2-6 block) and append:

```typescript
export async function runTimeseries(
  file_id: string, date_col: string, value_col: string,
  grain: string, agg: string, comparisons: string[],
  rolling_window = 7, cumulative_reset = 'year',
): Promise<TimeseriesResult> {
  const { data } = await client.post<TimeseriesResult>('/ml/timeseries', {
    file_id, date_col, value_col, grain, agg, comparisons,
    rolling_window, cumulative_reset,
  })
  return data
}
```

- [ ] **Step 3: Add the collapsible "Chuỗi thời gian" panel to MlChartView**

In `frontend/src/components/ml/MlChartView.tsx`:

3a. Extend three existing imports (verbatim — these are the exact current lines):
- Line 2 (lucide): `import { ArrowUpDown, Grid2x2, Users, TrendingUp } from 'lucide-react'`
- Line 12 (types): `import type { QueryResult, DatasetInfo, CorrelationMatrix, QualityResult, TimeseriesResult } from '../../types'`
- Line 13 (api): `import { fetchCorrelation, runCohort, runTimeseries, type CohortResult } from '../../api/ml'`

3b. Add module-scope constants at the top of the file, beside the other top-level `const` config (e.g. `CHART_TYPES`/`PIE_COLORS`) — **not** inside the component:

```tsx
const TS_GRAINS = ['auto', 'day', 'week', 'month', 'quarter', 'year'] as const
const TS_AGGS   = ['sum', 'mean', 'count', 'n_unique', 'min', 'max'] as const
const TS_COMPARISONS: { key: string; label: string }[] = [
  { key: 'yoy',        label: 'YoY' },
  { key: 'pop',        label: 'Kỳ trước' },
  { key: 'rolling',    label: 'TB trượt' },
  { key: 'cumulative', label: 'Lũy kế' },
]
```

3c. Add component state immediately after the Cohort state block (after `setCohortError` on line 167, before the `data` useMemo on line 169):

```tsx
  // Time series (server-side: dataset.columns + file_id → /ml/timeseries)
  const [showTs,    setShowTs]    = useState(false)
  const [tsDate,    setTsDate]    = useState('')
  const [tsValue,   setTsValue]   = useState('')
  const [tsGrain,   setTsGrain]   = useState<string>('auto')
  const [tsAgg,     setTsAgg]     = useState<string>('sum')
  const [tsComps,   setTsComps]   = useState<string[]>(['yoy', 'pop', 'rolling', 'cumulative'])
  const [tsResult,  setTsResult]  = useState<TimeseriesResult | null>(null)
  const [tsLoading, setTsLoading] = useState(false)
  const [tsError,   setTsError]   = useState('')
```

3d. Add the run handler immediately after `handleCohort` (after line 236, before the `tooltipStyle` const on line 238):

```tsx
  async function handleTimeseries() {
    if (!dataset || !tsDate || !tsValue) return
    setTsLoading(true); setTsError(''); setTsResult(null)
    try {
      setTsResult(await runTimeseries(dataset.file_id, tsDate, tsValue, tsGrain, tsAgg, tsComps))
    } catch (e: unknown) {
      setTsError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Timeseries failed')
    } finally { setTsLoading(false) }
  }
```

3e. **Append the panel after the Correlation panel.** Insert it between the Correlation block's closing `)}` (line 612) and the scroll-container's closing `</div>` (line 613). It reuses the file's existing `tooltipStyle`/`axisStyle` (lines 238-239), the confirmed CSS classes (`input-base`, `btn-primary`, `text-danger`, the blue active-toggle style copied from the cohort period buttons), and the already-imported recharts symbols (`LineChart`, `Line`, `XAxis`, `YAxis`, `CartesianGrid`, `Tooltip`, `Legend`, `ResponsiveContainer`):

```tsx
      {/* ── Chuỗi thời gian ──────────────────────────────────── */}
      {dataset && (
        <div className="border border-white/5 rounded-lg overflow-hidden">
          <button onClick={() => setShowTs(o => !o)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left">
            <TrendingUp size={12} className="text-gray-500" />
            <span className="text-[11px] font-medium text-gray-300">Chuỗi thời gian</span>
            <span className="text-[10px] text-gray-600 ml-1">— gộp ngày/tuần/tháng/quý/năm + YoY/kỳ trước</span>
          </button>

          {showTs && (
            <div className="p-3 flex flex-col gap-3">
              <div className="flex gap-2 flex-wrap items-end">
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Date column</label>
                  <select className="input-base text-xs" value={tsDate} onChange={e => setTsDate(e.target.value)}>
                    <option value="">—</option>
                    {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Value column</label>
                  <select className="input-base text-xs" value={tsValue} onChange={e => setTsValue(e.target.value)}>
                    <option value="">—</option>
                    {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Grain</label>
                  <select className="input-base text-xs" value={tsGrain} onChange={e => setTsGrain(e.target.value)}>
                    {TS_GRAINS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-600 mb-1">Agg</label>
                  <select className="input-base text-xs" value={tsAgg} onChange={e => setTsAgg(e.target.value)}>
                    {TS_AGGS.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
                <div className="flex gap-1 pb-0.5">
                  {TS_COMPARISONS.map(c => (
                    <button key={c.key}
                      onClick={() => setTsComps(prev => prev.includes(c.key) ? prev.filter(x => x !== c.key) : [...prev, c.key])}
                      className={`px-2 py-1 rounded text-[11px] border transition-all ${
                        tsComps.includes(c.key)
                          ? 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                          : 'text-gray-500 border-transparent hover:text-gray-300'
                      }`}>{c.label}</button>
                  ))}
                </div>
                <button onClick={handleTimeseries} disabled={tsLoading || !tsDate || !tsValue}
                  className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-50">
                  <TrendingUp size={11} /> {tsLoading ? 'Computing…' : 'Run'}
                </button>
              </div>

              {tsError && <p className="text-danger text-xs">{tsError}</p>}

              {tsResult && (
                <>
                  <p className="text-[10px] text-gray-500">
                    {tsResult.grain} · {tsResult.meta.periods} kỳ · gợi ý: {tsResult.meta.suggested_grain}
                  </p>
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={tsResult.series.labels.map((label, i) => ({
                      label,
                      value:      tsResult.series.values[i],
                      yoy:        tsResult.comparisons.yoy?.values[i] ?? null,
                      pop:        tsResult.comparisons.pop?.values[i] ?? null,
                      rolling:    tsResult.comparisons.rolling?.values[i] ?? null,
                      cumulative: tsResult.comparisons.cumulative?.values[i] ?? null,
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="label" tick={axisStyle} />
                      <YAxis tick={axisStyle} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend wrapperStyle={{ fontSize: 10 }} />
                      <Line type="monotone" dataKey="value" stroke="#3b82f6" dot={false} name={tsResult.value_col} />
                      {tsResult.comparisons.yoy        && <Line type="monotone" dataKey="yoy"        stroke="#a855f7" strokeDasharray="4 2" dot={false} name="YoY" />}
                      {tsResult.comparisons.pop        && <Line type="monotone" dataKey="pop"        stroke="#f59e0b" strokeDasharray="4 2" dot={false} name="Kỳ trước" />}
                      {tsResult.comparisons.rolling    && <Line type="monotone" dataKey="rolling"    stroke="#22c55e" dot={false} name="TB trượt" />}
                      {tsResult.comparisons.cumulative && <Line type="monotone" dataKey="cumulative" stroke="#eab308" dot={false} name="Lũy kế" />}
                    </LineChart>
                  </ResponsiveContainer>
                </>
              )}
            </div>
          )}
        </div>
      )}
```

- [ ] **Step 4: Pre-fill the pickers and reset on file change**

Add an effect (next to the existing corr-reset effect at lines 152-158) that guesses `tsDate`/`tsValue` from the dataset schema and clears stale results when the loaded file changes. It reads `dataset.columns` (`ColumnInfo[]` — `{ name, dtype }`):

```tsx
  // Pre-fill time-series pickers from the dataset schema; reset on file change
  useEffect(() => {
    setTsResult(null); setTsError(''); setShowTs(false)
    if (!dataset) { setTsDate(''); setTsValue(''); return }
    const cols = dataset.columns
    const dateGuess =
      cols.find(c => /date|datetime|timestamp/i.test(c.dtype))?.name ??
      cols.find(c => /date|time|day|month|year|period|ngay|thang/i.test(c.name))?.name ??
      cols[0]?.name ?? ''
    const numGuess =
      cols.find(c => /int|float|decimal|double/i.test(c.dtype) && c.name !== dateGuess)?.name ?? ''
    setTsDate(dateGuess); setTsValue(numGuess)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset?.file_id])
```

- [ ] **Step 5: Verify the build**

Run: `cd frontend ; npm run build`
Expected: build succeeds, zero TS errors.

- [ ] **Step 6: Manual smoke**

Start the app (`python run.py`), upload a dated dataset, open Charts, expand the **Chuỗi thời gian** panel, pick date+value, switch grain month/quarter, toggle YoY/PoP. Confirm lines render and "gợi ý" grain shows. (Quý/năm grains are also exercised by the forecast task.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): charts time-series mode — grain/agg + YoY/PoP/rolling/cumulative" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Forecast by time-grain (Component 2 — backend)

Aggregate to the chosen grain before forecasting, and **step forecast dates by grain** (month → +i months, quarter → +i·3 months, year → +i years, week → +i·7 days, day → +i days). Today every method steps by `timedelta(days=i)` regardless of grain. Seasonal period auto-derives from grain when not given.

**Files:**
- Modify: `backend/routers/ml.py` — `ForecastIn` (84-90), `ForecastCompareIn` (93-99), add date/seasonal helpers, `run_forecast` setup + 5 date-step sites + 2 seasonal sites, `compare_forecast` aggregation
- Test: `backend/tests/test_ml.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml.py`:

```python
# ── Forecast by grain (Component 2) ────────────────────────────────────────
def _daily_csv(start_year=2024, n_days=150):
    import datetime as _dt
    base = _dt.date(start_year, 1, 1)
    rows = b"date,val\n"
    for i in range(n_days):
        d = base + _dt.timedelta(days=i)
        rows += f"{d.isoformat()},{100 + i}\n".encode()
    return rows


def test_forecast_grain_month_steps_by_month(client):
    up = client.post("/api/ml/upload",
                     files={"file": ("fc.csv", io.BytesIO(_daily_csv()), "text/csv")}).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "val",
        "periods": 3, "method": "linear", "grain": "month", "agg": "sum",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["forecast"]) == 3
    from datetime import date as _D
    ds = [_D.fromisoformat(f["date"]) for f in d["forecast"]]
    # consecutive forecast points are ~1 month apart, not 1 day
    assert (ds[1] - ds[0]).days >= 27
    assert d["forecast"][0]["value"] > 0


def test_forecast_raw_grain_steps_by_day(client):
    up = client.post("/api/ml/upload",
                     files={"file": ("fcr.csv", io.BytesIO(_daily_csv(n_days=30)), "text/csv")}).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "val",
        "periods": 3, "method": "linear", "grain": "raw",
    })
    d = resp.json()
    from datetime import date as _D
    ds = [_D.fromisoformat(f["date"]) for f in d["forecast"]]
    assert (ds[1] - ds[0]).days == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml.py -k "forecast_grain or forecast_raw" -q`
Expected: `test_forecast_grain_month_steps_by_month` fails — points are 1 day apart (`grain` ignored / field rejected).

- [ ] **Step 3: Extend the request models**

Replace `ForecastIn` (lines 84-90) with:

```python
class ForecastIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7
    method: str = 'linear'          # linear | moving_average | sarimax | supervised | ets
    seasonal_period: int | None = None   # None → derive from grain
    grain: Grain | Literal["auto", "raw"] = "auto"
    agg: Agg = "sum"
```

Replace `ForecastCompareIn` (lines 93-99) with:

```python
class ForecastCompareIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7
    seasonal_period: int = 12
    methods: list[str]
    grain: Grain | Literal["auto", "raw"] = "auto"
    agg: Agg = "sum"
```

- [ ] **Step 4: Add date-step + seasonal helpers**

In `backend/routers/ml.py`, insert just **above** `@router.post("/forecast")` (before line 1310):

```python
import calendar as _calendar

GRAIN_SEASONAL = {"day": 7, "week": 52, "month": 12, "quarter": 4, "year": 1}


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    mo = m % 12 + 1
    day = min(d.day, _calendar.monthrange(y, mo)[1])
    return date(y, mo, day)


def _step_date(last: date, i: int, grain: str) -> date:
    if grain == "year":
        return _add_months(last, 12 * i)
    if grain == "quarter":
        return _add_months(last, 3 * i)
    if grain == "month":
        return _add_months(last, i)
    if grain == "week":
        return last + timedelta(days=7 * i)
    return last + timedelta(days=i)        # day | raw


def _seasonal(body: ForecastIn, grain: str) -> int:
    if body.seasonal_period is not None:
        return body.seasonal_period
    return GRAIN_SEASONAL.get(grain, 12)
```

- [ ] **Step 5: Rewrite the `run_forecast` setup block**

Replace lines 1327-1340 (from `df_sorted = df.sort("_date_parsed")` through the `last_date` `except` block) with:

```python
    df_sorted = df.sort("_date_parsed")
    dmin, dmax = df_sorted["_date_parsed"].min(), df_sorted["_date_parsed"].max()
    if body.grain == "raw":
        eff_grain = "raw"
    elif body.grain == "auto":
        eff_grain = suggest_grain(dmin, dmax) if isinstance(dmin, date) else "day"
    else:
        eff_grain = body.grain
    step_grain = "day" if eff_grain == "raw" else eff_grain

    if eff_grain == "raw":
        values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
        labels = df_sorted[body.date_col].cast(pl.Utf8).to_list()
        try:
            raw_last = df_sorted["_date_parsed"].drop_nulls()[-1]
            last_date = raw_last.item() if hasattr(raw_last, "item") else raw_last
            if not isinstance(last_date, date):
                last_date = date.today()
        except Exception:
            last_date = date.today()
    else:
        agg_series = aggregate_series(df_sorted, "_date_parsed", body.value_col, eff_grain, body.agg)
        values = np.array([v for v in agg_series["values"] if v is not None], dtype=float)
        labels = agg_series["labels"]
        starts = agg_series["period_starts"]
        last_date = starts[-1] if starts else date.today()

    n = len(values)
    if n < 2:
        raise HTTPException(400, "Need at least 2 data points")
```

> This removes the old `values` / `dates_raw` / `n` / `last_date` lines (1328-1340). The history block below references `dates_raw`; fix it in the next step.

- [ ] **Step 6: Point history at `labels`**

In the `_history` comprehension (≈ lines 1352-1360), replace `dates_raw[n - hist_n + i]` with `labels[n - hist_n + i]`:

```python
    _history = [
        {
            "date":       labels[n - hist_n + i],
            "value":      round(float(values[n - hist_n + i]), 4),
            "is_anomaly": bool(is_anomaly_arr[n - hist_n + i]),
            "z_score":    round(float(z_scores_arr[n - hist_n + i]), 2),
        }
        for i in range(hist_n)
    ]
```

- [ ] **Step 7: Replace the 5 date-step sites and 2 seasonal sites**

Make these exact edits inside `run_forecast`:

1. moving_average (≈1374): `"date": (last_date + timedelta(days=i)).isoformat(),` → `"date": _step_date(last_date, i, step_grain).isoformat(),`
2. sarimax seasonal (≈1388): `s = body.seasonal_period` → `s = _seasonal(body, step_grain)`
3. sarimax date (≈1421): `"date":  (last_date + timedelta(days=i + 1)).isoformat(),` → `"date":  _step_date(last_date, i + 1, step_grain).isoformat(),`
4. supervised date (≈1458): `"date":  (last_date + timedelta(days=i + 1)).isoformat(),` → `"date":  _step_date(last_date, i + 1, step_grain).isoformat(),`
5. ets seasonal (≈1480): `s = body.seasonal_period` → `s = _seasonal(body, step_grain)`
6. ets date (≈1505): `"date":  (last_date + timedelta(days=i + 1)).isoformat(),` → `"date":  _step_date(last_date, i + 1, step_grain).isoformat(),`
7. linear date (≈1533): `"date": (last_date + timedelta(days=i)).isoformat(),` → `"date": _step_date(last_date, i, step_grain).isoformat(),`

> The two `(last_date + timedelta(days=i + 1))` strings in sarimax/supervised are identical and there are 3 such occurrences total (sarimax, supervised, ets) — edit each in its own block; do not use replace-all blindly. Likewise the two `(last_date + timedelta(days=i))` strings (moving_average, linear).

- [ ] **Step 8: Aggregate in `compare_forecast` too**

In `compare_forecast`, replace lines 746-747:

```python
    df_sorted = df.sort("_date_parsed")
    values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
```

with:

```python
    df_sorted = df.sort("_date_parsed")
    if body.grain == "raw":
        values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
    else:
        dmin, dmax = df_sorted["_date_parsed"].min(), df_sorted["_date_parsed"].max()
        eff_grain = suggest_grain(dmin, dmax) if body.grain == "auto" else body.grain
        _cmp = aggregate_series(df_sorted, "_date_parsed", body.value_col, eff_grain, body.agg)
        values = np.array([v for v in _cmp["values"] if v is not None], dtype=float)
```

(Leave `s = body.seasonal_period` in compare as-is — compare always receives an explicit seasonal period.)

- [ ] **Step 9: Run the forecast tests + full suite**

Run: `cd backend ; uv run pytest tests/test_ml.py -k forecast -q`
Expected: new grain tests pass AND existing forecast tests still pass (`test_forecast`, `test_forecast_non_iso_dates`, `test_forecast_returns_history`, `test_forecast_ets`, `test_forecast_sarimax_insufficient`, `test_forecast_compare`).
Then: `cd backend ; uv run pytest -q` → all pass.

- [ ] **Step 10: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(ml): forecast by time-grain — aggregate + step dates per grain" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Forecast UI — Grain / Agg selectors (Component 2 — frontend)

**Files:**
- Modify: `frontend/src/api/ml.ts` (`runForecast` signature)
- Modify: `frontend/src/types.ts` (`ForecastResult` optional grain fields)
- Modify: `frontend/src/components/ml/MlForecastView.tsx` (selectors + wiring)

- [ ] **Step 1: Extend `runForecast`**

In `frontend/src/api/ml.ts` replace `runForecast` (lines 39-47):

```typescript
export async function runForecast(
  file_id: string, date_col: string, value_col: string,
  periods: number, method: string, seasonal_period: number | null = null,
  grain = 'auto', agg = 'sum',
): Promise<ForecastResult> {
  const { data } = await client.post<ForecastResult>('/ml/forecast', {
    file_id, date_col, value_col, periods, method, seasonal_period, grain, agg,
  })
  return data
}
```

- [ ] **Step 2: Add Grain/Agg state + selectors in MlForecastView**

In `frontend/src/components/ml/MlForecastView.tsx`:

2a. Add state near the other hooks:

```tsx
const [grain, setGrain] = useState<string>('auto')
const [agg, setAgg] = useState<string>('sum')
const FC_GRAINS = ['auto', 'raw', 'day', 'week', 'month', 'quarter', 'year'] as const
const FC_AGGS = ['sum', 'mean', 'count', 'n_unique', 'min', 'max'] as const
```

2b. In `handleRun`, pass the new args to `runForecast`. Change the call to:

```tsx
const res = await runForecast(
  dataset.file_id, dateCol, valueCol, periods, method,
  seasonalPeriod, grain, agg,
)
```

(Keep `seasonalPeriod` as the existing state; the backend now treats it as an explicit override.)

2c. Add the two selectors into the config toolbar (next to the existing date/value/method controls):

```tsx
<label className="flex flex-col text-[10px] text-gray-500">Grain
  <select className="input-base text-xs" value={grain} onChange={e => setGrain(e.target.value)}>
    {FC_GRAINS.map(g => <option key={g} value={g}>{g}</option>)}
  </select>
</label>
<label className="flex flex-col text-[10px] text-gray-500">Agg
  <select className="input-base text-xs" value={agg} onChange={e => setAgg(e.target.value)}>
    {FC_AGGS.map(a => <option key={a} value={a}>{a}</option>)}
  </select>
</label>
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend ; npm run build`
Expected: build succeeds, zero TS errors.

- [ ] **Step 4: Manual smoke**

Upload daily data, Forecast tab → set Grain=month, method=linear, run. Forecast x-axis labels should be monthly; switching to Grain=raw returns daily steps.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ml.ts frontend/src/types.ts frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(ml): forecast UI — grain/agg selectors" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: `GET /api/ml/profile/{file_id}` (Component 4 — backend)

Per-column profile with an inferred role (`date | metric | dimension | id | flag`) that drives field-placement suggestions on the frontend.

**Files:**
- Modify: `backend/routers/ml.py` (add `_infer_role` + `profile_dataset`)
- Test: `backend/tests/test_ml.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ml.py`:

```python
# ── /profile endpoint (Component 4) ────────────────────────────────────────
def test_profile_roles(client):
    csv = (
        b"order_date,customer_id,region,amount,is_paid\n"
        b"2024-01-01,C001,North,100,1\n"
        b"2024-01-02,C002,South,200,1\n"
        b"2024-01-03,C003,North,150,0\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("prof.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.get(f"/api/ml/profile/{up['file_id']}")
    assert resp.status_code == 200
    cols = {c["name"]: c for c in resp.json()["columns"]}
    assert cols["order_date"]["role"] == "date"
    assert cols["customer_id"]["role"] == "id"
    assert cols["region"]["role"] == "dimension"
    assert cols["amount"]["role"] == "metric"
    assert cols["is_paid"]["role"] == "flag"
    assert cols["amount"]["min"] == 100.0
    assert cols["amount"]["max"] == 200.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_ml.py -k profile -q`
Expected: 404 / not found — endpoint missing.

- [ ] **Step 3: Implement `_infer_role` + `profile_dataset`**

In `backend/routers/ml.py`, insert just **after** `describe_dataset` (after line 476). (Place before or after `TimeseriesIn` from Task 3 — order doesn't matter.)

```python
def _infer_role(col: str, s: pl.Series, nunq: int, n: int, is_num: bool) -> str:
    name = col.lower()
    dt = str(s.dtype).lower()
    # date
    if dt.startswith("date") or dt.startswith("datetime"):
        return "date"
    if not is_num:
        try:
            parsed = _try_parse_dates(s)
            if parsed.null_count() < len(parsed):
                return "date"
        except Exception:
            pass
    # id
    if re.search(r"(^id$|_id$|^id_|\bcode\b|phone|msisdn)", name):
        return "id"
    if (not is_num) and n > 0 and nunq >= 0.9 * n:
        return "id"
    # flag
    if (is_num or dt == "boolean") and nunq <= 2:
        return "flag"
    # metric
    if is_num:
        return "metric"
    # dimension (low-cardinality categorical) — default for the rest
    return "dimension"


@router.get("/profile/{file_id}")
def profile_dataset(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    n = df.height
    out = []
    for col in df.columns:
        s = df[col]
        nunq = int(s.n_unique())
        is_num = s.dtype.is_numeric()
        entry: dict = {
            "name": col,
            "dtype": str(s.dtype),
            "role": _infer_role(col, s, nunq, n, is_num),
            "cardinality": nunq,
            "null_pct": round(s.null_count() / max(n, 1) * 100, 1),
            "is_constant": bool(s.null_count() < n and nunq <= 1),
            "samples": [str(v) for v in s.drop_nulls().unique().head(3).to_list()],
        }
        if is_num:
            arr = s.drop_nulls().cast(pl.Float64)
            if len(arr) > 0:
                entry["min"] = round(float(arr.min()), 4)   # type: ignore[arg-type]
                entry["max"] = round(float(arr.max()), 4)   # type: ignore[arg-type]
        out.append(entry)
    return {"columns": out, "rows": n}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_ml.py -k profile -q`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(ml): add /profile endpoint with column role inference" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Field-placement suggestions (Component 4 — frontend)

A "Gợi ý biểu đồ" (suggested charts) panel in the Charts tab: fetch `/profile`, classify columns by role, and offer one-click recipes. Each recipe routes to the right surface: **date + metric** opens the server-side **Chuỗi thời gian** panel (Task 4); **≥2 metrics** opens the **Correlation** panel; **dimension + metric** (and metric-vs-metric) pre-fill the existing client-side chart pickers — but only when those columns exist in the current SQL `result` (profile/dataset columns can differ from the query result).

**Files:**
- Modify: `frontend/src/types.ts` (add `ProfileColumn` / `ProfileResult`)
- Modify: `frontend/src/api/ml.ts` (add `fetchProfile`)
- Modify: `frontend/src/components/ml/MlChartView.tsx` (suggestions panel)

- [ ] **Step 1: Add profile types**

In `frontend/src/types.ts` add:

```typescript
export interface ProfileColumn {
  name: string
  dtype: string
  role: 'date' | 'metric' | 'dimension' | 'id' | 'flag'
  cardinality: number
  null_pct: number
  is_constant: boolean
  samples: string[]
  min?: number
  max?: number
}

export interface ProfileResult {
  columns: ProfileColumn[]
  rows: number
}
```

- [ ] **Step 2: Add `fetchProfile`**

In `frontend/src/api/ml.ts` add `ProfileResult` to the type import and append:

```typescript
export async function fetchProfile(file_id: string): Promise<ProfileResult> {
  const { data } = await client.get<ProfileResult>(`/ml/profile/${file_id}`)
  return data
}
```

- [ ] **Step 3: Build recipes from the profile in MlChartView**

In `frontend/src/components/ml/MlChartView.tsx`:

3a. Add `fetchProfile` to the api import and `ProfileResult` to the types import.

3b. Add state, fetch, and recipe-building (the time-series and correlation setters come from Task 4 / the existing correlation handler — Task 8 ships after Task 4):

```tsx
  const [profile, setProfile] = useState<ProfileResult | null>(null)

  useEffect(() => {
    if (!dataset) { setProfile(null); return }
    fetchProfile(dataset.file_id).then(setProfile).catch(() => setProfile(null))
  }, [dataset?.file_id])

  // A bar/scatter recipe drives the *client-side* chart, which plots
  // result.columns — so only offer it when the column exists in the current
  // SQL result (profile/dataset columns can differ from the query result).
  const inResult = (name: string) => result.columns.includes(name)

  interface Recipe { title: string; apply: () => void }
  const recipes: Recipe[] = (() => {
    if (!profile) return []
    const dates   = profile.columns.filter(c => c.role === 'date')
    const metrics = profile.columns.filter(c => c.role === 'metric')
    const dims    = profile.columns.filter(c => c.role === 'dimension')
    const r: Recipe[] = []
    // Date + metric → server-side time series (opens the Chuỗi thời gian panel)
    if (dates[0] && metrics[0]) {
      r.push({
        title: `📈 ${metrics[0].name} theo thời gian (${dates[0].name})`,
        apply: () => { setShowTs(true); setTsDate(dates[0].name); setTsValue(metrics[0].name); setTsGrain('auto') },
      })
    }
    // ≥2 numeric metrics → server-side correlation (opens + loads the panel)
    if (metrics.length >= 2) {
      r.push({
        title: `🔗 Tương quan ${metrics.length} cột số`,
        apply: () => { if (!showCorr) handleCorrToggle() },
      })
    }
    // Dimension + metric → client-side bar over the CURRENT result (guarded)
    if (dims[0] && metrics[0] && inResult(dims[0].name) && inResult(metrics[0].name)) {
      r.push({
        title: `📊 ${metrics[0].name} theo ${dims[0].name}`,
        apply: () => { setShowTs(false); setXCol(dims[0].name); setYCol(metrics[0].name); setType('bar') },
      })
    }
    // Two metrics, both present in the result → client-side scatter (guarded)
    if (metrics[0] && metrics[1] && inResult(metrics[0].name) && inResult(metrics[1].name)) {
      r.push({
        title: `⚬ ${metrics[0].name} vs ${metrics[1].name}`,
        apply: () => { setShowTs(false); setXCol(metrics[0].name); setYCol(metrics[1].name); setType('scatter') },
      })
    }
    return r
  })()
```

> All setters used above already exist after Task 4: `setShowTs`/`setTsDate`/`setTsValue`/`setTsGrain` (Task 4 state), `showCorr`/`handleCorrToggle` (existing correlation toggle, lines 145/208), `setXCol`/`setYCol`/`setType` (existing chart pickers, lines 136-138). Do not invent new state.

3c. Render the recipe chips as the **first child of the scroll container** — insert immediately after `<div className="flex flex-col gap-3 p-4 flex-1 overflow-auto">` (line 244), before the existing controls:

```tsx
      {recipes.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] text-gray-500">Gợi ý biểu đồ:</span>
          {recipes.map((rec, i) => (
            <button key={i} onClick={rec.apply}
              className="px-2 py-1 rounded text-[10px] border border-blue-500/30 text-blue-400 hover:bg-blue-600/20 transition-all">
              {rec.title}
            </button>
          ))}
        </div>
      )}
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend ; npm run build`
Expected: build succeeds, zero TS errors.

- [ ] **Step 5: Manual smoke**

Upload a dataset with a date + numeric + categorical column; the Charts tab shows "Gợi ý biểu đồ" chips. Clicking the 📈 chip opens the **Chuỗi thời gian** panel pre-filled; 🔗 opens + loads **Correlation**; 📊/⚬ pre-fill the client-side pickers (only shown when those columns exist in the current SQL result).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): field-placement suggestions from column profile" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Cohort suitability engine (Component 5 — backend, pure)

Acquisition-cohort retention is only meaningful when the same entity recurs across ≥2 periods. Daily-aggregate data (one row/day, no repeat id) degenerates to "1 user / 100%". This pure check flags that.

**Files:**
- Create: `backend/analytics/cohort_check.py`
- Test: `backend/tests/test_cohort_check.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_cohort_check.py`:

```python
from datetime import date
import polars as pl
from analytics.cohort_check import check_suitability


def _df(dates, users):
    return pl.DataFrame({"d": dates, "u": users})


def test_suitable_when_entities_recur():
    df = _df(
        [date(2024, 1, 5), date(2024, 2, 5), date(2024, 1, 6), date(2024, 3, 6), date(2024, 2, 10)],
        ["U1", "U1", "U2", "U2", "U3"],
    )
    res = check_suitability(df, "d", "u", df["d"])
    assert res["suitable"] is True
    assert res["reasons"] == []


def test_unsuitable_when_no_recurrence():
    df = _df(
        [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1), date(2024, 4, 1)],
        ["A", "B", "C", "D"],   # each entity appears once
    )
    res = check_suitability(df, "d", "u", df["d"])
    assert res["suitable"] is False
    assert any("kỳ" in r or "giữ chân" in r for r in res["reasons"])
    assert res["role_hint"] == {"date": "d", "user": "u"}


def test_unsuitable_single_period():
    df = _df([date(2024, 1, 1), date(2024, 1, 2)], ["X", "X"])
    res = check_suitability(df, "d", "u", df["d"])
    assert res["suitable"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_cohort_check.py -q`
Expected: `ModuleNotFoundError: No module named 'analytics.cohort_check'`.

- [ ] **Step 3: Implement `check_suitability`**

Create `backend/analytics/cohort_check.py`:

```python
"""Cohort data-suitability pre-check (pure functions).

Cohort retention needs the same entity recurring across multiple periods.
check_suitability flags daily-aggregate / one-shot data before we render a
misleading '1 user / 100%' matrix. Cohort period = year-month.
"""
from __future__ import annotations

import polars as pl


def _result(suitable: bool, reasons: list[str], date_col: str, user_col: str) -> dict:
    return {
        "suitable": suitable,
        "reasons": reasons,
        "needs": "Cần cột định danh khách hàng lặp lại qua nhiều kỳ + cột ngày sự kiện.",
        "role_hint": {"date": date_col, "user": user_col},
    }


def check_suitability(df: pl.DataFrame, date_col: str, user_col: str,
                      parsed_dates: pl.Series) -> dict:
    """parsed_dates: date_col already parsed to Date (aligned to df rows)."""
    reasons: list[str] = []

    null_pct = df[user_col].null_count() / max(df.height, 1)
    if null_pct > 0.5:
        reasons.append(
            f"Cột '{user_col}' rỗng {null_pct * 100:.0f}% — không đủ để theo dõi khách hàng."
        )

    work = df.with_columns(parsed_dates.alias("_d")).drop_nulls(subset=["_d"])
    if work.height == 0:
        reasons.append("Không có ngày hợp lệ sau khi parse cột ngày.")
        return _result(False, reasons, date_col, user_col)

    work = work.with_columns(
        (pl.col("_d").dt.year() * 100 + pl.col("_d").dt.month()).alias("_p")
    )

    per_user = work.group_by(user_col).agg(pl.col("_p").n_unique().alias("_np"))
    recurring = per_user.filter(pl.col("_np") >= 2).height
    if recurring == 0:
        reasons.append(
            "Mỗi khách chỉ xuất hiện trong 1 kỳ — không đo được tỉ lệ giữ chân (retention)."
        )

    if work["_p"].n_unique() < 2:
        reasons.append("Dữ liệu chỉ có 1 kỳ — cần ít nhất 2 kỳ để tạo cohort.")

    return _result(len(reasons) == 0, reasons, date_col, user_col)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_cohort_check.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/cohort_check.py backend/tests/test_cohort_check.py
git commit -m "feat(ml): add cohort data-suitability check" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Wire the cohort gate (Component 5 — backend)

Run the suitability check in **transactional mode only** (not pre-aggregated mode), before computing the matrix. Unsuitable → return the suitability dict (HTTP 200) so the UI can explain it.

**Files:**
- Modify: `backend/routers/ml.py` (`run_cohort` transactional branch, ≈633-642)
- Test: `backend/tests/test_ml.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml.py`:

```python
# ── Cohort suitability gate (Component 5) ──────────────────────────────────
def test_cohort_gate_blocks_no_recurrence(client):
    csv = b"date,cust\n2024-01-01,A\n2024-02-01,B\n2024-03-01,C\n2024-04-01,D\n"
    up = client.post("/api/ml/upload",
                     files={"file": ("coh1.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/cohort", json={
        "file_id": up["file_id"], "date_col": "date", "user_col": "cust", "period": "month",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["suitable"] is False
    assert d["reasons"]
    assert d["role_hint"]["user"] == "cust"


def test_cohort_gate_allows_recurring(client):
    csv = (
        b"date,user\n"
        b"2024-01-05,U1\n2024-02-05,U1\n2024-01-06,U2\n2024-03-06,U2\n2024-02-10,U3\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("coh2.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/cohort", json={
        "file_id": up["file_id"], "date_col": "date", "user_col": "user", "period": "month",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d.get("suitable") is not False    # normal result, no gate
    assert "matrix" in d
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml.py -k cohort_gate -q`
Expected: `test_cohort_gate_blocks_no_recurrence` fails — currently returns a degenerate matrix with no `suitable` key.

- [ ] **Step 3: Add the import**

In `backend/routers/ml.py`, add next to the timegrain import (after line 17 area):

```python
from analytics.cohort_check import check_suitability
```

- [ ] **Step 4: Insert the gate in the transactional branch**

Replace the transactional date-parse block (lines 633-642):

```python
    # ── Transactional mode (default) ────────────────────────────────────────────
    try:
        parsed = _try_parse_dates(df[body.date_col])
        df = df.with_columns(parsed.alias("_date"))
    except ValueError as e:
        raise HTTPException(400, str(e))

    df = df.drop_nulls(subset=["_date"])
    if len(df) == 0:
        raise HTTPException(400, "No valid dates after parsing")
```

with:

```python
    # ── Transactional mode (default) ────────────────────────────────────────────
    try:
        parsed = _try_parse_dates(df[body.date_col])
    except ValueError as e:
        raise HTTPException(400, str(e))

    suit = check_suitability(df, body.date_col, body.user_col, parsed)
    if not suit["suitable"]:
        return suit

    df = df.with_columns(parsed.alias("_date"))
    df = df.drop_nulls(subset=["_date"])
    if len(df) == 0:
        raise HTTPException(400, "No valid dates after parsing")
```

- [ ] **Step 5: Run tests + full suite**

Run: `cd backend ; uv run pytest tests/test_ml.py -k cohort -q` → all cohort tests pass (including the existing ones).
Then: `cd backend ; uv run pytest -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(ml): gate cohort on data suitability (transactional mode)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: Cohort UI — suitability explanation (Component 5 — frontend)

When the backend returns `suitable: false` (Task 10), render an explanation instead of a misleading matrix. Guard **all three** cohort render sites: `MlCohortView` (dedicated tab), `MlChartView`'s inline cohort panel, and `CohortCompareView` (per panel). `CohortResult` keeps its core fields **required** (so the existing table code needs no `?.` churn) and gains four **optional** suitability fields.

**Files:**
- Modify: `frontend/src/api/ml.ts` (add 4 optional fields to `CohortResult`)
- Modify: `frontend/src/components/ml/MlCohortView.tsx` (suitability block)
- Modify: `frontend/src/components/ml/MlChartView.tsx` (guard inline cohort)
- Modify: `frontend/src/components/ml/CohortCompareView.tsx` (per-panel guard)

- [ ] **Step 1: Add suitability fields to `CohortResult` (keep core required)**

In `frontend/src/api/ml.ts` replace the `CohortResult` interface (lines 69-76). Add only the four suitability fields — do **not** make `cohorts/periods/matrix/cohort_sizes` optional (a successful result always has them, and the `suitable !== false` guards below ensure the table code only runs when they're present, so no cascade of "possibly undefined" errors):

```typescript
export interface CohortResult {
  cohorts:         string[]
  periods:         number[]
  matrix:          (number | null)[][]
  cohort_sizes:    number[]
  all_users_row?:  (number | null)[]
  all_users_size?: number
  // suitability-gate shape (transactional mode, unsuitable data → HTTP 200):
  suitable?:       boolean
  reasons?:        string[]
  needs?:          string
  role_hint?:      { date: string; user: string }
}
```

(`runCohort` is unchanged here; its `period` type is widened in Task 12.)

- [ ] **Step 2: Render the suitability block in MlCohortView**

In `frontend/src/components/ml/MlCohortView.tsx`, the result table is rendered by `{result && (` at lines 270-271. Replace those two lines so unsuitable data shows the explanation and the table only renders when suitable. Uses Tailwind `amber` utilities (confirmed available — `text-danger`/`text-amber-*` are used across the ML views):

old:
```tsx
      {/* Retention table */}
      {result && (
```
new:
```tsx
      {result && result.suitable === false && (
        <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/5">
          <p className="text-amber-400 text-sm font-semibold mb-2">
            Dữ liệu này chưa phù hợp cho phân tích Cohort
          </p>
          <ul className="list-disc pl-5 text-gray-400 text-xs space-y-1">
            {result.reasons?.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          {result.needs && <p className="text-gray-500 text-[11px] mt-2">{result.needs}</p>}
        </div>
      )}

      {/* Retention table */}
      {result && result.suitable !== false && (
```

The existing matrix-table JSX (the `<>…</>` body after the old `{result && (`) is untouched.

- [ ] **Step 3: Guard the inline cohort in MlChartView**

In `frontend/src/components/ml/MlChartView.tsx`, the inline cohort result renders at `{cohortResult && (` on line 493. Replace that opening so unsuitable data shows a compact note instead of the table:

old:
```tsx
              {cohortResult && (
                <div className="overflow-auto rounded-lg border border-white/8">
```
new:
```tsx
              {cohortResult && cohortResult.suitable === false && (
                <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
                  <p className="text-amber-400 text-xs font-semibold mb-1">Dữ liệu chưa phù hợp cho Cohort</p>
                  <ul className="list-disc pl-4 text-gray-500 text-[10px] space-y-0.5">
                    {cohortResult.reasons?.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}

              {cohortResult && cohortResult.suitable !== false && (
                <div className="overflow-auto rounded-lg border border-white/8">
```

The existing inline cohort table (everything inside the original `{cohortResult && (…)}`) is untouched.

- [ ] **Step 4: Guard the compare view**

In `frontend/src/components/ml/CohortCompareView.tsx`, the result area is a ternary chain (`'error' in … ? (…) : result ? (<table>) : loading ? (…) : (…)`). Insert a suitability branch **before** the `) : result ? (` at line 133:

old:
```tsx
        ) : result ? (
          <>
            <table className="text-[10px] border-collapse w-full">
```
new:
```tsx
        ) : result && (result as CohortResult).suitable === false ? (
          <div className="px-3 py-3">
            <p className="text-amber-400 text-xs font-semibold mb-1">Không phù hợp cohort</p>
            <ul className="list-disc pl-4 text-gray-500 text-[10px] space-y-0.5">
              {(result as CohortResult).reasons?.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        ) : result ? (
          <>
            <table className="text-[10px] border-collapse w-full">
```

The existing `<table>…</table>` + sparkline (the `: result ? (<>…</>)` body) is untouched.

- [ ] **Step 5: Verify the build**

Run: `cd frontend ; npm run build`
Expected: build succeeds, zero TS errors. (Because the core `CohortResult` fields stay required, the existing matrix/table code needs no changes.)

- [ ] **Step 6: Manual smoke**

Upload no-recurrence data (e.g. one row per customer per month) → Cohort tab shows the amber explanation block (with reasons), not a misleading 100% column. The inline cohort in Charts and each Compare panel show the same note. Upload event-level recurring data → all three render the matrix as before.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/ml.ts frontend/src/components/ml/MlCohortView.tsx frontend/src/components/ml/MlChartView.tsx frontend/src/components/ml/CohortCompareView.tsx
git commit -m "feat(ml): cohort suitability UI — explain unsuitable data (3 render sites)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 12: Cohort quarter/year periods (Component 5 — optional polish)

Add `quarter` and `year` to cohort period selection end-to-end. The new grains use **monotonic** period indices (`year*4 + quarter`, `year`) so retention offsets stay correct across year boundaries — unlike the existing month/week `year*100+x` encoding (a pre-existing latent bug; left unchanged, out of scope). Lowest priority; safe to defer or drop. Ships after Tasks 9-11.

**Files:**
- Test: `backend/tests/test_ml.py` (append a quarter-offset test)
- Modify: `backend/routers/ml.py` (`run_cohort` period branches + `fmt_period`)
- Modify: `frontend/src/components/ml/cohortUtils.ts` (`Period`)
- Modify: `frontend/src/api/ml.ts` (`runCohort` period type)
- Modify: `frontend/src/components/ml/MlCohortView.tsx` (period buttons + `periodLabel` + legend)
- Modify: `frontend/src/components/ml/CohortCompareView.tsx` (period buttons + `periodLabel`)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ml.py` (uses the file's existing `client` fixture + upload pattern; `io` is already imported). It proves quarter offsets are **monotonic** within a year (Q1→Q2 = offset 1, Q1→Q4 = offset 3) and that cohort labels read `YYYY-Qn`:

```python
# ── Cohort quarter period (Component 5, Task 12) ──────────────────────────────
def test_cohort_quarter_offsets_are_monotonic(client):
    # Both users acquired 2024-Q1. U1 returns in Q2 (offset 1); U2 in Q4 (offset 3).
    # Each user also spans 2 distinct months → passes the suitability gate
    # (check_suitability measures recurrence by month, not by the chosen period).
    csv = (
        b"date,user\n"
        b"2024-01-15,U1\n2024-04-15,U1\n"
        b"2024-02-10,U2\n2024-10-10,U2\n"
    )
    up = client.post(
        "/api/ml/upload",
        files={"file": ("cohq.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.post("/api/ml/cohort", json={
        "file_id": up["file_id"], "date_col": "date", "user_col": "user",
        "period": "quarter",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d.get("suitable") is not False     # gate passed → full result (no suitable key)
    assert d["cohorts"] == ["2024-Q1"]        # both acquired Q1 2024 → one cohort
    assert d["periods"] == [0, 1, 2, 3]       # max offset 3 ⇒ 4 columns
    assert d["matrix"][0][0] == 100.0         # offset 0 = 2/2 users
    assert d["matrix"][0][1] == 50.0          # offset 1 = U1 only
    assert d["matrix"][0][3] == 50.0          # offset 3 = U2 only
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_ml.py::test_cohort_quarter_offsets_are_monotonic -q`
Expected: FAIL — `quarter` currently falls into the month `else` branch, so labels are `2024-01`/`2024-02` (two cohorts) and offsets use `year*100+month` (non-monotonic). The `cohorts`/`periods` assertions fail.

- [ ] **Step 3: Add quarter/year branches to `run_cohort`**

In `backend/routers/ml.py`, replace the period if/elif/else block (currently lines 644-655 — **match by content**, since Task 10 inserts code above it and shifts line numbers):

old:
```python
    if body.period == "week":
        df = df.with_columns(
            (pl.col("_date").dt.year() * 100 + pl.col("_date").dt.week()).alias("_period_num")
        )
    elif body.period == "day":
        df = df.with_columns(
            pl.col("_date").dt.epoch("d").cast(pl.Int64).alias("_period_num")
        )
    else:
        df = df.with_columns(
            (pl.col("_date").dt.year() * 100 + pl.col("_date").dt.month()).alias("_period_num")
        )
```
new:
```python
    if body.period == "week":
        df = df.with_columns(
            (pl.col("_date").dt.year() * 100 + pl.col("_date").dt.week()).alias("_period_num")
        )
    elif body.period == "day":
        df = df.with_columns(
            pl.col("_date").dt.epoch("d").cast(pl.Int64).alias("_period_num")
        )
    elif body.period == "quarter":
        # Monotonic quarter index: year*4 + (0..3) ⇒ consecutive quarters differ by 1
        df = df.with_columns(
            (pl.col("_date").dt.year() * 4 + (pl.col("_date").dt.month() - 1) // 3)
            .cast(pl.Int64).alias("_period_num")
        )
    elif body.period == "year":
        df = df.with_columns(
            pl.col("_date").dt.year().cast(pl.Int64).alias("_period_num")
        )
    else:
        df = df.with_columns(
            (pl.col("_date").dt.year() * 100 + pl.col("_date").dt.month()).alias("_period_num")
        )
```

(`max_cap = 30 if body.period == "day" else 11` already covers quarter/year through the `else` — no change.)

- [ ] **Step 4: Extend `fmt_period` for quarter/year**

In `backend/routers/ml.py`, replace `fmt_period` (currently lines 687-696 — match by content):

old:
```python
    def fmt_period(p: int) -> str:
        if body.period == "week":
            y, m = divmod(p, 100)
            return f"{y}-W{m:02d}"
        elif body.period == "day":
            d = date(1970, 1, 1) + timedelta(days=int(p))
            return d.strftime("%b %d")
        else:
            y, m = divmod(p, 100)
            return f"{y}-{m:02d}"
```
new:
```python
    def fmt_period(p: int) -> str:
        if body.period == "week":
            y, m = divmod(p, 100)
            return f"{y}-W{m:02d}"
        elif body.period == "day":
            d = date(1970, 1, 1) + timedelta(days=int(p))
            return d.strftime("%b %d")
        elif body.period == "quarter":
            y, q = divmod(p, 4)
            return f"{y}-Q{q + 1}"
        elif body.period == "year":
            return str(int(p))
        else:
            y, m = divmod(p, 100)
            return f"{y}-{m:02d}"
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_ml.py::test_cohort_quarter_offsets_are_monotonic -q`
Expected: PASS. Then run the whole suite: `cd backend ; uv run pytest -q` — all green.

- [ ] **Step 6: Widen the frontend `Period` type**

In `frontend/src/components/ml/cohortUtils.ts` replace line 3:

old:
```typescript
export type Period = 'day' | 'week' | 'month'
```
new:
```typescript
export type Period = 'day' | 'week' | 'month' | 'quarter' | 'year'
```

- [ ] **Step 7: Widen `runCohort`'s period parameter**

In `frontend/src/api/ml.ts` replace the `runCohort` signature's first line (line 79):

old:
```typescript
  file_id: string, date_col: string, user_col: string, period: 'month' | 'week' | 'day',
```
new:
```typescript
  file_id: string, date_col: string, user_col: string,
  period: 'day' | 'week' | 'month' | 'quarter' | 'year',
```

- [ ] **Step 8: Add quarter/year to MlCohortView**

In `frontend/src/components/ml/MlCohortView.tsx`:

8a. Period buttons (line 203) — add the two grains:

old:
```tsx
                {(['day','week','month'] as Period[]).map(p => (
```
new:
```tsx
                {(['day','week','month','quarter','year'] as Period[]).map(p => (
```

8b. `periodLabel` (lines 128-132) — add quarter/year cases:

old:
```tsx
  const periodLabel = (n: number) => {
    if (period === 'day')  return `Day ${n}`
    if (period === 'week') return `Wk ${n}`
    return `Mo ${n}`
  }
```
new:
```tsx
  const periodLabel = (n: number) => {
    if (period === 'day')     return `Day ${n}`
    if (period === 'week')    return `Wk ${n}`
    if (period === 'quarter') return `Q ${n}`
    if (period === 'year')    return `Yr ${n}`
    return `Mo ${n}`
  }
```

8c. The legend caption (line 347) — extend the day/week/month ternary so quarter/year read correctly:

old:
```tsx
                : `${period === 'day' ? 'Day' : period === 'week' ? 'Week' : 'Month'} 0 = first activity`}
```
new:
```tsx
                : `${period === 'day' ? 'Day' : period === 'week' ? 'Week' : period === 'quarter' ? 'Quarter' : period === 'year' ? 'Year' : 'Month'} 0 = first activity`}
```

- [ ] **Step 9: Add quarter/year to CohortCompareView**

In `frontend/src/components/ml/CohortCompareView.tsx`:

9a. Period buttons (line 331):

old:
```tsx
            {(['day', 'week', 'month'] as Period[]).map(p => (
```
new:
```tsx
            {(['day', 'week', 'month', 'quarter', 'year'] as Period[]).map(p => (
```

9b. `periodLabel` (lines 45-49):

old:
```tsx
function periodLabel(n: number, period: Period): string {
  if (period === 'day')  return `D${n}`
  if (period === 'week') return `Wk${n}`
  return `Mo${n}`
}
```
new:
```tsx
function periodLabel(n: number, period: Period): string {
  if (period === 'day')     return `D${n}`
  if (period === 'week')    return `Wk${n}`
  if (period === 'quarter') return `Q${n}`
  if (period === 'year')    return `Yr${n}`
  return `Mo${n}`
}
```

> Leave the inline cohort in `MlChartView` (its `cohortPeriod` is a local `'day'|'week'|'month'` union, line 164) at day/week/month — it's a quick-look; quarter/year live in the dedicated Cohort tab + Compare view. Intentional, not an omission.

- [ ] **Step 10: Verify the build**

Run: `cd frontend ; npm run build`
Expected: build succeeds, zero TS errors.

- [ ] **Step 11: Manual smoke**

Upload multi-year dated data with repeat customers; Cohort tab → pick **quarter** → cohort labels read `2024-Q1` etc. and offsets advance by 1 per quarter; pick **year** → `2024`/`2025` cohorts. Compare view offers the same grains.

- [ ] **Step 12: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py frontend/src/components/ml/cohortUtils.ts frontend/src/api/ml.ts frontend/src/components/ml/MlCohortView.tsx frontend/src/components/ml/CohortCompareView.tsx
git commit -m "feat(ml): cohort quarter/year periods (monotonic offsets)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Backend:** `cd backend ; uv run pytest -q` — entire suite green (new + existing).
- [ ] **Frontend:** `cd frontend ; npm run build` — clean type-check + build.
- [ ] **End-to-end smoke** (`python run.py`): correlation heatmap loads with no 500 and shows the excluded-columns note; Charts time-series with YoY/PoP/grain; suggestions chips pre-fill; forecast monthly stepping; cohort gate explains unsuitable data; cohort quarter/year grains label as `2024-Q1`/`2024` with monotonic offsets.
- [ ] **Confirm not pushed:** `git log --oneline origin/master..HEAD` lists the new commits as local-only. Do **not** push.

## Out of scope (Spec B / non-goals)

Multi-file merge (the 23-xlsx phone-dedup workflow), auto-pick-best forecast, Prophet/deep-learning, new dependencies, saved chart presets, image export, i18n toggle. These are deferred to a separate brainstorm after Spec A ships.
