# Correlation Heatmap — Design Spec

**Date:** 2026-05-27
**Feature:** Correlation Heatmap upgrade for ML Studio Charts tab
**Location:** Collapsible section at the bottom of `MlChartView`, after Cohort Retention

---

## Overview

A Pearson correlation heatmap already exists in ML Studio as a basic HTML table triggered by a button in the chart controls. This feature upgrades it to a proper visual heatmap component: larger cells, rotated column headers, hover tooltips with correlation interpretation, a colour legend, and better discoverability via a collapsible section (same UX pattern as Cohort Retention).

No backend changes required. The existing `GET /api/ml/{file_id}/correlation` endpoint is sufficient.

---

## What Changes

### Existing (before)
- Small "Correlation Matrix" toggle button in the chart controls row (top-right)
- Renders as a plain HTML `<table>` with 56×28px cells at the bottom of the page
- No tooltip, no legend, no clear section header

### After
- Button removed from controls row
- New collapsible section at the bottom of `MlChartView` (after Cohort Retention), using the same `border border-white/5 rounded-lg overflow-hidden` style
- Header row: `Grid2x2` icon + **"Correlation Heatmap"** label + subtitle `"— Pearson, numeric columns only"`
- On first expand: lazy-load correlation data; renders `<CorrelationHeatmap data={corrData} />`
- On collapse: data is kept in state (no re-fetch)

---

## Backend

**No changes.** Existing endpoint:

```
GET /api/ml/{file_id}/correlation
```

Returns `CorrelationMatrix { columns: string[], matrix: (number | null)[][] }` with up to 15 numeric columns. Already imported as `fetchCorrelation` in `api/ml.ts`.

---

## Frontend

### New File

```
frontend/src/components/ml/CorrelationHeatmap.tsx
```

### Modified File

```
frontend/src/components/ml/MlChartView.tsx
```

---

### `CorrelationHeatmap.tsx`

**Props:**
```typescript
interface Props {
  data: CorrelationMatrix
}
```

**Layout (SVG-based):**

- `CELL = 64` px — cell width and height
- `HEADER_H = 80` px — rotated header row height
- `ROW_LABEL_W = 96` px — left column for row labels
- Total SVG width: `ROW_LABEL_W + n * CELL`
- Total SVG height: `HEADER_H + n * CELL + 28` (28px for legend)

**Column headers:** `<text>` rotated −45° per column, anchored at cell midpoint, truncated to 12 chars if longer.

**Cells:**
- Background: `corrToColor(val)` — same function currently in `MlChartView` (moved into this component)
- Text: correlation value formatted to 2 decimal places (`0.87`, `−0.34`, `1.00`)
- Text colour: white if `|r| > 0.3`, `#9ca3af` otherwise
- Diagonal cells (i === j): rendered identically but `corrToColor` returns the same colour for `r = 1.0`

**Tooltip on hover:**
- Implemented with a `<title>` element inside each `<g>` cell group (native SVG tooltip — no extra state needed)
- Format:
  ```
  colA × colB: 0.87
  Strong positive correlation
  ```
- Interpretation thresholds (applied to `Math.abs(r)`):
  | Range | Label |
  |-------|-------|
  | ≥ 0.7 | Strong positive / Strong negative |
  | ≥ 0.4 | Moderate positive / Moderate negative |
  | ≥ 0.1 | Weak positive / Weak negative |
  | < 0.1 | No correlation |
  | = 1.0 (diagonal) | Same column |

**Row labels:** Right-aligned `<text>` in the left margin, truncated to 12 chars.

**Colour legend (below grid):**
- 7 sample swatches from r = −1 to r = +1 (steps: −1, −0.67, −0.33, 0, 0.33, 0.67, 1)
- Labels: `−1` on left, `0` in centre, `+1` on right
- Caption: `"Blue = positive · Red = negative"`

---

### `MlChartView.tsx` changes

**Remove:**
- The "Correlation Matrix" `<button>` from the controls `<div>` (currently the last item in the controls flex row, rendered only when `dataset` is truthy)
- The `corrToColor` function (moved into `CorrelationHeatmap.tsx`)

**Add import:**
```typescript
import CorrelationHeatmap from './CorrelationHeatmap'
```
Add `Grid2x2` to the lucide-react import line.

**State — reuse existing:**
```typescript
const [showCorr,    setShowCorr]    = useState(false)
const [corrData,    setCorrData]    = useState<CorrelationMatrix | null>(null)
const [corrLoading, setCorrLoading] = useState(false)
const [corrError,   setCorrError]   = useState('')
```
(already present — just renamed `showCorr` from implicit toggle logic)

**Reset on dataset change:** Add a `useEffect` to clear correlation state when the loaded file changes:
```typescript
useEffect(() => {
  setCorrData(null)
  setCorrError('')
  setShowCorr(false)
}, [dataset?.file_id])
```

**Lazy-load handler** (replaces current `loadCorrelation`):
```typescript
async function handleCorrToggle() {
  if (showCorr) { setShowCorr(false); return }
  setShowCorr(true)
  if (corrData || !dataset) return   // already loaded
  setCorrLoading(true); setCorrError('')
  try { setCorrData(await fetchCorrelation(dataset.file_id)) }
  catch (e: unknown) {
    setCorrError((e as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail ?? 'Failed to load correlation')
  } finally { setCorrLoading(false) }
}
```

**New JSX section** (after the Cohort Retention section, before closing `</div>`):

```tsx
{dataset && (
  <div className="border border-white/5 rounded-lg overflow-hidden">
    <button
      onClick={handleCorrToggle}
      className="w-full flex items-center gap-2 px-3 py-2 bg-white/3 hover:bg-white/5 transition-colors text-left"
    >
      <Grid2x2 size={12} className="text-gray-500" />
      <span className="text-[11px] font-medium text-gray-300">Correlation Heatmap</span>
      <span className="text-[10px] text-gray-600 ml-1">— Pearson, numeric columns only</span>
    </button>

    {showCorr && (
      <div className="p-3">
        {corrLoading && <p className="text-[11px] text-gray-500">Computing…</p>}
        {corrError  && <p className="text-[11px] text-danger">{corrError}</p>}
        {corrData   && <CorrelationHeatmap data={corrData} />}
      </div>
    )}
  </div>
)}
```

---

## Testing

No new backend tests needed (endpoint unchanged, already covered by existing `test_ml.py`).

Frontend: `npm run build` must produce zero new TypeScript errors.

Manual smoke test:
1. Upload a CSV with at least 2 numeric columns
2. Run a query → Charts tab → scroll to bottom → click "Correlation Heatmap" header
3. Verify: heatmap renders, hover tooltip shows `colA × colB: r` + interpretation, colour legend visible
4. Click header again → collapses, data preserved
5. Switch dataset → heatmap resets (corrData is per-component state, resets when dataset changes)

---

## Out of Scope

- Clicking a cell to filter or highlight data
- Spearman / Kendall alternatives
- Exporting the heatmap as image
- Auto-opening the section when quality issues include a "high correlation" warning
