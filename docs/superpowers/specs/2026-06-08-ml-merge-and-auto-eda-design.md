# ML Studio — Multi-file Merge + Auto-EDA — Design Spec

**Date:** 2026-06-08
**Approach:** A for both features (backend does the heavy lifting in polars + a thin React surface). Chosen by user.
**Target directory (live app):** `D:\assitant_tools\tools_performance\08_Projects\leonie` (branch `master`, **local commits only — never push**, history has secrets).
**Scope:** Two new ML Studio surfaces — **(1) Multi-file Merge** (the "Spec B" data-prep effort flagged in `2026-06-06-ml-studio-analytics-upgrade-design.md`) and **(2) Auto-EDA report**. One spec, two parts, one implementation plan. Build **Merge first**, then **Auto-EDA**.

---

## Context

ML Studio (`pages/analytics/MlStudio.tsx` → `components/ml/MlResultTabs.tsx`) is a **single-dataset** tool: upload one file → `DatasetInfo {file_id}` → tabs Table · Charts · Stats · Forecast · Cohort operate on it. Backend `backend/routers/ml.py` runs polars/DuckDB; datasets are registered in the `uploaded_files` table (`file_id, filename, filepath, rows, cols, uploaded`) with the raw file in `UPLOADS_DIR`, loaded by `_load_df` (parquet sidecar cache). AI insights use `_call_ai_ml` (Claude `claude-haiku-4-5-20251001` → Ollama fallback).

Two manual workflows the user wants to absorb into the app:

1. **Multi-file Merge.** Source: a notebook (`Final Nghiệm Thu - 2026.ipynb`) that hard-codes the merge of 23 survey `.xlsx`: a manual `COL_MAPPING` of full-Vietnamese question headers → canonical names (`'Số điện thoại liên hệ:' → 'phone'`…), keep mapped columns, fill missing as null, `concat`, `clean_phone` (strip non-digits → last 9 → prefix `0`), dedup by phone, completeness check, export. The user wants this **generalized**: upload N files with differing schemas/nulls/dupes, **detect the common fields** (a chip/button list of fields shared across files), pick them, merge, clean, and use the result.

2. **Auto-EDA.** Source: the `EDA Analysis` sheet inside `Query (1).xlsx` — a hand-built gold-standard report over a 418,311×20 ColosBaby sales export (`Sheet1`). It is the exact target layout: numeric profile (Min/Max/Mean/Median/Std/P25/P75/P95), categorical breakdown by `Product_Type__c`, **log-transformed** correlation matrix (ln_Qty↔ln_Price = −0.894), binned distributions, top-10 products, rule-based customer segments, **5 insights as Finding→So-what→Action**, and data-quality flags. The dataset is heavily right-skewed (`Quantity__c` median 4 vs mean 69) and has a 100%-null column (`Shipping_Province_Name_New__c`).

Much of Auto-EDA is an **orchestrator + narrative over existing endpoints** (`/profile`, `/describe`, `/correlation`, quality, the `interpretStats` `{numbers, insights, actions}` pattern); Merge is mostly net-new.

---

## Design decisions (from clarification — 15 dropdown answers)

| # | Area | Decision |
|---|------|----------|
| 1 | Merge · header match | **Auto exact-match (normalized) + optional manual alias/map panel** for near-matching columns. |
| 2 | Merge · "common field" | **Strict intersection** — a field is common only if present in **all** staged files (with an optional "present in ≥ N% of files" toggle). |
| 3 | Merge · output | **Becomes the active ML Studio dataset _and_ downloadable** (CSV/XLSX). |
| 4 | Merge · cleaning v1 | **Basic** — union + dedup by key + drop null-key rows + trim whitespace + one optional phone-normalize preset. |
| 5 | Merge · file types | **CSV + XLSX**, with per-file **sheet picker** when a workbook has multiple sheets (default first sheet). |
| 6 | EDA · trigger | **One "Generate EDA" button** on the active dataset → one scrollable report. |
| 7 | EDA · layout | **Mirror the `EDA Analysis` sheet** section order. |
| 8 | EDA · cluster | **Group-by a chosen categorical (rule-based segments) + a 2-variable scatter.** No KMeans in v1. |
| 9 | EDA · insights | **AI-first (`_call_ai_ml`) with a deterministic rule-based fallback**, ≤5 insights. |
| 10 | EDA · export | **On-screen + "Copy as Markdown" + reuse existing per-chart PNG/CSV.** No PDF in v1. |
| 11 | EDA · skew | **Auto** — detect skew, prefer median, log-transform skewed metrics before correlation (with a note). |
| 12 | Build order | **Merge first → Auto-EDA.** |
| 13 | Spec/plan | **One combined spec (two parts) → one implementation plan.** |
| 14 | Language | **Vietnamese** UI labels + generated insights. |
| 15 | Delivery | **Worktree → build + pytest → FF-merge into MAIN. Never push.** |

---

## Part 1 — Multi-file Merge

### Surface & flow

A new tab **"Gộp file"** in `MlResultTabs`. Unlike the other tabs it is reachable **with no active dataset** (it is an entry point that *produces* one). Flow:

1. **Drop zone** — drag/drop or pick N files (`.csv`/`.xlsx`). Each upload calls `stage` and appends to the current merge session.
2. **Staged-files list** — per file: name · rows · column count · **sheet picker** (only when the workbook has >1 sheet) · remove button.
3. **Common-field chips** — chips built from the staged schemas. Each chip: canonical field name · `có ở X/N file` · null%. **Common fields (intersection) are pre-checked.** A toggle "Field có ở ≥ [80]% file" relaxes the set. Non-common fields appear unchecked/dimmed.
4. **Alias/map panel** (optional, collapsed) — for headers that *mean* the same thing but differ in text (the notebook's case), map several source columns → one canonical name. Mapped groups then behave as one field/chip.
5. **Options** — `Cột khử trùng lặp (key) ▾` (none default) · ☐ `Bỏ dòng trống ở key` · ☑ `Cắt khoảng trắng` · `Chuẩn hóa SĐT cho cột ▾` (multi-select, off default).
6. **Nút "Gộp"** → calls `run`.
7. **Summary panel** (the notebook's payoff) — `Tổng dòng thô · Hợp lệ · Null · Trùng đã bỏ · Distinct · Đủ field`.
8. **Output actions** — **"Dùng làm dataset"** (set active → switch to Table/Auto-EDA) + **"Tải CSV" / "Tải XLSX"**.

### Backend — merge session

A merge session stages each uploaded file as parquet under `data/merge_sessions/{session_id}/` so files are parsed **once** (no re-upload at run time). Sessions older than N hours are swept on access.

**Name normalization** (`backend/analytics/merge.py`, pure + unit-tested):
```python
def normalize_field(name: str) -> str:
    # strip, collapse internal whitespace, casefold, strip a trailing ':'.
    # 'Số điện thoại liên hệ:' -> 'số điện thoại liên hệ'
```
Two columns are "the same field" when `normalize_field` is equal. `common_fields` = intersection of normalized names across **all** staged files; `all_fields` = union, each with `present_in` count and aggregate null%.

```python
def common_fields(schemas: list[list[str]], threshold: float = 1.0) -> list[FieldInfo]:
    # threshold=1.0 → strict intersection; <1.0 → present_in/N >= threshold.
def align_and_merge(frames, selected, alias_map, options) -> tuple[pl.DataFrame, MergeSummary]:
    # per frame: apply alias_map (rename source->canonical), keep `selected`,
    # add missing selected cols as null; vertical concat (how="diagonal_relaxed");
    # trim string cols; phone-normalize chosen cols; optional drop-null-key;
    # optional dedup by key (keep="first"); compute summary.
def clean_phone(v: str | None) -> str | None:
    # re.sub(r'\D','',v); len>=9 -> '0'+last9 else None  (generalized from the notebook)
```

`MergeSummary` mirrors the notebook: `total_raw, valid, nulls, duplicates_removed, distinct, complete_records` (`complete_records` = rows with all selected fields non-null).

**Endpoints (`routers/ml.py`):**

| Method | Path | Body / params | Returns |
|--------|------|---------------|---------|
| `POST` | `/api/ml/merge/stage` | multipart: 1+ files, optional `session_id`, optional `sheet` per file | `{session_id, files:[{name, sheets:[...], chosen_sheet, rows, columns:[{name, normalized, dtype, null_pct}]}], common_fields:[FieldInfo], all_fields:[FieldInfo]}` |
| `POST` | `/api/ml/merge/run` | `{session_id, selected_fields:[str], alias_map:{src→canonical}, options:{dedup_key?, drop_null_key, trim, phone_cols:[]}, output:{as_dataset, download_fmt?}}` | `{summary: MergeSummary, dataset: DatasetInfo}` (registered) |
| `DELETE` | `/api/ml/merge/{session_id}` | — | 204 (cleanup staged files) |
| `GET` | `/api/ml/{file_id}/download` | `?fmt=csv\|xlsx` | streamed file (generic, reused by the download buttons) |

`stage` lists sheet names cheaply from workbook metadata (the Excel engine polars already uses); a different sheet is selected by re-staging that file with `sheet=` (a re-stage **replaces** the entry with the same filename rather than appending a duplicate). `run` writes the merged frame as `UPLOADS_DIR/{file_id}_merged.parquet`, inserts the `uploaded_files` row (same mechanism as `/upload`), and returns a standard `DatasetInfo` so **every existing tab + Auto-EDA work on it unchanged**.

**Small supporting change:** extend `_read_source` to also read `.parquet` (`if suffix == ".parquet": return pl.read_parquet(p)`) so a merged parquet is a first-class source (preserves dtypes; today `_read_source` only handles xlsx/xls/csv). Low-risk, benefits the whole app.

### Frontend

- `components/ml/MlMergeView.tsx` — orchestrates the flow above. Sub-components: `MlMergeDropzone.tsx`, `MlMergeChips.tsx` (chip list + ≥N% toggle + alias panel), `MlMergeSummary.tsx`.
- `api/ml.ts` — `stageMergeFiles(files, sessionId?, sheets?)`, `runMerge(payload)`, `deleteMergeSession(id)`, `downloadDataset(fileId, fmt)`. New types in `types.ts`: `MergeFieldInfo`, `MergeStageResult`, `MergeSummary`, `MergeRunResult`.
- Session lifetime kept in `mlStudioStore` (so navigating away/back doesn't lose staged files); `reset` clears it and calls `deleteMergeSession`.

### Error handling (Merge)

- No common fields across files → empty pre-checked set + inline hint: *"Không có field chung — hãy dùng 'Map cột' để gộp các cột cùng ý nghĩa."*
- A file fails to parse → that file shows an error row and is excluded; others proceed.
- `run` with 0 selected fields → 400 with a clear message.
- Dedup key not in selected fields → 400.
- Session missing/expired → 404 with "phiên đã hết hạn, hãy nạp lại file".

---

## Part 2 — Auto-EDA

### Surface & flow

A new tab **"Auto-EDA"** (requires an active dataset, gated like the other analysis tabs). A **"Tạo báo cáo EDA"** button runs one request and renders a single scrollable report mirroring the `EDA Analysis` sheet:

1. **Header** — dataset name · `rows × cols` · generated timestamp · (note when sampled).
2. **Profile số** — per numeric column: count · nulls · min · max · mean · median · std · **P25 / P75 / P95** · skew flag.
3. **Breakdown theo nhóm** — for the chosen segment column (auto-picked, overridable): group-by → count + avg of key metrics (the example's Product Type table).
4. **Correlation** — numeric columns; **auto log-transform** skewed positive metrics (`log1p`) before Pearson → matrix + ranked pairs; render with the existing `CorrelationHeatmap`; note which columns were log-transformed.
5. **Distribution** — histogram bins for the top numeric columns + **Top-N** values for the main dimension (top 10 products).
6. **Segment / Cluster** — group-by the segment column → per-segment table (count + avg metrics) + a **2-variable scatter** (sampled ≤2000 points, colored by segment).
7. **KEY INSIGHTS** — ≤5 cards, each **[Finding: số + delta] → [So what] → [Action]**.
8. **Cờ chất lượng dữ liệu** — null% per column, ~100%-null columns, all-unique/id columns, high-skew columns, constant columns.

### Backend — one orchestrator endpoint

`POST /api/ml/{file_id}/eda` with body `{segment_col?: str, metric_cols?: [str], top_n: int = 10, max_insights: int = 5, log_transform: "auto"|"on"|"off" = "auto", sample_n: int = 0}`.

Compute (reusing existing helpers — `_load_df`, `_infer_role`, `_numeric_cols`, `_is_date_id_column`, the `/correlation` logic, `_call_ai_ml`):

1. **Classify columns** via `_infer_role`: `metric`→profile+distribution; `dimension` (low-cardinality)→breakdown; `id`/all-unique & `null_pct≈100`→**flag & skip** from analysis. Auto-pick `segment_col` = the lowest-cardinality dimension (≥2, ≤ ~30 distinct) unless supplied; `metric_cols` = numeric non-id/non-flag.
2. **Profile** (exact, full data): polars `min/max/mean/median/std` + `quantile(.25/.75/.95)`. Skew flag = `mean/median ≥ 2` (or `< 0.5`) on positive metrics.
3. **Breakdown**: `group_by(segment_col).agg(count, mean(metric)…)`, sorted by count.
4. **Correlation**: build numeric matrix; if `log_transform` resolves on (auto + skewed + strictly positive), apply `log1p`; compute pairwise-complete Pearson (same null-safe path as `/correlation`, `excluded_columns` for constants); list `log_cols`.
5. **Distributions**: fixed-width or quantile bins per metric (default: up to 4 numeric metrics) → `{bucket_label, count, pct}`; Top-N for the main dimension.
6. **Segments**: the breakdown table + a scatter sample — two numeric axes (default the two highest-|corr| metrics), ≤2000 rows sampled (stratified by segment), each point `{x, y, segment}`.
7. **Quality flags**: reuse the quality checks (null/constant/dtype) + add all-unique and ~100%-null callouts.
8. **Insights**: assemble a compact stats digest (shape, strongest correlations, skewed metrics, dominant segment shares, top products, null flags) → prompt `_call_ai_ml` for ≤`max_insights` Vietnamese items as JSON `[{finding, so_what, action}]`; parse. On any AI failure/unparseable output, **fall back** to deterministic rules over the same digest (skew, top correlation, dominant category, retention/share, null). Return `insights_source: "ai"|"rule"`.

**Sampling:** all aggregates (profile, breakdown, correlation, histogram, quality) are computed on the **full** dataset (polars handles 418k easily); only the **scatter** is sampled (≤2000 pts) to bound payload. `sample_n>0` caps the whole compute for very large inputs (echoed in the header note).

Response shape:
```json
{
  "meta": { "filename": "...", "rows": 418311, "cols": 20, "sampled": false, "segment_col": "Product_Type__c", "generated_at": "..." },
  "profile": [ { "col": "Quantity__c", "count": 418311, "nulls": 0, "min": 1, "max": 23040, "mean": 68.9, "median": 4, "std": ..., "p25": ..., "p75": ..., "p95": ..., "skewed": true } ],
  "breakdown": { "by": "Product_Type__c", "rows": [ { "group": "SBPS", "count": 1234, "avg_Quantity__c": ..., "avg_Sales_Price__c": ... } ] },
  "correlation": { "columns": [...], "matrix": [[1.0, -0.894, null], ...], "log_cols": ["Quantity__c","Sales_Price__c"], "excluded_columns": [...] },
  "distributions": [ { "col": "Quantity__c", "bins": [ { "label": "1-5", "count": ..., "pct": ... } ] } ],
  "top_values": { "col": "Product_Name__c", "rows": [ { "value": "...", "count": ..., "pct": ... } ] },
  "segments": { "table": [...], "scatter": { "x": "Quantity__c", "y": "Sales_Price__c", "points": [ { "x":..., "y":..., "segment":"SBPS" } ] } },
  "quality": [ { "type": "null", "column": "Shipping_Province_Name_New__c", "detail": "100% null" } ],
  "insights": [ { "finding": "...", "so_what": "...", "action": "..." } ],
  "insights_source": "ai"
}
```

All floats scrub `NaN/±Inf` → `null` before serialization (same rule as the rest of `ml.py`).

### Frontend

- `components/ml/MlEdaView.tsx` — "Tạo báo cáo EDA" button + controls (`Cột phân nhóm ▾`, `Số insight ▾`, "Tạo lại") → renders sections top-to-bottom. Sub-components: `MlEdaProfile.tsx`, `MlEdaDistribution.tsx` (recharts bar), `MlEdaSegments.tsx` (recharts scatter + table), `MlEdaInsights.tsx` (Finding→So-what→Action cards reusing the stats-interpret card style). Correlation reuses the existing `CorrelationHeatmap`.
- **"Copy as Markdown"** — `components/ml/edaMarkdown.ts` serializes the report JSON to Markdown (tables + insight bullets) for pasting into Obsidian/Notion. Per-chart PNG/CSV reuse the shipped `chartExport.ts`.
- `api/ml.ts` — `runEda(fileId, opts)`; types in `types.ts`: `EdaReport` and section types.

### Error handling (EDA)

- Dataset not found → 404. No numeric columns → omit numeric/correlation sections with a note. No suitable dimension → skip breakdown/segments. AI down → rule-based insights + a one-line note. Empty/all-null dataset → friendly message instead of a crash.

---

## Shared changes

- `stores/mlStudioStore.ts` — extend `MlTab` with `'merge' | 'eda'`; add merge-session state.
- `components/ml/MlResultTabs.tsx` — extend the `Tab` union + `TABS` array (icons: `Combine`/`Layers` for merge, `FileSearch`/`Sparkles` for EDA, lucide-react). `merge` renders without an active dataset; `eda` gated on one. `EmptyStudio` onboarding mentions both.
- `api/ml.ts` / `types.ts` — new clients + types listed above.

---

## API contracts summary

| Method | Path | Status |
|--------|------|--------|
| `POST` | `/api/ml/merge/stage` | **new** |
| `POST` | `/api/ml/merge/run` | **new** |
| `DELETE` | `/api/ml/merge/{session_id}` | **new** |
| `GET` | `/api/ml/{file_id}/download` | **new** (csv/xlsx) |
| `POST` | `/api/ml/{file_id}/eda` | **new** |
| — | `_read_source` | **extend** (read `.parquet`) |

---

## Testing (TDD — write failing tests first; `backend/tests/`, `uv run pytest -q`)

**Merge (`analytics/merge.py` + endpoints):**
- `normalize_field` — trims/casefolds/strips trailing `:` (the survey-header case).
- `common_fields` — 3 frames with differing columns → strict intersection correct; `present_in` counts correct; `threshold=0.8` relaxes as expected.
- `align_and_merge` — missing columns filled null; `diagonal_relaxed` concat row count = Σ rows; trim applied; `clean_phone` (`'+84 912.345.678' → '0912345678'`, junk → null); dedup keeps first; drop-null-key drops; `MergeSummary` fields match a known fixture (replicating the notebook's 8 metrics on a small set).
- `run` — registers a `DatasetInfo`; the new `file_id` loads via `_load_df`; `/download?fmt=csv` returns rows.

**Auto-EDA (`/eda`):**
- Synthetic skewed df → profile percentiles correct; `skewed` flag set; correlation includes `log_cols`; a constant column appears in `excluded_columns`; a 100%-null column flagged in `quality`; breakdown counts correct; `insights` non-empty with `insights_source:"rule"` when AI is unavailable (force no `ANTHROPIC_API_KEY`/no Ollama).
- `_read_source` reads a written `.parquet` round-trip.

**Frontend:** `npm run build` (`tsc -b && vite build`) stays green — `noUnusedLocals/Parameters` are on, so no stray imports. No frontend test runner; manual smoke per tab.

---

## Delivery & validation

- Work on the worktree branch; verify **build green + backend pytest** (the 8 pre-existing `test_sql_sandbox.py` failures from the missing `data/vina_brew` fixture are unrelated and expected — see memory), then **FF-merge into the MAIN tree** `D:\…\leonie` (branch `master`). **Never push** (secrets in history).
- Build order: **Part 1 (Merge) → Part 2 (Auto-EDA)**, each: tests green + build green before commit. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Restart backend after changes (uvicorn `--reload` picks up router edits; restart fully if `.env`/startup touched).

---

## File change summary

| File | Change |
|------|--------|
| `backend/analytics/merge.py` | **new** — `normalize_field`, `common_fields`, `align_and_merge`, `clean_phone`, `MergeSummary` |
| `backend/routers/ml.py` | add `/merge/stage`, `/merge/run`, `DELETE /merge/{sid}`, `/{file_id}/download`, `/{file_id}/eda`; extend `_read_source` (parquet) |
| `backend/tests/test_merge.py`, `test_eda.py` | **new** — failing-first tests above |
| `frontend/src/components/ml/MlMergeView.tsx` (+ `MlMergeDropzone`, `MlMergeChips`, `MlMergeSummary`) | **new** — merge surface |
| `frontend/src/components/ml/MlEdaView.tsx` (+ `MlEdaProfile`, `MlEdaDistribution`, `MlEdaSegments`, `MlEdaInsights`) | **new** — EDA report |
| `frontend/src/components/ml/edaMarkdown.ts` | **new** — report → Markdown |
| `frontend/src/components/ml/MlResultTabs.tsx` | add `merge`/`eda` tabs + onboarding |
| `frontend/src/stores/mlStudioStore.ts` | extend `MlTab`; merge-session state |
| `frontend/src/api/ml.ts`, `types.ts` | merge + eda clients and types |

---

## Non-goals (v1)

- KMeans / scikit clustering (group-by segments only); no new heavy Python deps.
- PDF export (Markdown + per-chart PNG/CSV only).
- "Show Code" panels for Merge/EDA — easy follow-up via the existing `analytics/codegen.py`, but out of scope for v1.
- Horizontal key-joins between files (vertical UNION only).
- Saving EDA report history / scheduling.
- Anomaly History Log + Action-Plan linking (tracked separately as pending ML features).
- i18n / VN-EN toggle (Vietnamese only).
