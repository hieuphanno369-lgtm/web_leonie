# Z-Score Analysis — ML Studio Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan.

**Goal:** Add a Z-Score test type to ML Studio's Stats tab that combines outlier detection (user-adjustable threshold) with z-score distribution histogram and a standardized CSV export.

**Architecture:** New `zscore` test type plugged into the existing `run_stats()` backend handler; a dedicated `ZScoreResult.tsx` component renders the custom UI (summary, slider, histogram, table); a new `/stats/zscore_csv` endpoint handles standardization download. Threshold filtering is done client-side so the slider is reactive without extra API calls.

**Tech Stack:** FastAPI + Polars (backend), React + TypeScript + Recharts + lucide-react (frontend), Tailwind CSS with existing design tokens.

---

## 1. Backend Changes (`backend/routers/ml.py`)

### 1a. New `zscore` handler inside `run_stats()`

Added after the existing `chi2` block:

```python
if body.test == "zscore":
    z = (a - a.mean()) / (a.std() + 1e-9)
    abs_z = np.abs(z)
    rows_sorted = sorted(
        [{"idx": int(i), "value": round(float(a[i]), 4), "z_score": round(float(z[i]), 4)}
         for i in range(len(a))],
        key=lambda r: abs(r["z_score"]), reverse=True
    )[:5000]   # cap at 5000 rows
    counts, edges = np.histogram(z, bins=30)
    return {
        "mean": round(float(a.mean()), 4),
        "std":  round(float(a.std()),  4),
        "n":    int(len(a)),
        "rows": rows_sorted,
        "histogram_bins": [
            {"x0": round(float(edges[i]), 3), "x1": round(float(edges[i+1]), 3), "count": int(counts[i])}
            for i in range(len(counts))
        ],
    }
```

**Notes:**
- `rows` contains ALL rows (up to 5000, sorted by |z| descending). The frontend filters by threshold client-side.
- Status (`normal` / `watch` / `outlier`) is NOT computed here — it depends on the user's threshold, which is client-side state.
- `+1e-9` guard prevents division by zero on constant columns.

### 1b. New endpoint `POST /stats/zscore_csv`

```python
class ZScoreCsvIn(BaseModel):
    file_id: int
    col_a:   str

@router.post("/stats/zscore_csv")
def zscore_csv(body: ZScoreCsvIn):
    conn = get_connection()
    row  = _get_file_row(conn, body.file_id)
    conn.close()
    df   = _load_df(row["filepath"])

    if body.col_a not in df.columns:
        raise HTTPException(400, f"Column '{body.col_a}' not found")

    series = df[body.col_a].cast(pl.Float64)
    mean_  = float(series.mean())
    std_   = float(series.std()) or 1e-9
    z_col  = ((series - mean_) / std_).alias("z_score")
    df_out = df.with_columns(z_col)

    # Add status column based on fixed threshold 2.0
    df_out = df_out.with_columns(
        pl.when(pl.col("z_score").abs() < 1).then(pl.lit("normal"))
          .when(pl.col("z_score").abs() < 2).then(pl.lit("watch"))
          .otherwise(pl.lit("outlier"))
          .alias("z_status")
    )

    csv_bytes = df_out.write_csv().encode("utf-8")
    filename  = f"zscore_{body.col_a}_{row['filename']}"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Notes:** CSV download uses fixed threshold 2.0 for status column (reasonable default; user can filter the CSV themselves). Returns the full dataset with `z_score` + `z_status` columns appended.

---

## 2. Frontend — Types (`frontend/src/types.ts`)

```typescript
export interface ZScoreRow {
  idx:     number
  value:   number
  z_score: number
}

export interface ZScoreData {
  mean:           number
  std:            number
  n:              number
  rows:           ZScoreRow[]
  histogram_bins: Array<{ x0: number; x1: number; count: number }>
}
```

---

## 3. Frontend — API (`frontend/src/api/ml.ts`)

Add two functions:

```typescript
// ZScoreData is already returned by runStats() — no separate function needed.
// Only the CSV download needs a new call:

export async function downloadZScoreCsv(fileId: number, colA: string): Promise<void> {
  const res = await axios.post(
    '/api/ml/stats/zscore_csv',
    { file_id: fileId, col_a: colA },
    { responseType: 'blob' }
  )
  const url = URL.createObjectURL(new Blob([res.data]))
  const a   = document.createElement('a')
  a.href = url
  a.download = `zscore_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

---

## 4. Frontend — `MlStatsView.tsx`

### 4a. TestType union

```typescript
type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney' | 'zscore'
```

### 4b. TESTS array entry

```typescript
{ value: 'zscore', label: 'Z-Score', needsColB: false },
```

Insert after `'bootstrap'` to keep the logical grouping (single-column tests first).

### 4c. HINTS entry

```typescript
zscore: {
  what: 'Tính z-score cho mỗi giá trị: (x − mean) / std. Phát hiện outlier và hiện phân phối chuẩn hoá.',
  when: 'Dùng khi muốn biết giá trị nào bất thường, hoặc trước khi đưa dữ liệu vào model ML cần chuẩn hoá.',
  colA: 'Cột số bất kỳ — VD: doanh thu, số ngày, transaction_interval.',
},
```

### 4d. Result rendering — special-case for `zscore`

In the results section, replace the generic grid with `<ZScoreResult>` when test is zscore:

```tsx
{result && (
  <>
    {test === 'zscore'
      ? <ZScoreResult
          data={result as unknown as ZScoreData}
          colA={colA}
          fileId={dataset.file_id}
        />
      : <div className="bg-secondary border border-white/5 rounded-lg p-4">
          <div className="grid grid-cols-2 gap-3">
            {/* existing generic grid */}
          </div>
        </div>
    }
    {/* Show Code + AI Interpretation remain below, always */}
  </>
)}
```

### 4e. `generateCode()` — add zscore case

```typescript
if (test === 'zscore')
  return `${load}\n${a}\nz = (a - a.mean()) / (a.std() + 1e-9)\nfor i, (val, zi) in enumerate(zip(a, z)):\n    status = "outlier" if abs(zi) >= 2 else "watch" if abs(zi) >= 1 else "normal"\n    print(f"row {i}: value={val:.4f}, z={zi:.4f}, {status}")\n`
```

---

## 5. Frontend — `ZScoreResult.tsx` (new component)

**File:** `frontend/src/components/ml/ZScoreResult.tsx`

**Props:**
```typescript
interface Props {
  data:   ZScoreData
  colA:   string
  fileId: number
}
```

**State:**
```typescript
const [threshold, setThreshold] = useState(2.0)
const [downloading, setDownloading] = useState(false)
```

**Derived (no extra API call):**
```typescript
const outliers = data.rows.filter(r => Math.abs(r.z_score) >= threshold)
const statusOf = (z: number) =>
  Math.abs(z) >= threshold ? 'outlier' : Math.abs(z) >= 1 ? 'watch' : 'normal'
```

**Sub-sections rendered (top to bottom):**

### Summary row
```
mean: 1,234.56   std: 456.78   n: 10,000
```
Class: same as describe grid — `text-[10px] text-gray-600 uppercase tracking-wider` label, `text-sm font-semibold text-white` value.

### Threshold control
```
Ngưỡng:  [slider 1.0 → 4.0]  2.0
Preset:  [1.5]  [2.0]  [2.5]  [3.0]
→ 47 outliers (0.47%)
```
- Slider: `<input type="range" min={1} max={4} step={0.1}>`
- Preset buttons: `bg-analytics/10 text-analytics border-analytics/30` when active, else `text-gray-500 border-transparent hover:text-gray-300`
- Outlier count: `text-danger` if > 0, else `text-work`

### Histogram
- `BarChart` from Recharts, height 160px
- X-axis: z-score value (x0 of each bin)
- Y-axis: count
- Bar fill color based on bin center `c = (x0 + x1) / 2`:
  - `Math.abs(c) >= threshold` → `#ef4444` (danger/outlier)
  - `Math.abs(c) >= 1` → `#f59e0b` (watch, amber-500)
  - else → `#34d399` (work/normal, green)
- Two `ReferenceLine`s at `x = threshold` and `x = -threshold`, `stroke="rgba(255,255,255,0.3)"`, dashed
- No legend needed — color is self-explanatory with the status badges below

### Outlier table
- Shows only rows where `|z| >= threshold`, sorted by |z| desc
- Columns: `Row`, `Value`, `Z-Score`, `Status`
- Max 200 rows shown (with "... and N more" note if exceeds)
- Status cell:
  - `outlier` → `<AlertTriangle size={10} />` + `text-danger` text
  - `watch` → `<AlertCircle size={10} />` + `text-yellow-400` text
  - `normal` → `<CheckCircle size={10} />` + `text-work` text

### Download button
```tsx
<button onClick={handleDownload} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors">
  <Download size={12} /> {downloading ? 'Đang tải...' : 'Download Standardized CSV'}
</button>
```
Calls `downloadZScoreCsv(fileId, colA)`.

---

## 6. Icon Summary (all from `lucide-react`)

| Location | Icon | Size |
|----------|------|------|
| Test hint card | `Activity` | 12 |
| Status: Normal | `CheckCircle` | 10 |
| Status: Watch | `AlertCircle` | 10 |
| Status: Outlier | `AlertTriangle` | 10 |
| Download button | `Download` | 12 |

---

## 7. Color Token Map

| Element | Tailwind class | Hex |
|---------|---------------|-----|
| Panel accent / threshold | `text-analytics` | `#fbbf24` |
| Histogram — Normal bar | `fill-[#34d399]` | `#34d399` |
| Histogram — Watch bar | `fill-[#f59e0b]` | `#f59e0b` |
| Histogram — Outlier bar | `fill-[#ef4444]` | `#ef4444` |
| Status Normal text | `text-work` | `#34d399` |
| Status Watch text | `text-yellow-400` | `#facc15` |
| Status Outlier text | `text-danger` | `#ef4444` |
| Slider preset active | `bg-analytics/10 text-analytics border-analytics/30` | amber |
| Download / Show Code | `text-gray-500 hover:text-gray-300` | gray |

---

## 8. Files Changed

| File | Action |
|------|--------|
| `backend/routers/ml.py` | Add `zscore` handler in `run_stats()` + new `POST /stats/zscore_csv` endpoint |
| `frontend/src/types.ts` | Add `ZScoreRow`, `ZScoreData` interfaces |
| `frontend/src/api/ml.ts` | Add `downloadZScoreCsv()` |
| `frontend/src/components/ml/MlStatsView.tsx` | Add `'zscore'` to TestType, TESTS, HINTS, generateCode(), special-case result rendering |
| `frontend/src/components/ml/ZScoreResult.tsx` | **New file** — full Z-Score UI component |

---

## 9. Out of Scope

- Z-score for categorical columns (not meaningful)
- Real-time threshold update via API (all filtering is client-side)
- Multivariate z-score / Mahalanobis distance
- AI interpretation for z-score results (can be added later)
