# ML Studio — Analyst Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn ML Studio into an "overview → detail" analysis tool — time drill-down, multi-angle chart suggestions, ranked +/− correlations, clustered measures, plus less friction (Show Code, export, auto-insight).

**Architecture:** Backend stays the source of truth for any "Show Code" string via the pure helper `backend/analytics/codegen.py` (returns `code: str` in the JSON response; frontend only renders it with `CodePanel`). All new frontend logic lands in **small new files** so the 830-line `MlChartView.tsx` only orchestrates. No new dependencies (PNG export uses the browser's own `<canvas>`).

**Tech Stack:** FastAPI + polars + pytest (backend); React 19 + Vite + TypeScript + recharts + lucide-react (frontend). Backend tests run `cd backend ; uv run pytest -q`. Frontend has **no JS test runner** — its gate is `cd frontend ; npm run build` (tsc type-check + vite build) plus a per-task manual checklist in the running app.

**Spec:** `docs/superpowers/specs/2026-06-07-ml-studio-analyst-upgrade-design.md`

---

## Delivery & safety rules (read first)

- **Deliver into the MAIN working tree** `D:\assitant_tools\tools_performance\08_Projects\leonie` — the dev servers (Vite 5177 + uvicorn 8000) run there, so edits made only in a worktree never reach the running app. (If executing inside a worktree, copy the final diffs into main, or run the app from the worktree.)
- **Never push.** `master` history contains live secrets. Commits stay local. Only the orphan `backup-clean` branch may ever be pushed (not part of this plan).
- Commit only when finishing a task (frequent local commits are fine). Commit messages end with the Co-Authored-By trailer shown in the commit steps.
- Do **not** edit `_legacy/`.

## Testing Strategy (why steps differ by layer)

- **Backend (codegen + endpoints):** real TDD with pytest — write the failing test, watch it fail, implement, watch it pass.
- **Frontend:** no runner exists and the spec explicitly avoids adding one. The gate per task is `npm run build` staying green (the TypeScript compiler catches type/contract breaks) **plus** a concrete manual checklist. The two genuinely pure helpers (`chartRecipes.ts`, `insights.ts`) ship with worked input→output examples in their task so behavior can be eyeballed in the browser devtools console.

## File Structure

| File | New/Modify | Responsibility |
|------|-----------|----------------|
| `backend/analytics/codegen.py` | Modify | add `describe_code()` (#1), `drilldown_code()` (#3) |
| `backend/routers/ml.py` | Modify | describe → `{rows, code}` + median/range (#1); new `GET /{file_id}/drilldown` (#3) |
| `backend/tests/test_codegen.py` | Modify | compile tests for the 2 new codegen helpers |
| `backend/tests/test_ml.py` | Modify | describe shape; drilldown grain/filter |
| `frontend/src/types.ts` | Modify | `DrilldownResult` |
| `frontend/src/api/ml.ts` | Modify | `DescribeRow` (+median,range); `fetchDescribe`→`{rows,code}`; `fetchDrilldown` |
| `frontend/src/components/ml/MlDescribePanel.tsx` | Modify | 6 stats + Show Code (#1) |
| `frontend/src/components/layout/Sidebar.tsx` | Modify | move Automation under ML Studio (#7) |
| `frontend/src/components/ml/MlDrilldownView.tsx` | **New** | time drill-down panel (#3) |
| `frontend/src/components/ml/CorrelationRanked.tsx` | **New** | ranked +/− pair list (#5) |
| `frontend/src/components/ml/chartRecipes.ts` | **New** | pure suggestion pool (#2) |
| `frontend/src/components/ml/insights.ts` | **New** | pure auto-insight sentences (#8c) |
| `frontend/src/components/ml/chartExport.ts` | **New** | CSV/PNG export helpers (#8b) |
| `frontend/src/components/ml/MlChartView.tsx` | Modify | scroll fix (#4), clustered (#6), recipe pool (#2), wire drilldown/ranked/insight/export |
| `frontend/src/components/ml/MlTableView.tsx` | Modify | Copy CSV button (#8b) |

## Task order & dependencies

1. #7 Sidebar move — isolated warm-up
2. #1 backend (codegen + endpoint)
3. #1 frontend (api + describe panel)
4. #3 backend (codegen + endpoint)
5. #3 frontend (types + api + `MlDrilldownView` + wire)
6. #4 scroll-jump fix
7. #5 ranked correlation
8. #6 clustered columns — **must precede Task 9** (recipe `apply` calls `setYCols`)
9. #2 recipe pool + ⟳ — depends on Task 8
10. #8c auto-insight — depends on Task 5 (renders under drilldown too)
11. #8b export — depends on Task 5
12. Final verification + commit

---

### Task 1: #7 — Move Automation under ML Studio (Sidebar)

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx:48-62`

- [ ] **Step 1: Edit the NAV array** — remove the Automation item from the `data` (SQL SANDBOX) group and add it to the `analytics` group right after ML Studio, recolored amber. Route path is unchanged so `App.tsx` is untouched.

Replace the `analytics` and `data` category objects (current lines 47-62):

```tsx
  {
    id: 'analytics', label: 'ANALYTICS', color: '#fbbf24',
    items: [
      { path: '/analytics/kpi',   label: 'KPI Tracker', iconName: 'TrendingUp',   color: '#fbbf24' },
      { path: '/analytics/ml',    label: 'ML Studio',   iconName: 'BrainCircuit', color: '#fbbf24' },
      { path: '/data/automation', label: 'Automation',  iconName: 'Workflow',     color: '#fbbf24' },
    ],
  },
  {
    id: 'data', label: 'SQL SANDBOX', color: '#60a5fa',
    items: [
      { path: '/data/sql',      label: 'SQL Sandbox',     iconName: 'Database', color: '#60a5fa' },
      { path: '/data/snippets', label: 'Snippet Library', iconName: 'Code2',    color: '#60a5fa' },
      { path: '/data/fabric',   label: 'Fabric Views',    iconName: 'Layers',   color: '#60a5fa' },
    ],
  },
```

- [ ] **Step 2: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds (exit 0), no TS errors.

- [ ] **Step 3: Manual verify**

Start the app (`python run.py`) → Sidebar shows **ANALYTICS → KPI Tracker · ML Studio · Automation** (amber dot), and **SQL SANDBOX** no longer lists Automation. Click Automation → still navigates to the automation page (route `/data/automation` unchanged).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(sidebar): move Automation under ML Studio (Analytics group)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: #1 backend — describe returns `{rows, code}` with median + range

**Files:**
- Modify: `backend/analytics/codegen.py` (add `describe_code`)
- Modify: `backend/routers/ml.py:22-24` (import) and `:495-514` (endpoint)
- Test: `backend/tests/test_codegen.py`, `backend/tests/test_ml.py`

- [ ] **Step 1: Write the failing codegen test**

Append to `backend/tests/test_codegen.py`:

```python
from analytics.codegen import describe_code


def test_describe_code_compiles_and_uses_polars():
    code = describe_code("báo cáo.xlsx")
    _compiles(code)
    assert "read_excel" in code
    assert "median" in code
    assert "range" in code
    assert "f\"" not in code and "f'" not in code   # no f-string in generated code
```

- [ ] **Step 2: Run it — verify it fails**

Run: `cd backend ; uv run pytest tests/test_codegen.py::test_describe_code_compiles_and_uses_polars -q`
Expected: FAIL — `ImportError: cannot import name 'describe_code'`.

- [ ] **Step 3: Implement `describe_code`**

Append to `backend/analytics/codegen.py` (after `cohort_code`):

```python
def describe_code(filename: str) -> str:
    """Snippet tái hiện bảng thống kê mô tả (min/max/mean/median/range/std) cho mỗi
    cột số — khớp endpoint /describe. Không f-string & không '{' trong code sinh ra."""
    return (
        _HEADER +
        "import polars as pl\n\n"
        f"df = {_read_call(filename)}\n"
        "rows = []\n"
        "for col in df.columns:\n"
        "    s = df[col]\n"
        "    if not s.dtype.is_numeric():\n"
        "        continue\n"
        "    arr = s.drop_nulls().cast(pl.Float64)\n"
        "    if len(arr) == 0:\n"
        "        continue\n"
        "    mn = float(arr.min()); mx = float(arr.max())\n"
        "    rows.append(dict(\n"
        "        column=col, min=mn, max=mx, mean=float(arr.mean()),\n"
        "        median=float(arr.median()), range=mx - mn, std=float(arr.std()),\n"
        "    ))\n"
        "print(pl.DataFrame(rows))\n"
    )
```

- [ ] **Step 4: Run the codegen test — verify it passes**

Run: `cd backend ; uv run pytest tests/test_codegen.py::test_describe_code_compiles_and_uses_polars -q`
Expected: PASS.

- [ ] **Step 5: Write the failing endpoint test**

Append to `backend/tests/test_ml.py` (after `test_stats_describe`; `NUMERIC_CSV` already exists at module level — values `a=1..5`, `b=10..50`):

```python
def test_describe_endpoint_returns_rows_and_code(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("num.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{upload['file_id']}/describe")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"rows", "code"}
    a = next(r for r in body["rows"] if r["col"] == "a")
    assert a["median"] == pytest.approx(3.0)
    assert a["range"] == pytest.approx(4.0)      # max 5 − min 1
    assert "import polars" in body["code"]
```

- [ ] **Step 6: Run it — verify it fails**

Run: `cd backend ; uv run pytest tests/test_ml.py::test_describe_endpoint_returns_rows_and_code -q`
Expected: FAIL — endpoint currently returns a bare list, so `set(body)` raises / assertion fails.

- [ ] **Step 7: Update the import in `ml.py`**

Replace the codegen import block (`backend/routers/ml.py:22-24`):

```python
from analytics.codegen import (
    forecast_code, timeseries_code, correlation_code, stats_code, cohort_code,
    describe_code,
)
```

- [ ] **Step 8: Rewrite the describe endpoint body**

Replace `describe_dataset` (`backend/routers/ml.py:495-514`):

```python
@router.get("/{file_id}/describe")
def describe_dataset(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    rows = []
    for col in df.columns:
        s = df[col]
        null_pct = round(s.null_count() / max(len(s), 1) * 100, 1)
        entry: dict = {"col": col, "dtype": str(s.dtype), "nulls": null_pct}
        if s.dtype.is_numeric():
            arr = s.drop_nulls().cast(pl.Float64)
            if len(arr) > 0:
                mn = round(float(arr.min()), 4)    # type: ignore[arg-type]
                mx = round(float(arr.max()), 4)    # type: ignore[arg-type]
                entry["min"]    = mn
                entry["max"]    = mx
                entry["mean"]   = round(float(arr.mean()), 4)    # type: ignore[arg-type]
                entry["median"] = round(float(arr.median()), 4)  # type: ignore[arg-type]
                entry["range"]  = round(mx - mn, 4)
                entry["std"]    = round(float(arr.std()), 4)     # type: ignore[arg-type]
        rows.append(entry)
    return {"rows": rows, "code": describe_code(row["filename"])}
```

- [ ] **Step 9: Run both new tests + the codegen suite — verify pass**

Run: `cd backend ; uv run pytest tests/test_ml.py::test_describe_endpoint_returns_rows_and_code tests/test_codegen.py -q`
Expected: PASS (all).

- [ ] **Step 10: Commit**

```bash
git add backend/analytics/codegen.py backend/routers/ml.py backend/tests/test_codegen.py backend/tests/test_ml.py
git commit -m "feat(ml): describe returns {rows, code} with median + range (#1 backend)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: #1 frontend — Dataset Overview shows 6 stats + Show Code

**Files:**
- Modify: `frontend/src/api/ml.ts:72-85`
- Modify: `frontend/src/components/ml/MlDescribePanel.tsx` (whole file)

- [ ] **Step 1: Update the API types & `fetchDescribe`**

Replace `frontend/src/api/ml.ts:72-85`:

```ts
export interface DescribeRow {
  col: string
  dtype: string
  nulls: number
  min?: number
  max?: number
  mean?: number
  median?: number
  range?: number
  std?: number
}

export interface DescribeResult {
  rows: DescribeRow[]
  code: string
}

export async function fetchDescribe(file_id: string): Promise<DescribeResult> {
  const { data } = await client.get<DescribeResult>(`/ml/${file_id}/describe`)
  return data
}
```

- [ ] **Step 2: Rewrite `MlDescribePanel.tsx`** to consume `{rows, code}`, render Min·Max·Mean·Median·Range·Std (in the existing `overflow-x-auto` so it scrolls sideways in the 280px rail), and add a "Show Code" toggle that mounts `CodePanel`.

Replace the whole file `frontend/src/components/ml/MlDescribePanel.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Code2 } from 'lucide-react'
import type { DatasetInfo } from '../../types'
import { fetchDescribe, type DescribeRow } from '../../api/ml'
import MlSqlEditor from './MlSqlEditor'
import CodePanel from './CodePanel'

interface Props {
  dataset: DatasetInfo
  running: boolean
  sqlError: string
  onRun: (sql: string) => void
}

function fmt(v: number | undefined) {
  if (v === undefined) return '—'
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 3 })
}

export default function MlDescribePanel({ dataset, running, sqlError, onRun }: Props) {
  const [rows,     setRows]     = useState<DescribeRow[]>([])
  const [code,     setCode]     = useState('')
  const [open,     setOpen]     = useState(true)
  const [loading,  setLoading]  = useState(false)
  const [showCode, setShowCode] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchDescribe(dataset.file_id)
      .then(res => { setRows(res.rows); setCode(res.code) })
      .catch(() => { setRows([]); setCode('') })
      .finally(() => setLoading(false))
  }, [dataset.file_id])

  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors"
      >
        <span className="text-[11px] font-medium text-gray-300">Dataset Overview</span>
        <span className="text-gray-600">
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>

      {open && (
        <>
          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-[10px] text-gray-600 px-3 py-2">Loading…</p>
            ) : (
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left  px-2 py-1.5 text-gray-600 font-normal">Column</th>
                    <th className="text-left  px-2 py-1.5 text-gray-600 font-normal">Type</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Nulls%</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Min</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Max</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Mean</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Median</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Range</th>
                    <th className="text-right px-2 py-1.5 text-gray-600 font-normal">Std</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => (
                    <tr key={r.col} className="border-b border-white/3 hover:bg-white/2">
                      <td className="px-2 py-1 text-gray-300 max-w-[80px] truncate" title={r.col}>{r.col}</td>
                      <td className="px-2 py-1 text-gray-600">{r.dtype.replace('DataType.', '')}</td>
                      <td className={`px-2 py-1 text-right ${r.nulls > 20 ? 'text-danger' : r.nulls > 5 ? 'text-yellow-500' : 'text-gray-500'}`}>
                        {r.nulls}%
                      </td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.min)}</td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.max)}</td>
                      <td className="px-2 py-1 text-right text-gray-400">{fmt(r.mean)}</td>
                      <td className="px-2 py-1 text-right text-gray-400">{fmt(r.median)}</td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.range)}</td>
                      <td className="px-2 py-1 text-right text-gray-500">{fmt(r.std)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {code && (
            <div className="px-2 pt-1 pb-2 space-y-1.5">
              <button
                onClick={() => setShowCode(s => !s)}
                className="flex items-center gap-1.5 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <Code2 size={11} /> {showCode ? 'Ẩn code' : 'Show Code'}
              </button>
              {showCode && <CodePanel code={code} filename="describe_overview.py" defaultOpen />}
            </div>
          )}
        </>
      )}

      {/* Quick run controls — sits flush at the bottom of this card */}
      <MlSqlEditor
        disabled={false}
        running={running}
        error={sqlError}
        onRun={onRun}
      />
    </div>
  )
}
```

- [ ] **Step 3: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds, no TS errors.

- [ ] **Step 4: Manual verify**

ML Studio → upload a dataset → left rail "Dataset Overview" shows **Min · Max · Mean · Median · Range · Std** (scroll sideways to see all). Click **Show Code** → a Python snippet panel opens; "Download .py" produces a file that runs. Numbers match the data.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ml.ts frontend/src/components/ml/MlDescribePanel.tsx
git commit -m "feat(ml): Dataset Overview shows median/range + Show Code (#1 frontend)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: #3 backend — `GET /{file_id}/drilldown` + `drilldown_code`

**Files:**
- Modify: `backend/analytics/codegen.py` (add `drilldown_code`)
- Modify: `backend/routers/ml.py` (import + new endpoint + `_agg_expr` helper)
- Test: `backend/tests/test_codegen.py`, `backend/tests/test_ml.py`

- [ ] **Step 1: Write the failing codegen tests**

Append to `backend/tests/test_codegen.py`:

```python
from analytics.codegen import drilldown_code


def test_drilldown_code_year_compiles():
    code = drilldown_code("Order Date", "Sales", "orders.csv", "year", "sum")
    _compiles(code)
    assert "strftime('%Y')" in code
    assert "group_by('_period')" in code
    assert "f\"" not in code and "f'" not in code


def test_drilldown_code_month_filters_year():
    code = drilldown_code("Ngày", "Doanh thu", "x.xlsx", "month", "mean", year=2024)
    _compiles(code)
    assert "read_excel" in code
    assert "dt.year() == 2024" in code
    assert "strftime('%Y-%m')" in code
    assert "mean()" in code
```

- [ ] **Step 2: Run them — verify they fail**

Run: `cd backend ; uv run pytest tests/test_codegen.py -k drilldown -q`
Expected: FAIL — `ImportError: cannot import name 'drilldown_code'`.

- [ ] **Step 3: Implement `drilldown_code`**

Append to `backend/analytics/codegen.py`:

```python
_DRILL_FMT = {"year": "%Y", "month": "%Y-%m", "day": "%Y-%m-%d"}


def drilldown_code(date_col: str, value_col: str, filename: str, grain: str,
                   agg: str, year: int | None = None, month: int | None = None) -> str:
    """Snippet khoan sâu thời gian (year/month/day, lọc year/month tuỳ chọn) — khớp
    endpoint /drilldown. Không f-string & không '{' trong code sinh ra."""
    method = _AGG_METHOD.get(agg, "sum")
    fmt = _DRILL_FMT.get(grain, "%Y")
    parts = [
        _HEADER,
        "import polars as pl\n\n",
        f"df = {_read_call(filename)}\n",
        "df = df.with_columns(\n"
        f"    pl.col({date_col!r}).cast(pl.Utf8).str.to_datetime(strict=False).alias('_d')\n"
        ").drop_nulls('_d')\n",
    ]
    if year is not None:
        parts.append(f"df = df.filter(pl.col('_d').dt.year() == {int(year)})\n")
    if month is not None:
        parts.append(f"df = df.filter(pl.col('_d').dt.month() == {int(month)})\n")
    parts.append(
        f"df = df.with_columns(pl.col('_d').dt.strftime({fmt!r}).alias('_period'))\n"
        "grouped = (\n"
        "    df.group_by('_period')\n"
        f"    .agg(pl.col({value_col!r}).{method}().alias('_value'))\n"
        "    .sort('_period')\n"
        ")\n"
        "print('labels =', grouped['_period'].to_list())\n"
        "print('values =', grouped['_value'].to_list())\n"
    )
    return "".join(parts)
```

- [ ] **Step 4: Run the codegen tests — verify pass**

Run: `cd backend ; uv run pytest tests/test_codegen.py -k drilldown -q`
Expected: PASS.

- [ ] **Step 5: Write the failing endpoint tests**

Append to `backend/tests/test_ml.py`:

```python
DRILL_CSV = (
    b"d,v\n"
    b"2024-01-15,10\n2024-01-20,5\n2024-07-03,7\n"
    b"2025-03-10,20\n2025-03-11,2\n"
)


def test_drilldown_year_level(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(DRILL_CSV), "text/csv")},
    ).json()
    r = client.get(f"/api/ml/{up['file_id']}/drilldown",
                   params={"date_col": "d", "value_col": "v", "agg": "sum", "grain": "year"})
    assert r.status_code == 200
    b = r.json()
    assert b["labels"] == ["2024", "2025"]
    assert b["values"] == [22.0, 22.0]          # 2024: 10+5+7 ; 2025: 20+2
    assert "code" in b


def test_drilldown_month_within_year(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(DRILL_CSV), "text/csv")},
    ).json()
    r = client.get(f"/api/ml/{up['file_id']}/drilldown",
                   params={"date_col": "d", "value_col": "v", "grain": "month", "year": 2024})
    assert r.status_code == 200
    b = r.json()
    assert b["labels"] == ["2024-01", "2024-07"]
    assert b["values"] == [15.0, 7.0]           # Jan: 10+5 ; Jul: 7
```

- [ ] **Step 6: Run them — verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml.py -k drilldown -q`
Expected: FAIL — 404 (endpoint not defined).

- [ ] **Step 7: Update the import in `ml.py`** (extend the block edited in Task 2):

```python
from analytics.codegen import (
    forecast_code, timeseries_code, correlation_code, stats_code, cohort_code,
    describe_code, drilldown_code,
)
```

- [ ] **Step 8: Add the `_agg_expr` helper + the endpoint.** Insert immediately **after** `describe_dataset` (i.e. before `def _infer_role`) in `backend/routers/ml.py`:

```python
def _agg_expr(col: pl.Expr, agg: str) -> pl.Expr:
    return {
        "sum": col.sum(), "mean": col.mean(), "count": col.count(),
        "n_unique": col.n_unique(), "min": col.min(), "max": col.max(),
    }.get(agg, col.sum())


@router.get("/{file_id}/drilldown")
def drilldown_dataset(
    file_id: str, date_col: str, value_col: str,
    agg: Agg = "sum",
    grain: Literal["year", "month", "day"] = "year",
    year: int | None = None, month: int | None = None,
):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    for col in (date_col, value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")
    try:
        parsed = _try_parse_dates(df[date_col])
    except ValueError as e:
        raise HTTPException(400, f"Không thể parse cột ngày '{date_col}': {e}")

    work = df.with_columns(parsed.alias("_d")).drop_nulls(subset=["_d"])
    if year is not None:
        work = work.filter(pl.col("_d").dt.year() == year)
    if month is not None:
        work = work.filter(pl.col("_d").dt.month() == month)

    code = drilldown_code(date_col, value_col, row["filename"], grain, agg, year, month)
    if work.height == 0:
        return {"grain": grain, "labels": [], "values": [],
                "value_col": value_col, "agg": agg, "code": code}

    fmt = {"year": "%Y", "month": "%Y-%m", "day": "%Y-%m-%d"}[grain]
    grouped = (
        work.with_columns(pl.col("_d").dt.strftime(fmt).alias("_k"))
        .group_by("_k")
        .agg(_agg_expr(pl.col(value_col), agg).alias("_v"))
        .sort("_k")
    )
    return {
        "grain": grain,
        "labels": grouped["_k"].to_list(),
        "values": [None if v is None else round(float(v), 4) for v in grouped["_v"].to_list()],
        "value_col": value_col,
        "agg": agg,
        "code": code,
    }
```

- [ ] **Step 9: Run the drilldown + full codegen tests — verify pass**

Run: `cd backend ; uv run pytest tests/test_ml.py -k drilldown tests/test_codegen.py -q`
Expected: PASS (all).

- [ ] **Step 10: Commit**

```bash
git add backend/analytics/codegen.py backend/routers/ml.py backend/tests/test_codegen.py backend/tests/test_ml.py
git commit -m "feat(ml): add /drilldown endpoint (year/month/day) + codegen (#3 backend)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: #3 frontend — `MlDrilldownView` panel + wiring

**Files:**
- Modify: `frontend/src/types.ts` (add `DrilldownResult`)
- Modify: `frontend/src/api/ml.ts` (add `fetchDrilldown`)
- Create: `frontend/src/components/ml/MlDrilldownView.tsx`
- Modify: `frontend/src/components/ml/MlChartView.tsx` (import + render the panel)

- [ ] **Step 1: Add the result type.** Append to `frontend/src/types.ts` (after `TimeseriesResult`, before `ProfileResult` is fine — anywhere top-level):

```ts
export interface DrilldownResult {
  grain: 'year' | 'month' | 'day'
  labels: string[]
  values: (number | null)[]
  value_col: string
  agg: string
  code?: string
}
```

- [ ] **Step 2: Add `fetchDrilldown`.** Append to `frontend/src/api/ml.ts` (and add `DrilldownResult` to the type import at the top of the file):

```ts
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix, QualityResult,
  ZScoreData, BoxPlotData, TimeseriesResult, ProfileResult, DrilldownResult,
} from '../types'
```

```ts
export async function fetchDrilldown(
  file_id: string, date_col: string, value_col: string,
  agg: string, grain: 'year' | 'month' | 'day',
  year?: number, month?: number,
): Promise<DrilldownResult> {
  const { data } = await client.get<DrilldownResult>(`/ml/${file_id}/drilldown`, {
    params: { date_col, value_col, agg, grain, year, month },
  })
  return data
}
```

- [ ] **Step 3: Create the panel** `frontend/src/components/ml/MlDrilldownView.tsx`. Self-contained (own collapse + fetch) so it just slots into `MlChartView` like the Cohort/Correlation panels. Year→Month→Day with clickable bars + a breadcrumb whose crumbs are lateral dropdowns.

```tsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { Layers, ChevronRight } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { DatasetInfo, DrilldownResult } from '../../types'
import { fetchDrilldown } from '../../api/ml'
import { type YScale, fmtY, fmtFull } from './numFormat'
import CodePanel from './CodePanel'

interface Props { dataset: DatasetInfo }

type Level = 'year' | 'month' | 'day'
const AGGS = ['sum', 'mean', 'count', 'n_unique', 'min', 'max'] as const
const MONTH_LABEL = (m: number) => `Th${String(m).padStart(2, '0')}`

export default function MlDrilldownView({ dataset }: Props) {
  const [open, setOpen] = useState(false)

  // Column guesses (same heuristic as the time-series panel)
  const guess = useMemo(() => {
    const cols = dataset.columns
    const date =
      cols.find(c => /date|datetime|timestamp/i.test(c.dtype))?.name ??
      cols.find(c => /date|time|day|month|year|period|ngay|thang/i.test(c.name))?.name ??
      cols[0]?.name ?? ''
    const value =
      cols.find(c => /int|float|decimal|double/i.test(c.dtype) && c.name !== date)?.name ?? ''
    return { date, value }
  }, [dataset.file_id])  // eslint-disable-line react-hooks/exhaustive-deps

  const [dateCol, setDateCol] = useState(guess.date)
  const [valueCol, setValueCol] = useState(guess.value)
  const [agg, setAgg] = useState<string>('sum')
  const [level, setLevel] = useState<Level>('year')
  const [year, setYear] = useState<number | undefined>(undefined)
  const [month, setMonth] = useState<number | undefined>(undefined)
  const [res, setRes] = useState<DrilldownResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [scale, setScale] = useState<YScale>('auto')
  const [yearOpts, setYearOpts] = useState<number[]>([])
  const [monthOpts, setMonthOpts] = useState<string[]>([])  // "YYYY-MM" of the current year

  // Reset to root when the dataset or the picked columns change
  useEffect(() => {
    setDateCol(guess.date); setValueCol(guess.value)
    setLevel('year'); setYear(undefined); setMonth(undefined)
    setRes(null); setError(''); setYearOpts([]); setMonthOpts([])
  }, [dataset.file_id])  // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch whenever an input changes while the panel is open
  useEffect(() => {
    if (!open || !dateCol || !valueCol) return
    let alive = true
    setLoading(true); setError('')
    fetchDrilldown(dataset.file_id, dateCol, valueCol, agg, level, year, month)
      .then(r => {
        if (!alive) return
        setRes(r)
        if (level === 'year') setYearOpts(r.labels.map(Number).filter(n => !Number.isNaN(n)))
        if (level === 'month') setMonthOpts(r.labels)
      })
      .catch((e: unknown) => {
        if (alive) setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Drilldown failed')
      })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [open, dataset.file_id, dateCol, valueCol, agg, level, year, month])

  const chartData = useMemo(
    () => (res?.labels ?? []).map((label, i) => ({ label, y: res!.values[i] ?? 0 })),
    [res],
  )
  const maxAbs = useMemo(
    () => Math.max(1, ...chartData.map(d => Math.abs(d.y))),
    [chartData],
  )

  function drillInto(label: string) {
    if (level === 'year') { setYear(Number(label)); setMonth(undefined); setLevel('month') }
    else if (level === 'month') { setMonth(Number(label.split('-')[1])); setLevel('day') }
    // day = leaf, no further drill
  }

  const tooltipStyle = { background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }
  const axisStyle = { fill: '#6b7280', fontSize: 10 }

  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left">
        <Layers size={12} className="text-gray-500" />
        <span className="text-[11px] font-medium text-gray-300">Khoan sâu thời gian</span>
        <span className="text-[10px] text-gray-600 ml-1">— Năm → Tháng → Ngày (bấm cột để khoan)</span>
      </button>

      {open && (
        <div className="p-3 flex flex-col gap-3">
          {/* Controls */}
          <div className="flex gap-2 flex-wrap items-end">
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Date field</label>
              <select className="input-base text-xs" value={dateCol} onChange={e => { setDateCol(e.target.value); setLevel('year'); setYear(undefined); setMonth(undefined) }}>
                <option value="">—</option>
                {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Value</label>
              <select className="input-base text-xs" value={valueCol} onChange={e => setValueCol(e.target.value)}>
                <option value="">—</option>
                {dataset.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">Agg</label>
              <select className="input-base text-xs" value={agg} onChange={e => setAgg(e.target.value)}>
                {AGGS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div className="flex gap-0.5 pb-0.5 ml-auto">
              {(['auto', 'K', 'M', 'B', '%'] as YScale[]).map(s => (
                <button key={s} onClick={() => setScale(s)}
                  className={`px-1.5 py-1 rounded text-[10px] border transition-all ${
                    scale === s ? 'bg-work/10 text-work border-work/30' : 'text-gray-600 border-transparent hover:text-gray-400'
                  }`}>{s}</button>
              ))}
            </div>
          </div>

          {/* Breadcrumb — each crumb is a lateral dropdown */}
          <div className="flex items-center gap-1 text-[11px] text-gray-400 flex-wrap">
            <button
              onClick={() => { setLevel('year'); setYear(undefined); setMonth(undefined) }}
              className={`px-1.5 py-0.5 rounded hover:bg-white/5 ${level === 'year' ? 'text-work font-medium' : ''}`}>
              Tất cả
            </button>
            {year !== undefined && (
              <>
                <ChevronRight size={11} className="text-gray-600" />
                <select
                  className="bg-transparent border border-white/10 rounded px-1 py-0.5 text-[11px] text-gray-300"
                  value={year}
                  onChange={e => { setYear(Number(e.target.value)); setMonth(undefined); setLevel('month') }}>
                  {yearOpts.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </>
            )}
            {month !== undefined && (
              <>
                <ChevronRight size={11} className="text-gray-600" />
                <select
                  className="bg-transparent border border-white/10 rounded px-1 py-0.5 text-[11px] text-gray-300"
                  value={month}
                  onChange={e => { setMonth(Number(e.target.value)); setLevel('day') }}>
                  {monthOpts.map(m => {
                    const mn = Number(m.split('-')[1])
                    return <option key={m} value={mn}>{MONTH_LABEL(mn)}</option>
                  })}
                </select>
              </>
            )}
          </div>

          {error && <p className="text-danger text-xs">{error}</p>}
          {loading && <p className="text-[11px] text-gray-500">Đang tính…</p>}

          {!loading && res && chartData.length > 0 && (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="label" tick={axisStyle} />
                  <YAxis tickFormatter={(v) => fmtY(v, scale, maxAbs)} tick={axisStyle} width={52} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v) => [fmtFull(v as number), res.value_col]} />
                  <Bar
                    dataKey="y"
                    fill="#fbbf24"
                    radius={[3, 3, 0, 0]}
                    cursor={level === 'day' ? 'default' : 'pointer'}
                    onClick={(d: { label?: string }) => { if (d?.label) drillInto(d.label) }}
                  />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-[10px] text-gray-600">
                {level === 'day' ? 'Cấp ngày (chi tiết nhất)' : 'Bấm vào một cột để khoan sâu xuống cấp dưới'}
                {' · '}{res.agg}({res.value_col})
              </p>
              {res.code && <CodePanel code={res.code} filename="drilldown_pipeline.py" />}
            </>
          )}

          {!loading && res && chartData.length === 0 && (
            <p className="text-[11px] text-gray-600">Không có dữ liệu cho mốc thời gian này.</p>
          )}
        </div>
      )}
    </div>
  )
}
```

> Note: `useRef` is imported for parity with sibling panels but is unused here; if `npm run build` flags it as unused, drop `useRef` from the import. (Vite's default `tsc` config does not error on unused imports unless `noUnusedLocals` is on — check the build output and trim if needed.)

- [ ] **Step 4: Wire the panel into `MlChartView.tsx`.** Add the import near the other ML imports (after the `CorrelationHeatmap` import, line 17):

```tsx
import MlDrilldownView from './MlDrilldownView'
```

Then render it right after the **Correlation Heatmap** panel block and before the **Chuỗi thời gian** block (i.e. insert between the `)}` that closes the correlation `{dataset && (...)}` at line ~724 and the `{/* ── Chuỗi thời gian ── */}` comment at line ~726):

```tsx
      {/* ── Khoan sâu thời gian (drill-down) ─────────────────── */}
      {dataset && <MlDrilldownView dataset={dataset} />}

```

- [ ] **Step 5: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds. (If it flags the unused `useRef`, remove it from `MlDrilldownView`'s React import and rebuild.)

- [ ] **Step 6: Manual verify**

ML Studio → Charts tab → open **Khoan sâu thời gian** → bars show by **year**. Click a year bar → drills to that year's **months**; breadcrumb shows `Tất cả › <select year>`. Click a month bar → drills to **days**; breadcrumb adds the month dropdown. Use the breadcrumb year/month dropdowns to jump sideways (e.g. 2024 → 2025). "Tất cả" returns to the year view. Show Code opens a runnable snippet.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts frontend/src/components/ml/MlDrilldownView.tsx frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): time drill-down panel Year/Month/Day with breadcrumb (#3 frontend)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: #4 — Fix scroll-jump when running "Chuỗi thời gian"

**Files:**
- Modify: `frontend/src/components/ml/MlChartView.tsx` (handlers + ts/cohort render)

**Root cause:** `setTsResult(null)` (and `setCohortResult(null)`) at the top of the run handler collapses the tall result block that sits at the bottom of the `overflow-auto` container, so the browser clamps `scrollTop` to the top. Fix: don't unmount the tall block on run (keep the previous result until the new one arrives), keep a fixed-height skeleton while loading, and `scrollIntoView({block:'nearest'})` once the result is in.

- [ ] **Step 1: Add panel refs.** In `MlChartView`, just after the time-series state declarations (after line 170 `const [tsScale, setTsScale] = useState<YScale>('auto')`), add:

```tsx
  const tsPanelRef     = useRef<HTMLDivElement>(null)
  const cohortPanelRef = useRef<HTMLDivElement>(null)
```

- [ ] **Step 2: Rewrite `handleTimeseries`** (replace lines 261-269) — drop the `setTsResult(null)`, scroll into view after success:

```tsx
  async function handleTimeseries() {
    if (!dataset || !tsDate || !tsValue) return
    setTsLoading(true); setTsError('')
    try {
      const r = await runTimeseries(dataset.file_id, tsDate, tsValue, tsGrain, tsAgg, tsComps)
      setTsResult(r)
      requestAnimationFrame(() => tsPanelRef.current?.scrollIntoView({ block: 'nearest' }))
    } catch (e: unknown) {
      setTsError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Timeseries failed')
    } finally { setTsLoading(false) }
  }
```

- [ ] **Step 3: Rewrite `handleCohort`** (replace lines 252-259) — same pattern (keep prior table during recompute):

```tsx
  async function handleCohort() {
    if (!dataset) return
    setCohortLoading(true); setCohortError('')
    try {
      setCohortResult(await runCohort(dataset.file_id, cohortDate, cohortUser, cohortPeriod))
      requestAnimationFrame(() => cohortPanelRef.current?.scrollIntoView({ block: 'nearest' }))
    } catch (e: unknown) {
      setCohortError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Cohort failed')
    } finally { setCohortLoading(false) }
  }
```

- [ ] **Step 4: Anchor the time-series result with a ref + min-height skeleton.** Replace the time-series result block (lines 782-822, the `{tsError && ...}` through the closing of `{tsResult && (…)}`) with:

```tsx
              {tsError && <p className="text-danger text-xs">{tsError}</p>}

              <div ref={tsPanelRef} style={{ minHeight: tsResult || tsLoading ? 360 : 0 }}>
                {tsLoading && !tsResult && (
                  <div className="h-[320px] rounded-lg bg-white/3 animate-pulse flex items-center justify-center">
                    <span className="text-[11px] text-gray-500">Đang tính chuỗi thời gian…</span>
                  </div>
                )}
                {tsResult && (
                  <>
                    <p className="text-[10px] text-gray-500">
                      {tsResult.grain} · {tsResult.meta.periods} kỳ · gợi ý: {tsResult.meta.suggested_grain}
                    </p>
                    <div className="flex justify-end">
                      <div className="flex gap-0.5">
                        {(['auto', 'K', 'M', 'B', '%'] as YScale[]).map(s => (
                          <button key={s} onClick={() => setTsScale(s)}
                            className={`px-1.5 py-1 rounded text-[10px] border transition-all ${
                              tsScale === s ? 'bg-work/10 text-work border-work/30' : 'text-gray-600 border-transparent hover:text-gray-400'
                            }`}>{s}</button>
                        ))}
                      </div>
                    </div>
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
                        <YAxis tick={axisStyle} tickFormatter={(v) => fmtY(v, tsScale, tsMaxAbs)} width={52} />
                        <Tooltip contentStyle={tooltipStyle} formatter={(v) => fmtFull(v as number)} />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                        <Line type="monotone" dataKey="value" stroke="#3b82f6" dot={false} name={tsResult.value_col} />
                        {tsResult.comparisons.yoy        && <Line type="monotone" dataKey="yoy"        stroke="#a855f7" strokeDasharray="4 2" dot={false} name="YoY" />}
                        {tsResult.comparisons.pop        && <Line type="monotone" dataKey="pop"        stroke="#f59e0b" strokeDasharray="4 2" dot={false} name="Kỳ trước" />}
                        {tsResult.comparisons.rolling    && <Line type="monotone" dataKey="rolling"    stroke="#22c55e" dot={false} name="TB trượt" />}
                        {tsResult.comparisons.cumulative && <Line type="monotone" dataKey="cumulative" stroke="#eab308" dot={false} name="Lũy kế" />}
                      </LineChart>
                    </ResponsiveContainer>
                    {tsResult.code && <CodePanel code={tsResult.code} filename="timeseries_pipeline.py" />}
                  </>
                )}
              </div>
```

- [ ] **Step 5: Anchor the cohort result with its ref.** On the cohort result wrapper (line ~600 `{cohortResult && cohortResult.suitable !== false && (`), attach the ref to the outer `div`. Change:

```tsx
                <div className="overflow-auto rounded-lg border border-white/8">
```
to:
```tsx
                <div ref={cohortPanelRef} className="overflow-auto rounded-lg border border-white/8">
```

- [ ] **Step 6: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds.

- [ ] **Step 7: Manual verify**

ML Studio → Charts → open **Chuỗi thời gian**, scroll down so the panel is in view, pick date+value, click **Run**. The viewport **stays put** (a skeleton holds the height during compute, then the chart replaces it in place) — no jump to the top. Repeat for **Cohort Retention** → Run Cohort: no jump.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ml/MlChartView.tsx
git commit -m "fix(ml): stop scroll-jump on Run in time-series/cohort panels (#4)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: #5 — Ranked +/− correlation list under the heatmap

**Files:**
- Create: `frontend/src/components/ml/CorrelationRanked.tsx`
- Modify: `frontend/src/components/ml/MlChartView.tsx` (render under heatmap)

- [ ] **Step 1: Create `CorrelationRanked.tsx`.** Pure render from `CorrelationMatrix` (upper triangle, split positive/negative, sorted by strength). Colors reuse the heatmap's diverging scale for consistency.

```tsx
import { useMemo } from 'react'
import type { CorrelationMatrix } from '../../types'

interface Props {
  data: CorrelationMatrix
  topN?: number
}

interface Pair { a: string; b: string; r: number }

/** Same diverging scale as CorrelationHeatmap (blue +, red −). */
function corrToColor(r: number): string {
  const t = Math.pow(Math.min(Math.abs(r), 1), 0.7)
  const gray = [55, 65, 81]
  const target = r >= 0 ? [37, 99, 235] : [220, 38, 38]
  const mix = gray.map((g, i) => Math.round(g + (target[i] - g) * t))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}

function Row({ p }: { p: Pair }) {
  return (
    <div className="flex items-center gap-2 text-[11px] py-0.5">
      <span className="text-gray-300 truncate flex-1" title={`${p.a} × ${p.b}`}>
        {p.a} <span className="text-gray-600">×</span> {p.b}
      </span>
      <div className="w-20 h-2 rounded bg-white/5 overflow-hidden">
        <div className="h-full" style={{ width: `${Math.min(Math.abs(p.r), 1) * 100}%`, background: corrToColor(p.r) }} />
      </div>
      <span className="tabular-nums w-12 text-right" style={{ color: corrToColor(p.r) }}>
        {p.r >= 0 ? '+' : ''}{p.r.toFixed(2)}
      </span>
    </div>
  )
}

export default function CorrelationRanked({ data, topN = 8 }: Props) {
  const { pos, neg } = useMemo(() => {
    const pairs: Pair[] = []
    for (let i = 0; i < data.columns.length; i++) {
      for (let j = i + 1; j < data.columns.length; j++) {
        const r = data.matrix[i]?.[j]
        if (r === null || r === undefined || Number.isNaN(r)) continue
        pairs.push({ a: data.columns[i], b: data.columns[j], r })
      }
    }
    return {
      pos: pairs.filter(p => p.r > 0).sort((x, y) => y.r - x.r).slice(0, topN),
      neg: pairs.filter(p => p.r < 0).sort((x, y) => x.r - y.r).slice(0, topN),
    }
  }, [data, topN])

  if (pos.length === 0 && neg.length === 0) {
    return <p className="text-[11px] text-gray-600 mt-3">Không có cặp tương quan để xếp hạng.</p>
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
      <div>
        <p className="text-[10px] font-semibold text-blue-400 mb-1">Tương quan DƯƠNG (cùng chiều)</p>
        {pos.length ? pos.map((p, i) => <Row key={i} p={p} />)
                    : <p className="text-[10px] text-gray-600">—</p>}
      </div>
      <div>
        <p className="text-[10px] font-semibold text-red-400 mb-1">Tương quan ÂM (ngược chiều)</p>
        {neg.length ? neg.map((p, i) => <Row key={i} p={p} />)
                    : <p className="text-[10px] text-gray-600">—</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Render it under the heatmap in `MlChartView.tsx`.** Add the import after the `CorrelationHeatmap` import:

```tsx
import CorrelationRanked from './CorrelationRanked'
```

In the correlation panel, update the `corrData` branch (lines ~714-719) to also render the ranked list:

```tsx
                    ? (
                      <>
                        <CorrelationHeatmap data={corrData} />
                        <CorrelationRanked data={corrData} />
                        {corrData.code && <CodePanel code={corrData.code} filename="correlation_pipeline.py" />}
                      </>
                    )
```

- [ ] **Step 3: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds.

- [ ] **Step 4: Manual verify**

ML Studio → Charts → open **Correlation Heatmap** on a numeric dataset → below the heatmap two columns appear: **DƯƠNG** (strongest positive first) and **ÂM** (most negative first), each with a strength bar and signed `r`. A dataset with no valid pairs shows the "không có cặp" message.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ml/CorrelationRanked.tsx frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): ranked +/- correlation pairs under heatmap (#5)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: #6 — Clustered Columns (multi-measure) chart

**Files:**
- Modify: `frontend/src/components/ml/MlChartView.tsx`

- [ ] **Step 1: Extend the chart-type union & list.** Change the `ChartType` type (line 26):

```tsx
type ChartType = 'bar' | 'line' | 'area' | 'scatter' | 'pie' | 'donut' | 'treemap' | 'clustered'
```

Add to `CHART_TYPES` (after the `treemap` entry, line 36):

```tsx
  { key: 'clustered', label: 'Cột nhóm' },
```

- [ ] **Step 2: Add multi-measure state + numeric-column detection.** After the `yMax` state (line 133), add:

```tsx
  const [yCols, setYCols] = useState<string[]>([])
```

After the `data` useMemo (after line 203), add a numeric-columns memo and a default initializer:

```tsx
  // Columns in the current result that look numeric (sample-based), for clustered measures.
  const numericResultCols = useMemo(() => {
    const out: string[] = []
    result.columns.forEach((c, idx) => {
      const sample = result.rows.slice(0, 20).map(r => r[idx]).filter(v => v !== null && v !== '')
      if (sample.length && sample.every(v => !isNaN(Number(v)))) out.push(c)
    })
    return out
  }, [result])

  // Default the clustered measures to the first 2–3 numeric columns when empty / stale.
  useEffect(() => {
    setYCols(prev => {
      const valid = prev.filter(c => numericResultCols.includes(c))
      return valid.length ? valid : numericResultCols.slice(0, Math.min(3, numericResultCols.length))
    })
  }, [numericResultCols])

  const isClustered = type === 'clustered'

  const clusterData = useMemo(() => {
    if (!isClustered) return []
    const xIdx = result.columns.indexOf(xCol)
    const idxs = yCols.map(c => result.columns.indexOf(c))
    return result.rows.slice(0, 500).map(row => {
      const o: Record<string, unknown> = { x: row[xIdx] }
      yCols.forEach((c, k) => { o[c] = Number(row[idxs[k]]) || 0 })
      return o
    })
  }, [isClustered, result, xCol, yCols])

  const clusterMaxAbs = useMemo(() => {
    let m = 1
    clusterData.forEach(o => yCols.forEach(c => { m = Math.max(m, Math.abs(Number(o[c]) || 0)) }))
    return m
  }, [clusterData, yCols])
```

- [ ] **Step 3: Swap the Y-axis control for chips when clustered.** The single-Y `<select>` lives inside the `{isXY && (...)}` X/Y block (lines 345-360). Replace that whole `{isXY && (<>…</>)}` block with one that hides the single-Y select for clustered and shows a chip multi-select instead:

```tsx
        {isXY && (
          <>
            <div>
              <label className="block text-[10px] text-gray-600 mb-1">X axis</label>
              <select className="input-base text-xs" value={xCol} onChange={e => setXCol(e.target.value)}>
                {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {!isClustered && (
              <div>
                <label className="block text-[10px] text-gray-600 mb-1">Y axis</label>
                <select className="input-base text-xs" value={yCol} onChange={e => setYCol(e.target.value)}>
                  {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            )}
            {isClustered && (
              <div>
                <label className="block text-[10px] text-gray-600 mb-1">Measures (cột số)</label>
                <div className="flex gap-1 flex-wrap max-w-[360px]">
                  {numericResultCols.map(c => {
                    const on = yCols.includes(c)
                    return (
                      <button key={c}
                        onClick={() => setYCols(prev => on ? prev.filter(x => x !== c) : [...prev, c])}
                        className={`px-2 py-1 rounded text-[10px] border transition-all ${
                          on ? 'bg-data/10 text-data border-data/30' : 'text-gray-500 border-white/10 hover:text-gray-300'
                        }`}>{c}</button>
                    )
                  })}
                  {numericResultCols.length === 0 && (
                    <span className="text-[10px] text-gray-600">Không có cột số trong kết quả.</span>
                  )}
                </div>
              </div>
            )}
          </>
        )}
```

- [ ] **Step 4: Add a >6-series warning** next to the treemap warning (after the treemap warning block, line ~438):

```tsx
      {isClustered && yCols.length > 6 && (
        <div className="text-[11px] bg-yellow-500/5 border border-yellow-500/20 rounded-lg px-3 py-2.5 text-yellow-400">
          <AlertTriangle size={12} className="inline mr-1" />
          {yCols.length} measure — quá nhiều cột cạnh nhau sẽ khó đọc; nên chọn ≤ 6.
        </div>
      )}
```

- [ ] **Step 5: Add the clustered render branch.** At the start of the chart conditional chain (line 443 `{type === 'bar' ? (`), prepend a clustered branch:

```tsx
          {type === 'clustered' ? (
            <BarChart data={clusterData} margin={{ top: 20, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={axisStyle} />
              <YAxis tickFormatter={(v) => fmtY(v, yScale, clusterMaxAbs)} tick={axisStyle} width={52} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v, n) => [fmtFull(v as number), n as string]} />
              <Legend wrapperStyle={{ fontSize: 10, color: '#6b7280' }} />
              {yCols.map((c, i) => (
                <Bar key={c} dataKey={c} fill={PIE_COLORS[i % PIE_COLORS.length]} radius={[2, 2, 0, 0]} />
              ))}
            </BarChart>
          ) : type === 'bar' ? (
```

(The existing `type === 'bar' ? (` becomes the second branch — keep everything else in the chain unchanged.)

- [ ] **Step 6: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds.

- [ ] **Step 7: Manual verify**

ML Studio → run a query returning a label column + ≥2 numeric columns (e.g. `SELECT region, SUM(sales) sales, SUM(profit) profit FROM data GROUP BY region`) → Charts → pick **Cột nhóm** → set X = `region`, toggle measure chips `sales`/`profit` → bars for each measure render **side-by-side per X group**, legend shows the measure names. Selecting >6 chips shows the warning.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): clustered columns chart for multiple measures (#6)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: #2 — Chart-suggestion pool with ⟳ "Góc nhìn khác"

**Files:**
- Create: `frontend/src/components/ml/chartRecipes.ts`
- Modify: `frontend/src/components/ml/MlChartView.tsx`

**Depends on Task 8** (the `clustered` apply path calls `setYCols`/`setType('clustered')`).

- [ ] **Step 1: Create the pure pool builder** `frontend/src/components/ml/chartRecipes.ts`:

```ts
import type { ProfileResult } from '../../types'

export type RecipeKind = 'timeseries' | 'correlation' | 'bar' | 'scatter' | 'clustered'
export type RecipeIcon = 'TrendingUp' | 'Link2' | 'BarChart3' | 'ScatterChart' | 'Grid2x2'

export interface Recipe {
  title: string
  kind: RecipeKind
  iconName: RecipeIcon
  x?: string
  y?: string
  ys?: string[]
}

/**
 * Build a (possibly large) pool of chart suggestions from the dataset profile,
 * guarded so client-side recipes only reference columns present in the current
 * SQL result. Pure & deterministic — unit-testable without React.
 *
 * Example: profile with date "Order Date", metrics ["Sales","Profit","Qty"],
 * dims ["Region","Segment"], flags ["Returned"] yields, in order:
 *   timeseries(Sales by Order Date), timeseries(Profit by Order Date),
 *   correlation(3 metrics), clustered(Region × [Sales,Profit,Qty]),
 *   bar(Sales by Region), bar(Sales by Segment), bar(Sales by Returned [flag]),
 *   scatter(Sales vs Profit), scatter(Sales vs Qty), ...
 */
export function buildRecipePool(profile: ProfileResult | null, resultColumns: string[]): Recipe[] {
  if (!profile) return []
  const inResult = (name: string) => resultColumns.includes(name)
  const dates   = profile.columns.filter(c => c.role === 'date')
  const metrics = profile.columns.filter(c => c.role === 'metric')
  const dims    = profile.columns.filter(c => c.role === 'dimension')
  const flags   = profile.columns.filter(c => c.role === 'flag')
  const out: Recipe[] = []

  // Date × metric → server-side time series (each metric = a different angle)
  for (const d of dates) {
    for (const m of metrics.slice(0, 4)) {
      out.push({ title: `${m.name} theo thời gian (${d.name})`, kind: 'timeseries', iconName: 'TrendingUp', x: d.name, y: m.name })
    }
  }
  // ≥2 metrics → correlation
  if (metrics.length >= 2) {
    out.push({ title: `Tương quan ${metrics.length} cột số`, kind: 'correlation', iconName: 'Link2' })
  }
  // ≥2 metrics present in result → clustered measures
  const metricsInResult = metrics.filter(m => inResult(m.name))
  if (dims[0] && metricsInResult.length >= 2 && inResult(dims[0].name)) {
    out.push({
      title: `${dims[0].name}: ${metricsInResult.slice(0, 3).map(m => m.name).join(' · ')}`,
      kind: 'clustered', iconName: 'Grid2x2', x: dims[0].name, ys: metricsInResult.slice(0, 3).map(m => m.name),
    })
  }
  // Dimension × metric → bar (guarded to result columns)
  for (const dim of dims) {
    for (const m of metrics.slice(0, 2)) {
      if (inResult(dim.name) && inResult(m.name)) {
        out.push({ title: `${m.name} theo ${dim.name}`, kind: 'bar', iconName: 'BarChart3', x: dim.name, y: m.name })
      }
    }
  }
  // Flag × metric → bar (e.g. has_campaign)
  for (const f of flags) {
    if (metrics[0] && inResult(f.name) && inResult(metrics[0].name)) {
      out.push({ title: `${metrics[0].name} theo ${f.name}`, kind: 'bar', iconName: 'BarChart3', x: f.name, y: metrics[0].name })
    }
  }
  // Metric × metric → scatter (guarded)
  for (let i = 0; i < metrics.length; i++) {
    for (let j = i + 1; j < metrics.length; j++) {
      if (inResult(metrics[i].name) && inResult(metrics[j].name)) {
        out.push({ title: `${metrics[i].name} vs ${metrics[j].name}`, kind: 'scatter', iconName: 'ScatterChart', x: metrics[i].name, y: metrics[j].name })
      }
    }
  }
  return out
}
```

- [ ] **Step 2: Replace the fixed `recipes` IIFE with the pool.** In `MlChartView.tsx`, add imports — extend the lucide import (line 2) to ensure `RefreshCw` is present, and import the builder:

```tsx
import { ArrowUpDown, Grid2x2, Users, TrendingUp, Link2, BarChart3, ScatterChart as ScatterIcon, ArrowUp, ArrowDown, AlertTriangle, RefreshCw } from 'lucide-react'
```
```tsx
import { buildRecipePool, type Recipe } from './chartRecipes'
```

Replace the entire `recipes` IIFE (lines 283-323, `interface Recipe { … } const recipes: Recipe[] = (() => { … })()`) with the pool + windowing + apply mapping:

```tsx
  const RECIPE_ICONS = { TrendingUp, Link2, BarChart3, ScatterChart: ScatterIcon, Grid2x2 }
  const RECIPE_WINDOW = 4

  const recipePool = useMemo(
    () => buildRecipePool(profile, result.columns),
    [profile, result.columns],
  )
  const [poolOffset, setPoolOffset] = useState(0)

  const visibleRecipes = useMemo(() => {
    if (!recipePool.length) return []
    const n = Math.min(RECIPE_WINDOW, recipePool.length)
    return Array.from({ length: n }, (_, k) => recipePool[(poolOffset + k) % recipePool.length])
  }, [recipePool, poolOffset])

  function applyRecipe(r: Recipe) {
    switch (r.kind) {
      case 'timeseries':
        setShowTs(true)
        if (r.x) setTsDate(r.x)
        if (r.y) setTsValue(r.y)
        setTsGrain('auto')
        break
      case 'correlation':
        if (!showCorr) handleCorrToggle()
        break
      case 'bar':
        setShowTs(false)
        if (r.x) setXCol(r.x)
        if (r.y) setYCol(r.y)
        setType('bar')
        break
      case 'scatter':
        setShowTs(false)
        if (r.x) setXCol(r.x)
        if (r.y) setYCol(r.y)
        setType('scatter')
        break
      case 'clustered':
        if (r.x) setXCol(r.x)
        if (r.ys) setYCols(r.ys)
        setType('clustered')
        break
    }
  }
```

- [ ] **Step 3: Replace the suggestions render block** (lines 332-342, `{recipes.length > 0 && (…)}`) with the windowed list + ⟳ button:

```tsx
      {visibleRecipes.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] text-gray-500">Gợi ý biểu đồ:</span>
          {visibleRecipes.map((rec, i) => {
            const Icon = RECIPE_ICONS[rec.iconName]
            return (
              <button key={`${poolOffset}-${i}`} onClick={() => applyRecipe(rec)}
                className="px-2 py-1 rounded text-[10px] border border-blue-500/30 text-blue-400 hover:bg-blue-600/20 transition-all flex items-center gap-1">
                <Icon size={11} /> {rec.title}
              </button>
            )
          })}
          {recipePool.length > RECIPE_WINDOW && (
            <button
              onClick={() => setPoolOffset(o => (o + RECIPE_WINDOW) % recipePool.length)}
              title="Xem bộ gợi ý khác"
              className="px-2 py-1 rounded text-[10px] border border-white/15 text-gray-400 hover:text-gray-200 hover:bg-white/5 transition-all flex items-center gap-1">
              <RefreshCw size={11} /> Góc nhìn khác
            </button>
          )}
        </div>
      )}
```

- [ ] **Step 4: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual verify (incl. a pure-logic eyeball)**

In the running app, ML Studio → Charts: the "Gợi ý biểu đồ" row shows up to 4 chips + a **⟳ Góc nhìn khác** button (only when the pool has >4). Clicking ⟳ rotates to the next 4 and wraps around at the end. Each chip applies: time-series chips open & fill the TS panel; bar/scatter set X/Y+type; the clustered chip sets X+measures+type. Optional logic check — in devtools console you can confirm `buildRecipePool` ordering matches the worked example in the file's docstring for a known profile.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ml/chartRecipes.ts frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): rotating chart-suggestion pool with reload button (#2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: #8c — Auto-insight sentences under charts

**Files:**
- Create: `frontend/src/components/ml/insights.ts`
- Modify: `frontend/src/components/ml/MlChartView.tsx` (main chart + time-series)
- Modify: `frontend/src/components/ml/MlDrilldownView.tsx` (drilldown)

- [ ] **Step 1: Create the pure insight helper** `frontend/src/components/ml/insights.ts`:

```ts
import { fmtFull } from './numFormat'

/**
 * Build 1–2 Vietnamese insight sentences from a labelled numeric series:
 * highest/lowest point, overall trend (first↔last), and anomaly count (|z|>2).
 * Pure & deterministic.
 *
 * Example: describeSeries(["T1","T2","T3","T4"], [10, 12, 9, 30])
 *   → "Cao nhất tại T4 (30); thấp nhất tại T3 (9). Xu hướng tăng (+200% từ đầu kỳ). 1 điểm bất thường (|z|>2)."
 */
export function describeSeries(labels: string[], values: (number | null)[]): string {
  const pts = labels
    .map((label, i) => ({ label, v: values[i] }))
    .filter((p): p is { label: string; v: number } => typeof p.v === 'number' && !Number.isNaN(p.v))
  if (pts.length < 2) return ''

  let hi = pts[0], lo = pts[0]
  for (const p of pts) { if (p.v > hi.v) hi = p; if (p.v < lo.v) lo = p }

  const first = pts[0].v, last = pts[pts.length - 1].v
  const sentences: string[] = []
  sentences.push(`Cao nhất tại ${hi.label} (${fmtFull(hi.v)}); thấp nhất tại ${lo.label} (${fmtFull(lo.v)}).`)
  sentences.push(formatTrend(first, last))

  const mean = pts.reduce((s, p) => s + p.v, 0) / pts.length
  const variance = pts.reduce((s, p) => s + (p.v - mean) ** 2, 0) / pts.length
  const std = Math.sqrt(variance)
  const anomalies = std > 0 ? pts.filter(p => Math.abs((p.v - mean) / std) > 2).length : 0
  if (anomalies > 0) sentences.push(`${anomalies} điểm bất thường (|z|>2).`)

  return sentences.filter(Boolean).join(' ')
}

export function formatTrend(first: number, last: number): string {
  if (first === 0) {
    if (last === 0) return 'Xu hướng đi ngang.'
    return last > 0 ? 'Xu hướng tăng từ 0.' : 'Xu hướng giảm xuống âm.'
  }
  const pct = ((last - first) / Math.abs(first)) * 100
  const dir = pct > 1 ? 'tăng' : pct < -1 ? 'giảm' : 'đi ngang'
  if (dir === 'đi ngang') return 'Xu hướng đi ngang.'
  const sign = pct > 0 ? '+' : ''
  return `Xu hướng ${dir} (${sign}${pct.toFixed(0)}% từ đầu kỳ).`
}
```

- [ ] **Step 2: Render insight under the main chart in `MlChartView.tsx`.** Add the import:

```tsx
import { describeSeries } from './insights'
```

Compute an insight memo (after the `clusterMaxAbs` memo added in Task 8, or after `maxAbs` if Task 8 not present — place it after `const maxAbs = …`):

```tsx
  const chartInsight = useMemo(
    () => (isXY ? describeSeries(data.map(d => String(d.x)), data.map(d => d.y)) : ''),
    [isXY, data],
  )
```

Render it just under the existing max/min stats line (after the closing `</div>` of the block at lines 533-544):

```tsx
      {chartInsight && (
        <p className="text-[11px] text-gray-400 bg-white/3 border border-white/5 rounded-md px-3 py-1.5">
          💡 {chartInsight}
        </p>
      )}
```

- [ ] **Step 3: Render insight under the time-series chart.** Inside the `{tsResult && (…)}` block (added in Task 6), right after the `</ResponsiveContainer>` and before `{tsResult.code && …}`:

```tsx
                    {(() => {
                      const ins = describeSeries(tsResult.series.labels, tsResult.series.values)
                      return ins ? (
                        <p className="text-[11px] text-gray-400 bg-white/3 border border-white/5 rounded-md px-3 py-1.5 mt-1">💡 {ins}</p>
                      ) : null
                    })()}
```

- [ ] **Step 4: Render insight under the drilldown chart.** In `MlDrilldownView.tsx`, add the import:

```tsx
import { describeSeries } from './insights'
```

Inside the `{!loading && res && chartData.length > 0 && (…)}` block, after the `</ResponsiveContainer>` and before the descriptive `<p>`:

```tsx
              {(() => {
                const ins = describeSeries(res.labels, res.values)
                return ins ? (
                  <p className="text-[11px] text-gray-400 bg-white/3 border border-white/5 rounded-md px-3 py-1.5">💡 {ins}</p>
                ) : null
              })()}
```

- [ ] **Step 5: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds.

- [ ] **Step 6: Manual verify**

ML Studio → Charts: under the main bar/line chart a `💡` insight line summarizes peak/trough + trend (+ anomaly count when present). Same under the time-series chart and the drilldown chart. Values agree with the visible chart.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ml/insights.ts frontend/src/components/ml/MlChartView.tsx frontend/src/components/ml/MlDrilldownView.tsx
git commit -m "feat(ml): auto-insight sentence under charts (#8c)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: #8b — Export (Copy CSV / Download PNG)

**Files:**
- Create: `frontend/src/components/ml/chartExport.ts`
- Modify: `frontend/src/components/ml/MlTableView.tsx`
- Modify: `frontend/src/components/ml/MlChartView.tsx` (main chart PNG)
- Modify: `frontend/src/components/ml/MlDrilldownView.tsx` (drilldown PNG)

- [ ] **Step 1: Create the export helpers** `frontend/src/components/ml/chartExport.ts`. No new dependency — PNG goes via an offscreen `<canvas>`.

```ts
/** Quote a CSV cell per RFC 4180 (wrap in quotes if it contains comma/quote/newline). */
function csvCell(v: unknown): string {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(columns: string[], rows: unknown[][]): string {
  const head = columns.map(csvCell).join(',')
  const body = rows.map(r => r.map(csvCell).join(',')).join('\n')
  return body ? `${head}\n${body}` : head
}

/** Copy rows as CSV to the clipboard. Returns true on success. */
export async function copyRowsAsCsv(columns: string[], rows: unknown[][]): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(toCsv(columns, rows))
    return true
  } catch {
    return false
  }
}

/** Trigger a .csv file download. */
export function downloadCsv(columns: string[], rows: unknown[][], filename = 'export.csv'): void {
  const blob = new Blob([toCsv(columns, rows)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

/**
 * Best-effort PNG export of an inline <svg> (e.g. a recharts chart).
 * Serializes the SVG, paints it onto a canvas, and downloads a PNG.
 * Resolves false on any failure (tainted canvas, missing svg) — caller shows a toast.
 */
export function downloadSvgAsPng(svg: SVGSVGElement | null, filename = 'chart.png'): Promise<boolean> {
  return new Promise((resolve) => {
    if (!svg) { resolve(false); return }
    try {
      const rect = svg.getBoundingClientRect()
      const w = Math.max(1, Math.round(rect.width || svg.clientWidth || 800))
      const h = Math.max(1, Math.round(rect.height || svg.clientHeight || 400))
      const clone = svg.cloneNode(true) as SVGSVGElement
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
      clone.setAttribute('width', String(w))
      clone.setAttribute('height', String(h))
      const xml = new XMLSerializer().serializeToString(clone)
      const svg64 = 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(xml)))
      const img = new Image()
      img.onload = () => {
        try {
          const scale = window.devicePixelRatio || 1
          const canvas = document.createElement('canvas')
          canvas.width = w * scale; canvas.height = h * scale
          const ctx = canvas.getContext('2d')
          if (!ctx) { resolve(false); return }
          ctx.scale(scale, scale)
          ctx.fillStyle = '#0d1117'           // match app background (avoid transparent black)
          ctx.fillRect(0, 0, w, h)
          ctx.drawImage(img, 0, 0, w, h)
          const png = canvas.toDataURL('image/png')
          const a = document.createElement('a')
          a.href = png; a.download = filename; a.click()
          resolve(true)
        } catch { resolve(false) }
      }
      img.onerror = () => resolve(false)
      img.src = svg64
    } catch {
      resolve(false)
    }
  })
}
```

- [ ] **Step 2: Add Copy/Download CSV to `MlTableView.tsx`.** Replace the whole file:

```tsx
import { useState } from 'react'
import { Copy, Download, Check } from 'lucide-react'
import type { QueryResult } from '../../types'
import { copyRowsAsCsv, downloadCsv } from './chartExport'

interface Props { result: QueryResult }

export default function MlTableView({ result }: Props) {
  const display = result.rows.slice(0, 500)
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    const ok = await copyRowsAsCsv(result.columns, result.rows)
    if (ok) { setCopied(true); setTimeout(() => setCopied(false), 1500) }
  }

  return (
    <div className="p-4 overflow-auto h-full">
      <div className="flex items-center justify-between mb-2">
        <p className="text-gray-600 text-[10px]">
          {result.rows.length} rows · {result.duration_ms.toFixed(1)}ms
          {result.rows.length > 500 && ' · showing first 500'}
        </p>
        <div className="flex items-center gap-2">
          <button onClick={handleCopy}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
            {copied ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
            {copied ? 'Copied!' : 'Copy CSV'}
          </button>
          <button onClick={() => downloadCsv(result.columns, result.rows, 'ml_result.csv')}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
            <Download size={11} /> CSV
          </button>
        </div>
      </div>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {result.columns.map(c => (
              <th key={c} className="text-left text-[10px] text-gray-500 uppercase tracking-wider px-3 py-1.5 border-b border-white/5 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {display.map((row, i) => (
            <tr key={i} className="hover:bg-white/3 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-1.5 text-gray-300 border-b border-white/3 whitespace-nowrap max-w-[200px] truncate">
                  {cell == null ? <span className="text-gray-600 italic">null</span> : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: Add a PNG button to the main chart in `MlChartView.tsx`.** Add the import:

```tsx
import { downloadSvgAsPng } from './chartExport'
```

Wrap the main chart container with a ref. Change the chart wrapper `<div>` (line 441):

```tsx
      <div ref={chartWrapRef} className="bg-secondary border border-white/5 rounded-lg p-3" style={{ height: 280 }}>
```

Declare the ref next to the other refs (near line 170, after `cohortPanelRef`):

```tsx
  const chartWrapRef = useRef<HTMLDivElement>(null)
```

Add a small PNG button on the stats line. In the stats row (lines 533-544), append (inside that `<div className="flex items-center gap-4 …">`):

```tsx
        <button
          onClick={async () => {
            const ok = await downloadSvgAsPng(chartWrapRef.current?.querySelector('svg') ?? null, 'ml_chart.png')
            if (!ok) alert('Không xuất được PNG (thử lại hoặc dùng Copy CSV).')
          }}
          className="ml-auto flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors">
          <Download size={12} /> PNG
        </button>
```

(`Download` is already imported via Task 9's lucide line — if not present, add it to the import.)

- [ ] **Step 4: Add a PNG button to the drilldown chart in `MlDrilldownView.tsx`.** Add `Download` to the lucide import and `downloadSvgAsPng` import:

```tsx
import { Layers, ChevronRight, Download } from 'lucide-react'
import { downloadSvgAsPng } from './chartExport'
```

Add a ref on the chart's wrapping element. Wrap the `<ResponsiveContainer>` for the drilldown in a `<div ref={drillChartRef}>`:

```tsx
  const drillChartRef = useRef<HTMLDivElement>(null)
```
```tsx
              <div ref={drillChartRef}>
                <ResponsiveContainer width="100%" height={300}>
                  {/* …existing BarChart… */}
                </ResponsiveContainer>
              </div>
              <button
                onClick={async () => {
                  const ok = await downloadSvgAsPng(drillChartRef.current?.querySelector('svg') ?? null, 'drilldown.png')
                  if (!ok) alert('Không xuất được PNG.')
                }}
                className="self-start flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors">
                <Download size={11} /> PNG
              </button>
```

(`useRef` is now actually used in `MlDrilldownView`, resolving the earlier optional-trim note.)

- [ ] **Step 5: Type-check & build**

Run: `cd frontend ; npm run build`
Expected: build succeeds.

- [ ] **Step 6: Manual verify**

- Table tab → **Copy CSV** copies (paste into a sheet → columns/rows correct, values with commas stay quoted); **CSV** downloads `ml_result.csv`.
- Charts main chart → **PNG** downloads `ml_chart.png` that opens and shows the chart on the dark background.
- Drilldown panel → **PNG** downloads `drilldown.png`.
- Force a failure path mentally: if PNG ever fails it alerts and the app keeps working (CSV remains the reliable path).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ml/chartExport.ts frontend/src/components/ml/MlTableView.tsx frontend/src/components/ml/MlChartView.tsx frontend/src/components/ml/MlDrilldownView.tsx
git commit -m "feat(ml): CSV copy/download + best-effort PNG export (#8b)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Final verification + delivery

**Files:** none (verification only)

- [ ] **Step 1: Full backend test suite**

Run: `cd backend ; uv run pytest -q`
Expected: all pass (the existing ~204 + the 4 new tests).

- [ ] **Step 2: Full frontend build**

Run: `cd frontend ; npm run build`
Expected: `tsc -b` clean, `vite build` writes `frontend/dist` with no errors.

- [ ] **Step 3: End-to-end manual smoke (in the running MAIN app)**

Run `python run.py`, then in ML Studio verify each shipped item:
1. Dataset Overview shows Min·Max·Mean·Median·Range·Std + Show Code.
2. ⟳ "Góc nhìn khác" rotates suggestions; chips apply.
3. Khoan sâu thời gian: Year→Month→Day drill + breadcrumb dropdowns.
4. Run in Chuỗi thời gian / Cohort: no scroll-jump.
5. Correlation: ranked +/− lists under heatmap.
6. Cột nhóm: clustered measures side-by-side.
7. Sidebar: Automation under ML Studio.
8. 💡 insight under main/TS/drilldown charts; Copy CSV + PNG export work.

- [ ] **Step 4: Confirm delivery target**

Verify the changes are in the MAIN working tree `D:\assitant_tools\tools_performance\08_Projects\leonie` (where the dev servers run), not only in a worktree. `git status` there should show the commits / files. **Do not push.**

- [ ] **Step 5: (Optional) Update auto-memory**

Add a memory note recording that Phase 1 of the ML Studio analyst-upgrade shipped locally (which commits), Phase 2 (Power BI value-format picker) and Phase 3 (pin-to-dashboard) remain as separate future specs.

---

## Self-Review (done against the spec)

**Spec coverage** — every Phase-1 item maps to a task:
- #1 describe +median/range +Show Code → Tasks 2 (backend) + 3 (frontend) ✓
- #2 rotating suggestion pool + ⟳ → Task 9 ✓
- #3 drill-down Year→Month→Day + breadcrumb → Tasks 4 (backend `/drilldown` + codegen) + 5 (panel + wiring) ✓
- #4 scroll-jump fix (ts + cohort) → Task 6 ✓
- #5 ranked +/− correlation → Task 7 ✓
- #6 clustered columns → Task 8 ✓
- #7 Sidebar Automation move → Task 1 ✓
- #8b CSV/PNG export → Task 11 ✓
- #8c auto-insight → Task 10 ✓
- #8a Ctrl+Enter → intentionally **not** built (already exists in `SqlEditor`, per spec QĐ-3) ✓
- Out-of-scope Phase 2/3 → left out by design, noted in Task 12 Step 5 ✓

**Placeholder scan:** no TBD/"handle edge cases"/"similar to Task N" — every code step shows full code. Backend steps have failing-test→implement→pass. Frontend steps use build + concrete manual checks (no JS runner exists; the two pure helpers carry worked examples).

**Type consistency:** `DescribeResult{rows,code}` (Task 2 endpoint ↔ Task 3 `fetchDescribe`); `DrilldownResult` fields `grain/labels/values/value_col/agg/code` identical across Task 4 endpoint, Task 5 type+`fetchDrilldown`+`MlDrilldownView`; `describe_code(filename)` / `drilldown_code(date_col,value_col,filename,grain,agg,year?,month?)` signatures match their callers; `buildRecipePool(profile, resultColumns)` and `Recipe{title,kind,iconName,x?,y?,ys?}` match the Task 9 consumer; `describeSeries(labels, values)` / `formatTrend(first,last)` match Task 10 callers; `copyRowsAsCsv/downloadCsv/downloadSvgAsPng/toCsv` match Task 11 callers; `setYCols`/`type:'clustered'` defined in Task 8 before Task 9 uses them.

**Cross-file edit note:** Tasks 5–11 all touch `MlChartView.tsx`. Executed in order, each edit's anchor lines are stable (different regions), but if applying out of order, re-read the file first and match on the surrounding code shown — not on line numbers.
