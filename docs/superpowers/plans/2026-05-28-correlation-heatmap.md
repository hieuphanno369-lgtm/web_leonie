# Correlation Heatmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing basic HTML table correlation matrix in ML Studio Charts tab to a proper SVG-based heatmap with rotated headers, hover tooltips, a colour legend, and a collapsible section replacing the old button.

**Architecture:** Create a standalone `CorrelationHeatmap.tsx` component (pure SVG, receives `CorrelationMatrix` props), then refactor `MlChartView.tsx` to remove the old button/table rendering and replace it with a collapsible section (same UX pattern as Cohort Retention) that lazy-loads and renders the new component.

**Tech Stack:** React 18, TypeScript, SVG (no chart library), lucide-react icons (`Grid2x2`), existing `fetchCorrelation` from `api/ml.ts`, existing `CorrelationMatrix` type from `types.ts`.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/components/ml/CorrelationHeatmap.tsx` | SVG heatmap: cells, rotated headers, row labels, tooltips, colour legend |
| Modify | `frontend/src/components/ml/MlChartView.tsx` | Remove old button/table/`corrToColor`; add collapsible section + `handleCorrToggle` + dataset-reset effect |

---

### Task 1: Create `CorrelationHeatmap.tsx`

**Files:**
- Create: `frontend/src/components/ml/CorrelationHeatmap.tsx`

- [ ] **Step 1: Write the component file**

Create `frontend/src/components/ml/CorrelationHeatmap.tsx` with the following complete content:

```tsx
import type { CorrelationMatrix } from '../../types'

const CELL        = 64   // cell width & height (px)
const HEADER_H    = 80   // rotated header row height (px)
const ROW_LABEL_W = 96   // left column for row labels (px)
const LEGEND_H    = 28   // footer for colour legend (px)

interface Props {
  data: CorrelationMatrix
}

/** Interpolates between gray → blue (positive) or gray → red (negative). */
function corrToColor(r: number | null): string {
  if (r === null) return '#1f2937'
  const t      = Math.abs(r)
  const gray   = [55, 65, 81]
  const pos    = [37, 99, 235]
  const neg    = [220, 38, 38]
  const target = r >= 0 ? pos : neg
  const rgb    = gray.map((g, i) => Math.round(g + t * (target[i] - g)))
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`
}

/** Truncate to max chars, appending '…' if trimmed. */
function trunc(s: string, max = 12): string {
  return s.length > max ? s.slice(0, max - 1) + '…' : s
}

/** Human-readable interpretation of a Pearson r value. */
function interpret(r: number | null, isSelf: boolean): string {
  if (r === null) return 'No data'
  if (isSelf) return 'Same column'
  const abs = Math.abs(r)
  const dir = r >= 0 ? 'positive' : 'negative'
  if (abs >= 0.7) return `Strong ${dir} correlation`
  if (abs >= 0.4) return `Moderate ${dir} correlation`
  if (abs >= 0.1) return `Weak ${dir} correlation`
  return 'No correlation'
}

const LEGEND_RS: readonly number[] = [-1, -0.67, -0.33, 0, 0.33, 0.67, 1]
const SWATCH_W = 28  // width of each legend colour swatch (px)

export default function CorrelationHeatmap({ data }: Props) {
  const n         = data.columns.length
  const svgWidth  = ROW_LABEL_W + n * CELL
  const svgHeight = HEADER_H + n * CELL + LEGEND_H

  const legendW = LEGEND_RS.length * SWATCH_W
  // Centre legend horizontally within the grid area
  const legendX = ROW_LABEL_W + Math.max(0, Math.floor((n * CELL - legendW) / 2))
  const legendY = HEADER_H + n * CELL   // y-offset where the legend row begins

  return (
    <div className="overflow-auto">
      <svg
        width={svgWidth}
        height={svgHeight}
        style={{ fontFamily: 'ui-sans-serif, system-ui, sans-serif', display: 'block' }}
      >
        {/* ── Column headers — rotated −45° ─────────────────── */}
        {data.columns.map((col, j) => {
          const cx = ROW_LABEL_W + j * CELL + CELL / 2
          const cy = HEADER_H - 4
          return (
            <text
              key={`ch-${j}`}
              x={cx}
              y={cy}
              fontSize={10}
              fill="#9ca3af"
              textAnchor="start"
              transform={`rotate(-45,${cx},${cy})`}
            >
              {trunc(col)}
            </text>
          )
        })}

        {/* ── Grid cells ────────────────────────────────────── */}
        {data.matrix.map((row, i) =>
          row.map((val, j) => {
            const x       = ROW_LABEL_W + j * CELL
            const y       = HEADER_H + i * CELL
            const isSelf  = i === j
            const txtFill = val !== null && Math.abs(val) > 0.3 ? '#ffffff' : '#9ca3af'
            const tipText =
              `${data.columns[i]} × ${data.columns[j]}: ${val !== null ? val.toFixed(2) : '—'}\n${interpret(val, isSelf)}`
            return (
              <g key={`cell-${i}-${j}`}>
                <title>{tipText}</title>
                <rect x={x} y={y} width={CELL} height={CELL} fill={corrToColor(val)} />
                <text
                  x={x + CELL / 2}
                  y={y + CELL / 2}
                  fontSize={10}
                  fill={txtFill}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontWeight={500}
                >
                  {val !== null ? val.toFixed(2) : '—'}
                </text>
              </g>
            )
          })
        )}

        {/* ── Row labels (right-aligned, left margin) ──────── */}
        {data.columns.map((col, i) => (
          <text
            key={`rl-${i}`}
            x={ROW_LABEL_W - 6}
            y={HEADER_H + i * CELL + CELL / 2}
            fontSize={10}
            fill="#9ca3af"
            textAnchor="end"
            dominantBaseline="middle"
          >
            {trunc(col)}
          </text>
        ))}

        {/* ── Colour legend: 7 swatches r = −1 … +1 ────────── */}
        {LEGEND_RS.map((r, k) => (
          <rect
            key={`sw-${k}`}
            x={legendX + k * SWATCH_W}
            y={legendY + 4}
            width={SWATCH_W}
            height={12}
            fill={corrToColor(r)}
          />
        ))}
        {/* Axis labels below swatches */}
        <text x={legendX}               y={legendY + 24} fontSize={9} fill="#6b7280" textAnchor="middle">{'−1'}</text>
        <text x={legendX + legendW / 2} y={legendY + 24} fontSize={9} fill="#6b7280" textAnchor="middle">0</text>
        <text x={legendX + legendW}     y={legendY + 24} fontSize={9} fill="#6b7280" textAnchor="middle">+1</text>
      </svg>
      {/* Caption below SVG */}
      <p className="text-[9px] text-gray-600 mt-1 text-center select-none">
        Blue = positive · Red = negative
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript build passes**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected output contains `✓ built in` with zero TypeScript errors. If errors appear, fix them before continuing.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/CorrelationHeatmap.tsx
git commit -m "feat: add CorrelationHeatmap SVG component with tooltips and colour legend"
```

---

### Task 2: Refactor `MlChartView.tsx`

**Files:**
- Modify: `frontend/src/components/ml/MlChartView.tsx`

**Current state of the file (relevant sections):**

| Lines | What's there | Action |
|-------|-------------|--------|
| 1 | `import { useState, useMemo } from 'react'` | add `useEffect` |
| 2 | `import { ArrowUpDown, Users } from 'lucide-react'` | add `Grid2x2` |
| 14 | `import DataQualityBanner from './DataQualityBanner'` | add `CorrelationHeatmap` import below |
| 101–108 | `corrToColor` function | delete entirely |
| 154–156 | `corrData/corrLoading/corrError` state | add `showCorr` + `useEffect` |
| 206–214 | `loadCorrelation()` function | replace with `handleCorrToggle()` |
| 313–323 | "Correlation Matrix" `<button>` in controls | delete |
| 586–621 | Old `corrData` table rendering | replace with new collapsible section |

- [ ] **Step 1: Update React and lucide-react imports**

In `frontend/src/components/ml/MlChartView.tsx`, make two import changes:

Change line 1 (add `useEffect`):
```tsx
// BEFORE:
import { useState, useMemo } from 'react'

// AFTER:
import { useState, useMemo, useEffect } from 'react'
```

Change line 2 (add `Grid2x2`):
```tsx
// BEFORE:
import { ArrowUpDown, Users } from 'lucide-react'

// AFTER:
import { ArrowUpDown, Grid2x2, Users } from 'lucide-react'
```

- [ ] **Step 2: Add `CorrelationHeatmap` import**

After line 14 (`import DataQualityBanner from './DataQualityBanner'`), add:

```tsx
import CorrelationHeatmap from './CorrelationHeatmap'
```

- [ ] **Step 3: Delete `corrToColor` function**

Remove the entire block (lines ~101–108):

```tsx
// ── Correlation heatmap ──────────────────────────────────────
function corrToColor(r: number | null): string {
  if (r === null) return '#1f2937'
  const t = Math.abs(r)
  const gray=[55,65,81]; const pos=[37,99,235]; const neg=[220,38,38]
  const target = r >= 0 ? pos : neg
  const rgb = gray.map((g,i) => Math.round(g + t*(target[i]-g)))
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`
}
```

Delete that whole block — `corrToColor` now lives in `CorrelationHeatmap.tsx`.

- [ ] **Step 4: Add `showCorr` state and dataset-reset `useEffect`**

Find the correlation state block inside `MlChartView` (inside the component function, lines ~153–157):

```tsx
  // Correlation
  const [corrData,    setCorrData]    = useState<CorrelationMatrix | null>(null)
  const [corrLoading, setCorrLoading] = useState(false)
  const [corrError,   setCorrError]   = useState('')
```

Replace with:

```tsx
  // Correlation
  const [showCorr,    setShowCorr]    = useState(false)
  const [corrData,    setCorrData]    = useState<CorrelationMatrix | null>(null)
  const [corrLoading, setCorrLoading] = useState(false)
  const [corrError,   setCorrError]   = useState('')

  // Reset corr state whenever the loaded file changes
  useEffect(() => {
    setCorrData(null)
    setCorrError('')
    setShowCorr(false)
  }, [dataset?.file_id])
```

- [ ] **Step 5: Replace `loadCorrelation` with `handleCorrToggle`**

Find (lines ~206–214):

```tsx
  async function loadCorrelation() {
    if (!dataset) return
    if (corrData) { setCorrData(null); return }
    setCorrLoading(true); setCorrError('')
    try { setCorrData(await fetchCorrelation(dataset.file_id)) }
    catch (e: unknown) {
      setCorrError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed')
    } finally { setCorrLoading(false) }
  }
```

Replace with:

```tsx
  async function handleCorrToggle() {
    if (showCorr) { setShowCorr(false); return }
    setShowCorr(true)
    if (corrData || !dataset) return          // already loaded — just expand
    setCorrLoading(true); setCorrError('')
    try { setCorrData(await fetchCorrelation(dataset.file_id)) }
    catch (e: unknown) {
      setCorrError(
        (e as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? 'Failed to load correlation',
      )
    } finally { setCorrLoading(false) }
  }
```

- [ ] **Step 6: Remove the old "Correlation Matrix" button from the controls row**

Find and delete the button block in the controls `<div>` (lines ~313–323):

```tsx
        {dataset && (
          <button onClick={loadCorrelation}
            className={`ml-auto px-2 py-1 rounded text-[11px] border transition-all ${
              corrData
                ? 'bg-analytics/10 text-analytics border-analytics/30'
                : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}>
            {corrLoading ? 'Loading…' : 'Correlation Matrix'}
          </button>
        )}
```

Delete the entire block above.

- [ ] **Step 7: Replace old correlation table with new collapsible section**

Find and delete the old correlation rendering block (lines ~586–621):

```tsx
      {/* Correlation Matrix */}
      {corrError && <p className="text-danger text-xs">{corrError}</p>}
      {corrData && (
        <div className="bg-secondary border border-white/5 rounded-lg p-3 overflow-auto">
          <p className="text-[10px] text-gray-500 mb-2">Pearson Correlation Matrix (numeric columns)</p>
          <table className="border-collapse text-[10px]">
            <thead>
              <tr>
                <th className="w-24" />
                {corrData.columns.map(c => (
                  <th key={c} className="px-1 py-0.5 text-gray-500 font-normal text-center max-w-[60px] truncate">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {corrData.matrix.map((row, i) => (
                <tr key={corrData.columns[i]}>
                  <td className="pr-2 py-0.5 text-gray-500 text-right whitespace-nowrap max-w-[96px] truncate">
                    {corrData.columns[i]}
                  </td>
                  {row.map((val, j) => (
                    <td key={j} className="w-14 h-7 text-center font-medium"
                      style={{
                        background: corrToColor(val),
                        color: val!==null && Math.abs(val)>0.3 ? '#fff' : '#9ca3af',
                      }}>
                      {val!==null ? val.toFixed(2) : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[10px] text-gray-600 mt-1.5">Blue = positive · Red = negative · Max 15 columns</p>
        </div>
      )}
```

In its place, add the new collapsible section (insert before the closing `</div>` of the inner scroll container — the `</div>` that closes `<div className="flex flex-col gap-3 p-4 flex-1 overflow-auto">`):

```tsx
      {/* ── Correlation Heatmap ──────────────────────────────── */}
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
              {corrError   && <p className="text-[11px] text-danger">{corrError}</p>}
              {corrData    && <CorrelationHeatmap data={corrData} />}
            </div>
          )}
        </div>
      )}
```

- [ ] **Step 8: Verify TypeScript build passes**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: `✓ built in` with zero TypeScript errors. Common errors to watch for:
- `corrToColor` referenced anywhere → you missed a deletion; remove it
- `loadCorrelation` referenced → you missed replacing it; check the old button removal
- `showCorr` not defined → you missed Step 4

- [ ] **Step 9: Manual smoke test**

1. Start dev server: in one terminal `cd frontend && npm run dev`; in another `.venv\Scripts\Activate.ps1 && uvicorn backend.main:app --reload`
2. Open the app, upload a CSV with ≥ 2 numeric columns, run a query → Charts tab
3. **Controls row**: confirm the "Correlation Matrix" button is GONE
4. **Bottom of Charts tab**: "Correlation Heatmap" collapsible section appears after the Cohort Retention section
5. Click the "Correlation Heatmap" header → expands, shows "Computing…" briefly, then renders the SVG heatmap
6. Hover over any cell → browser native tooltip shows `colA × colB: 0.87` + correlation interpretation label
7. Click the header again → section collapses; data is preserved (no spinner on re-expand)
8. Switch to a different dataset (upload another file or switch) → heatmap collapses and clears
9. Verify the colour legend is visible below the grid (7 swatches + −1/0/+1 labels + caption)

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/ml/MlChartView.tsx
git commit -m "feat: replace correlation table with collapsible heatmap section in MlChartView"
```
