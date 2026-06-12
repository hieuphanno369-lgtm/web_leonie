# Data Quality Check — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a collapsible data quality banner to every ML Studio analysis tab that auto-runs five checks (null, duplicate, outlier, constant, dtype) when a file is loaded.

**Architecture:** New `GET /api/ml/quality/{file_id}` endpoint added to the existing `ml.py` router; frontend caches results per `file_id` in `MlStudio.tsx` and passes a `quality` prop down through `MlResultTabs` to four tab components, each rendering a shared `DataQualityBanner` component at the top.

**Tech Stack:** Python/polars (backend checks), FastAPI, React 18 + TypeScript, Tailwind CSS, Lucide React icons.

---

## File Map

| Action | File | What changes |
|--------|------|-------------|
| Modify | `backend/routers/ml.py` | Add `QualityIssue`, `QualityResult` models + `GET /quality/{file_id}` endpoint |
| Create | `backend/tests/test_ml_quality.py` | 8 tests for the quality endpoint |
| Modify | `frontend/src/types.ts` | Add `QualityIssue`, `QualityResult` interfaces |
| Modify | `frontend/src/api/ml.ts` | Add `fetchQuality(file_id)` function |
| Create | `frontend/src/components/ml/DataQualityBanner.tsx` | Collapsible banner component |
| Modify | `frontend/src/pages/analytics/MlStudio.tsx` | Add `qualityCache` state + `useEffect`, pass `quality` to `MlResultTabs` |
| Modify | `frontend/src/components/ml/MlResultTabs.tsx` | Add `quality` prop, pass to 4 tab components |
| Modify | `frontend/src/components/ml/MlForecastView.tsx` | Add `quality` prop, render banner at top |
| Modify | `frontend/src/components/ml/MlStatsView.tsx` | Add `quality` prop, render banner at top |
| Modify | `frontend/src/components/ml/MlChartView.tsx` | Add `quality` prop, render banner at top |
| Modify | `frontend/src/components/ml/MlCohortView.tsx` | Add `quality` prop, render banner at top |

---

## Task 1: Backend Quality Endpoint (TDD)

**Files:**
- Modify: `backend/routers/ml.py`
- Create: `backend/tests/test_ml_quality.py`

Context: `ml.py` already imports `polars as pl`, defines `_get_file_row(conn, file_id)` (raises 404 if not found) and `_load_df(filepath)` (reads CSV/Excel). Helper `_numeric_cols(df)` returns numeric column names. Tests use `TestClient(app)` with auto-reset DB from `conftest.py`.

- [ ] **Step 1: Write all 8 failing tests**

Create `backend/tests/test_ml_quality.py`:

```python
import io
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _upload(client, csv_bytes: bytes, name: str = "test.csv") -> str:
    resp = client.post(
        "/api/ml/upload",
        files={"file": (name, io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["file_id"]


def test_quality_clean_data(client):
    fid = _upload(client, b"name,value\nAlice,100\nBob,200\nCarol,150\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    assert resp.status_code == 200
    d = resp.json()
    assert d["issue_count"] == 0
    assert d["issues"] == []
    assert d["rows"] == 3
    assert d["cols"] == 2


def test_quality_null_detection(client):
    fid = _upload(client, b"name,value\nAlice,100\nBob,\nCarol,150\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    assert resp.status_code == 200
    null_issues = [i for i in resp.json()["issues"] if i["type"] == "null"]
    assert len(null_issues) == 1
    assert null_issues[0]["column"] == "value"
    assert "%" in null_issues[0]["detail"]


def test_quality_duplicate_detection(client):
    fid = _upload(client, b"name,value\nAlice,100\nAlice,100\nBob,200\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    dup_issues = [i for i in resp.json()["issues"] if i["type"] == "duplicate"]
    assert len(dup_issues) == 1
    assert dup_issues[0]["column"] is None
    assert "duplicate" in dup_issues[0]["detail"]


def test_quality_outlier_detection(client):
    # 1000 is a clear outlier vs 1,2,3,4,5 (z-score >> 3)
    fid = _upload(client, b"val\n1\n2\n3\n4\n5\n1000\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    outlier_issues = [i for i in resp.json()["issues"] if i["type"] == "outlier"]
    assert len(outlier_issues) == 1
    assert outlier_issues[0]["column"] == "val"
    assert "z > 3" in outlier_issues[0]["detail"]


def test_quality_constant_column(client):
    fid = _upload(client, b"name,region\nAlice,VN\nBob,VN\nCarol,VN\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    const_issues = [i for i in resp.json()["issues"] if i["type"] == "constant"]
    assert any(i["column"] == "region" for i in const_issues)


def test_quality_dtype_mismatch(client):
    # order_date column name contains "date" but values are strings
    fid = _upload(client, b"order_date,value\n2026-01-01,100\n2026-01-02,200\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    dtype_issues = [i for i in resp.json()["issues"] if i["type"] == "dtype"]
    assert any(i["column"] == "order_date" for i in dtype_issues)


def test_quality_file_not_found(client):
    resp = client.get("/api/ml/quality/nonexistent-file-id")
    assert resp.status_code == 404


def test_quality_zero_std_no_crash(client):
    # All same value → std = 0, must not raise ZeroDivisionError
    fid = _upload(client, b"val\n5\n5\n5\n5\n5\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_ml_quality.py -v
```

Expected: 8 FAILED (endpoint doesn't exist yet — `404` or `405` responses).

- [ ] **Step 3: Add Pydantic models to `ml.py`**

Open `backend/routers/ml.py`. After the existing `ForecastInterpretIn` class (around line 104), add:

```python
class QualityIssue(BaseModel):
    type: str           # "null" | "outlier" | "duplicate" | "constant" | "dtype"
    column: str | None  # None for row-level issues (duplicate)
    detail: str


class QualityResult(BaseModel):
    file_id: str
    rows: int
    cols: int
    issues: list[QualityIssue]
    issue_count: int
```

- [ ] **Step 4: Add the quality endpoint to `ml.py`**

Add after the `_get_file_row` and `_numeric_cols` helpers (after line ~124), before `@router.get("/datasets")`:

```python
@router.get("/quality/{file_id}", response_model=QualityResult)
def get_quality(file_id: str):
    conn = get_connection()
    try:
        row = _get_file_row(conn, file_id)
    finally:
        conn.close()

    try:
        df = _load_df(row["filepath"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {e}")

    n_rows, n_cols = df.shape
    issues: list[QualityIssue] = []

    # Null check — flag every column with at least one null
    for col in df.columns:
        null_n = df[col].null_count()
        if null_n > 0:
            pct = null_n / n_rows * 100
            issues.append(QualityIssue(
                type="null",
                column=col,
                detail=f"{pct:.1f}% null ({null_n}/{n_rows})",
            ))

    # Duplicate rows
    dup_count = int(df.is_duplicated().sum())
    if dup_count > 0:
        issues.append(QualityIssue(
            type="duplicate",
            column=None,
            detail=f"{dup_count} duplicate rows",
        ))

    # Outliers — z-score > 3 for numeric columns (skip if std == 0)
    for col in _numeric_cols(df):
        series = df[col].drop_nulls()
        if len(series) < 2:
            continue
        mean_val = series.mean()
        std_val = series.std()
        if not std_val or std_val == 0:
            continue
        z_scores = ((series - mean_val) / std_val).abs()
        outlier_count = int((z_scores > 3).sum())
        if outlier_count > 0:
            issues.append(QualityIssue(
                type="outlier",
                column=col,
                detail=f"{outlier_count} outlier{'s' if outlier_count != 1 else ''} (z > 3)",
            ))

    # Constant columns — only 1 unique value
    for col in df.columns:
        if df[col].n_unique() == 1:
            issues.append(QualityIssue(
                type="constant",
                column=col,
                detail="Only 1 unique value",
            ))

    # Dtype mismatch — column name suggests temporal/ID but stored as string
    _DATE_KEYWORDS = ("date", "time", "year", "id")
    for col in df.columns:
        if any(kw in col.lower() for kw in _DATE_KEYWORDS):
            if str(df[col].dtype).lower() in ("utf8", "string"):
                issues.append(QualityIssue(
                    type="dtype",
                    column=col,
                    detail="Likely date stored as string",
                ))

    return QualityResult(
        file_id=file_id,
        rows=n_rows,
        cols=n_cols,
        issues=issues,
        issue_count=len(issues),
    )
```

- [ ] **Step 5: Run tests to confirm all 8 pass**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/test_ml_quality.py -v
```

Expected: 8 PASSED.

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
.venv/Scripts/python.exe -m pytest -v
```

Expected: all existing tests still PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml_quality.py
git commit -m "feat(ml): add data quality check endpoint GET /ml/quality/{file_id}"
```

---

## Task 2: Frontend Types + API Helper

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/ml.ts`

Context: `types.ts` uses a section-comment style (`// ─── Section ───`). `api/ml.ts` imports `client` from `./client` (baseURL is `/api`, so calls use `/ml/...` without the `/api` prefix). Existing functions: `uploadFile`, `fetchDatasets`, `deleteDataset`, `runQuery`, `runStats`, `runForecast`, etc.

- [ ] **Step 1: Add types to `frontend/src/types.ts`**

Append at the end of the file (after the `QuickNote` section):

```typescript
// ─── ML Data Quality ──────────────────────────────────────────────────────────

export interface QualityIssue {
  type: 'null' | 'outlier' | 'duplicate' | 'constant' | 'dtype'
  column: string | null
  detail: string
}

export interface QualityResult {
  file_id: string
  rows: number
  cols: number
  issues: QualityIssue[]
  issue_count: number
}
```

- [ ] **Step 2: Add `fetchQuality` to `frontend/src/api/ml.ts`**

Add the import for `QualityResult` to the existing import block at the top of the file:

```typescript
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix,
  QualityResult,
} from '../types'
```

Then add `fetchQuality` at the end of the file:

```typescript
export async function fetchQuality(file_id: string): Promise<QualityResult> {
  const { data } = await client.get<QualityResult>(`/ml/quality/${file_id}`)
  return data
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Expected: no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts
git commit -m "feat(ml): add QualityResult types and fetchQuality API helper"
```

---

## Task 3: DataQualityBanner Component

**Files:**
- Create: `frontend/src/components/ml/DataQualityBanner.tsx`

Context: Existing ML components use Lucide icons, Tailwind dark-theme classes (`text-gray-400`, `border-white/5`, `bg-white/5`). Badge style pattern used elsewhere (e.g. in `NoteItem.tsx`): inline `className` strings with colour tokens. The banner should render nothing when `quality` is `null`.

- [ ] **Step 1: Create `DataQualityBanner.tsx`**

```tsx
import { useState } from 'react'
import { AlertTriangle, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react'
import type { QualityResult } from '../../types'

interface Props {
  quality: QualityResult | null
}

const BADGE_STYLE: Record<string, string> = {
  null:      'bg-[#f87171]/10 text-[#f87171] border border-[#f87171]/20',
  outlier:   'bg-[#fb923c]/10 text-[#fb923c] border border-[#fb923c]/20',
  duplicate: 'bg-[#fbbf24]/10 text-[#fbbf24] border border-[#fbbf24]/20',
  constant:  'bg-[#9ca3af]/10 text-[#9ca3af] border border-[#9ca3af]/20',
  dtype:     'bg-[#a78bfa]/10 text-[#a78bfa] border border-[#a78bfa]/20',
}

const BADGE_LABEL: Record<string, string> = {
  null: 'NULL', outlier: 'OUTLIER', duplicate: 'DUPLIC.', constant: 'CONSTANT', dtype: 'DTYPE',
}

export default function DataQualityBanner({ quality }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!quality) return null

  if (quality.issue_count === 0) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/5 border-b border-emerald-500/10 text-emerald-400 text-xs flex-shrink-0">
        <CheckCircle size={13} />
        No data quality issues
      </div>
    )
  }

  return (
    <div className="border-b border-yellow-500/20 bg-yellow-500/5 flex-shrink-0">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-yellow-400 hover:bg-yellow-500/5 transition-colors"
      >
        <span className="flex items-center gap-2">
          <AlertTriangle size={13} />
          {quality.issue_count} data quality issue{quality.issue_count !== 1 ? 's' : ''} found
        </span>
        {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {expanded && (
        <div className="px-4 pb-3 flex flex-col gap-1.5">
          {quality.issues.map((issue, i) => (
            <div key={i} className="flex items-center gap-3 text-xs">
              <span className="text-gray-400 font-mono w-32 truncate flex-shrink-0">
                {issue.column ?? '—'}
              </span>
              <span className="text-gray-300 flex-1">{issue.detail}</span>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded flex-shrink-0 ${BADGE_STYLE[issue.type] ?? ''}`}>
                {BADGE_LABEL[issue.type] ?? issue.type.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/DataQualityBanner.tsx
git commit -m "feat(ml): add DataQualityBanner component"
```

---

## Task 4: Wire Banner into MlStudio + MlResultTabs + Tab Components

**Files:**
- Modify: `frontend/src/pages/analytics/MlStudio.tsx`
- Modify: `frontend/src/components/ml/MlResultTabs.tsx`
- Modify: `frontend/src/components/ml/MlForecastView.tsx`
- Modify: `frontend/src/components/ml/MlStatsView.tsx`
- Modify: `frontend/src/components/ml/MlChartView.tsx`
- Modify: `frontend/src/components/ml/MlCohortView.tsx`

Context:
- `MlStudio.tsx` currently imports `{ useState, useCallback }` from react and `{ uploadFile, deleteDataset, runQuery }` from `../../api/ml`. It holds `dataset: DatasetInfo | null` state and renders `<MlResultTabs result={result} dataset={dataset} activeTab={activeTab} onTabChange={setActiveTab} />`.
- `MlResultTabs` Props currently: `result`, `dataset`, `activeTab`, `onTabChange`. Renders 4 relevant tab components: `MlForecastView`, `MlStatsView`, `MlChartView`, `MlCohortView`.
- Tab component Props: `MlForecastView { dataset: DatasetInfo }`, `MlStatsView { dataset: DatasetInfo }`, `MlCohortView { dataset: DatasetInfo }`, `MlChartView { result: QueryResult; dataset: DatasetInfo | null }`.

- [ ] **Step 1: Update `MlStudio.tsx` — add quality cache + fetch**

Change the imports at the top of `frontend/src/pages/analytics/MlStudio.tsx`:

```typescript
import { useState, useCallback, useEffect, useRef } from 'react'
import type { DatasetInfo, QueryResult, QualityResult } from '../../types'
import { uploadFile, deleteDataset, runQuery, fetchQuality } from '../../api/ml'
```

Add two new state declarations after the existing `useState` calls (after `const [activeTab, setActiveTab] = useState<Tab>('table')`):

```typescript
const [qualityCache, setQualityCache] = useState<Record<string, QualityResult>>({})
const fetchedRef = useRef<Set<string>>(new Set())
```

Add a `useEffect` after the `handleRun` function:

```typescript
useEffect(() => {
  const fid = dataset?.file_id
  if (!fid || fetchedRef.current.has(fid)) return
  fetchedRef.current.add(fid)
  fetchQuality(fid)
    .then(result => setQualityCache(prev => ({ ...prev, [fid]: result })))
    .catch(() => { fetchedRef.current.delete(fid) })
}, [dataset?.file_id])

const quality = dataset ? (qualityCache[dataset.file_id] ?? null) : null
```

Update the `<MlResultTabs>` JSX to pass `quality`:

```tsx
<MlResultTabs
  result={result}
  dataset={dataset}
  activeTab={activeTab}
  onTabChange={setActiveTab}
  quality={quality}
/>
```

- [ ] **Step 2: Update `MlResultTabs.tsx` — add quality prop + pass down**

Add `QualityResult` to the import line at the top:

```typescript
import type { DatasetInfo, QueryResult, QualityResult } from '../../types'
```

Add `quality` to the `Props` interface:

```typescript
interface Props {
  result: QueryResult | null
  dataset: DatasetInfo | null
  activeTab: Tab
  onTabChange: (t: Tab) => void
  quality: QualityResult | null
}
```

Update the function signature:

```typescript
export default function MlResultTabs({ result, dataset, activeTab, onTabChange, quality }: Props) {
```

Update the 4 tab renders to pass `quality`:

```tsx
<div className={activeTab === 'charts'   ? '' : 'hidden'}>
  {result  ? <MlChartView result={result} dataset={dataset} quality={quality} /> : <Empty text="Run a query to see charts" />}
</div>
<div className={activeTab === 'stats'    ? '' : 'hidden'}>
  {dataset ? <MlStatsView dataset={dataset} quality={quality} /> : <Empty text="Upload a dataset first" />}
</div>
<div className={activeTab === 'forecast' ? '' : 'hidden'}>
  {dataset ? <MlForecastView dataset={dataset} quality={quality} /> : <Empty text="Upload a dataset first" />}
</div>
<div className={activeTab === 'cohort' ? '' : 'hidden'}>
  {dataset ? <MlCohortView dataset={dataset} quality={quality} /> : <Empty text="Upload a dataset first" />}
</div>
```

(Leave the `table` tab unchanged — it shows raw query results, not data analysis.)

- [ ] **Step 3: Update `MlForecastView.tsx` — add quality prop + banner**

Add `QualityResult` to the existing type import line (currently imports from `../../types`):

```typescript
import type { DatasetInfo, ForecastResult, ForecastCompareResult, ForecastInterpretResult, QualityResult } from '../../types'
```

Add import for the banner component (add after existing component imports):

```typescript
import DataQualityBanner from './DataQualityBanner'
```

Update the `Props` interface:

```typescript
interface Props { dataset: DatasetInfo; quality: QualityResult | null }
```

Update the function signature:

```typescript
export default function MlForecastView({ dataset, quality }: Props) {
```

Add `<DataQualityBanner quality={quality} />` as the very first element inside the component's root `<div>`. The current top-level element is a `<div className="flex flex-col h-full ...">` or similar — add it directly inside, before any other content:

```tsx
return (
  <div className="flex flex-col h-full overflow-hidden">
    <DataQualityBanner quality={quality} />
    {/* ... rest of existing content unchanged ... */}
  </div>
)
```

- [ ] **Step 4: Update `MlStatsView.tsx` — same pattern**

Add imports:

```typescript
import type { DatasetInfo, StatsResult, QualityResult } from '../../types'
import DataQualityBanner from './DataQualityBanner'
```

Update Props:

```typescript
interface Props { dataset: DatasetInfo; quality: QualityResult | null }
```

Update function signature:

```typescript
export default function MlStatsView({ dataset, quality }: Props) {
```

Add banner as first child of root div:

```tsx
<DataQualityBanner quality={quality} />
```

- [ ] **Step 5: Update `MlChartView.tsx` — same pattern**

Add imports:

```typescript
import type { QueryResult, DatasetInfo, CorrelationMatrix, QualityResult } from '../../types'
import DataQualityBanner from './DataQualityBanner'
```

Update Props:

```typescript
interface Props {
  result: QueryResult
  dataset: DatasetInfo | null
  quality: QualityResult | null
}
```

Update function signature:

```typescript
export default function MlChartView({ result, dataset, quality }: Props) {
```

Add banner as first child of root div:

```tsx
<DataQualityBanner quality={quality} />
```

- [ ] **Step 6: Update `MlCohortView.tsx` — same pattern**

Add imports:

```typescript
import type { DatasetInfo, QualityResult } from '../../types'
import DataQualityBanner from './DataQualityBanner'
```

Update Props:

```typescript
interface Props { dataset: DatasetInfo; quality: QualityResult | null }
```

Update function signature:

```typescript
export default function MlCohortView({ dataset, quality }: Props) {
```

Add banner as first child of root div:

```tsx
<DataQualityBanner quality={quality} />
```

- [ ] **Step 7: TypeScript build check**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Expected: zero type errors, build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/analytics/MlStudio.tsx \
        frontend/src/components/ml/MlResultTabs.tsx \
        frontend/src/components/ml/MlForecastView.tsx \
        frontend/src/components/ml/MlStatsView.tsx \
        frontend/src/components/ml/MlChartView.tsx \
        frontend/src/components/ml/MlCohortView.tsx
git commit -m "feat(ml): wire DataQualityBanner into all ML Studio analysis tabs"
```
