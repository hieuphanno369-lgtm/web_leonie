# ML Studio Analytics Upgrade — Design Spec (Spec A)

**Date:** 2026-06-06
**Approach:** A — backend "analytics engine" + thin frontend (chosen by user)
**Target directory (live app):** `D:\assitant_tools\tools_performance\08_Projects\leonie` (branch `master`, local commits only — **never push**, history has secrets)
**Scope:** Analysis upgrades only. The multi-file **merge / data-prep** subsystem is a separate effort (**Spec B**, to be brainstormed after Spec A ships).

---

## Context

ML Studio (`pages/analytics/MlStudio.tsx`) has tabs Table · Charts · Stats · Forecast · Cohort, running on Polars/DuckDB in `backend/routers/ml.py`. Five user requests:

1. **Charts — time comparison.** Data has dates + daily detail. User wants to chart by **day/week/month/quarter/year** and compare periods (esp. **YoY same-period**). Today `MlChartView` plots raw query rows with no time grouping.
2. **Cohort — make it meaningful.** On a daily-aggregate dataset (1 row/day, no recurring entity) cohort math degenerates to "1 user / 100%". Needs data-suitability detection + field-role guidance.
3. **Correlation — broken.** `/correlation` throws "Failed to load" (HTTP 500). Root cause: a constant column (e.g. `has_new_account` ≡ 1) makes `scipy.pearsonr` return `NaN`; Starlette serializes JSON with `allow_nan=False` → 500. Plus a hidden row-misalignment bug (per-column independent `drop_nulls()` then `[:n]` slice).
4. **Forecast — by time grain.** When grouped by month, predict next month's total. Today all methods step dates by `last_date + timedelta(days=i)` regardless of granularity, and never aggregate to a grain.
5. **Field-placement suggestions.** Help a non-technical user visualize from just a dataset: suggest which field goes into which chart slot.

The user confirmed their data spans **all shapes** (event-level ≥2yr, daily-aggregate, dateless customer lists, mixed), so every feature must **auto-detect data shape** and degrade gracefully — never assume one shape.

---

## Design decisions (from clarification)

| # | Decision |
|---|----------|
| Order | Spec A first, then Spec B. Within A: **correlation fix ships first** (live bug), then charts → forecast → suggestions → cohort. |
| Chart data source | **Both** — keep "chart the SQL result" mode, **add** a field-picker mode that aggregates the **full dataset** via backend. |
| Aggregation | Dropdown `SUM · AVG · COUNT · COUNT DISTINCT · MIN · MAX`, default **SUM**. |
| Comparison types | **YoY same-period · PoP (DoD/WoW/MoM) · Rolling avg (7/28) · Cumulative (MTD/QTD/YTD)** as primary; **Index-to-100** and **% share** as optional extras. |
| Comparison rendering | **Both** — overlay line(s) + % badges on the chart, **and** a delta table below. |
| Field suggestions | **Both** — smart auto-filled defaults **and** click-to-apply "recipe cards". |
| AI usage | **Hybrid** — heuristics run instantly offline; an explicit **✨ AI** button calls the existing interpret endpoint (Claude Haiku → Ollama) for Vietnamese narration. |
| Cohort on unsuitable data | **Block** the run + explain what data is needed + show field-role guidance. |
| Forecast method | Keep **manual** method selection; only add grain aggregation + grain-correct date stepping. |
| UI placement | **Enhance existing tabs** in place — no new tabs. |

---

## Component 0 — Time-grain engine (shared backbone for #1 and #4)

New pure-function module `backend/analytics/timegrain.py` (keeps `ml.py` from bloating; unit-tested in isolation).

```python
Grain = Literal["day", "week", "month", "quarter", "year"]
Agg   = Literal["sum", "mean", "count", "n_unique", "min", "max"]

def truncate_dates(dates: pl.Series, grain: Grain) -> pl.Series:
    # Polars dt.truncate: day="1d", week="1w" (ISO, Monday), month="1mo",
    # quarter="1q", year="1y". Each date -> start-of-period.

def aggregate_series(df, date_col, value_col, grain, agg) -> dict:
    # parse date_col via _try_parse_dates, truncate to grain, group_by period,
    # apply agg, sort by period. Returns {period_starts: [date], labels: [str], values: [float]}.

def suggest_grain(period_min, period_max) -> Grain:
    # coarsest grain that yields ~8..60 buckets; prefer day->week->month->quarter->year.
    # (Revenue 887 days -> "month".)

def add_comparisons(period_starts, values, grain, comparisons, rolling_window) -> dict:
    # returns only the requested keys.
```

**Comparison math (one source of truth):**

- **yoy** — for each period `p`, look up the value at the same sub-period one year earlier, by period-start:
  - month → `date(y-1, m, 1)`; quarter → same quarter, `y-1`; day → same calendar date `y-1`;
    week → ISO `(iso_year-1, iso_week)` (fallback: shift 52 weeks); year → `y-1`.
  - `delta_pct = (cur - prior) / prior * 100` when `prior` is non-null and ≠ 0, else `null`.
- **pop** — shift by 1 period (`values[i-1]`), same delta_pct rule.
- **rolling** — rolling mean over `rolling_window` periods (default 7; UI also offers 28).
- **cumulative** — running sum that resets on a boundary. `reset` param `month|quarter|year`, default `year` (YTD). At month grain, `year`→YTD, `quarter`→QTD; at day grain, `month`→MTD, etc.
- **index100** *(optional)* — `value / first_nonnull * 100`.
- **share** *(optional)* — `value / sum(values) * 100` (per-period share when a `group_col` is set; grand-total share otherwise).

All outputs scrub non-finite floats (`NaN`/`±Inf`) → `null` before serialization.

---

## Component 1 — Charts: time grain + comparisons (#1)

### Backend — new endpoint `POST /api/ml/timeseries`

```python
class TimeseriesIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    grain: Grain | Literal["auto"] = "auto"
    agg: Agg = "sum"
    comparisons: list[str] = []          # subset: yoy, pop, rolling, cumulative, index100, share
    rolling_window: int = 7
    cumulative_reset: Literal["month","quarter","year"] = "year"
    group_col: str | None = None         # optional dimension for share / multi-series
```

Response:

```json
{
  "grain": "month", "agg": "sum", "date_col": "...", "value_col": "...",
  "series": { "labels": ["2024-01", ...], "values": [12345.0, ...] },
  "comparisons": {
    "yoy":        { "values": [null, ...], "delta_pct": [null, ...] },
    "pop":        { "values": [...], "delta_pct": [...] },
    "rolling":    { "window": 7, "values": [...] },
    "cumulative": { "reset": "year", "values": [...] }
  },
  "meta": { "rows_used": 887, "periods": 30, "span_days": 887, "suggested_grain": "month" }
}
```

Only requested comparison keys are present. `grain="auto"` resolves via `suggest_grain` and is echoed back.

### Frontend — enhance `MlChartView.tsx`

- **Mode toggle** in the controls row: `Field-picker | SQL result`.
  - **Field-picker** (default for non-tech, runs full dataset): `Cột ngày ▾` · `Cột giá trị ▾` · `Grain D/W/M/Q/Y` · `Agg ▾` · comparison checkboxes `☑YoY ☑PoP ☑Rolling ☑Lũy kế` (+ "Khác ▾" for index100/share). Calls `/timeseries`.
  - **SQL result** (current behaviour): plots returned rows; adds **client-side grain grouping + rolling** for a quick look. YoY/PoP/cumulative are disabled here with a hint to use field-picker (they need the full dataset).
- **Chart:** primary line + comparison overlays (YoY drawn as a second line aligned by period; rolling as a smoothed line; cumulative as its own toggle/line). `%` change badges rendered on points. Reuse recharts + existing `formatNum`.
- **Delta table** under the chart: `Kỳ · Giá trị · YoY% · PoP%` (columns appear per enabled comparison).
- Empty/short-history states: if YoY has no overlapping prior year, show only available cells + a one-line note.

---

## Component 2 — Forecast by grain (#4), wired to #1

### Backend — extend `/forecast` (`ForecastIn`)

Add `grain: Grain | "auto" = "auto"` and `agg: Agg = "sum"`. Flow:

1. Parse `date_col` (`_try_parse_dates`), sort.
2. If `grain != raw`, aggregate to grain via `aggregate_series` → series of (period_start, value). (Default behaviour for `auto` = `suggest_grain`.)
3. Run the **chosen** method (linear / moving_average / ets / sarimax / supervised) on the aggregated series.
4. **Fix date stepping** — step future periods by grain, not days:
   - day → `+i days`; week → `+i*7 days`; month → `+i months`; quarter → `+i*3 months`; year → `+i years` (month-end safe via `dateutil`-style month add).
5. Seasonal period auto-derives from grain (month→12, quarter→4, week→52, day→7) unless `seasonal_period` is explicitly set.
6. `periods` = number of **future grain units** ("3 tháng tới"). `history` is the aggregated series.

`/forecast/compare` and `/forecast/interpret` inherit grain/agg the same way.

### Frontend — `MlForecastView.tsx`

- Add `Grain ▾` + `Agg ▾` selectors; horizon label reflects grain ("kỳ" → "tháng/tuần/quý").
- **Default-inherit** `date_col / value_col / grain / agg` from the chart the user is viewing (continuity with #1).
- `seasonal_period` preset auto-set from grain (still overridable). Method selection stays manual.

---

## Component 3 — Correlation fix (#3) — **ships first, straight to main**

### Backend — fix `GET /api/ml/{file_id}/correlation`

1. From numeric columns (cap 15), **drop constant / all-null** columns (`n_unique <= 1`) before building the matrix; collect them as `excluded_columns: [{name, reason}]` (`reason ∈ {"constant","all_null"}`).
2. If `< 2` columns remain → `HTTPException(400, "...")` with a clear Vietnamese message.
3. For each pair `(c1, c2)`: select the two columns into one frame, `drop_nulls()` **together** (pairwise-complete); require `>= 3` rows; compute Pearson. Diagonal = `1.0`.
4. Pairs with `< 3` valid rows or zero variance → cell `null`. Any residual non-finite → `null` (eliminates the `allow_nan=False` 500).

Response extends the existing type:

```json
{ "columns": [...], "matrix": [[1.0, 0.87, null], ...],
  "excluded_columns": [{ "name": "has_new_account", "reason": "constant" }] }
```

### Frontend — `CorrelationHeatmap.tsx` / `types.ts`

- `CorrelationMatrix` already types `matrix: (number|null)[][]`; add `excluded_columns?: {name:string; reason:string}[]`.
- Render `null` cells as a neutral gray "—" (guard `corrToColor`/`toFixed` against null).
- Show a one-line note under the heatmap: `"Đã bỏ N cột hằng số (không có biến thiên): …"` when `excluded_columns` is non-empty.

### Test (TDD — write first)

`backend/tests/test_ml.py`: a dataset with one constant column + nulls must return **200** with `1.0` on the diagonal, a `null` where a pair is constant, and the constant column listed in `excluded_columns`. This test must fail on current code (reproduces the 500) and pass after the fix.

---

## Component 4 — Field suggestions for non-tech users (#5)

### Backend — new lightweight `GET /api/ml/profile/{file_id}`

Per column: `name`, `dtype`, `role`, `cardinality (n_unique)`, `null_pct`, `is_constant`, `min`/`max` (numeric/date), few `sample` values.

`role` heuristic:
- **date** — dtype date, or parseable by `_try_parse_dates`, or `_is_date_id_column`.
- **id** — high-cardinality (≈unique) string/int, or name matches `id|code|phone|sf.*id`.
- **flag** — numeric/bool with `n_unique <= 2` (e.g. 0/1).
- **metric** — numeric, not id, not flag.
- **dimension** — low-cardinality (`n_unique <= ~50`) non-numeric.

### Frontend — heuristic + recipe cards (instant; ✨ AI optional)

From the profile, the Charts field-picker:
- **Auto-fills smart defaults** (a date col + a metric + a sensible grain + chart type).
- Renders **recipe cards** (click → fills X/Y/chart-type/grain/agg/comparison + renders):
  - `📈 {metric} theo {grain}` · `📅 YoY {metric}` (if ≥2 yrs) · `🏆 Top {dimension} theo {metric}` · `📊 Phân bố {dimension}` · `📉 Phân phối {metric}` · `🔵 {m1} vs {m2}` · `👥 Cohort theo {date}` (if a recurring id exists → links to Cohort tab).
- **✨ Giải thích (AI)** button: posts the chart context to the existing interpret endpoint → Vietnamese narrative. Heuristics never block on AI.

New components: `components/ml/FieldPicker.tsx`, `components/ml/RecipeCards.tsx`. Client `api/ml.ts`: `fetchProfile`.

---

## Component 5 — Cohort guardrails (#2)

### Backend — suitability pre-check in `/cohort`

New pure helper `backend/analytics/cohort_check.py: check_suitability(df, date_col, user_col) -> dict`:

1. `user_col` present and not mostly null.
2. **Recurrence** — count entities appearing in `>= 2` distinct cohort periods. `~0` (e.g. Revenue, 1 row/day, no repeat entity) → unsuitable.
3. `>= 2` distinct cohort-start periods.
4. `date_col` parseable.

If unsuitable, `/cohort` returns `200` with:

```json
{ "suitable": false,
  "reasons": ["Mỗi khách chỉ xuất hiện 1 lần — không đo được giữ chân", ...],
  "needs": "Cần cột định danh KH lặp lại qua nhiều kỳ + cột ngày sự kiện",
  "role_hint": { "date": "<best date col>", "user": "<best id col>" } }
```

Suitable → run as today (count-distinct retention; sum-metric pre-agg mode unchanged).

### Frontend — `MlCohortView.tsx` / `cohortUtils.ts`

- On `suitable:false` → **block** the retention render; show reasons + `needs` + field-role guidance with labels: **"Cột định danh KH (lặp lại)"**, **"Cột ngày sự kiện"**, **"Giá trị (tùy chọn)"**; pre-select `role_hint` columns when present.
- Extend `Period` type from `'day'|'week'|'month'` to include `'quarter'|'year'` (align with grain engine).

---

## API contracts summary

| Method | Path | Status |
|--------|------|--------|
| `GET`  | `/api/ml/{file_id}/correlation` | **fix** (add `excluded_columns`, null-safe) |
| `POST` | `/api/ml/timeseries` | **new** |
| `POST` | `/api/ml/forecast` | **extend** (`grain`, `agg`) |
| `GET`  | `/api/ml/profile/{file_id}` | **new** |
| `POST` | `/api/ml/cohort` | **extend** (suitability gate) |

---

## Testing (TDD)

- **Backend (`backend/tests/`, `uv run pytest -q`):** write failing tests first for —
  - correlation constant-column (200 + null + `excluded_columns`);
  - `timegrain.aggregate_series` / `suggest_grain` / each comparison (YoY alignment incl. missing prior year, PoP, rolling, cumulative reset);
  - forecast grain stepping (monthly data → monthly future dates);
  - cohort suitability (Revenue-shaped data → `suitable:false`; event-level → `suitable:true`).
- **Frontend:** `npm run build` must stay green (zero new TS errors). Manual smoke per component.

---

## Delivery & validation

- All work lands in the **main working tree** `D:\…\leonie` (branch `master`), committed **locally only** (never push — secrets in history). The worktree does not reach the running app.
- Restart the backend after changes that touch `.env`/startup (`--reload` does not catch `.env`).
- **Ship order:** ① correlation fix (commit + verify on real `Revenue_2024_to_Current.xlsx`) → ② timeseries + charts → ③ forecast grain → ④ profile + suggestions → ⑤ cohort guardrails. Each step: tests green + build green before commit.

---

## File change summary

| File | Change |
|------|--------|
| `backend/analytics/timegrain.py` | **new** — grain truncation, aggregation, grain suggestion, comparison math |
| `backend/analytics/cohort_check.py` | **new** — cohort suitability |
| `backend/routers/ml.py` | fix `/correlation`; add `/timeseries`, `/profile`; extend `/forecast`, `/cohort` |
| `backend/tests/test_ml.py` (+ new test modules) | failing-first tests for all of the above |
| `frontend/src/components/ml/MlChartView.tsx` | mode toggle, field-picker, grain/agg/comparison controls, overlay + delta table |
| `frontend/src/components/ml/FieldPicker.tsx`, `RecipeCards.tsx` | **new** |
| `frontend/src/components/ml/MlForecastView.tsx` | grain/agg selectors, inherit-from-chart defaults |
| `frontend/src/components/ml/MlCohortView.tsx` | suitability block + field-role guidance |
| `frontend/src/components/ml/CorrelationHeatmap.tsx` | null cells + excluded-columns note |
| `frontend/src/components/ml/cohortUtils.ts` | extend `Period` with quarter/year |
| `frontend/src/api/ml.ts`, `types.ts` | `runTimeseries`, `fetchProfile`; extend forecast/cohort/correlation types |

---

## Non-goals (Spec A)

- Multi-file merge / data-prep (**Spec B**).
- Auto-pick "best" forecast method (kept manual per user).
- Prophet / deep-learning forecasters; new Python deps.
- Saving chart presets; image export of charts/heatmap.
- i18n / VN-EN toggle.
