# Box Plot — ML Studio Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan.

**Goal:** Add a `boxplot` test type to ML Studio's Stats tab that renders a custom SVG box plot (single column or grouped by a category column), detects Tukey outliers (1.5×IQR), and provides CSV downloads for outliers and box stats.

**Architecture:** New `boxplot` branch in `run_stats()` (returns a unified `groups: []` shape for both single and group-by modes); two new endpoints for CSV exports; a self-contained `BoxPlotResult.tsx` component renders a custom SVG (no Recharts BoxPlot native, no Plotly bloat). Group cap is selected client-side via a dropdown that re-runs the API call.

**Tech Stack:** FastAPI + Polars + NumPy (backend), React 18 + TypeScript + lucide-react + Tailwind CSS (frontend). SVG `viewBox` for responsive sizing.

---

## 1. Backend Changes (`backend/routers/ml.py`)

### 1a. Add `max_groups` to `StatsIn` model

Existing `StatsIn` already has `file_id`, `test`, `col_a`, `col_b?`. Add:

```python
class StatsIn(BaseModel):
    file_id:    str
    test:       str
    col_a:      str
    col_b:      Optional[str] = None
    max_groups: int           = 10        # NEW — only used by boxplot
```

### 1b. New `boxplot` handler inside `run_stats()`

Added after the existing `zscore` block, before `raise HTTPException(...)`:

```python
if body.test == "boxplot":
    def _box_stats(arr: np.ndarray, name: str) -> dict:
        if len(arr) < 4:
            return None  # too small to compute meaningful quartiles
        q1, med, q3 = np.percentile(arr, [25, 50, 75])
        iqr = float(q3 - q1)
        lo, hi = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
        outlier_mask = (arr < lo) | (arr > hi)
        outlier_idx  = np.where(outlier_mask)[0]
        return {
            "name":         name,
            "n":            int(len(arr)),
            "min":          round(float(arr.min()),  4),
            "q1":           round(float(q1),         4),
            "median":       round(float(med),        4),
            "q3":           round(float(q3),         4),
            "max":          round(float(arr.max()),  4),
            "iqr":          round(iqr,               4),
            "lower_fence":  round(lo,                4),
            "upper_fence":  round(hi,                4),
            "outliers": [
                {"idx": int(i), "value": round(float(arr[i]), 4)}
                for i in outlier_idx[:1000]  # cap per group
            ],
        }

    groups: list[dict] = []
    truncated = False
    total_groups = 1

    if body.col_b:
        # Group-by mode — top N groups by count desc
        group_col = df[body.col_b].cast(pl.Utf8)
        counts    = group_col.value_counts(sort=True)  # desc by count
        all_names = counts[body.col_b].to_list()
        total_groups = len(all_names)
        top_names = all_names[: body.max_groups]
        truncated = total_groups > body.max_groups

        for name in top_names:
            sub = df.filter(pl.col(body.col_b) == name)[body.col_a]
            arr_g = sub.drop_nulls().cast(pl.Float64).to_numpy()
            stats_dict = _box_stats(arr_g, str(name))
            if stats_dict is not None:
                groups.append(stats_dict)
    else:
        stats_dict = _box_stats(a, body.col_a)
        if stats_dict is not None:
            groups.append(stats_dict)

    if not groups:
        raise HTTPException(400, "Not enough data to compute box plot (need ≥4 values per group)")

    return {
        "groups":       groups,
        "total_n":      sum(g["n"] for g in groups),
        "total_groups": total_groups,
        "truncated":    truncated,
    }
```

**Notes:**
- `outliers` per group capped at 1000 to bound payload size.
- Groups with `n < 4` are silently dropped (can't compute quartiles meaningfully).
- `top_names` ordering is preserved in the returned `groups` array — frontend uses this order for x-axis.

### 1c. New endpoint `POST /stats/boxplot_outliers_csv`

```python
class BoxPlotCsvIn(BaseModel):
    file_id:    str
    col_a:      str
    col_b:      Optional[str] = None
    max_groups: int           = 10


@router.post("/stats/boxplot_outliers_csv")
def boxplot_outliers_csv(body: BoxPlotCsvIn):
    # Loads df, computes outliers per group (same fence rule),
    # writes CSV with columns: row_idx, group, value, distance_iqr
    # where distance_iqr = signed (value - upper_fence)/iqr if above,
    #                     (value - lower_fence)/iqr if below.
```

### 1d. New endpoint `POST /stats/boxplot_stats_csv`

```python
@router.post("/stats/boxplot_stats_csv")
def boxplot_stats_csv(body: BoxPlotCsvIn):
    # Writes CSV with columns:
    # group, n, min, q1, median, q3, max, iqr, lower_fence, upper_fence, outlier_count
```

Both endpoints follow the same Response pattern as `/stats/zscore_csv`.

---

## 2. Frontend — Types (`frontend/src/types.ts`)

```typescript
export interface BoxPlotGroup {
  name:         string
  n:            number
  min:          number
  q1:           number
  median:       number
  q3:           number
  max:          number
  iqr:          number
  lower_fence:  number
  upper_fence:  number
  outliers:     Array<{ idx: number; value: number }>
}

export interface BoxPlotData {
  groups:        BoxPlotGroup[]
  total_n:       number
  total_groups:  number
  truncated:     boolean
}
```

---

## 3. Frontend — API (`frontend/src/api/ml.ts`)

```typescript
export async function runBoxPlot(
  file_id: string, col_a: string,
  col_b?: string, max_groups: number = 10,
): Promise<BoxPlotData> {
  const { data } = await client.post<BoxPlotData>('/ml/stats', {
    file_id, test: 'boxplot', col_a, col_b, max_groups,
  })
  return data
}

export async function downloadBoxOutliersCsv(
  fileId: string, colA: string, colB?: string, maxGroups: number = 10,
): Promise<void> {
  const { data } = await client.post(
    '/ml/stats/boxplot_outliers_csv',
    { file_id: fileId, col_a: colA, col_b: colB, max_groups: maxGroups },
    { responseType: 'blob' },
  )
  // ... same blob download pattern as downloadZScoreCsv
}

export async function downloadBoxStatsCsv(
  fileId: string, colA: string, colB?: string, maxGroups: number = 10,
): Promise<void> {
  // Same pattern, different endpoint
}
```

---

## 4. Frontend — `MlStatsView.tsx`

### 4a. TestType union

```typescript
type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney' | 'zscore' | 'boxplot'
```

### 4b. TESTS array entry — insert after `zscore`

```typescript
{ value: 'boxplot', label: 'Box Plot', needsColB: false, colBHint: 'phân nhóm (optional)' },
```

### 4c. HINTS entry

```typescript
boxplot: {
  what: 'Vẽ box plot (min/Q1/median/Q3/max) cho 1 cột số, hoặc so sánh phân phối nhiều nhóm khi chọn cột B. Tự phát hiện outlier (vượt 1.5×IQR).',
  when: 'Dùng để xem nhanh độ rải, độ skew, outlier; hoặc so sánh phân phối giữa các nhóm trước khi chạy ANOVA / Mann-Whitney.',
  colA: 'Cột số bất kỳ — VD: doanh thu, transaction_interval.',
  colB: '(Optional) Cột phân nhóm để so sánh — VD: Brand, Tier, Region.',
},
```

### 4d. Column B optional toggle (boxplot-specific)

Since `needsColB: false` but col B is still usable, add a checkbox above the col B select when `test === 'boxplot'`:

```tsx
{test === 'boxplot' && (
  <label className="flex items-center gap-1.5 text-[11px] text-gray-400 cursor-pointer">
    <input
      type="checkbox"
      checked={useGroupBy}
      onChange={e => setUseGroupBy(e.target.checked)}
      className="accent-analytics"
    />
    So sánh theo nhóm (chọn cột B)
  </label>
)}
```

Add state `const [useGroupBy, setUseGroupBy] = useState(false)`.
Add state `const [maxGroups, setMaxGroups] = useState(10)`.

When `test === 'boxplot' && useGroupBy`, treat col B as needed and show the col B dropdown (any column type, like ANOVA).

When `handleRun` fires with `test === 'boxplot'`, call `runBoxPlot()` with `col_b = useGroupBy ? colB : undefined` and `max_groups = maxGroups`.

### 4e. `generateCode()` — add boxplot case

```typescript
if (test === 'boxplot') {
  const groupBlock = colB ? `\n\n# Group-by mode\nfor g in df["${colB}"].unique().to_list():\n    sub = df.filter(pl.col("${colB}") == g)["${colA}"].drop_nulls().to_numpy()\n    if len(sub) >= 4:\n        box_stats(sub, str(g))\n` : ''
  return `${load}\n${a}\ndef box_stats(arr, name="all"):\n    q1, med, q3 = np.percentile(arr, [25, 50, 75])\n    iqr = q3 - q1\n    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr\n    outliers = arr[(arr < lo) | (arr > hi)]\n    print(f"{name}: n={len(arr)}, Q1={q1:.2f}, med={med:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}, fences=[{lo:.2f}, {hi:.2f}], outliers={len(outliers)}")\n\nbox_stats(a, "${colA}")${groupBlock}`
}
```

### 4f. Result rendering — special-case for `boxplot`

```tsx
{result && (
  <>
    {test === 'zscore' ? (
      <ZScoreResult ... />
    ) : test === 'boxplot' ? (
      <BoxPlotResult
        data={result as unknown as BoxPlotData}
        colA={colA}
        colB={useGroupBy ? colB : undefined}
        fileId={dataset.file_id}
        maxGroups={maxGroups}
        onMaxGroupsChange={setMaxGroups}
        onRerun={handleRun}
      />
    ) : (
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        {/* existing generic grid */}
      </div>
    )}
    {/* Show Code button stays; AI Interpret hidden when boxplot too */}
  </>
)}
```

Update AI Interpret hide condition:
```tsx
{test !== 'zscore' && test !== 'boxplot' && <button>Giải thích AI</button>}
```

---

## 5. Frontend — `BoxPlotResult.tsx` (new component)

**File:** `frontend/src/components/ml/BoxPlotResult.tsx`

**Props:**
```typescript
interface Props {
  data:              BoxPlotData
  colA:              string
  colB?:             string                       // undefined = single mode
  fileId:            string
  maxGroups:         number
  onMaxGroupsChange: (n: number) => void
  onRerun:           () => void                    // called after maxGroups change
}
```

**State:**
```typescript
const [downloadingOutliers, setDownloadingOutliers] = useState(false)
const [downloadingStats,    setDownloadingStats]    = useState(false)
const [hoveredGroup,        setHoveredGroup]        = useState<string | null>(null)
```

**Derived values:**
```typescript
const isGrouped     = !!colB
const allOutliers   = data.groups.flatMap(g =>
  g.outliers.map(o => ({ ...o, group: g.name, distanceIqr: signedDistance(o.value, g) }))
).sort((a, b) => Math.abs(b.distanceIqr) - Math.abs(a.distanceIqr))
const medians       = data.groups.map(g => g.median)
const minMedian     = Math.min(...medians)
const maxMedian     = Math.max(...medians)

function gradientFill(median: number): string {
  if (!isGrouped || minMedian === maxMedian) return '#fbbf24'  // single = analytics yellow
  const t = (median - minMedian) / (maxMedian - minMedian)
  if (t < 0.5) {
    // green → amber
    return lerpHex('#34d399', '#fbbf24', t * 2)
  }
  return lerpHex('#fbbf24', '#ef4444', (t - 0.5) * 2)
}

function signedDistance(value: number, g: BoxPlotGroup): number {
  // Outliers only: how many IQR units beyond Q3 (positive) or below Q1 (negative).
  // For a value at upper_fence (Q3 + 1.5×IQR), this returns +1.5.
  if (value > g.upper_fence) return (value - g.q3) / g.iqr
  if (value < g.lower_fence) return (value - g.q1) / g.iqr
  return 0
}
```

`lerpHex` is a small utility — defined inline in the component file.

**Sub-sections rendered (top to bottom):**

### Summary row
```
total n: 10,000   groups: 8   outliers: 47
```
3-column grid, same styling as Z-Score summary.

### Group cap selector (only when `isGrouped`)
```
Top groups: [10 ▾]   (showing top 10 of 23 groups)
```
- Dropdown values: `[5, 10, 20, 50]`
- On change: `onMaxGroupsChange(newValue)` then `onRerun()`
- Truncation note shown only if `data.truncated`

### Custom SVG Box Plot
- Container: `<div style={{ height: 320 }}>` with internal `<svg width="100%" height="100%" viewBox={`0 0 ${W} 320`} preserveAspectRatio="xMidYMid meet">`
- `W = max(640, groups.length × 80)` — horizontal scroll if many groups
- Y-axis scale: `[overall_min - pad, overall_max + pad]` where overall_min/max include outliers
- Box dimensions:
  - Box width: `min(60, slot_width × 0.6)`
  - Box: `<rect>` from y(Q3) to y(Q1), x=center-w/2 to x=center+w/2
  - Fill: `gradientFill(g.median)` with opacity 0.4
  - Stroke: `gradientFill(g.median)` with opacity 0.9
  - Median line: `<line>` y=y(median), stroke white 2px
  - Whisker: 2 vertical lines (Q1→lower_fence, Q3→upper_fence) stroke rgba(255,255,255,0.4) 1px
  - Whisker caps: 2 short horizontal lines at fence ends
  - Outlier dots: `<circle r={3} fill={fillColor} stroke="white" strokeWidth={1} />`
- X-axis labels: rotate -45° if any name length > 8, else horizontal
- Y-axis ticks: 5 ticks via `niceTickValues` helper (defined inline)
- Hover tooltip: positioned tooltip showing `n / min / Q1 / median / Q3 / max / IQR / outliers`

### Gradient legend (only when `isGrouped`)
A 200px-wide bar with green→amber→red gradient + labels "Low median" / "High median".

### Outlier table
- Columns: `Row | Group | Value | Distance` (single mode hides Group column)
- Row count: max 200, with "...và N more" note
- `Distance` cell: red text `text-danger`, format `+2.3×IQR` or `-1.8×IQR`
- Status icon: `<AlertTriangle size={10} />` red

### Download buttons (side by side)
```tsx
<div className="flex gap-4">
  <button onClick={handleDownloadOutliers}>
    <Download size={12} /> Download Outliers CSV
  </button>
  <button onClick={handleDownloadStats}>
    <Download size={12} /> Download Box Stats CSV
  </button>
</div>
```

---

## 6. Icon Summary (all from `lucide-react`)

| Location | Icon | Size |
|----------|------|------|
| Test hint card | `BoxSelect` | 12 |
| Group cap dropdown label | `Users` | 11 |
| Outlier table status | `AlertTriangle` | 10 |
| Download buttons | `Download` | 12 |

---

## 7. Color Token Map

| Element | Class / Hex |
|---------|-------------|
| Single-mode box fill | `#fbbf24` (analytics) |
| Group-mode gradient start | `#34d399` (work/green) |
| Group-mode gradient mid | `#fbbf24` (analytics/amber) |
| Group-mode gradient end | `#ef4444` (danger/red) |
| Median line | `#ffffff` (2px) |
| Whisker line | `rgba(255,255,255,0.4)` |
| Outlier dot stroke | `#ffffff` |
| Outlier table distance text | `text-danger` |
| Group cap dropdown | `input-base text-xs` |
| Download buttons | `text-gray-500 hover:text-gray-300` |

---

## 8. Files Changed

| File | Action |
|------|--------|
| `backend/routers/ml.py` | Add `max_groups` field to `StatsIn`; add `boxplot` handler in `run_stats()`; add `BoxPlotCsvIn` model + 2 endpoints (`/stats/boxplot_outliers_csv`, `/stats/boxplot_stats_csv`) |
| `backend/tests/test_ml.py` | Add `test_stats_boxplot_single`, `test_stats_boxplot_grouped`, `test_boxplot_outliers_csv`, `test_boxplot_stats_csv`, `test_stats_boxplot_insufficient_data` |
| `frontend/src/types.ts` | Add `BoxPlotGroup`, `BoxPlotData` interfaces |
| `frontend/src/api/ml.ts` | Add `runBoxPlot()`, `downloadBoxOutliersCsv()`, `downloadBoxStatsCsv()` |
| `frontend/src/components/ml/BoxPlotResult.tsx` | **New** — full Box Plot UI component (custom SVG) |
| `frontend/src/components/ml/MlStatsView.tsx` | Add `'boxplot'` to TestType, TESTS, HINTS, generateCode; add `useGroupBy` + `maxGroups` state; add "So sánh theo nhóm" checkbox; render `<BoxPlotResult>` conditionally; hide AI interpret for boxplot |

---

## 9. Out of Scope

- Horizontal box plot orientation (vertical only)
- Notched box plot (95% CI on median)
- Violin plot (could be added later as its own test)
- Custom whisker rules other than Tukey 1.5×IQR (e.g., 9th/91st percentile)
- AI interpretation for box plot results
- Per-group outlier table sorting/filtering UI (use CSV download for analysis)
