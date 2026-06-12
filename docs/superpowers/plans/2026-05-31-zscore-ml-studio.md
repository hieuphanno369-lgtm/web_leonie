# Z-Score Analysis — ML Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `zscore` test type to ML Studio's Stats tab that shows a threshold-reactive outlier table, a z-score distribution histogram, and a standardized CSV export.

**Architecture:** New `zscore` branch in `run_stats()` plus a new `POST /stats/zscore_csv` endpoint in the backend; a self-contained `ZScoreResult.tsx` component handles all UI (summary, slider, histogram, table, download); `MlStatsView.tsx` renders it in place of the generic results grid when `test === 'zscore'`.

**Tech Stack:** FastAPI + Polars + NumPy (backend), React 18 + TypeScript + Recharts + lucide-react + Tailwind CSS design tokens (frontend).

---

## File Map

| File | Change |
|------|--------|
| `backend/routers/ml.py` | Add `Response` import; add `zscore` handler in `run_stats()`; add `ZScoreCsvIn` model + `POST /stats/zscore_csv` endpoint |
| `backend/tests/test_ml.py` | Add `test_stats_zscore`, `test_zscore_csv` |
| `frontend/src/types.ts` | Add `ZScoreRow`, `ZScoreData` interfaces |
| `frontend/src/api/ml.ts` | Add `downloadZScoreCsv()` |
| `frontend/src/components/ml/ZScoreResult.tsx` | **New** — full Z-Score UI component |
| `frontend/src/components/ml/MlStatsView.tsx` | Add `'zscore'` to TestType, TESTS, HINTS, `generateCode()`; render `<ZScoreResult>` conditionally; hide AI interpret for zscore |

---

## Task 1: Backend — zscore handler + CSV endpoint

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write the failing tests**

Open `backend/tests/test_ml.py` and add after the last existing test:

```python
OUTLIER_CSV = b"val,cat\n1,a\n2,b\n2,c\n2,d\n2,e\n2,f\n2,g\n2,h\n2,i\n50,j\n"
# val = [1,2,2,2,2,2,2,2,2,50]  mean≈7.1  std≈15.2  z(50)≈2.83


def test_stats_zscore(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("ztest.csv", io.BytesIO(OUTLIER_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "zscore", "col_a": "val"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "mean" in d
    assert "std" in d
    assert d["n"] == 10
    assert "rows" in d
    assert isinstance(d["rows"], list)
    assert len(d["rows"]) == 10          # all rows returned (< 5000 cap)
    assert "histogram_bins" in d
    assert isinstance(d["histogram_bins"], list)
    # Top row must be the outlier (value=50, highest |z|)
    assert d["rows"][0]["value"] == pytest.approx(50.0)
    assert abs(d["rows"][0]["z_score"]) > 2.0
    # Every row has idx, value, z_score
    for row in d["rows"]:
        assert "idx" in row
        assert "value" in row
        assert "z_score" in row
    # histogram bins have x0, x1, count
    for bin_ in d["histogram_bins"]:
        assert "x0" in bin_
        assert "x1" in bin_
        assert "count" in bin_


def test_zscore_csv(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("zcsv.csv", io.BytesIO(OUTLIER_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/zscore_csv", json={
        "file_id": upload["file_id"], "col_a": "val"
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.content.decode("utf-8")
    header = text.splitlines()[0]
    assert "z_score" in header
    assert "z_status" in header
    # The outlier row (val=50) must be labelled outlier
    assert "outlier" in text


def test_stats_zscore_unknown_col(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("zbad.csv", io.BytesIO(OUTLIER_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "zscore", "col_a": "nonexistent"
    })
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv\Scripts\python.exe -m pytest backend/tests/test_ml.py::test_stats_zscore backend/tests/test_ml.py::test_zscore_csv backend/tests/test_ml.py::test_stats_zscore_unknown_col -v
```

Expected: 3 FAILs — `test_stats_zscore` fails with 400 "Unknown test 'zscore'", others fail similarly.

- [ ] **Step 3: Add `Response` to FastAPI imports in `ml.py`**

Find line 11 in `backend/routers/ml.py`:
```python
# Before:
from fastapi import APIRouter, HTTPException, UploadFile, File

# After:
from fastapi import APIRouter, HTTPException, UploadFile, File, Response
```

- [ ] **Step 4: Add `zscore` handler inside `run_stats()`**

Find the line `raise HTTPException(400, f"Unknown test '{body.test}'")` near line 860.
Insert the zscore block **immediately before** that line:

```python
    if body.test == "zscore":
        z = (a - a.mean()) / (a.std() + 1e-9)
        rows_sorted = sorted(
            [
                {
                    "idx":     int(i),
                    "value":   round(float(a[i]),   4),
                    "z_score": round(float(z[i]),   4),
                }
                for i in range(len(a))
            ],
            key=lambda r: abs(r["z_score"]),
            reverse=True,
        )[:5000]
        counts, edges = np.histogram(z, bins=30)
        return {
            "mean": round(float(a.mean()), 4),
            "std":  round(float(a.std()),  4),
            "n":    int(len(a)),
            "rows": rows_sorted,
            "histogram_bins": [
                {
                    "x0":    round(float(edges[i]),     3),
                    "x1":    round(float(edges[i + 1]), 3),
                    "count": int(counts[i]),
                }
                for i in range(len(counts))
            ],
        }

    raise HTTPException(400, f"Unknown test '{body.test}'")
```

- [ ] **Step 5: Add `ZScoreCsvIn` model and `POST /stats/zscore_csv` endpoint**

Find the `# ── AI Interpretation ─` comment block (after `run_stats` ends around line 863). Insert the new model + endpoint **before** that comment:

```python
# ── Z-Score CSV export ───────────────────────────────────────────────────────

class ZScoreCsvIn(BaseModel):
    file_id: str
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
    z_col  = ((series - mean_) / std_).round(4).alias("z_score")
    df_out = df.with_columns(z_col)
    df_out = df_out.with_columns(
        pl.when(pl.col("z_score").abs() < 1).then(pl.lit("normal"))
          .when(pl.col("z_score").abs() < 2).then(pl.lit("watch"))
          .otherwise(pl.lit("outlier"))
          .alias("z_status")
    )

    csv_bytes = df_out.write_csv().encode("utf-8")
    safe_col  = body.col_a.replace("/", "_").replace(" ", "_")
    filename  = f"zscore_{safe_col}_{row['filename']}"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: Run tests — expect all 3 to pass**

```
.venv\Scripts\python.exe -m pytest backend/tests/test_ml.py::test_stats_zscore backend/tests/test_ml.py::test_zscore_csv backend/tests/test_ml.py::test_stats_zscore_unknown_col -v
```

Expected: 3 PASSED.

- [ ] **Step 7: Run full test suite to check no regressions**

```
.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Expected: all previously passing tests still pass.

- [ ] **Step 8: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat: add zscore stats handler and zscore_csv export endpoint"
```

---

## Task 2: Frontend types + API

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/ml.ts`

- [ ] **Step 1: Add ZScoreRow and ZScoreData to types.ts**

Open `frontend/src/types.ts`. Find the `// ─── ML Studio ───` section (around line 145). Add after the `QualityResult` interface (the last ML-related interface, around line 239):

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

- [ ] **Step 2: Add downloadZScoreCsv to api/ml.ts**

Open `frontend/src/api/ml.ts`. Add the import for `ZScoreData` in the types import at the top:

```typescript
// Before:
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix, QualityResult,
} from '../types'

// After:
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix, QualityResult,
  ZScoreData,
} from '../types'
```

Then add at the **bottom** of the file (after `fetchQuality`):

```typescript
export async function runZScore(
  file_id: string, col_a: string
): Promise<ZScoreData> {
  const { data } = await client.post<ZScoreData>('/ml/stats', {
    file_id, test: 'zscore', col_a,
  })
  return data
}

export async function downloadZScoreCsv(
  fileId: string, colA: string
): Promise<void> {
  const { data } = await client.post(
    '/ml/stats/zscore_csv',
    { file_id: fileId, col_a: colA },
    { responseType: 'blob' },
  )
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a   = document.createElement('a')
  a.href     = url
  a.download = `zscore_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 3: TypeScript check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/types.ts frontend/src/api/ml.ts
git commit -m "feat: add ZScoreData types and downloadZScoreCsv API helper"
```

---

## Task 3: ZScoreResult component

**Files:**
- Create: `frontend/src/components/ml/ZScoreResult.tsx`

- [ ] **Step 1: Create the file with the full component**

```tsx
import { useState } from 'react'
import { AlertTriangle, AlertCircle, CheckCircle, Download } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts'
import type { ZScoreData } from '../../types'
import { downloadZScoreCsv } from '../../api/ml'

interface Props {
  data:   ZScoreData
  colA:   string
  fileId: string
}

const PRESETS = [1.5, 2.0, 2.5, 3.0]

type Status = 'outlier' | 'watch' | 'normal'

export default function ZScoreResult({ data, colA, fileId }: Props) {
  const [threshold,   setThreshold]   = useState(2.0)
  const [downloading, setDownloading] = useState(false)

  function statusOf(z: number): Status {
    const az = Math.abs(z)
    if (az >= threshold) return 'outlier'
    if (az >= 1)         return 'watch'
    return 'normal'
  }

  function barFill(x0: number, x1: number): string {
    const c = (x0 + x1) / 2
    if (Math.abs(c) >= threshold) return '#ef4444'
    if (Math.abs(c) >= 1)         return '#f59e0b'
    return '#34d399'
  }

  async function handleDownload() {
    setDownloading(true)
    try { await downloadZScoreCsv(fileId, colA) }
    finally { setDownloading(false) }
  }

  const outliers     = data.rows.filter(r => Math.abs(r.z_score) >= threshold)
  const outlierCount = outliers.length
  const outlierPct   = data.n > 0
    ? ((outlierCount / data.n) * 100).toFixed(2)
    : '0.00'

  const STATUS_STYLE: Record<Status, { cls: string; Icon: typeof AlertTriangle; label: string }> = {
    outlier: { cls: 'text-danger',       Icon: AlertTriangle, label: 'Outlier' },
    watch:   { cls: 'text-yellow-400',   Icon: AlertCircle,   label: 'Watch'   },
    normal:  { cls: 'text-work',         Icon: CheckCircle,   label: 'Normal'  },
  }

  return (
    <div className="flex flex-col gap-4">

      {/* ── Summary ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-3">
          {(['mean', 'std', 'n'] as const).map(key => (
            <div key={key}>
              <p className="text-[10px] text-gray-600 uppercase tracking-wider">{key}</p>
              <p className="text-sm font-semibold text-white">
                {(data[key] as number).toLocaleString('vi-VN', { maximumFractionDigits: 4 })}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Threshold control ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4 flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-gray-600 uppercase tracking-wider whitespace-nowrap">
            Ngưỡng outlier
          </span>
          <input
            type="range" min={1} max={4} step={0.1}
            value={threshold}
            onChange={e => setThreshold(parseFloat(e.target.value))}
            className="flex-1 accent-analytics h-1"
          />
          <span className="text-sm font-semibold text-analytics w-8 text-right">
            {threshold.toFixed(1)}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] text-gray-600">Preset:</span>
          {PRESETS.map(p => (
            <button
              key={p}
              onClick={() => setThreshold(p)}
              className={`px-2 py-0.5 rounded text-[10px] border transition-all ${
                threshold === p
                  ? 'bg-analytics/10 text-analytics border-analytics/30'
                  : 'text-gray-500 border-transparent hover:text-gray-300'
              }`}
            >
              {p}
            </button>
          ))}
          <span className={`ml-auto text-[11px] font-medium ${
            outlierCount > 0 ? 'text-danger' : 'text-work'
          }`}>
            → {outlierCount} outliers ({outlierPct}%)
          </span>
        </div>
      </div>

      {/* ── Histogram ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">
          Phân phối Z-Score
        </p>
        <div style={{ height: 160 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.histogram_bins}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="x0"
                type="number"
                domain={[
                  data.histogram_bins[0]?.x0 ?? -4,
                  data.histogram_bins[data.histogram_bins.length - 1]?.x1 ?? 4,
                ]}
                tick={{ fill: '#6b7280', fontSize: 9 }}
                tickFormatter={v => Number(v).toFixed(1)}
              />
              <YAxis tick={{ fill: '#6b7280', fontSize: 9 }} width={32} />
              <Tooltip
                contentStyle={{
                  background: '#161b22',
                  border: '1px solid rgba(255,255,255,0.1)',
                  fontSize: 11,
                }}
                formatter={(v: number) => [v, 'count']}
                labelFormatter={(x0: number) => `z ≈ ${Number(x0).toFixed(2)}`}
              />
              <ReferenceLine
                x={threshold}
                stroke="rgba(239,68,68,0.5)"
                strokeDasharray="4 2"
              />
              <ReferenceLine
                x={-threshold}
                stroke="rgba(239,68,68,0.5)"
                strokeDasharray="4 2"
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {data.histogram_bins.map((bin, i) => (
                  <Cell key={i} fill={barFill(bin.x0, bin.x1)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex gap-4 mt-2 flex-wrap">
          {[
            { color: '#34d399', label: 'Normal (|z|<1)' },
            { color: '#f59e0b', label: 'Watch (1≤|z|<threshold)' },
            { color: '#ef4444', label: `Outlier (|z|≥${threshold.toFixed(1)})` },
          ].map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1 text-[9px] text-gray-500">
              <span
                className="inline-block w-2 h-2 rounded-sm flex-shrink-0"
                style={{ background: color }}
              />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* ── Outlier table ── */}
      {outlierCount > 0 && (
        <div className="bg-secondary border border-white/5 rounded-lg overflow-hidden">
          <p className="text-[10px] text-gray-600 uppercase tracking-wider px-4 py-2 border-b border-white/5">
            Outlier rows — |z| ≥ {threshold.toFixed(1)}
          </p>
          <div className="overflow-auto max-h-64">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-white/5">
                  {['Row', 'Value', 'Z-Score', 'Status'].map(h => (
                    <th
                      key={h}
                      className={`px-4 py-1.5 text-gray-600 font-normal ${
                        h === 'Row' ? 'text-left' : h === 'Status' ? 'text-center' : 'text-right'
                      }`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {outliers.slice(0, 200).map(row => {
                  const s   = statusOf(row.z_score)
                  const { cls, Icon, label } = STATUS_STYLE[s]
                  return (
                    <tr key={row.idx} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="px-4 py-1.5 text-gray-400">{row.idx}</td>
                      <td className="px-4 py-1.5 text-right text-white font-mono">
                        {row.value.toLocaleString('vi-VN', { maximumFractionDigits: 4 })}
                      </td>
                      <td className={`px-4 py-1.5 text-right font-mono font-semibold ${cls}`}>
                        {row.z_score > 0 ? '+' : ''}{row.z_score.toFixed(3)}
                      </td>
                      <td className="px-4 py-1.5 text-center">
                        <span className={`flex items-center justify-center gap-1 ${cls}`}>
                          <Icon size={10} /> {label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {outliers.length > 200 && (
            <p className="text-[10px] text-gray-600 px-4 py-1.5 border-t border-white/5">
              ... và {outliers.length - 200} dòng nữa — Download CSV để xem tất cả
            </p>
          )}
        </div>
      )}

      {outlierCount === 0 && (
        <p className="text-[11px] text-work text-center py-2">
          ✓ Không có outlier nào với ngưỡng |z| ≥ {threshold.toFixed(1)}
        </p>
      )}

      {/* ── Download ── */}
      <div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <Download size={12} />
          {downloading ? 'Đang tải...' : 'Download Standardized CSV'}
        </button>
        <p className="text-[9px] text-gray-700 mt-0.5">
          CSV gốc + cột z_score + z_status (threshold cố định 2.0)
        </p>
      </div>

    </div>
  )
}
```

- [ ] **Step 2: TypeScript check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/ml/ZScoreResult.tsx
git commit -m "feat: add ZScoreResult component (histogram + outlier table + download)"
```

---

## Task 4: Wire into MlStatsView

**Files:**
- Modify: `frontend/src/components/ml/MlStatsView.tsx`

- [ ] **Step 1: Add `ZScoreResult` import and `ZScoreData` type**

At the top of `frontend/src/components/ml/MlStatsView.tsx`, add the component import after `import CodePanel`:

```typescript
// Before:
import CodePanel from './CodePanel'
import type { DatasetInfo, StatsResult, QualityResult } from '../../types'

// After:
import CodePanel from './CodePanel'
import ZScoreResult from './ZScoreResult'
import type { DatasetInfo, StatsResult, QualityResult, ZScoreData } from '../../types'
```

- [ ] **Step 2: Add `'zscore'` to TestType union**

```typescript
// Before:
type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney'

// After:
type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney' | 'zscore'
```

- [ ] **Step 3: Add to TESTS array**

Find the `TESTS` array. Insert after the `bootstrap` entry:

```typescript
// Before:
  { value: 'bootstrap',    label: 'Bootstrap CI',     needsColB: false },
  { value: 'distribution', label: 'Distribution',     needsColB: false },

// After:
  { value: 'bootstrap',    label: 'Bootstrap CI',     needsColB: false },
  { value: 'zscore',       label: 'Z-Score',          needsColB: false },
  { value: 'distribution', label: 'Distribution',     needsColB: false },
```

- [ ] **Step 4: Add to HINTS object**

Find the `HINTS` object. Add after the `bootstrap` entry:

```typescript
// Find this line (end of bootstrap entry):
                  colA: 'Cột số — VD: transaction_interval, revenue.' },

// Add after (before the next entry):
  zscore:       { what: 'Tính z-score cho mỗi giá trị: (x − mean) / std. Phát hiện giá trị bất thường và hiện phân phối chuẩn hoá.',
                  when: 'Dùng khi muốn biết giá trị nào bất thường, hoặc trước khi đưa dữ liệu vào model ML cần chuẩn hoá.',
                  colA: 'Cột số bất kỳ — VD: doanh thu, số ngày, transaction_interval.' },
```

- [ ] **Step 5: Add zscore case to generateCode()**

Find the `return ''` line at the end of `generateCode()` (the fallback). Insert before it:

```typescript
  if (test === 'zscore')
    return `${load}\n${a}\nz = (a - a.mean()) / (a.std() + 1e-9)\nfor i, (val, zi) in enumerate(zip(a, z)):\n    status = "outlier" if abs(zi) >= 2 else "watch" if abs(zi) >= 1 else "normal"\n    if abs(zi) >= 2:\n        print(f"row {i}: value={val:.4f}, z={zi:.4f} → {status}")\n`

  return ''
```

- [ ] **Step 6: Render ZScoreResult in place of generic grid**

Find the results section in the JSX (the block that starts with `{result && (`). Replace the inner div that renders the generic key-value grid:

```tsx
// Before:
        <>
          {/* Results grid */}
          <div className="bg-secondary border border-white/5 rounded-lg p-4">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(result).map(([k, v]) => (
                <div key={k}>
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider">{k}</p>
                  <p className={`text-sm font-semibold ${typeof v === 'string' && v.includes('significant') ? 'text-work' : 'text-white'}`}>
                    {typeof v === 'number' ? v.toLocaleString('vi-VN', { maximumFractionDigits: 4 }) : String(v)}
                  </p>
                </div>
              ))}
            </div>
          </div>

// After:
        <>
          {/* Results grid — or ZScoreResult for zscore test */}
          {test === 'zscore' ? (
            <ZScoreResult
              data={result as unknown as ZScoreData}
              colA={colA}
              fileId={dataset.file_id}
            />
          ) : (
          <div className="bg-secondary border border-white/5 rounded-lg p-4">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(result).map(([k, v]) => (
                <div key={k}>
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider">{k}</p>
                  <p className={`text-sm font-semibold ${typeof v === 'string' && v.includes('significant') ? 'text-work' : 'text-white'}`}>
                    {typeof v === 'number' ? v.toLocaleString('vi-VN', { maximumFractionDigits: 4 }) : String(v)}
                  </p>
                </div>
              ))}
            </div>
          </div>
          )}
```

**Note:** Add the closing `)}` after the existing generic grid `</div>` to close the ternary.

- [ ] **Step 7: Hide AI Interpret button for zscore**

The AI Interpret button is inside `{result && ( <> ... </>)}`. Find it and wrap with a condition:

```tsx
// Before:
            <button
              onClick={handleInterpret}
              disabled={interpreting}

// After:
            {test !== 'zscore' && <button
              onClick={handleInterpret}
              disabled={interpreting}
```

And close the conditional:
```tsx
// The closing tag of the button:
              {interpreting ? 'Đang phân tích...' : interpretation ? 'Phân tích lại' : 'Giải thích AI'}
            </button>

// After:
              {interpreting ? 'Đang phân tích...' : interpretation ? 'Phân tích lại' : 'Giải thích AI'}
            </button>}
```

- [ ] **Step 8: TypeScript check**

```
cd frontend && npx tsc --noEmit
```

Expected: no errors. Fix any type errors before proceeding.

- [ ] **Step 9: Commit**

```
git add frontend/src/components/ml/MlStatsView.tsx
git commit -m "feat: wire Z-Score test type into ML Studio Stats tab"
```

---

## Task 5: Manual verification

- [ ] **Step 1: Start the dev server**

```
cd frontend && npm run dev
```

Open `http://localhost:5173` → Analytics → ML Studio.

- [ ] **Step 2: Verify Z-Score in Stats dropdown**

Upload any CSV with a numeric column. Go to Stats tab. Confirm "Z-Score" appears in the test dropdown between "Bootstrap CI" and "Distribution".

- [ ] **Step 3: Verify hint card**

Select Z-Score. Confirm the hint card shows the correct Vietnamese description.

- [ ] **Step 4: Run Z-Score on a dataset with outliers**

Select a numeric column → click Run. Expect:
- Summary row showing mean, std, n
- Threshold slider at 2.0 with preset buttons
- Outlier count shown in red (if any outliers exist)
- Histogram with green/yellow/red bars
- Outlier table listing rows above threshold

- [ ] **Step 5: Test threshold slider reactivity**

Drag the slider or click presets. Confirm:
- Outlier count updates immediately (no loading spinner)
- Histogram bar colors update to reflect new threshold zones
- Outlier table updates instantly

- [ ] **Step 6: Test Download CSV**

Click "Download Standardized CSV". Confirm browser downloads a `.csv` file. Open it and verify it has the original columns plus `z_score` and `z_status` columns.

- [ ] **Step 7: Verify Show Code**

Click "Show Code". Confirm Python snippet is shown with z-score loop code.

- [ ] **Step 8: Verify AI Interpret is hidden**

Confirm the "Giải thích AI" button does NOT appear when Z-Score test is selected.

- [ ] **Step 9: Final commit**

```
git add -A
git commit -m "feat: Z-Score Analysis complete in ML Studio Stats tab"
```
