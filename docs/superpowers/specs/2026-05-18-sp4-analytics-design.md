# SP4 Analytics — Design Spec
**Date:** 2026-05-18  
**Pages:** KPI Tracker · ML Studio · Performance  
**Approach:** A — extend existing FastAPI backend, DuckDB in-process for ML Studio

---

## 1. Overview

Three new Analytics pages added to the existing Leonie Work Hub. All share the same dark theme, Lucide icon vocabulary, and connect to the existing FastAPI backend on port 8000. No new services — DuckDB runs as a library inside the Python process.

**Icon rule:** All icons use Lucide React. No emoji as functional icons. Emojis only in empty-state decorative text.

---

## 2. KPI Tracker

### Purpose
Log and visualize DA output metrics (queries written, EDAs done, tasks done) and business metrics (GMV, conversion rate, etc.) over time — both entered manually.

### Layout
Left panel (280px) — scrollable list of KPI entries with category filter tabs (All / DA Output / Business). Right panel — metric selector dropdown + date range picker + line chart (Recharts) + 3 stat cards (total, delta vs prev period, target).

### Data Model (backend)
Existing `kpi_entries` table already in SQLite schema:
```sql
CREATE TABLE kpi_entries (
    id      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    metric  TEXT NOT NULL,       -- e.g. "Queries viết", "GMV ColosBaby"
    value   REAL NOT NULL,
    date    TEXT NOT NULL,       -- ISO date YYYY-MM-DD
    note    TEXT,
    created TEXT NOT NULL DEFAULT (datetime('now'))
);
```
Add `category TEXT NOT NULL DEFAULT 'da_output' CHECK(category IN ('da_output','business'))` column via migration.

### Backend (`/kpi` router)
- `GET /kpi` — list entries, filter by `?metric=&category=&from=&to=`
- `POST /kpi` — create entry `{ metric, value, date, category, note? }`
- `DELETE /kpi/{id}` — delete entry
- `GET /kpi/metrics` — distinct metric names (for dropdown autocomplete)

### Frontend Components
- `KpiTracker.tsx` (page) — state: entries, selectedMetric, dateRange, apiError
- `KpiList.tsx` — left panel list with category filter tabs
- `KpiItem.tsx` — single row: metric name, value, category badge, date
- `KpiForm.tsx` — modal/inline form: metric (text + autocomplete), value, category, date, note
- `KpiChart.tsx` — Recharts LineChart, grouped by metric + date range selector

### Charts
Recharts `<LineChart>` with `<Tooltip>` and `<CartesianGrid>`. Color by category: `#34d399` for DA Output, `#60a5fa` for Business. Date range options: 7d / 30d / 90d / All.

---

## 3. Performance

### Purpose
Streak tracker with custom rule + monthly output summary derived from live data (tasks, EDA, KPI entries).

### Layout
Left column (200px) — streak counter (Lucide `Flame` icon), current streak count, rule display, "Edit Rule" button. Right column — 2×2 output metric grid + monthly calendar heatmap.

### Streak Rule
Stored as JSON in a new `performance_settings` SQLite table:
```sql
CREATE TABLE IF NOT EXISTS performance_settings (
    id          INTEGER PRIMARY KEY DEFAULT 1,
    streak_rule TEXT NOT NULL DEFAULT '{"conditions":[{"type":"tasks_done","op":"gte","value":2}],"logic":"OR"}'
    -- logic: "AND" | "OR"
    -- condition types: tasks_done, eda_done, kpi_logged, wip_updated
);
```
Backend evaluates the rule against actual data for each date to compute daily streak status.

### Output Metrics (read-only, derived)
- **Tasks done this month** — `COUNT(*) FROM tasks WHERE status='done' AND updated >= first_of_month`
- **EDA completed** — same pattern on `eda_requests`
- **KPI logs** — `COUNT(*) FROM kpi_entries WHERE created >= first_of_month`
- **WIP avg progress** — `AVG(progress) FROM wip_items`

### Calendar Heatmap
30-day grid, one cell per day. Color: `#34d399` = rule fully met, `#fbbf24` = partially met (for AND rules: some but not all conditions true; for OR rules: N/A — it's either met or not), `rgba(255,255,255,0.05)` = miss. Computed by backend endpoint.

### Backend (`/performance` router)
- `GET /performance/summary` — returns streak, output metrics, 30-day calendar array
- `GET /performance/settings` — returns current streak rule
- `POST /performance/settings` — saves new streak rule JSON

### Frontend Components
- `Performance.tsx` (page) — fetches summary on mount
- `StreakCard.tsx` — `Flame` icon, count, rule text, edit button
- `RuleEditor.tsx` — inline form to build/edit rule conditions (type + op + value + AND/OR)
- `OutputGrid.tsx` — 2×2 card grid with derived stats
- `CalendarHeatmap.tsx` — 30-cell grid

---

## 4. ML Studio

### Purpose
Upload CSV/Excel → Polars reads → DuckDB SQL query → auto-charts + stats tests + forecast. Supports up to 10M rows; all heavy processing on backend.

### Layout
Left sidebar (260px): drag-drop upload zone, dataset info (rows/cols/size), column list, SQL editor (Monaco or `<textarea>` with mono font), Run button.  
Right panel: tab bar (Charts · Table · Stats Tests · Forecast), chart type selector, result area.

### Backend (`/ml` router)

**File Upload**
- `POST /ml/upload` — multipart form, Polars reads CSV/Excel, infers schema, stores file path in `uploaded_datasets` table, returns `{ file_id, filename, rows, cols, columns: [{name, dtype}] }`
- `DELETE /ml/{file_id}` — delete uploaded file + DB record

**Query**
- `POST /ml/query` — `{ file_id, sql }` — DuckDB registers Polars DataFrame as virtual table named `data`, executes SQL, returns `{ columns, rows, duration_ms }` (max 10k rows returned to frontend; backend full scan for stats)

**Auto Charts**
- `POST /ml/auto-chart` — `{ file_id, x_col, y_col?, chart_type }` — backend generates Recharts-compatible data array

**Stats Tests**
- `POST /ml/stats` — `{ file_id, test, col_a, col_b? }` — runs via `scipy` (or `polars` native):
  - `correlation` — Pearson r + p-value
  - `ttest` — independent samples t-test
  - `describe` — summary stats per column
  - `distribution` — histogram bins

**Forecast**
- `POST /ml/forecast` — `{ file_id, date_col, value_col, periods }` — simple linear trend or Prophet (optional dep); returns forecast array + confidence interval

### DuckDB Integration
```python
import duckdb
conn = duckdb.connect()          # in-memory, per request
conn.register("data", df)        # df is polars DataFrame
result = conn.execute(sql).df()  # returns pandas, convert to list
```
No persistent DuckDB file needed — each query gets a fresh connection with the dataset registered.

### Frontend Components
- `MlStudio.tsx` (page)
- `MlUpload.tsx` — drag-drop zone (`Upload` Lucide icon), dataset info card, column list with dtype badges
- `MlSqlEditor.tsx` — `<textarea>` with mono font, line numbers (simple), Run button (`Play` icon)
- `MlResultTabs.tsx` — tab container
- `MlChartView.tsx` — chart type buttons + Recharts output
- `MlTableView.tsx` — paginated result table (max 500 rows shown)
- `MlStatsView.tsx` — test selector + result display (r value, p-value, interpretation)
- `MlForecastView.tsx` — date col + value col + periods input + line chart with forecast

### Error Handling
- SQL syntax errors → backend returns 400 with DuckDB error message → shown inline under editor
- File too large (> 500MB) → reject at upload with clear message
- Query timeout (> 30s) → backend cancels with 504

---

## 5. Shared Patterns

**All pages follow existing conventions:**
- Left panel 280px or 260px + right panel flex-1
- `apiError` banner: `absolute top-4 right-4` inside `relative` wrapper
- Lucide icons throughout — no emoji as functional UI elements
- `btn-primary`, `btn-ghost`, `btn-danger`, `input-base`, `badge` CSS classes from existing stylesheet
- Error state: red text `text-danger text-xs`
- Loading state: spinner or `opacity-50 disabled`

**New backend dependencies (add to `backend/pyproject.toml`):**
- `duckdb` — SQL engine for ML Studio
- `polars` — fast CSV/Excel reader
- `openpyxl` — Excel support for Polars
- `scipy` — stats tests (optional, graceful fallback)

**New frontend dependencies:**
- `recharts` — not yet installed, must be added
- No Monaco editor — use styled `<textarea>` to keep bundle small

---

## 6. File Structure

```
backend/routers/
  kpi.py          ← new
  performance.py  ← new
  ml.py           ← new

frontend/src/
  pages/analytics/
    KpiTracker.tsx      ← replace placeholder
    Performance.tsx     ← replace placeholder
    MlStudio.tsx        ← replace placeholder
  components/
    kpi/
      KpiList.tsx
      KpiItem.tsx
      KpiForm.tsx
      KpiChart.tsx
    performance/
      StreakCard.tsx
      RuleEditor.tsx
      OutputGrid.tsx
      CalendarHeatmap.tsx
    ml/
      MlUpload.tsx
      MlSqlEditor.tsx
      MlResultTabs.tsx
      MlChartView.tsx
      MlTableView.tsx
      MlStatsView.tsx
      MlForecastView.tsx
  api/
    kpi.ts          ← new
    performance.ts  ← new
    ml.ts           ← new
```

---

## 7. Out of Scope (SP4)

- Monaco editor (styled textarea sufficient)
- Prophet forecast (use linear trend; Prophet is optional)
- Export to Excel/CSV from ML Studio results
- Team KPIs (multi-user) — Leonie is solo
- Real-time query progress bar
