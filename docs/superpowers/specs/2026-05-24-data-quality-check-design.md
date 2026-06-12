# Data Quality Check — Design Spec

**Date:** 2026-05-24
**Feature:** Data Quality Check for ML Studio
**Location:** Inline banner in each ML Studio tab (Forecast, Stats, Cohort, SQL)

---

## Overview

When a user loads a file in ML Studio, a data quality banner appears at the top of every tab. The banner auto-runs once per `file_id` (cached), shows a collapsible warning list if issues are found, or a green "all clear" if the data is clean.

Five check types: null values, duplicate rows, numeric outliers (z-score > 3), constant columns, and dtype mismatches.

---

## Backend

### Endpoint

```
GET /api/ml/quality/{file_id}
```

Added to existing `backend/routers/ml.py` — no new file.

Reads the file from `UPLOADS_DIR` using polars (already imported). Returns 404 if `file_id` not found.

### Check Logic

| Check | Implementation |
|-------|---------------|
| **null** | `df.null_count()` per column → flag columns where null % > 0 |
| **duplicate** | `df.is_duplicated().sum()` → flag if > 0 duplicate rows |
| **outlier** | For each numeric column: compute z-scores via `(col - mean) / std`, count values where `abs(z) > 3` → flag if count > 0 |
| **constant** | `col.n_unique() == 1` → flag column |
| **dtype** | Column name contains "date", "time", "year", "id" (case-insensitive) but polars dtype is `Utf8`/`String` → flag |

### Response Model

```python
class QualityIssue(BaseModel):
    type: str          # "null" | "outlier" | "duplicate" | "constant" | "dtype"
    column: str | None # None for duplicate (row-level issue)
    detail: str        # human-readable description

class QualityResult(BaseModel):
    file_id: str
    rows: int
    cols: int
    issues: list[QualityIssue]
    issue_count: int
```

### Example Response

```json
{
  "file_id": "abc123",
  "rows": 1000,
  "cols": 8,
  "issues": [
    { "type": "null",      "column": "revenue",    "detail": "23.4% null (234/1000)" },
    { "type": "outlier",   "column": "revenue",    "detail": "5 outliers (z > 3)" },
    { "type": "duplicate", "column": null,          "detail": "12 duplicate rows" },
    { "type": "constant",  "column": "region",     "detail": "Only 1 unique value" },
    { "type": "dtype",     "column": "order_date", "detail": "Likely date stored as string" }
  ],
  "issue_count": 5
}
```

Returns `{ issues: [], issue_count: 0 }` when data is clean.

### Error Handling

- `file_id` not found in `UPLOADS_DIR` → 404
- File unreadable (corrupt/unsupported format) → 400 with message
- Column std = 0 for z-score calc → skip outlier check for that column (avoid division by zero)

---

## Frontend

### New Files

```
frontend/src/
  components/ml/DataQualityBanner.tsx
```

### Modified Files

| File | Change |
|------|--------|
| `frontend/src/types.ts` | Add `QualityIssue`, `QualityResult` interfaces |
| `frontend/src/api/ml.ts` | Add `fetchQuality(file_id: string)` function |
| `frontend/src/pages/analytics/MlStudio.tsx` | Add quality fetch + cache state, pass `quality` prop to MlResultTabs |
| `frontend/src/components/ml/MlResultTabs.tsx` | Pass `quality` prop down to each tab |
| `frontend/src/components/ml/MlForecastView.tsx` | Render `<DataQualityBanner>` at top |
| `frontend/src/components/ml/MlStatsView.tsx` | Render `<DataQualityBanner>` at top |
| `frontend/src/components/ml/MlChartView.tsx` | Render `<DataQualityBanner>` at top |
| `frontend/src/components/ml/MlCohortView.tsx` | Render `<DataQualityBanner>` at top |

### Types (`types.ts`)

```typescript
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

### API Helper (`api/ml.ts`)

```typescript
export async function fetchQuality(file_id: string): Promise<QualityResult> {
  const { data } = await client.get(`/api/ml/quality/${file_id}`)
  return data
}
```

### Caching in `MlStudio.tsx`

```typescript
const [qualityCache, setQualityCache] = useState<Record<string, QualityResult>>({})

useEffect(() => {
  if (!fileId || qualityCache[fileId]) return
  fetchQuality(fileId)
    .then(result => setQualityCache(prev => ({ ...prev, [fileId]: result })))
    .catch(() => {}) // silent fail — quality check is non-blocking
}, [fileId])

const quality = fileId ? qualityCache[fileId] ?? null : null
```

Pass `quality` as prop to each tab component.

### `DataQualityBanner` Component

Props: `quality: QualityResult | null`

**States:**
- `quality === null` → render nothing (loading or no file selected)
- `issue_count === 0` → green bar: `✓ No data quality issues`
- `issue_count > 0` → yellow collapsible banner

**Collapsed:**
```
⚠  5 data quality issues found                    [▼ Show details]
```

**Expanded:**
```
⚠  5 issues                                        [▲ Hide]
  revenue      23.4% null (234/1000)          NULL
  revenue      5 outliers (z > 3)           OUTLIER
  —            12 duplicate rows            DUPLIC.
  region       Only 1 unique value          CONSTANT
  order_date   Likely date stored as string   DTYPE
```

**Badge colours by type:**
| Type | Colour |
|------|--------|
| `null` | red (`#f87171`) |
| `outlier` | orange (`#fb923c`) |
| `duplicate` | yellow (`#fbbf24`) |
| `constant` | grey (`#9ca3af`) |
| `dtype` | purple (`#a78bfa`) |

The banner is collapsible via local `useState`. Default: collapsed if issues exist.

---

## Testing

File: `backend/tests/test_ml_quality.py`

| Test | Description |
|------|-------------|
| `test_quality_clean_data` | File with no issues → `issue_count == 0` |
| `test_quality_null_detection` | Column with nulls → `null` issue present |
| `test_quality_duplicate_detection` | Rows duplicated → `duplicate` issue present |
| `test_quality_outlier_detection` | Numeric column with extreme value → `outlier` issue |
| `test_quality_constant_column` | Column with single unique value → `constant` issue |
| `test_quality_dtype_mismatch` | Column named "order_date" stored as string → `dtype` issue |
| `test_quality_file_not_found` | Unknown `file_id` → 404 |
| `test_quality_zero_std_no_crash` | Column with std=0 → no division-by-zero error |

---

## Out of Scope

- Auto-blocking forecast/stats when data quality is poor (user decides)
- Fixing data quality inline (rename columns, drop nulls)
- Persisting quality reports to SQLite
- Quality check on SQL query results (only on uploaded files)
