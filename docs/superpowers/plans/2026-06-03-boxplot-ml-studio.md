# Box Plot ML Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `boxplot` test type to ML Studio's Stats tab that renders a custom SVG box plot (single column or grouped by a category column), detects Tukey outliers (1.5×IQR), and provides CSV downloads for outliers and box stats.

**Architecture:** Backend adds a `boxplot` branch to `run_stats()` returning unified `groups: []` shape, plus two CSV endpoints. Frontend adds a self-contained `BoxPlotResult.tsx` component (custom SVG via `viewBox`) wired into `MlStatsView.tsx` as a new test type with optional group-by checkbox.

**Tech Stack:** FastAPI + Polars + NumPy (backend), React 18 + TypeScript + lucide-react + Tailwind (frontend).

---

## File Map

| File | Change |
|------|--------|
| `backend/routers/ml.py` | Add `max_groups: int = 10` to `StatsIn`; add `boxplot` handler in `run_stats()`; add `BoxPlotCsvIn` model + `POST /stats/boxplot_outliers_csv` + `POST /stats/boxplot_stats_csv` |
| `backend/tests/test_ml.py` | Add `test_stats_boxplot_single`, `test_stats_boxplot_grouped`, `test_stats_boxplot_max_groups`, `test_stats_boxplot_drops_tiny_groups`, `test_boxplot_outliers_csv`, `test_boxplot_stats_csv` |
| `frontend/src/types.ts` | Add `BoxPlotGroup`, `BoxPlotData` |
| `frontend/src/api/ml.ts` | Add `runBoxPlot()`, `downloadBoxOutliersCsv()`, `downloadBoxStatsCsv()` |
| `frontend/src/components/ml/BoxPlotResult.tsx` | **New** — full Box Plot UI (custom SVG) |
| `frontend/src/components/ml/MlStatsView.tsx` | Add `'boxplot'` to TestType, TESTS, HINTS, `generateCode()`; add `useGroupBy` + `maxGroups` state; add "So sánh theo nhóm" checkbox; render `<BoxPlotResult>` conditionally; hide AI interpret for boxplot |

---

## Task 1: Backend — boxplot handler + 2 CSV endpoints

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write the failing tests**

Open `backend/tests/test_ml.py` and append after the last existing test:

```python
BOX_SINGLE_CSV = b"val\n1\n2\n3\n4\n5\n6\n7\n8\n9\n100\n"
# val = [1..9, 100]  Q1≈3.25, Q3≈7.75, IQR≈4.5, upper_fence≈14.5 → outlier: 100

BOX_GROUPED_CSV = b"""val,grp
1,A
2,A
3,A
4,A
5,A
6,A
7,A
10,B
20,B
30,B
40,B
50,B
100,C
200,C
300,C
"""
# A: 7 rows (Q1≈2.5, Q3≈5.5, IQR=3.0)
# B: 5 rows (Q1=20, Q3=40, IQR=20)
# C: 3 rows  — DROPPED (n < 4)

BOX_SMALL_IQR_CSV = b"val\n1\n2\n2\n2\n2\n2\n"
# IQR will be 0 → handler must not crash


def test_stats_boxplot_single(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxs.csv", io.BytesIO(BOX_SINGLE_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot", "col_a": "val",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_n"] == 10
    assert d["total_groups"] == 1
    assert d["truncated"] is False
    assert len(d["groups"]) == 1
    g = d["groups"][0]
    assert g["name"] == "val"
    assert g["n"] == 10
    assert g["min"] == pytest.approx(1.0)
    assert g["max"] == pytest.approx(100.0)
    assert g["median"] == pytest.approx(5.5)
    assert g["iqr"] > 0
    assert g["upper_fence"] < 100
    assert len(g["outliers"]) == 1
    assert g["outliers"][0]["value"] == pytest.approx(100.0)


def test_stats_boxplot_grouped(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxg.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 200
    d = resp.json()
    # C dropped (n=3 < 4)
    assert len(d["groups"]) == 2
    names = {g["name"] for g in d["groups"]}
    assert names == {"A", "B"}
    # Order is top-N by count desc — A (7) before B (5)
    assert d["groups"][0]["name"] == "A"
    assert d["groups"][1]["name"] == "B"
    assert d["total_groups"] == 3        # before dropping (3 unique values)
    assert d["truncated"] is False        # max_groups (10) ≥ total_groups (3)


def test_stats_boxplot_max_groups(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxm.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    # Cap at 1 — only top group (A, count=7) returned
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp", "max_groups": 1,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["groups"]) == 1
    assert d["groups"][0]["name"] == "A"
    assert d["truncated"] is True


def test_stats_boxplot_drops_tiny_groups(client):
    """When all groups are too small, return 400."""
    tiny = b"val,grp\n1,A\n2,A\n1,B\n2,B\n"
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxt.csv", io.BytesIO(tiny), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 400


def test_stats_boxplot_handles_zero_iqr(client):
    """Constant-ish column (IQR=0) must not crash."""
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxz.csv", io.BytesIO(BOX_SMALL_IQR_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot", "col_a": "val",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["groups"]) == 1
    assert d["groups"][0]["iqr"] == pytest.approx(0.0)


def test_boxplot_outliers_csv(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxoc.csv", io.BytesIO(BOX_SINGLE_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/boxplot_outliers_csv", json={
        "file_id": upload["file_id"], "col_a": "val",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.content.decode("utf-8")
    header = text.splitlines()[0]
    assert "row_idx" in header
    assert "group"   in header
    assert "value"   in header
    assert "distance_iqr" in header
    # The outlier row (val=100) must appear
    assert "100" in text


def test_boxplot_stats_csv(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxsc.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/boxplot_stats_csv", json={
        "file_id": upload["file_id"], "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.content.decode("utf-8")
    header = text.splitlines()[0]
    for col in ["group", "n", "min", "q1", "median", "q3", "max",
                "iqr", "lower_fence", "upper_fence", "outlier_count"]:
        assert col in header
    # A and B should appear (C dropped due to n<4)
    assert "A" in text
    assert "B" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run from project root (PowerShell or cmd):
```
.venv\Scripts\python.exe -m pytest backend/tests/test_ml.py::test_stats_boxplot_single backend/tests/test_ml.py::test_stats_boxplot_grouped backend/tests/test_ml.py::test_stats_boxplot_max_groups backend/tests/test_ml.py::test_stats_boxplot_drops_tiny_groups backend/tests/test_ml.py::test_stats_boxplot_handles_zero_iqr backend/tests/test_ml.py::test_boxplot_outliers_csv backend/tests/test_ml.py::test_boxplot_stats_csv -v
```

Expected: 7 FAILs — `test_stats_boxplot_single` fails with 400 "Unknown test 'boxplot'", others similarly.

- [ ] **Step 3: Add `max_groups` field to `StatsIn` model**

Find the `class StatsIn(BaseModel):` block in `backend/routers/ml.py` (around line 750):

```python
# Before:
class StatsIn(BaseModel):
    file_id: str
    test:    str
    col_a:   str
    col_b:   Optional[str] = None

# After:
class StatsIn(BaseModel):
    file_id:    str
    test:       str
    col_a:      str
    col_b:      Optional[str] = None
    max_groups: int           = 10
```

If `Optional` is not yet imported, add `from typing import Optional` to the imports near the top (it likely already exists since `col_b` uses it).

- [ ] **Step 4: Add `boxplot` handler inside `run_stats()`**

Find the existing `if body.test == "zscore":` block. Insert the boxplot block **immediately after** the zscore return, **before** `raise HTTPException(400, f"Unknown test '{body.test}'")`:

```python
    if body.test == "boxplot":
        def _box_stats(arr: np.ndarray, name: str):
            if len(arr) < 4:
                return None
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
                    for i in outlier_idx[:1000]
                ],
            }

        groups: list[dict] = []
        truncated = False
        total_groups = 1

        if body.col_b:
            if body.col_b not in df.columns:
                raise HTTPException(400, f"Column '{body.col_b}' not found")
            df_g = df.with_columns(pl.col(body.col_b).cast(pl.Utf8))
            counts_df = df_g.group_by(body.col_b).len().sort("len", descending=True)
            all_names = counts_df[body.col_b].to_list()
            total_groups = len(all_names)
            top_names = all_names[: body.max_groups]
            truncated = total_groups > body.max_groups

            for name in top_names:
                sub = df_g.filter(pl.col(body.col_b) == name)[body.col_a]
                arr_g = sub.drop_nulls().cast(pl.Float64).to_numpy()
                s = _box_stats(arr_g, str(name))
                if s is not None:
                    groups.append(s)
        else:
            s = _box_stats(a, body.col_a)
            if s is not None:
                groups.append(s)

        if not groups:
            raise HTTPException(400, "Not enough data to compute box plot (need ≥4 values per group)")

        return {
            "groups":       groups,
            "total_n":      sum(g["n"] for g in groups),
            "total_groups": total_groups,
            "truncated":    truncated,
        }

    raise HTTPException(400, f"Unknown test '{body.test}'")
```

- [ ] **Step 5: Add `BoxPlotCsvIn` model + 2 CSV endpoints**

Find the `# ── AI Interpretation ─` comment in `backend/routers/ml.py` (after the existing `zscore_csv` endpoint). Insert the new model and endpoints **before** that comment:

```python
# ── Box Plot CSV exports ─────────────────────────────────────────────────────

class BoxPlotCsvIn(BaseModel):
    file_id:    str
    col_a:      str
    col_b:      Optional[str] = None
    max_groups: int           = 10


def _boxplot_compute_for_csv(df: "pl.DataFrame", body: "BoxPlotCsvIn"):
    """Compute box stats per group (or single). Returns list of dicts with raw outlier indices."""
    def _stats(arr, name):
        if len(arr) < 4:
            return None
        q1, med, q3 = np.percentile(arr, [25, 50, 75])
        iqr = float(q3 - q1)
        lo, hi = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
        mask = (arr < lo) | (arr > hi)
        idx  = np.where(mask)[0]
        return {
            "name": name, "n": int(len(arr)),
            "min": float(arr.min()), "q1": float(q1), "median": float(med),
            "q3": float(q3), "max": float(arr.max()),
            "iqr": iqr, "lower_fence": lo, "upper_fence": hi,
            "outlier_indices": idx, "outlier_values": arr[mask],
        }

    if body.col_a not in df.columns:
        raise HTTPException(400, f"Column '{body.col_a}' not found")

    groups = []
    if body.col_b:
        if body.col_b not in df.columns:
            raise HTTPException(400, f"Column '{body.col_b}' not found")
        df_g = df.with_columns(pl.col(body.col_b).cast(pl.Utf8))
        counts_df = df_g.group_by(body.col_b).len().sort("len", descending=True)
        top_names = counts_df[body.col_b].to_list()[: body.max_groups]
        for name in top_names:
            sub = df_g.filter(pl.col(body.col_b) == name)[body.col_a]
            arr = sub.drop_nulls().cast(pl.Float64).to_numpy()
            s = _stats(arr, str(name))
            if s is not None:
                groups.append(s)
    else:
        arr = df[body.col_a].drop_nulls().cast(pl.Float64).to_numpy()
        s = _stats(arr, body.col_a)
        if s is not None:
            groups.append(s)

    if not groups:
        raise HTTPException(400, "Not enough data to compute box plot (need ≥4 values per group)")
    return groups


@router.post("/stats/boxplot_outliers_csv")
def boxplot_outliers_csv(body: BoxPlotCsvIn):
    conn = get_connection()
    row  = _get_file_row(conn, body.file_id)
    conn.close()
    df   = _load_df(row["filepath"])
    groups = _boxplot_compute_for_csv(df, body)

    lines = ["row_idx,group,value,distance_iqr"]
    for g in groups:
        for i, v in zip(g["outlier_indices"], g["outlier_values"]):
            # signed distance in IQR units from nearest quartile
            if v > g["upper_fence"]:
                dist = (v - g["q3"]) / g["iqr"] if g["iqr"] > 0 else 0.0
            elif v < g["lower_fence"]:
                dist = (v - g["q1"]) / g["iqr"] if g["iqr"] > 0 else 0.0
            else:
                dist = 0.0
            safe_grp = str(g["name"]).replace(",", ";").replace("\n", " ")
            lines.append(f"{int(i)},{safe_grp},{float(v):.4f},{dist:.4f}")

    csv_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    safe_col  = body.col_a.replace("/", "_").replace(" ", "_")
    filename  = f"box_outliers_{safe_col}_{row['filename']}"
    return Response(
        content=csv_bytes, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/stats/boxplot_stats_csv")
def boxplot_stats_csv(body: BoxPlotCsvIn):
    conn = get_connection()
    row  = _get_file_row(conn, body.file_id)
    conn.close()
    df   = _load_df(row["filepath"])
    groups = _boxplot_compute_for_csv(df, body)

    lines = ["group,n,min,q1,median,q3,max,iqr,lower_fence,upper_fence,outlier_count"]
    for g in groups:
        safe_grp = str(g["name"]).replace(",", ";").replace("\n", " ")
        lines.append(
            f"{safe_grp},{g['n']},{g['min']:.4f},{g['q1']:.4f},{g['median']:.4f},"
            f"{g['q3']:.4f},{g['max']:.4f},{g['iqr']:.4f},"
            f"{g['lower_fence']:.4f},{g['upper_fence']:.4f},"
            f"{len(g['outlier_indices'])}"
        )

    csv_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    safe_col  = body.col_a.replace("/", "_").replace(" ", "_")
    filename  = f"box_stats_{safe_col}_{row['filename']}"
    return Response(
        content=csv_bytes, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: Run tests — expect all 7 to pass**

```
.venv\Scripts\python.exe -m pytest backend/tests/test_ml.py -v -k "boxplot"
```

Expected: 7 PASSED.

- [ ] **Step 7: Run full backend suite to check no regressions**

```
.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

Expected: all previously passing tests still pass (should be 129 + 7 = 136 passed).

- [ ] **Step 8: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat: add boxplot stats handler + box outliers/stats CSV endpoints"
```

---

## Task 2: Frontend types + API

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/ml.ts`

- [ ] **Step 1: Add `BoxPlotGroup` and `BoxPlotData` to types.ts**

Open `frontend/src/types.ts`. Find the `// ─── ML Z-Score ───` section. Append immediately before the `// ─── Action Plan ───` divider:

```typescript
// ─── ML Box Plot ──────────────────────────────────────────────────────────────

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

- [ ] **Step 2: Add API functions to api/ml.ts**

Open `frontend/src/api/ml.ts`. Add `BoxPlotData` to the type import:

```typescript
// Before:
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix, QualityResult,
  ZScoreData,
} from '../types'

// After:
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult, CorrelationMatrix, QualityResult,
  ZScoreData, BoxPlotData,
} from '../types'
```

Add at the **bottom** of the file (after `downloadZScoreCsv`):

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
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a   = document.createElement('a')
  a.href     = url
  a.download = `box_outliers_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function downloadBoxStatsCsv(
  fileId: string, colA: string, colB?: string, maxGroups: number = 10,
): Promise<void> {
  const { data } = await client.post(
    '/ml/stats/boxplot_stats_csv',
    { file_id: fileId, col_a: colA, col_b: colB, max_groups: maxGroups },
    { responseType: 'blob' },
  )
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: 'text/csv' }))
  const a   = document.createElement('a')
  a.href     = url
  a.download = `box_stats_${colA}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 3: TypeScript check**

```
cd frontend
node_modules\.bin\tsc --noEmit --project tsconfig.app.json
```

Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/types.ts frontend/src/api/ml.ts
git commit -m "feat: add BoxPlotData types and box plot CSV download helpers"
```

---

## Task 3: BoxPlotResult component (custom SVG)

**Files:**
- Create: `frontend/src/components/ml/BoxPlotResult.tsx`

- [ ] **Step 1: Create the file with the full component**

```tsx
import { useState } from 'react'
import { AlertTriangle, Download, BoxSelect, Users } from 'lucide-react'
import type { BoxPlotData, BoxPlotGroup } from '../../types'
import { downloadBoxOutliersCsv, downloadBoxStatsCsv } from '../../api/ml'

interface Props {
  data:              BoxPlotData
  colA:              string
  colB?:             string
  fileId:            string
  maxGroups:         number
  onMaxGroupsChange: (n: number) => void
}

const CAP_OPTIONS = [5, 10, 20, 50]

const SVG_H       = 320
const PAD_TOP     = 20
const PAD_RIGHT   = 20
const PAD_BOTTOM  = 60
const PAD_LEFT    = 50
const SLOT_MIN    = 80

function lerpHex(a: string, b: string, t: number): string {
  const pa = [parseInt(a.slice(1, 3), 16), parseInt(a.slice(3, 5), 16), parseInt(a.slice(5, 7), 16)]
  const pb = [parseInt(b.slice(1, 3), 16), parseInt(b.slice(3, 5), 16), parseInt(b.slice(5, 7), 16)]
  const r = pa.map((c, i) => Math.round(c + (pb[i] - c) * t))
  return `#${r.map(c => c.toString(16).padStart(2, '0')).join('')}`
}

function formatNum(v: number): string {
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 4 })
}

export default function BoxPlotResult({
  data, colA, colB, fileId, maxGroups, onMaxGroupsChange,
}: Props) {
  const [downloadingOutliers, setDownloadingOutliers] = useState(false)
  const [downloadingStats,    setDownloadingStats]    = useState(false)
  const [hoveredIdx,          setHoveredIdx]          = useState<number | null>(null)

  const isGrouped = !!colB
  const groups    = data.groups
  const n         = groups.length

  // ── Color gradient by median (only meaningful in grouped mode) ──
  const medians   = groups.map(g => g.median)
  const minMedian = Math.min(...medians)
  const maxMedian = Math.max(...medians)
  function gradientFill(median: number): string {
    if (!isGrouped || minMedian === maxMedian) return '#fbbf24'
    const t = (median - minMedian) / (maxMedian - minMedian)
    if (t < 0.5) return lerpHex('#34d399', '#fbbf24', t * 2)
    return lerpHex('#fbbf24', '#ef4444', (t - 0.5) * 2)
  }

  // ── SVG dimensions ──
  const W       = Math.max(640, PAD_LEFT + PAD_RIGHT + n * SLOT_MIN)
  const plotW   = W - PAD_LEFT - PAD_RIGHT
  const plotH   = SVG_H - PAD_TOP - PAD_BOTTOM
  const slotW   = plotW / Math.max(1, n)
  const boxW    = Math.min(60, slotW * 0.6)

  // ── Y-scale ──
  const allValues = groups.flatMap(g => [
    g.min, g.max, g.lower_fence, g.upper_fence,
    ...g.outliers.map(o => o.value),
  ])
  const yMinData = Math.min(...allValues)
  const yMaxData = Math.max(...allValues)
  const yPad     = (yMaxData - yMinData) * 0.05 || 1
  const yMin     = yMinData - yPad
  const yMax     = yMaxData + yPad
  const y        = (v: number) => PAD_TOP + (1 - (v - yMin) / (yMax - yMin)) * plotH

  // ── Y-axis ticks (5 evenly-spaced) ──
  const ticks = Array.from({ length: 5 }, (_, i) => yMin + (yMax - yMin) * (i / 4))

  // ── X-axis label rotation ──
  const needRotate = groups.some(g => g.name.length > 8)

  // ── Outlier table data ──
  function signedDistance(value: number, g: BoxPlotGroup): number {
    if (g.iqr === 0) return 0
    if (value > g.upper_fence) return (value - g.q3) / g.iqr
    if (value < g.lower_fence) return (value - g.q1) / g.iqr
    return 0
  }
  const allOutliers = groups.flatMap(g =>
    g.outliers.map(o => ({
      idx:      o.idx,
      value:    o.value,
      group:    g.name,
      distance: signedDistance(o.value, g),
    }))
  ).sort((a, b) => Math.abs(b.distance) - Math.abs(a.distance))

  async function handleDownloadOutliers() {
    setDownloadingOutliers(true)
    try { await downloadBoxOutliersCsv(fileId, colA, colB, maxGroups) }
    finally { setDownloadingOutliers(false) }
  }

  async function handleDownloadStats() {
    setDownloadingStats(true)
    try { await downloadBoxStatsCsv(fileId, colA, colB, maxGroups) }
    finally { setDownloadingStats(false) }
  }

  return (
    <div className="flex flex-col gap-4">

      {/* ── Summary ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">total n</p>
            <p className="text-sm font-semibold text-white">{formatNum(data.total_n)}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">
              {isGrouped ? 'groups shown' : 'groups'}
            </p>
            <p className="text-sm font-semibold text-white">
              {n}{isGrouped && data.total_groups !== n ? ` / ${data.total_groups}` : ''}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-wider">outliers</p>
            <p className={`text-sm font-semibold ${allOutliers.length > 0 ? 'text-danger' : 'text-work'}`}>
              {allOutliers.length}
            </p>
          </div>
        </div>
      </div>

      {/* ── Group cap selector (grouped mode only) ── */}
      {isGrouped && (
        <div className="bg-secondary border border-white/5 rounded-lg p-4 flex items-center gap-3 flex-wrap">
          <span className="text-[10px] text-gray-600 uppercase tracking-wider flex items-center gap-1.5">
            <Users size={11} /> Top groups
          </span>
          <select
            className="input-base text-xs"
            value={maxGroups}
            onChange={e => onMaxGroupsChange(parseInt(e.target.value))}
          >
            {CAP_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          {data.truncated && (
            <span className="text-[11px] text-gray-500">
              showing top {n} of {data.total_groups} groups (by count)
            </span>
          )}
        </div>
      )}

      {/* ── SVG Box Plot ── */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4">
        <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <BoxSelect size={12} /> Box Plot
        </p>
        <div className="overflow-x-auto">
          <svg
            width="100%"
            viewBox={`0 0 ${W} ${SVG_H}`}
            preserveAspectRatio="xMidYMid meet"
            style={{ minWidth: W, height: SVG_H }}
          >
            {/* Y-axis ticks + grid lines */}
            {ticks.map((t, i) => (
              <g key={i}>
                <line
                  x1={PAD_LEFT} x2={W - PAD_RIGHT}
                  y1={y(t)} y2={y(t)}
                  stroke="rgba(255,255,255,0.05)"
                  strokeDasharray="3 3"
                />
                <text
                  x={PAD_LEFT - 6} y={y(t)}
                  textAnchor="end" dominantBaseline="middle"
                  fontSize={9} fill="#6b7280"
                >
                  {formatNum(t)}
                </text>
              </g>
            ))}

            {/* Boxes */}
            {groups.map((g, i) => {
              const cx       = PAD_LEFT + slotW * (i + 0.5)
              const x0       = cx - boxW / 2
              const fill     = gradientFill(g.median)
              const isHover  = hoveredIdx === i
              return (
                <g key={g.name}
                  onMouseEnter={() => setHoveredIdx(i)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Invisible hit area for tooltip */}
                  <rect
                    x={cx - slotW / 2} y={PAD_TOP}
                    width={slotW} height={plotH}
                    fill="transparent"
                  />

                  {/* Whisker line (upper) */}
                  <line
                    x1={cx} x2={cx}
                    y1={y(g.q3)} y2={y(g.upper_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />
                  {/* Whisker cap (upper) */}
                  <line
                    x1={cx - 10} x2={cx + 10}
                    y1={y(g.upper_fence)} y2={y(g.upper_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />
                  {/* Whisker line (lower) */}
                  <line
                    x1={cx} x2={cx}
                    y1={y(g.q1)} y2={y(g.lower_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />
                  {/* Whisker cap (lower) */}
                  <line
                    x1={cx - 10} x2={cx + 10}
                    y1={y(g.lower_fence)} y2={y(g.lower_fence)}
                    stroke="rgba(255,255,255,0.4)" strokeWidth={1}
                  />

                  {/* Box */}
                  <rect
                    x={x0} y={y(g.q3)}
                    width={boxW} height={y(g.q1) - y(g.q3)}
                    fill={fill} fillOpacity={isHover ? 0.6 : 0.4}
                    stroke={fill} strokeOpacity={0.9} strokeWidth={1}
                    rx={2}
                  />

                  {/* Median line */}
                  <line
                    x1={x0} x2={x0 + boxW}
                    y1={y(g.median)} y2={y(g.median)}
                    stroke="#ffffff" strokeWidth={2}
                  />

                  {/* Outlier dots */}
                  {g.outliers.map((o, oi) => (
                    <circle
                      key={oi}
                      cx={cx} cy={y(o.value)} r={3}
                      fill={fill} stroke="#ffffff" strokeWidth={1}
                    />
                  ))}

                  {/* X-axis label */}
                  <text
                    x={cx} y={SVG_H - PAD_BOTTOM + 14}
                    textAnchor={needRotate ? 'end' : 'middle'}
                    fontSize={10} fill="#9ca3af"
                    transform={needRotate ? `rotate(-35, ${cx}, ${SVG_H - PAD_BOTTOM + 14})` : undefined}
                  >
                    {g.name.length > 14 ? g.name.slice(0, 12) + '…' : g.name}
                  </text>
                </g>
              )
            })}

            {/* Hover tooltip */}
            {hoveredIdx !== null && (() => {
              const g     = groups[hoveredIdx]
              const cx    = PAD_LEFT + slotW * (hoveredIdx + 0.5)
              const tipW  = 160
              const tipH  = 130
              const tipX  = Math.min(W - tipW - 4, Math.max(4, cx + 12))
              const tipY  = PAD_TOP + 4
              return (
                <g style={{ pointerEvents: 'none' }}>
                  <rect
                    x={tipX} y={tipY} width={tipW} height={tipH}
                    rx={4} fill="#161b22" stroke="rgba(255,255,255,0.1)"
                  />
                  {[
                    ['name',    g.name],
                    ['n',       formatNum(g.n)],
                    ['min',     formatNum(g.min)],
                    ['Q1',      formatNum(g.q1)],
                    ['median',  formatNum(g.median)],
                    ['Q3',      formatNum(g.q3)],
                    ['max',     formatNum(g.max)],
                    ['IQR',     formatNum(g.iqr)],
                    ['outliers', String(g.outliers.length)],
                  ].map(([k, v], li) => (
                    <text
                      key={k}
                      x={tipX + 8} y={tipY + 14 + li * 13}
                      fontSize={10} fill="#d1d5db"
                    >
                      <tspan fill="#6b7280">{k}:</tspan>{' '}{v}
                    </text>
                  ))}
                </g>
              )
            })()}
          </svg>
        </div>

        {/* Gradient legend (grouped mode only) */}
        {isGrouped && groups.length > 1 && (
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[9px] text-gray-500">Low median</span>
            <svg width="160" height="10">
              <defs>
                <linearGradient id="medianGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%"   stopColor="#34d399" />
                  <stop offset="50%"  stopColor="#fbbf24" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>
              </defs>
              <rect width="160" height="8" y="1" fill="url(#medianGradient)" rx="2" />
            </svg>
            <span className="text-[9px] text-gray-500">High median</span>
          </div>
        )}
      </div>

      {/* ── Outlier table ── */}
      {allOutliers.length > 0 && (
        <div className="bg-secondary border border-white/5 rounded-lg overflow-hidden">
          <p className="text-[10px] text-gray-600 uppercase tracking-wider px-4 py-2 border-b border-white/5">
            Outlier rows — vượt 1.5×IQR fence
          </p>
          <div className="overflow-auto max-h-64">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-left">Row</th>
                  {isGrouped && <th className="px-4 py-1.5 text-gray-600 font-normal text-left">Group</th>}
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-right">Value</th>
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-right">Distance</th>
                  <th className="px-4 py-1.5 text-gray-600 font-normal text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {allOutliers.slice(0, 200).map((o, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="px-4 py-1.5 text-gray-400">{o.idx}</td>
                    {isGrouped && <td className="px-4 py-1.5 text-gray-300">{o.group}</td>}
                    <td className="px-4 py-1.5 text-right text-white font-mono">
                      {formatNum(o.value)}
                    </td>
                    <td className="px-4 py-1.5 text-right font-mono font-semibold text-danger">
                      {o.distance > 0 ? '+' : ''}{o.distance.toFixed(2)}×IQR
                    </td>
                    <td className="px-4 py-1.5 text-center">
                      <span className="flex items-center justify-center gap-1 text-danger">
                        <AlertTriangle size={10} /> Outlier
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {allOutliers.length > 200 && (
            <p className="text-[10px] text-gray-600 px-4 py-1.5 border-t border-white/5">
              ... và {allOutliers.length - 200} dòng nữa — Download CSV để xem tất cả
            </p>
          )}
        </div>
      )}

      {allOutliers.length === 0 && (
        <p className="text-[11px] text-work text-center py-2">
          ✓ Không có outlier nào (toàn bộ giá trị nằm trong fence 1.5×IQR)
        </p>
      )}

      {/* ── Download buttons ── */}
      <div className="flex gap-6 flex-wrap">
        <button
          onClick={handleDownloadOutliers}
          disabled={downloadingOutliers || allOutliers.length === 0}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <Download size={12} />
          {downloadingOutliers ? 'Đang tải...' : 'Download Outliers CSV'}
        </button>
        <button
          onClick={handleDownloadStats}
          disabled={downloadingStats}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <Download size={12} />
          {downloadingStats ? 'Đang tải...' : 'Download Box Stats CSV'}
        </button>
      </div>

    </div>
  )
}
```

- [ ] **Step 2: TypeScript check**

```
cd frontend
node_modules\.bin\tsc --noEmit --project tsconfig.app.json
```

Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/ml/BoxPlotResult.tsx
git commit -m "feat: add BoxPlotResult component (custom SVG box plot + outlier table + downloads)"
```

---

## Task 4: Wire into MlStatsView

**Files:**
- Modify: `frontend/src/components/ml/MlStatsView.tsx`

- [ ] **Step 1: Add imports**

At the top of `frontend/src/components/ml/MlStatsView.tsx`, add the BoxPlot imports next to the existing ZScoreResult import:

```typescript
// Before:
import ZScoreResult from './ZScoreResult'
import type { DatasetInfo, StatsResult, QualityResult, ZScoreData } from '../../types'
import { runStats, interpretStats } from '../../api/ml'

// After:
import ZScoreResult from './ZScoreResult'
import BoxPlotResult from './BoxPlotResult'
import type { DatasetInfo, StatsResult, QualityResult, ZScoreData, BoxPlotData } from '../../types'
import { runStats, interpretStats, runBoxPlot } from '../../api/ml'
```

- [ ] **Step 2: Add `'boxplot'` to TestType union**

```typescript
// Before:
type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney' | 'zscore'

// After:
type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'
  | 'anova' | 'chi2' | 'bootstrap' | 'mannwhitney' | 'zscore' | 'boxplot'
```

- [ ] **Step 3: Add `boxplot` entry to TESTS array (after zscore)**

```typescript
// Find:
  { value: 'zscore',       label: 'Z-Score',          needsColB: false },
  { value: 'distribution', label: 'Distribution',     needsColB: false },

// Replace with:
  { value: 'zscore',       label: 'Z-Score',          needsColB: false },
  { value: 'boxplot',      label: 'Box Plot',         needsColB: false, colBHint: 'phân nhóm (optional)' },
  { value: 'distribution', label: 'Distribution',     needsColB: false },
```

- [ ] **Step 4: Add HINTS entry**

Find the `zscore:` HINTS entry. Insert immediately after it:

```typescript
  zscore:       { what: 'Tính z-score cho mỗi giá trị: (x − mean) / std. Phát hiện giá trị bất thường và hiện phân phối chuẩn hoá.',
                  when: 'Dùng khi muốn biết giá trị nào bất thường, hoặc trước khi đưa dữ liệu vào model ML cần chuẩn hoá.',
                  colA: 'Cột số bất kỳ — VD: doanh thu, số ngày, transaction_interval.' },
  boxplot:      { what: 'Vẽ box plot (min/Q1/median/Q3/max) cho 1 cột số, hoặc so sánh phân phối nhiều nhóm khi chọn cột B. Tự phát hiện outlier (vượt 1.5×IQR).',
                  when: 'Dùng để xem nhanh độ rải, độ skew, outlier; hoặc so sánh phân phối giữa các nhóm trước khi chạy ANOVA / Mann-Whitney.',
                  colA: 'Cột số bất kỳ — VD: doanh thu, transaction_interval.',
                  colB: '(Optional) Cột phân nhóm để so sánh — VD: Brand, Tier, Region.' },
}
```

- [ ] **Step 5: Add `boxplot` case to `generateCode()`**

Find the existing `if (test === 'zscore')` block in `generateCode`. Insert immediately after it (before `return ''`):

```typescript
  if (test === 'boxplot') {
    const groupBlock = colB
      ? `\n\n# Group-by mode\nfor g in df["${colB}"].unique().to_list():\n    sub = df.filter(pl.col("${colB}") == g)["${colA}"].drop_nulls().to_numpy()\n    if len(sub) >= 4:\n        box_stats(sub, str(g))\n`
      : ''
    return `${load}\n${a}\ndef box_stats(arr, name="all"):\n    q1, med, q3 = np.percentile(arr, [25, 50, 75])\n    iqr = q3 - q1\n    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr\n    outliers = arr[(arr < lo) | (arr > hi)]\n    print(f"{name}: n={len(arr)}, Q1={q1:.2f}, med={med:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}, fences=[{lo:.2f}, {hi:.2f}], outliers={len(outliers)}")\n\nbox_stats(a, "${colA}")${groupBlock}`
  }

  return ''
}
```

- [ ] **Step 6: Add `useGroupBy` and `maxGroups` state, refactor `handleRun`**

Inside the component, find the state block:

```typescript
// Before (around line 108):
  const [showCode,       setShowCode]       = useState(false)

// Add after:
  const [showCode,       setShowCode]       = useState(false)
  const [useGroupBy,     setUseGroupBy]     = useState(false)
  const [maxGroups,      setMaxGroups]      = useState(10)
```

Replace the existing `handleRun` function:

```typescript
// Before:
  async function handleRun() {
    setRunning(true); setError(''); setResult(null)
    setInterpretation(null); setAiError('')
    try {
      setResult(await runStats(dataset.file_id, test, colA, needsColB ? colB : undefined))
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Stats failed')
    } finally { setRunning(false) }
  }

// After:
  async function handleRun(overrideMaxGroups?: number) {
    setRunning(true); setError(''); setResult(null)
    setInterpretation(null); setAiError('')
    try {
      if (test === 'boxplot') {
        const r = await runBoxPlot(
          dataset.file_id, colA,
          useGroupBy ? colB : undefined,
          overrideMaxGroups ?? maxGroups,
        )
        setResult(r as unknown as StatsResult)
      } else {
        setResult(await runStats(dataset.file_id, test, colA, needsColB ? colB : undefined))
      }
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Stats failed')
    } finally { setRunning(false) }
  }

  // Called by BoxPlotResult when user changes the group cap dropdown.
  async function handleMaxGroupsChange(newMax: number) {
    setMaxGroups(newMax)
    await handleRun(newMax)
  }
```

- [ ] **Step 7: Update the column B logic to treat boxplot + useGroupBy as needing B**

Find the line:
```typescript
  const needsColB = testMeta.needsColB
```

Replace with:
```typescript
  const needsColB     = testMeta.needsColB
  const showColB      = needsColB || (test === 'boxplot' && useGroupBy)
  const sendColB      = needsColB || (test === 'boxplot' && useGroupBy)
```

Then update the col B render condition. Find:
```typescript
        {needsColB && (
          <div>
            <label className="block text-[10px] text-gray-600 mb-1">
              Column B{testMeta.colBHint ? ` (${testMeta.colBHint})` : ''}
```

Replace `{needsColB && (` with `{showColB && (`.

Also update the col B options selector for boxplot to allow any column (like ANOVA/chi2). Find:
```typescript
  const colBOptions = (test === 'anova' || test === 'chi2') ? allCols : numericCols
```

Replace with:
```typescript
  const colBOptions = (test === 'anova' || test === 'chi2' || test === 'boxplot') ? allCols : numericCols
```

- [ ] **Step 8: Add the "So sánh theo nhóm" checkbox**

Find the col B div block. Add **immediately before** it the boxplot group-by checkbox:

```tsx
// Before:
        {needsColB && (
          <div>
            ...
          </div>
        )}

// (Now showColB after Step 7) — Replace with:
        {test === 'boxplot' && (
          <div className="flex items-end pb-1.5">
            <label className="flex items-center gap-1.5 text-[11px] text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={useGroupBy}
                onChange={e => setUseGroupBy(e.target.checked)}
                className="accent-analytics"
              />
              So sánh theo nhóm
            </label>
          </div>
        )}
        {showColB && (
          <div>
            ...existing col B render unchanged...
          </div>
        )}
```

- [ ] **Step 9: Render `<BoxPlotResult>` when test is boxplot**

Find the results render block (starts at `{result && (`). Locate the existing ternary:

```tsx
// Before:
          {test === 'zscore' ? (
            <ZScoreResult
              data={result as unknown as ZScoreData}
              colA={colA}
              fileId={dataset.file_id}
            />
          ) : (
            <div className="bg-secondary border border-white/5 rounded-lg p-4">
              ...generic grid...
            </div>
          )}

// After (3-way ternary):
          {test === 'zscore' ? (
            <ZScoreResult
              data={result as unknown as ZScoreData}
              colA={colA}
              fileId={dataset.file_id}
            />
          ) : test === 'boxplot' ? (
            <BoxPlotResult
              data={result as unknown as BoxPlotData}
              colA={colA}
              colB={useGroupBy ? colB : undefined}
              fileId={dataset.file_id}
              maxGroups={maxGroups}
              onMaxGroupsChange={handleMaxGroupsChange}
            />
          ) : (
            <div className="bg-secondary border border-white/5 rounded-lg p-4">
              ...generic grid unchanged...
            </div>
          )}
```

- [ ] **Step 10: Hide AI Interpret button for boxplot**

Find the existing AI Interpret button conditional:

```tsx
// Before:
            {test !== 'zscore' && (
            <button
              onClick={handleInterpret}
              ...
            </button>
            )}

// After:
            {test !== 'zscore' && test !== 'boxplot' && (
            <button
              onClick={handleInterpret}
              ...
            </button>
            )}
```

- [ ] **Step 11: TypeScript check**

```
cd frontend
node_modules\.bin\tsc --noEmit --project tsconfig.app.json
```

Expected: no errors. Fix any type errors before proceeding.

- [ ] **Step 12: Commit**

```
git add frontend/src/components/ml/MlStatsView.tsx
git commit -m "feat: wire Box Plot test type into ML Studio Stats tab"
```

---

## Task 5: Manual verification

- [ ] **Step 1: Start backend and frontend**

In two terminals:

```
# Terminal 1
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

```
# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173` → Analytics → ML Studio.

- [ ] **Step 2: Verify Box Plot appears in Stats dropdown**

Upload a CSV with a numeric column and a category column. Go to Stats tab. Confirm "Box Plot" appears between "Z-Score" and "Distribution" in the test dropdown.

- [ ] **Step 3: Verify hint card text**

Select Box Plot. Confirm the hint card shows the correct Vietnamese description including the col B hint.

- [ ] **Step 4: Run Box Plot in single mode**

Select a numeric column → click Run (do NOT check "So sánh theo nhóm").
Expect:
- Summary row: total n, groups: 1, outlier count
- No group cap selector visible
- SVG box plot with 1 yellow box centered (analytics color)
- Median line in white
- Whiskers + caps visible
- Outlier dots (if any) above/below whiskers
- No gradient legend
- Outlier table with Row / Value / Distance / Status columns (no Group column)

- [ ] **Step 5: Switch to group-by mode**

Check "So sánh theo nhóm" → select a category column for B → click Run.
Expect:
- Summary updated: groups: N (where N = unique values in B, capped at 10)
- Group cap selector visible with dropdown [5/10/20/50]
- SVG box plot with N boxes, each a different color (green→amber→red by median)
- X-axis labels showing group names
- Gradient legend below chart: "Low median ●●● High median"
- Outlier table now includes Group column

- [ ] **Step 6: Test group cap changes**

Click cap dropdown → choose 5. Confirm:
- Chart updates with only top 5 groups
- Summary shows "5 / N" if total groups > 5
- Truncation note: "showing top 5 of N groups (by count)"

- [ ] **Step 7: Test hover tooltip**

Hover over a box. Confirm:
- Tooltip appears with: name, n, min, Q1, median, Q3, max, IQR, outlier count
- Box fill opacity increases slightly on hover

- [ ] **Step 8: Test downloads**

Click "Download Outliers CSV". Confirm browser downloads `box_outliers_<col>.csv`. Open it:
- Header: `row_idx,group,value,distance_iqr`
- Rows include the outlier values

Click "Download Box Stats CSV". Confirm browser downloads `box_stats_<col>.csv`. Open it:
- Header includes: group, n, min, q1, median, q3, max, iqr, lower_fence, upper_fence, outlier_count
- One row per group

- [ ] **Step 9: Verify Show Code**

Click "Show Code". Confirm Python snippet appears with `box_stats()` function. In group-by mode, the snippet includes a `for g in df[...].unique()` loop. In single mode, only the single-column call.

- [ ] **Step 10: Verify AI Interpret is hidden**

Confirm the "Giải thích AI" button does NOT appear when Box Plot is selected (either mode).

- [ ] **Step 11: Final commit**

If any tweaks were made during verification, commit them:

```
git add -A
git commit -m "feat: Box Plot complete in ML Studio Stats tab"
```
