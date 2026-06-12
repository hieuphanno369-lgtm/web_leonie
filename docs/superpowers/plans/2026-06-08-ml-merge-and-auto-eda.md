# ML Studio: Multi-file Merge + Auto-EDA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two features to ML Studio — (1) a multi-file **Merge** tool that detects common fields across uploaded files and unions/cleans/dedupes them into a new dataset, and (2) an **Auto-EDA** module that profiles a dataset, draws correlation/distribution/segment charts, and emits Finding→So-what→Action insights.

**Architecture:** Backend gets two pure, unit-tested modules — `backend/analytics/merge.py` and `backend/analytics/eda.py` — plus thin FastAPI endpoints in `backend/routers/ml.py` that compose them. Merge stages each uploaded file as a parquet under `data/merge_sessions/{session_id}/`, then `run` unions selected fields and registers the result as a normal ML dataset (reusing the existing `uploaded_files` + `UPLOADS_DIR` registration). Auto-EDA aggregates exactly over the full dataset (only the scatter is sampled) and falls back to rule-based insights when the AI helper is unavailable. Frontend adds two new tabs to the existing `MlResultTabs`, reusing `CorrelationHeatmap` and the AI-card styling already in the app.

**Tech Stack:** Backend — FastAPI, polars, numpy, scipy (already deps), pytest. Frontend — React 19, TypeScript ~5.7, recharts, lucide-react, Zustand. No frontend test runner (build gate = `tsc -b && vite build`).

**Source spec:** `docs/superpowers/specs/2026-06-08-ml-merge-and-auto-eda-design.md`

**Delivery constraints (PRESERVE):**
- Build Part 1 (Merge) fully, then Part 2 (Auto-EDA).
- Backend = strict TDD (pytest). Frontend = build-gated (`npm run build`), no unit tests.
- Deliver to the MAIN working tree (`D:\assitant_tools\tools_performance\08_Projects\leonie`); the user runs MAIN, not this worktree.
- **NEVER push** — master history contains real secrets. Local commits + local FF-merge only.
- Do not edit `_legacy/`. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Commit via the **Bash** tool with multiple `-m` flags (avoid `"` in PowerShell here-strings).

---

## File Structure

**Backend — create:**
- `backend/analytics/merge.py` — pure functions: `normalize_field`, `clean_phone`, `common_fields`, `align_and_merge`, `MergeSummary`.
- `backend/analytics/eda.py` — pure functions: `infer_role`, `profile_columns`, `correlation_matrix`, `numeric_distributions`, `segment_breakdown`, `derive_rule_insights`.
- `backend/tests/test_merge.py` — unit tests for `merge.py` + endpoint tests for `/merge/*` and `/{file_id}/download`.
- `backend/tests/test_ml_eda.py` — unit tests for `eda.py` + endpoint test for `/{file_id}/eda`. **(Named `test_ml_eda.py`, NOT `test_eda.py` — that name is taken by the EdaTracker work module.)**

**Backend — modify:**
- `backend/routers/ml.py` — add `Form` import + `MERGE_SESSIONS_DIR`; extend `_read_source` for `.parquet`; add merge models + endpoints (`/merge/stage`, `/merge/run`, `/merge/{session_id}`), download endpoint (`/{file_id}/download`), and EDA models + endpoint (`/{file_id}/eda`).

**Frontend — create:**
- `frontend/src/components/ml/MlMergeView.tsx` — Merge tab container (multi-file upload → field chips → options → run → summary).
- `frontend/src/components/ml/MlMergeDropzone.tsx` — multi-file dropzone (mirrors `MlUpload`).
- `frontend/src/components/ml/MlMergeChips.tsx` — common/all field chips with select toggles + role hints.
- `frontend/src/components/ml/MlMergeSummary.tsx` — result metric cards + Download buttons.
- `frontend/src/components/ml/MlEdaView.tsx` — Auto-EDA tab container (Generate → profile + charts + insights).
- `frontend/src/components/ml/MlEdaProfile.tsx` — per-column profile table.
- `frontend/src/components/ml/MlEdaDistribution.tsx` — recharts histogram(s) with skew/log note.
- `frontend/src/components/ml/MlEdaSegments.tsx` — segment table + recharts scatter.
- `frontend/src/components/ml/MlEdaInsights.tsx` — Finding→So-what→Action cards + Copy Markdown.
- `frontend/src/components/ml/edaMarkdown.ts` — pure helper turning an `EdaReport` into Markdown text.

**Frontend — modify:**
- `frontend/src/types.ts` — add Merge + EDA types (after the ML Studio section, ~line 266).
- `frontend/src/api/ml.ts` — add `stageMerge`, `runMerge`, `deleteMergeSession`, `downloadDataset`, `runEda`.
- `frontend/src/stores/mlStudioStore.ts` — extend `MlTab` union with `'merge' | 'eda'`.
- `frontend/src/components/ml/MlResultTabs.tsx` — add Merge + EDA to `Tab`/`TABS`; rework the `if (!dataset)` short-circuit so Merge renders with no active dataset.
- `frontend/src/pages/analytics/MlStudio.tsx` — pass an `onDatasetCreated` handler to wire Merge output into the Studio.

---

## Conventions used throughout

- Backend router prefix is `/ml`, mounted under `/api` in `main.py`. So endpoint decorators use `/merge/stage` etc.; tests hit `/api/ml/merge/stage`.
- Tests use the existing harness: `client = TestClient(app)` + `conftest.py`'s autouse `fresh_db` (temp SQLite per test). Upload via `POST /api/ml/upload` with `files={"file": (name, io.BytesIO(bytes), mime)}`.
- Run backend tests from `backend/`: `uv run pytest -q`. **Pre-existing unrelated failure:** 8 `test_sql_sandbox.py` tests fail in fresh worktrees (missing `data/vina_brew` CSVs). That is NOT a regression — expect `8 failed, N passed`. All NEW tests in this plan must pass.
- Frontend: `noUnusedLocals`/`noUnusedParameters` are ON — never leave an unused import/var or the build fails.

---
---

# PART 1 — MULTI-FILE MERGE

---

### Task 1: `merge.py` — `normalize_field` + `clean_phone`

**Files:**
- Create: `backend/analytics/merge.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_merge.py`:

```python
from analytics.merge import normalize_field, clean_phone


def test_normalize_field_strips_case_space_colon():
    assert normalize_field("  Số điện thoại liên hệ:  ") == "số điện thoại liên hệ"
    assert normalize_field("Phone") == "phone"
    assert normalize_field("PHONE ") == "phone"
    assert normalize_field("first   name") == "first name"


def test_normalize_field_handles_non_str():
    assert normalize_field(123) == "123"


def test_clean_phone_normalizes_vn():
    assert clean_phone("0987.654.321") == "0987654321"
    assert clean_phone("84987654321") == "0987654321"
    assert clean_phone("(+84) 987 654 321") == "0987654321"


def test_clean_phone_rejects_short_or_empty():
    assert clean_phone("12345") is None
    assert clean_phone("") is None
    assert clean_phone(None) is None
    assert clean_phone("abc") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_merge.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'analytics.merge'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/analytics/merge.py`:

```python
"""Pure helpers for the ML Studio multi-file Merge feature.

No FastAPI/DB imports here — keep this unit-testable with plain polars.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import polars as pl


def normalize_field(name) -> str:
    """Canonical key for matching a field name across files.

    Lowercase (casefold), collapse internal whitespace, strip a trailing colon.
    """
    s = str(name).strip().casefold()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(":").strip()
    return s


def clean_phone(v) -> str | None:
    """VN phone normalize: keep digits, take last 9, prefix '0'.

    Returns None when fewer than 9 digits remain (treated as invalid/null).
    """
    if v is None:
        return None
    digits = re.sub(r"\D", "", str(v))
    if len(digits) >= 9:
        return "0" + digits[-9:]
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_merge.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): normalize_field + clean_phone helpers" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `merge.py` — `common_fields`

**Files:**
- Modify: `backend/analytics/merge.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_merge.py`:

```python
from analytics.merge import common_fields


def test_common_fields_intersection_default():
    schemas = [
        ["Phone", "Name", "Age"],
        ["phone ", "name", "Product"],
        ["PHONE", "Branch"],
    ]
    # Only the normalized field present in ALL three is "phone"
    # (Name is in 2/3, Age/Product/Branch in 1/3 — all excluded by strict intersection).
    assert common_fields(schemas) == ["Phone"]


def test_common_fields_preserves_first_display_name_and_order():
    schemas = [
        ["Email:", "Phone"],
        ["email", "phone"],
    ]
    assert common_fields(schemas) == ["Email:", "Phone"]


def test_common_fields_threshold_below_one():
    schemas = [
        ["a", "b"],
        ["a", "c"],
        ["a", "b"],
    ]
    # threshold 0.5 -> present in >= 1.5 schemas: a(3), b(2) qualify; c(1) does not.
    assert common_fields(schemas, threshold=0.5) == ["a", "b"]


def test_common_fields_empty():
    assert common_fields([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_merge.py -k common_fields -q`
Expected: FAIL — `ImportError: cannot import name 'common_fields'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/analytics/merge.py`:

```python
def common_fields(schemas: list[list[str]], threshold: float = 1.0) -> list[str]:
    """Fields present in >= `threshold` fraction of schemas (by normalized name).

    threshold=1.0 -> strict intersection (present in every file).
    Returns the first-seen DISPLAY name for each qualifying field, in first-seen order.
    """
    if not schemas:
        return []
    n = len(schemas)
    counts: dict[str, int] = {}
    display: dict[str, str] = {}
    order: list[str] = []
    for schema in schemas:
        seen: set[str] = set()
        for col in schema:
            key = normalize_field(col)
            if key in seen:
                continue
            seen.add(key)
            if key not in counts:
                counts[key] = 0
                display[key] = col
                order.append(key)
            counts[key] += 1
    need = threshold * n - 1e-9
    return [display[k] for k in order if counts[k] >= need]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_merge.py -q`
Expected: PASS (10 tests total).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): common_fields intersection detector" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `merge.py` — `align_and_merge` + `MergeSummary`

**Files:**
- Modify: `backend/analytics/merge.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_merge.py`:

```python
import polars as pl
from analytics.merge import align_and_merge, MergeSummary


def test_align_and_merge_unions_and_aligns_by_normalized_name():
    f1 = pl.DataFrame({"Phone": ["0987654321"], "Name": ["A"]})
    f2 = pl.DataFrame({"phone ": ["0912345678"], "Product": ["X"]})
    merged, summary = align_and_merge(
        [f1, f2], selected=["Phone", "Name", "Product"], alias_map={},
    )
    assert merged.columns == ["Phone", "Name", "Product"]
    assert merged.height == 2
    # f2 had no Name -> null; f1 had no Product -> null
    assert merged["Name"].to_list() == ["A", None]
    assert merged["Product"].to_list() == [None, "X"]
    assert summary.total_raw == 2


def test_align_and_merge_dedup_and_phone_clean():
    f1 = pl.DataFrame({"phone": ["0987.654.321", "0987654321", None],
                       "name": ["A", "B", "C"]})
    f2 = pl.DataFrame({"phone": ["84987654321"], "name": ["D"]})
    merged, summary = align_and_merge(
        [f1, f2],
        selected=["phone", "name"],
        alias_map={},
        dedup_key="phone",
        drop_null_key=True,
        phone_cols=["phone"],
    )
    # All non-null phones normalize to 0987654321 -> 1 distinct, nulls dropped.
    assert summary.total_raw == 4
    assert summary.nulls == 1
    assert summary.valid == 3
    assert summary.distinct == 1
    assert summary.duplicates_removed == 2
    assert merged.height == 1
    assert merged["phone"].to_list() == ["0987654321"]


def test_align_and_merge_complete_records():
    f1 = pl.DataFrame({"phone": ["0987654321", "0912345678"],
                       "name": ["A", None], "age": ["5", "6"]})
    merged, summary = align_and_merge(
        [f1], selected=["phone", "name", "age"], alias_map={},
        dedup_key="phone", phone_cols=["phone"],
    )
    # complete = all non-key fields (name, age) non-null -> only the first row.
    assert summary.complete_records == 1
    assert isinstance(summary, MergeSummary)


def test_align_and_merge_keeps_null_keys_when_not_dropping():
    f1 = pl.DataFrame({"phone": ["0987654321", None], "name": ["A", "B"]})
    merged, summary = align_and_merge(
        [f1], selected=["phone", "name"], alias_map={},
        dedup_key="phone", drop_null_key=False, phone_cols=["phone"],
    )
    # 1 distinct valid + 1 null row kept = 2 rows out.
    assert merged.height == 2
    assert summary.nulls == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_merge.py -k align_and_merge -q`
Expected: FAIL — `ImportError: cannot import name 'align_and_merge'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/analytics/merge.py`:

```python
@dataclass
class MergeSummary:
    total_raw: int          # rows after union, before dedup/drop
    valid: int              # rows with a non-null dedup key (== total_raw when no key)
    nulls: int              # total_raw - valid
    duplicates_removed: int # valid - distinct (true dup keys removed)
    distinct: int           # unique dedup-key count among valid
    complete_records: int   # final rows with every non-key selected field non-null


def align_and_merge(
    frames: list[pl.DataFrame],
    selected: list[str],
    alias_map: dict[str, str] | None = None,
    *,
    dedup_key: str | None = None,
    drop_null_key: bool = False,
    trim: bool = True,
    phone_cols: list[str] | None = None,
) -> tuple[pl.DataFrame, MergeSummary]:
    """Union frames on `selected` canonical fields, clean, optionally dedup.

    - alias_map: explicit raw-column-name -> canonical mapping (user overrides).
    - Auto-aligns any column whose normalized name matches a selected field.
    - All values are cast to Utf8 (the merge use-case is messy text/contact data;
      this guarantees diagonal concat + trim + phone-clean never fail on dtype).
    """
    alias_map = alias_map or {}
    phone_cols = phone_cols or []
    sel_norm = {normalize_field(s): s for s in selected}

    aligned: list[pl.DataFrame] = []
    for df in frames:
        rename: dict[str, str] = {}
        used: set[str] = set()
        for c in df.columns:
            tgt = alias_map.get(c) or sel_norm.get(normalize_field(c))
            if tgt and tgt not in used:
                rename[c] = tgt
                used.add(tgt)
        d = df.rename(rename) if rename else df
        keep = [c for c in selected if c in d.columns]
        d = d.select(keep)
        for c in selected:
            if c not in d.columns:
                d = d.with_columns(pl.lit(None).alias(c))
        d = d.select(selected)
        d = d.with_columns([pl.col(c).cast(pl.Utf8, strict=False) for c in selected])
        aligned.append(d)

    merged = pl.concat(aligned, how="diagonal_relaxed") if aligned else pl.DataFrame()
    total_raw = merged.height

    if trim and merged.width:
        merged = merged.with_columns([pl.col(c).str.strip_chars() for c in merged.columns])
        merged = merged.with_columns([
            pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c)).alias(c)
            for c in merged.columns
        ])

    for c in phone_cols:
        if c in merged.columns:
            merged = merged.with_columns(
                pl.col(c).map_elements(clean_phone, return_dtype=pl.Utf8).alias(c)
            )

    if dedup_key and dedup_key in merged.columns:
        valid_mask = merged[dedup_key].is_not_null()
        valid = int(valid_mask.sum())
        nulls = total_raw - valid
        valid_df = merged.filter(valid_mask)
        distinct = int(valid_df[dedup_key].n_unique())
        duplicates_removed = valid - distinct
        final = valid_df.unique(subset=[dedup_key], keep="first", maintain_order=True)
        if not drop_null_key:
            final = pl.concat([final, merged.filter(~valid_mask)], how="diagonal_relaxed")
    else:
        valid, nulls, distinct, duplicates_removed = total_raw, 0, total_raw, 0
        final = merged

    other_cols = [c for c in selected if c != dedup_key]
    if other_cols and final.height:
        mask = pl.all_horizontal([pl.col(c).is_not_null() for c in other_cols])
        complete_records = int(final.select(mask.alias("_c"))["_c"].sum())
    else:
        complete_records = final.height

    summary = MergeSummary(
        total_raw=total_raw, valid=valid, nulls=nulls,
        duplicates_removed=duplicates_removed, distinct=distinct,
        complete_records=complete_records,
    )
    return final, summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_merge.py -q`
Expected: PASS (14 tests total).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/merge.py backend/tests/test_merge.py
git commit -m "feat(merge): align_and_merge union/clean/dedup + MergeSummary" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Extend `_read_source` to read `.parquet`

**Files:**
- Modify: `backend/routers/ml.py` (the `_read_source` helper, ~line 136)
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_merge.py`:

```python
def test_read_source_reads_parquet(tmp_path):
    from routers.ml import _read_source
    p = tmp_path / "x.parquet"
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_parquet(p)
    df = _read_source(str(p))
    assert df.columns == ["a", "b"]
    assert df.height == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k read_source -q`
Expected: FAIL — `_read_source` raises/falls through to CSV reader on a `.parquet` path.

- [ ] **Step 3: Add the parquet branch**

In `backend/routers/ml.py`, find `_read_source` (it currently handles `.xlsx/.xls` then defaults to CSV). Add a parquet branch BEFORE the excel check:

```python
def _read_source(filepath: str) -> pl.DataFrame:
    p = pathlib.Path(filepath)
    if p.suffix.lower() == ".parquet":
        return pl.read_parquet(p)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pl.read_excel(p)
    return pl.read_csv(p, infer_schema_length=10000)
```

(Match the existing body — only the two `if` lines for parquet are new.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k read_source -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): read .parquet sources in _read_source" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `POST /merge/stage` endpoint

**Files:**
- Modify: `backend/routers/ml.py` (imports + new models + endpoint)
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_merge.py`:

```python
import io
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


CSV_A = b"Phone,Name,Age\n0987654321,Alice,5\n0912345678,Bob,6\n"
CSV_B = b"phone,Name,Product\n0987654321,Alice,Milk\n0900000000,Carol,Juice\n"


def test_merge_stage_returns_common_fields(client):
    resp = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["session_id"]
    assert len(d["files"]) == 2
    assert d["files"][0]["filename"] == "a.csv"
    # "Phone"/"phone" and "Name" are common; "Age"/"Product" are not.
    assert set(normalize_field(f) for f in d["common_fields"]) == {"phone", "name"}
    assert "Age" in d["all_fields"] and "Product" in d["all_fields"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k stage -q`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Add imports, constant, models, and endpoint**

In `backend/routers/ml.py`:

1. Extend the FastAPI import (line 14) to include `Form`:

```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
```

2. Add `shutil` and `uuid` to the stdlib imports at the top (near `import os`):

```python
import shutil
import uuid
```

3. After `MAX_FILE_BYTES = 500 * 1024 * 1024` (~line 56), add:

```python
MERGE_SESSIONS_DIR = UPLOADS_DIR.parent / "merge_sessions"
MERGE_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
```

4. Add the merge import near the other analytics imports (top of file):

```python
from analytics.merge import common_fields, align_and_merge
```

5. Add models + endpoint. Place them AFTER the `upload_file` endpoint (after line 403) so the literal `/merge/*` routes register before the `/{file_id}` catch-alls:

```python
# ── Multi-file Merge ─────────────────────────────────────────────────────────

class MergeFileSchema(BaseModel):
    filename: str
    fields: list[str]


class MergeStageOut(BaseModel):
    session_id: str
    files: list[MergeFileSchema]
    common_fields: list[str]
    all_fields: list[str]


def _read_upload(content: bytes, filename: str, sheet: str | None) -> pl.DataFrame:
    suffix = pathlib.Path(filename).suffix.lower()
    bio = io.BytesIO(content)
    if suffix in (".xlsx", ".xls"):
        return pl.read_excel(bio, sheet_name=sheet) if sheet else pl.read_excel(bio)
    return pl.read_csv(bio, infer_schema_length=10000)


@router.post("/merge/stage", response_model=MergeStageOut)
async def merge_stage(
    files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
    sheet: str | None = Form(None),
):
    if not files:
        raise HTTPException(400, "No files uploaded")
    sid = session_id or uuid.uuid4().hex[:12]
    sdir = MERGE_SESSIONS_DIR / sid
    sdir.mkdir(parents=True, exist_ok=True)

    manifest_path = sdir / "_session.json"
    manifest: list[dict] = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for f in files:
        content = await f.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(413, f"{f.filename} exceeds 500 MB limit")
        try:
            df = _read_upload(content, f.filename or "file", sheet)
        except Exception as e:
            raise HTTPException(422, f"Cannot parse {f.filename}: {e}")
        # Re-staging the same filename replaces the prior entry (no duplicates).
        manifest = [m for m in manifest if m["filename"] != f.filename]
        idx = len(manifest)
        pq = sdir / f"{idx}_{uuid.uuid4().hex[:6]}.parquet"
        df.write_parquet(pq)
        manifest.append({
            "filename": f.filename, "parquet": pq.name, "fields": list(df.columns),
        })

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    schemas = [m["fields"] for m in manifest]
    seen: list[str] = []
    for m in manifest:
        for c in m["fields"]:
            if c not in seen:
                seen.append(c)
    return MergeStageOut(
        session_id=sid,
        files=[MergeFileSchema(filename=m["filename"], fields=m["fields"]) for m in manifest],
        common_fields=common_fields(schemas),
        all_fields=seen,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k stage -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): POST /merge/stage detects common fields" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `POST /merge/run` endpoint

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_merge.py`:

```python
def test_merge_run_registers_dataset(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    ).json()
    resp = client.post("/api/ml/merge/run", json={
        "session_id": stage["session_id"],
        "selected_fields": ["Phone", "Name"],
        "alias_map": {},
        "options": {"dedup_key": "Phone", "drop_null_key": True,
                    "trim": True, "phone_cols": ["Phone"]},
    })
    assert resp.status_code == 200
    d = resp.json()
    # 4 rows total, phone 0987654321 duplicated across files -> 3 distinct.
    assert d["summary"]["total_raw"] == 4
    assert d["summary"]["distinct"] == 3
    assert d["summary"]["duplicates_removed"] == 1
    # Registered dataset is loadable.
    fid = d["dataset"]["file_id"]
    assert d["dataset"]["rows"] == 3
    q = client.post("/api/ml/query", json={
        "file_id": fid, "sql": "SELECT COUNT(*) AS n FROM data",
    })
    assert q.status_code == 200
    assert q.json()["rows"][0][0] == 3


def test_merge_run_unknown_session(client):
    resp = client.post("/api/ml/merge/run", json={
        "session_id": "nope", "selected_fields": ["a"],
    })
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k merge_run -q`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Add models + endpoint**

In `backend/routers/ml.py`, after the `merge_stage` endpoint, add:

```python
class MergeOptions(BaseModel):
    dedup_key: str | None = None
    drop_null_key: bool = False
    trim: bool = True
    phone_cols: list[str] = []


class MergeRunIn(BaseModel):
    session_id: str
    selected_fields: list[str]
    alias_map: dict[str, str] = {}
    options: MergeOptions = MergeOptions()


class MergeSummaryOut(BaseModel):
    total_raw: int
    valid: int
    nulls: int
    duplicates_removed: int
    distinct: int
    complete_records: int


class MergeRunOut(BaseModel):
    summary: MergeSummaryOut
    dataset: DatasetInfo


@router.post("/merge/run", response_model=MergeRunOut)
def merge_run(body: MergeRunIn):
    sdir = MERGE_SESSIONS_DIR / body.session_id
    manifest_path = sdir / "_session.json"
    if not manifest_path.exists():
        raise HTTPException(404, "Merge session not found")
    if not body.selected_fields:
        raise HTTPException(400, "No fields selected")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = [pl.read_parquet(sdir / m["parquet"]) for m in manifest]

    opts = body.options
    merged, summary = align_and_merge(
        frames, body.selected_fields, body.alias_map,
        dedup_key=opts.dedup_key, drop_null_key=opts.drop_null_key,
        trim=opts.trim, phone_cols=opts.phone_cols,
    )

    # Register as a normal ML dataset (mirror upload_file).
    out_name = "merged.parquet"
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO uploaded_files (filename, filepath, rows, cols) VALUES (?,?,0,0)",
        (out_name, ""),
    )
    file_id = conn.execute(
        "SELECT file_id FROM uploaded_files WHERE rowid=?", (cur.lastrowid,)
    ).fetchone()[0]
    dest = UPLOADS_DIR / f"{file_id}_{out_name}"
    merged.write_parquet(dest)
    rows, cols = merged.shape
    conn.execute(
        "UPDATE uploaded_files SET filepath=?, rows=?, cols=? WHERE file_id=?",
        (str(dest), rows, cols, file_id),
    )
    conn.commit()
    conn.close()

    cols_info = [ColumnInfo(name=c, dtype=str(merged[c].dtype)) for c in merged.columns]
    return MergeRunOut(
        summary=MergeSummaryOut(**summary.__dict__),
        dataset=DatasetInfo(file_id=file_id, filename=out_name,
                            rows=rows, cols=cols, columns=cols_info),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k merge_run -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): POST /merge/run unions + registers dataset" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `DELETE /merge/{session_id}` endpoint

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_merge.py`:

```python
def test_merge_delete_session(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("a.csv", io.BytesIO(CSV_A), "text/csv"))],
    ).json()
    sid = stage["session_id"]
    assert client.delete(f"/api/ml/merge/{sid}").status_code == 204
    # Running a deleted session is a 404.
    resp = client.post("/api/ml/merge/run", json={
        "session_id": sid, "selected_fields": ["Phone"],
    })
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k merge_delete -q`
Expected: FAIL — DELETE returns 405/404 (route not registered; note `DELETE /{file_id}` won't match a 2-segment path).

- [ ] **Step 3: Add endpoint**

In `backend/routers/ml.py`, after `merge_run`, add:

```python
@router.delete("/merge/{session_id}", status_code=204)
def merge_delete(session_id: str):
    sdir = MERGE_SESSIONS_DIR / session_id
    if sdir.exists():
        shutil.rmtree(sdir, ignore_errors=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k merge_delete -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): DELETE /merge/{session_id} cleanup" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `GET /{file_id}/download` endpoint (CSV + XLSX)

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_merge.py`:

```python
def test_download_csv_and_xlsx(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(CSV_A), "text/csv")},
    ).json()
    fid = up["file_id"]

    csv = client.get(f"/api/ml/{fid}/download?fmt=csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert b"Phone" in csv.content

    xlsx = client.get(f"/api/ml/{fid}/download?fmt=xlsx")
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert xlsx.content[:2] == b"PK"  # xlsx is a zip


def test_download_bad_fmt(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d2.csv", io.BytesIO(CSV_A), "text/csv")},
    ).json()
    assert client.get(f"/api/ml/{up['file_id']}/download?fmt=json").status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_merge.py -k download -q`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Add endpoint**

In `backend/routers/ml.py`, add near the other `/{file_id}/...` GET routes (e.g. after the `delete_dataset` endpoint, ~line 438):

```python
@router.get("/{file_id}/download")
def download_dataset(file_id: str, fmt: str = "csv"):
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(400, "fmt must be 'csv' or 'xlsx'")
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    stem = pathlib.Path(row["filename"]).stem
    if fmt == "csv":
        return Response(
            content=df.write_csv().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'},
        )
    bio = io.BytesIO()
    df.write_excel(bio)
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{stem}.xlsx"'},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_merge.py -k download -q`
Expected: PASS. (If `df.write_excel` raises about a missing engine, `xlsxwriter` is required — add it: `cd backend ; uv add xlsxwriter` then re-run. polars' `write_excel` uses xlsxwriter.)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_merge.py
git commit -m "feat(merge): GET /{file_id}/download csv|xlsx" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 6: Full backend regression**

Run: `cd backend ; uv run pytest -q`
Expected: All NEW merge tests pass; only the 8 pre-existing `test_sql_sandbox.py` failures remain (unrelated — missing vina_brew fixtures).

---

### Task 9: Frontend — Merge types + API client

**Files:**
- Modify: `frontend/src/types.ts` (after ML Studio section, ~line 266)
- Modify: `frontend/src/api/ml.ts`

- [ ] **Step 1: Add types**

In `frontend/src/types.ts`, after the `ProfileResult` interface (line 266), add:

```typescript
// ─── ML Merge ─────────────────────────────────────────────────────────────────

export interface MergeFileSchema {
  filename: string
  fields: string[]
}

export interface MergeStageResult {
  session_id: string
  files: MergeFileSchema[]
  common_fields: string[]
  all_fields: string[]
}

export interface MergeOptions {
  dedup_key: string | null
  drop_null_key: boolean
  trim: boolean
  phone_cols: string[]
}

export interface MergeSummary {
  total_raw: number
  valid: number
  nulls: number
  duplicates_removed: number
  distinct: number
  complete_records: number
}

export interface MergeRunResult {
  summary: MergeSummary
  dataset: DatasetInfo
}
```

- [ ] **Step 2: Add API client functions**

In `frontend/src/api/ml.ts`, EXTEND the existing top-of-file `import type { … } from '../types'` block (lines 2-6) to also include `MergeStageResult, MergeRunResult, MergeOptions`, then append the functions below. Use the default `client` (imported as `import client from './client'`, baseURL `/api`) and mirror the FormData pattern from `uploadFile` and the blob-download pattern from `downloadZScoreCsv`:

```typescript
export async function stageMerge(
  files: File[], sessionId?: string, sheet?: string,
): Promise<MergeStageResult> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  if (sessionId) form.append('session_id', sessionId)
  if (sheet) form.append('sheet', sheet)
  const { data } = await client.post<MergeStageResult>('/ml/merge/stage', form, {
    headers: { 'Content-Type': undefined }, timeout: 120_000,
  })
  return data
}

export async function runMerge(
  sessionId: string, selectedFields: string[],
  aliasMap: Record<string, string>, options: MergeOptions,
): Promise<MergeRunResult> {
  const { data } = await client.post<MergeRunResult>('/ml/merge/run', {
    session_id: sessionId, selected_fields: selectedFields,
    alias_map: aliasMap, options,
  }, { timeout: 120_000 })
  return data
}

export async function deleteMergeSession(sessionId: string): Promise<void> {
  await client.delete(`/ml/merge/${sessionId}`)
}

export async function downloadDataset(fileId: string, fmt: 'csv' | 'xlsx'): Promise<void> {
  // Blob download — mirror downloadZScoreCsv: GET the file as a blob, then click
  // a transient anchor. baseURL is /api, so the path carries only the /ml/ prefix.
  const { data } = await client.get(`/ml/${fileId}/download`, { params: { fmt }, responseType: 'blob' })
  const mime = fmt === 'csv'
    ? 'text/csv'
    : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  const url = URL.createObjectURL(new Blob([data as BlobPart], { type: mime }))
  const a = document.createElement('a'); a.href = url; a.download = `merged.${fmt}`; a.click()
  URL.revokeObjectURL(url)
}
```

> All API paths use the `/ml/...` prefix on `client` (baseURL `/api`) — confirmed against `uploadFile` and `downloadZScoreCsv` in this file.

- [ ] **Step 3: Build gate**

Run: `cd frontend ; npm run build`
Expected: PASS (`tsc -b && vite build`). No unused-import errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts
git commit -m "feat(merge): frontend merge types + api client" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Frontend — store tab union + `MlResultTabs` rework

**Files:**
- Modify: `frontend/src/stores/mlStudioStore.ts`
- Modify: `frontend/src/components/ml/MlResultTabs.tsx`

- [ ] **Step 1: Extend the tab union**

In `frontend/src/stores/mlStudioStore.ts`, change:

```typescript
export type MlTab = 'table' | 'charts' | 'stats' | 'forecast' | 'cohort'
```

to:

```typescript
export type MlTab = 'merge' | 'table' | 'charts' | 'stats' | 'forecast' | 'cohort' | 'eda'
```

- [ ] **Step 2: Add the Merge tab + rework the no-dataset short-circuit in `MlResultTabs.tsx`**

The real file (verified) uses `import { BarChart2, Table, FlaskConical, TrendingUp, Users, Upload } from 'lucide-react'` (keep `Upload` — `EmptyStudio` uses it), a LOCAL `type Tab`, a `TABS` array typed `Icon: React.ElementType` with ENGLISH labels, and short-circuits at ~line 80 with `if (!dataset) return <EmptyStudio />`. In THIS task wire ONLY Merge — the EDA tab is wired in Task 21, after `MlEdaView` exists (importing `Telescope`/`MlEdaView` now would break the build via `noUnusedLocals`). Apply these exact edits:

1. Replace the `lucide-react` import (line 1) — add only `Combine`:

```tsx
import { BarChart2, Table, FlaskConical, TrendingUp, Users, Upload, Combine } from 'lucide-react'
```

Add the Merge view import after the `MlCohortView` import (line 7):

```tsx
import MlMergeView    from './MlMergeView'
```

2. Replace the local `Tab` type (line 9) with the full union (matches the store's `MlTab`), and add `onDatasetCreated` to `Props` (lines 11-19):

```tsx
type Tab = 'merge' | 'table' | 'charts' | 'stats' | 'forecast' | 'cohort' | 'eda'

interface Props {
  result: QueryResult | null
  dataset: DatasetInfo | null
  activeTab: Tab
  onTabChange: (t: Tab) => void
  quality: QualityResult | null
  qualityError?: boolean
  datasets: DatasetInfo[]
  onDatasetCreated: (d: DatasetInfo) => void
}
```

3. Replace the `TABS` array (lines 21-27) — keep the 5 existing English labels, add `merge` first (the `eda` entry is added in Task 21):

```tsx
const TABS: { key: Tab; label: string; Icon: React.ElementType }[] = [
  { key: 'merge',    label: 'Gộp file', Icon: Combine      },
  { key: 'table',    label: 'Table',    Icon: Table        },
  { key: 'charts',   label: 'Charts',   Icon: BarChart2    },
  { key: 'stats',    label: 'Stats',    Icon: FlaskConical },
  { key: 'forecast', label: 'Forecast', Icon: TrendingUp   },
  { key: 'cohort',   label: 'Cohort',   Icon: Users        },
]
```

4. Replace the whole component body (from `export default function MlResultTabs(...)` at line 77 to its final `}`). Remove the `if (!dataset) return <EmptyStudio />` early return so the tab bar is ALWAYS visible, Merge renders with no dataset, and every other tab falls back to `<EmptyStudio />` until a dataset exists. Uses the file's REAL Tailwind classes (verified):

```tsx
export default function MlResultTabs({ result, dataset, activeTab, onTabChange, quality, qualityError, datasets, onDatasetCreated }: Props) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex border-b border-white/5 flex-shrink-0">
        {TABS.map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => onTabChange(key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-all ${
              activeTab === key
                ? 'border-data text-data'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            <Icon size={12} /> {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto relative">
        {/* Merge works with no dataset — it CREATES one */}
        <div className={activeTab === 'merge' ? '' : 'hidden'}>
          <MlMergeView onDatasetCreated={onDatasetCreated} />
        </div>

        {/* Every other tab needs a dataset — show onboarding until one exists */}
        {activeTab !== 'merge' && !dataset && <EmptyStudio />}

        {activeTab !== 'merge' && dataset && (
          <>
            <div className={activeTab === 'table'    ? '' : 'hidden'}>
              {result ? <MlTableView result={result} /> : <Empty text="Run a query to see results" />}
            </div>
            <div className={activeTab === 'charts'   ? '' : 'hidden'}>
              {result ? <MlChartView result={result} dataset={dataset} quality={quality} qualityError={qualityError} /> : <Empty text="Run a query to see charts" />}
            </div>
            <div className={activeTab === 'stats'    ? '' : 'hidden'}>
              <MlStatsView dataset={dataset} quality={quality} qualityError={qualityError} />
            </div>
            <div className={activeTab === 'forecast' ? '' : 'hidden'}>
              <MlForecastView dataset={dataset} quality={quality} qualityError={qualityError} />
            </div>
            <div className={activeTab === 'cohort'   ? '' : 'hidden'}>
              <MlCohortView dataset={dataset} datasets={datasets} quality={quality} qualityError={qualityError} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

(The `Empty`, `EmptyStudio`, and `STUDIO_FEATURES` helpers above the component stay exactly as they are. The `eda` tab button + `<MlEdaView>` block are added in Task 21 — until then `activeTab` can never become `'eda'` via the bar, so no `eda` branch is needed here. `MlMergeView` is created in Task 11 and `MlStudio` passes the new required `onDatasetCreated` in Task 12, so the first green frontend build is Task 12 Step 2.)

- [ ] **Step 3: Defer build to Task 12** (`MlMergeView` is created in Task 11; `MlStudio.tsx` passes the new required `onDatasetCreated` prop in Task 12 — the first green build gate is Task 12 Step 2). Do NOT build here.

- [ ] **Step 4: Commit** (this is an intermediate state — the green frontend build is Task 12)

```bash
git add frontend/src/stores/mlStudioStore.ts frontend/src/components/ml/MlResultTabs.tsx
git commit -m "feat(merge): add Merge tab + rework no-dataset gate" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Frontend — Merge components (`MlMergeView` + children)

**Files:**
- Create: `frontend/src/components/ml/MlMergeDropzone.tsx`
- Create: `frontend/src/components/ml/MlMergeChips.tsx`
- Create: `frontend/src/components/ml/MlMergeSummary.tsx`
- Create: `frontend/src/components/ml/MlMergeView.tsx`

- [ ] **Step 1: `MlMergeDropzone.tsx`** (multi-file; mirrors `MlUpload`)

```tsx
import { useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'

interface Props { onFiles: (files: File[]) => void; busy: boolean }

export default function MlMergeDropzone({ onFiles, busy }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDrag(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length) onFiles(files)
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      className={`border border-dashed rounded-lg p-5 text-center cursor-pointer transition
        ${drag ? 'border-data bg-data/5' : 'border-data/30 hover:border-data/60'}`}
    >
      <UploadCloud size={22} className="mx-auto mb-2 text-data" />
      <p className="text-xs text-gray-300">
        {busy ? 'Đang đọc file với Polars…' : 'Kéo-thả hoặc bấm để chọn nhiều file (CSV, XLSX)'}
      </p>
      <input
        ref={inputRef} type="file" multiple accept=".csv,.xlsx,.xls" className="hidden"
        onChange={e => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) onFiles(files)
          e.target.value = ''
        }}
      />
    </div>
  )
}
```

- [ ] **Step 2: `MlMergeChips.tsx`** (select fields + mark phone/dedup key)

```tsx
import { Phone, Key } from 'lucide-react'

interface Props {
  allFields: string[]
  commonFields: string[]
  selected: string[]
  onToggle: (field: string) => void
  dedupKey: string | null
  onDedupKey: (field: string | null) => void
  phoneCols: string[]
  onTogglePhone: (field: string) => void
}

export default function MlMergeChips({
  allFields, commonFields, selected, onToggle,
  dedupKey, onDedupKey, phoneCols, onTogglePhone,
}: Props) {
  const common = new Set(commonFields)
  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-400">
        Chọn field để gộp. <span className="text-data">Field chung</span> (có trong mọi file) được tô sáng.
      </p>
      <div className="flex flex-wrap gap-2">
        {allFields.map(f => {
          const on = selected.includes(f)
          return (
            <div key={f} className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs
              ${on ? 'border-data bg-data/10 text-data' : 'border-gray-700 text-gray-400'}`}>
              <button onClick={() => onToggle(f)} className="flex items-center gap-1">
                {common.has(f) && <span className="h-1.5 w-1.5 rounded-full bg-data" />}
                {f}
              </button>
              {on && (
                <>
                  <button title="Đánh dấu cột số điện thoại"
                    onClick={() => onTogglePhone(f)}
                    className={phoneCols.includes(f) ? 'text-emerald-400' : 'text-gray-500'}>
                    <Phone size={12} />
                  </button>
                  <button title="Dùng làm khóa loại trùng"
                    onClick={() => onDedupKey(dedupKey === f ? null : f)}
                    className={dedupKey === f ? 'text-amber-400' : 'text-gray-500'}>
                    <Key size={12} />
                  </button>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: `MlMergeSummary.tsx`** (metric cards + downloads)

```tsx
import { Download } from 'lucide-react'
import type { MergeRunResult } from '../../types'
import { downloadDataset } from '../../api/ml'

const CARDS: { key: keyof MergeRunResult['summary']; label: string }[] = [
  { key: 'total_raw',          label: 'Tổng dòng' },
  { key: 'valid',             label: 'Hợp lệ' },
  { key: 'nulls',             label: 'Null/sai' },
  { key: 'duplicates_removed', label: 'Trùng đã loại' },
  { key: 'distinct',          label: 'Distinct' },
  { key: 'complete_records',   label: 'Đủ thông tin' },
]

export default function MlMergeSummary({ result }: { result: MergeRunResult }) {
  const fid = result.dataset.file_id
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {CARDS.map(c => (
          <div key={c.key} className="rounded-lg border border-data/20 p-3">
            <p className="text-lg font-semibold text-data">{result.summary[c.key]}</p>
            <p className="text-xs text-gray-400">{c.label}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={() => downloadDataset(fid, 'csv')}
          className="flex items-center gap-1 rounded-md border border-data/30 px-3 py-1.5 text-xs text-gray-200 hover:bg-data/10">
          <Download size={14} /> CSV
        </button>
        <button onClick={() => downloadDataset(fid, 'xlsx')}
          className="flex items-center gap-1 rounded-md border border-data/30 px-3 py-1.5 text-xs text-gray-200 hover:bg-data/10">
          <Download size={14} /> XLSX
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: `MlMergeView.tsx`** (orchestration)

```tsx
import { useState } from 'react'
import type { DatasetInfo, MergeStageResult, MergeRunResult } from '../../types'
import { stageMerge, runMerge } from '../../api/ml'
import MlMergeDropzone from './MlMergeDropzone'
import MlMergeChips from './MlMergeChips'
import MlMergeSummary from './MlMergeSummary'

interface Props { onDatasetCreated: (d: DatasetInfo) => void }

export default function MlMergeView({ onDatasetCreated }: Props) {
  const [stage, setStage]       = useState<MergeStageResult | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [dedupKey, setDedupKey] = useState<string | null>(null)
  const [phoneCols, setPhone]   = useState<string[]>([])
  const [dropNull, setDropNull] = useState(true)
  const [result, setResult]     = useState<MergeRunResult | null>(null)
  const [busy, setBusy]         = useState(false)
  const [error, setError]       = useState('')

  async function handleFiles(files: File[]) {
    setBusy(true); setError('')
    try {
      const r = await stageMerge(files, stage?.session_id)
      setStage(r)
      setSelected(r.common_fields)
    } catch (e) {
      setError(errMsg(e))
    } finally { setBusy(false) }
  }

  function toggle(f: string) {
    setSelected(s => s.includes(f) ? s.filter(x => x !== f) : [...s, f])
  }
  function togglePhone(f: string) {
    setPhone(s => s.includes(f) ? s.filter(x => x !== f) : [...s, f])
  }

  async function handleRun() {
    if (!stage) return
    setBusy(true); setError('')
    try {
      const r = await runMerge(stage.session_id, selected, {}, {
        dedup_key: dedupKey, drop_null_key: dropNull, trim: true, phone_cols: phoneCols,
      })
      setResult(r)
      onDatasetCreated(r.dataset)
    } catch (e) {
      setError(errMsg(e))
    } finally { setBusy(false) }
  }

  return (
    <div className="p-4 space-y-4 max-w-3xl">
      <div>
        <h2 className="text-sm font-semibold text-gray-200 mb-1">Gộp nhiều file</h2>
        <p className="text-xs text-gray-500">
          Tải lên N file lệch schema → công cụ tìm field chung → chọn → gộp + làm sạch + loại trùng.
        </p>
      </div>

      <MlMergeDropzone onFiles={handleFiles} busy={busy} />

      {stage && (
        <>
          <div className="text-xs text-gray-400">
            {stage.files.length} file: {stage.files.map(f => f.filename).join(', ')}
          </div>
          <MlMergeChips
            allFields={stage.all_fields} commonFields={stage.common_fields}
            selected={selected} onToggle={toggle}
            dedupKey={dedupKey} onDedupKey={setDedupKey}
            phoneCols={phoneCols} onTogglePhone={togglePhone}
          />
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={dropNull} onChange={e => setDropNull(e.target.checked)} />
            Bỏ dòng có khóa rỗng
          </label>
          <button
            onClick={handleRun}
            disabled={busy || selected.length === 0}
            className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40"
          >
            {busy ? 'Đang gộp…' : 'Gộp & tạo dataset'}
          </button>
        </>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
      {result && <MlMergeSummary result={result} />}
    </div>
  )
}

function errMsg(e: unknown): string {
  return (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ?? 'Có lỗi xảy ra'
}
```

- [ ] **Step 5: Defer build to Task 12**

Do NOT build yet. `MlResultTabs` (Task 10) now requires the `onDatasetCreated` prop, which `MlStudio.tsx` does not pass until Task 12 — building now fails with "Property 'onDatasetCreated' is missing". The first green frontend build gate is Task 12 Step 2.

- [ ] **Step 6: Commit** (the green build runs next, in Task 12)

```bash
git add frontend/src/components/ml/MlMerge*.tsx
git commit -m "feat(merge): MlMergeView + dropzone/chips/summary" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Frontend — wire Merge output into `MlStudio`

**Files:**
- Modify: `frontend/src/pages/analytics/MlStudio.tsx`

- [ ] **Step 1: Add the `onDatasetCreated` handler and pass it to `MlResultTabs`**

In `frontend/src/pages/analytics/MlStudio.tsx`, define a handler that sets the new dataset as active and refreshes the dataset list (mirror the existing `handleUpload` flow — `setDataset`, `setResult(null)`, `refreshDatasets`, then jump to a useful tab):

```tsx
function handleDatasetCreated(d: DatasetInfo) {
  setDataset(d)
  setResult(null)
  refreshDatasets()
  setActiveTab('eda')   // land on Auto-EDA so the user immediately profiles the merge
}
```

Then pass it down:

```tsx
<MlResultTabs
  /* ...existing props... */
  onDatasetCreated={handleDatasetCreated}
/>
```

(All four helpers — `setDataset`, `setResult`, `refreshDatasets`, `setActiveTab` — already exist in this file (lines 14-35), and `DatasetInfo` is already imported (line 2). Add `onDatasetCreated={handleDatasetCreated}` to the existing `<MlResultTabs>` JSX, right after `datasets={datasets}` (line 127). Note: `setActiveTab('eda')` is valid here even though the EDA tab button is not added until Task 21 — `'eda'` is already part of the `MlTab` union (Task 10 Step 1), and the manual smoke test runs after Task 22.)

- [ ] **Step 2: Build gate**

Run: `cd frontend ; npm run build`
Expected: PASS.

- [ ] **Step 3: Manual smoke test (optional but recommended)**

Run `python run.py` from the MAIN tree after delivery (Task 22). Verify: ML Studio → "Gộp file" tab → drop 2 CSVs → common-field chips appear → select + run → summary cards + dataset loads → lands on Auto-EDA tab.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/analytics/MlStudio.tsx
git commit -m "feat(merge): wire merge output into ML Studio" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
---

# PART 2 — AUTO-EDA

---

### Task 13: `eda.py` — `infer_role` + `profile_columns`

**Files:**
- Create: `backend/analytics/eda.py`
- Test: `backend/tests/test_ml_eda.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_ml_eda.py`:

```python
import polars as pl
from analytics.eda import infer_role, profile_columns


def test_infer_role_basic():
    df = pl.DataFrame({
        "id": [1, 2, 3, 4],
        "amount": [10.0, 20.0, 30.0, 40.0],
        "city": ["A", "B", "A", "C"],
        "active": [True, False, True, False],
        "order_date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
    })
    roles = {c["name"]: c["role"] for c in profile_columns(df)}
    assert roles["id"] == "id"
    assert roles["amount"] == "metric"
    assert roles["city"] == "dimension"
    assert roles["active"] == "flag"
    assert roles["order_date"] == "date"


def test_profile_columns_null_pct_and_constant():
    df = pl.DataFrame({"k": [1, None, 3, None], "const": ["x", "x", "x", "x"]})
    prof = {c["name"]: c for c in profile_columns(df)}
    assert prof["k"]["null_pct"] == 50.0
    assert prof["const"]["is_constant"] is True
    assert prof["const"]["cardinality"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'analytics.eda'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/analytics/eda.py`:

```python
"""Pure helpers for the ML Studio Auto-EDA feature (unit-testable, no FastAPI)."""
from __future__ import annotations

import numpy as np
import polars as pl

_DATE_HINTS = ("date", "time", "ngay", "thang", "ngày", "tháng")


def infer_role(name: str, s: pl.Series, nunq: int, n: int, is_num: bool) -> str:
    low = name.lower()
    if s.dtype in (pl.Date, pl.Datetime) or any(h in low for h in _DATE_HINTS):
        return "date"
    if n > 0 and nunq == n:
        return "id"
    if "id" in low and nunq > n * 0.9:
        return "id"
    if nunq <= 2:
        return "flag"
    if is_num:
        return "metric"
    return "dimension"


def profile_columns(df: pl.DataFrame) -> list[dict]:
    n = df.height
    out: list[dict] = []
    for name in df.columns:
        s = df[name]
        nulls = int(s.null_count())
        nunq = int(s.n_unique())
        is_num = s.dtype.is_numeric()
        col = {
            "name": name,
            "dtype": str(s.dtype),
            "role": infer_role(name, s, nunq, n, is_num),
            "cardinality": nunq,
            "null_pct": round(100.0 * nulls / n, 2) if n else 0.0,
            "is_constant": nunq <= 1,
            "samples": [str(v) for v in s.drop_nulls().head(3).to_list()],
        }
        if is_num and s.drop_nulls().len():
            col["min"] = float(s.min())
            col["max"] = float(s.max())
        out.append(col)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/eda.py backend/tests/test_ml_eda.py
git commit -m "feat(eda): infer_role + profile_columns" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: `eda.py` — `correlation_matrix`

**Files:**
- Modify: `backend/analytics/eda.py`
- Test: `backend/tests/test_ml_eda.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml_eda.py`:

```python
from analytics.eda import correlation_matrix


def test_correlation_matrix_perfect_positive():
    df = pl.DataFrame({"a": [1.0, 2, 3, 4], "b": [2.0, 4, 6, 8], "c": [4.0, 3, 2, 1]})
    cm = correlation_matrix(df)
    i = cm["columns"].index("a"); j = cm["columns"].index("b"); k = cm["columns"].index("c")
    assert round(cm["matrix"][i][j], 3) == 1.0
    assert round(cm["matrix"][i][k], 3) == -1.0
    assert cm["matrix"][i][i] == 1.0


def test_correlation_matrix_excludes_constant_and_allnull():
    df = pl.DataFrame({"a": [1.0, 2, 3], "const": [5.0, 5, 5], "x": [None, None, None]})
    cm = correlation_matrix(df)
    assert "a" in cm["columns"]
    assert "const" not in cm["columns"]
    excluded = {e["name"] for e in cm["excluded_columns"]}
    assert "const" in excluded
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k correlation -q`
Expected: FAIL — `ImportError: cannot import name 'correlation_matrix'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/analytics/eda.py`:

```python
def correlation_matrix(df: pl.DataFrame, max_cols: int = 12) -> dict:
    """Pairwise Pearson correlation over numeric columns.

    Excludes all-null and constant columns. Returns columns/matrix (with None for
    pairs lacking >=3 overlapping non-null rows) and the excluded-columns note.
    """
    numeric = [c for c in df.columns if df[c].dtype.is_numeric()]
    cols: list[str] = []
    excluded: list[dict] = []
    series: dict[str, np.ndarray] = {}
    for c in numeric[:max_cols]:
        s = df[c]
        if s.null_count() == len(s):
            excluded.append({"name": c, "reason": "all_null"})
            continue
        if s.n_unique() <= 1:
            excluded.append({"name": c, "reason": "constant"})
            continue
        cols.append(c)
        series[c] = s.cast(pl.Float64).to_numpy()

    size = len(cols)
    matrix: list[list[float | None]] = [[None] * size for _ in range(size)]
    for i in range(size):
        for j in range(i, size):
            if i == j:
                matrix[i][j] = 1.0
                continue
            a, b = series[cols[i]], series[cols[j]]
            mask = ~(np.isnan(a) | np.isnan(b))
            if int(mask.sum()) < 3:
                r = None
            else:
                with np.errstate(invalid="ignore"):
                    r = float(np.corrcoef(a[mask], b[mask])[0, 1])
                if np.isnan(r):
                    r = None
            matrix[i][j] = r
            matrix[j][i] = r
    return {"columns": cols, "matrix": matrix, "excluded_columns": excluded}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k correlation -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/eda.py backend/tests/test_ml_eda.py
git commit -m "feat(eda): correlation_matrix with exclusions" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: `eda.py` — `numeric_distributions`

**Files:**
- Modify: `backend/analytics/eda.py`
- Test: `backend/tests/test_ml_eda.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml_eda.py`:

```python
from analytics.eda import numeric_distributions


def test_numeric_distributions_bins_and_stats():
    df = pl.DataFrame({"v": [float(i) for i in range(100)], "label": ["x"] * 100})
    dists = numeric_distributions(df, ["v"], log_transform="off")
    assert len(dists) == 1
    d = dists[0]
    assert d["column"] == "v"
    assert sum(b["count"] for b in d["bins"]) == 100
    assert d["min"] == 0.0 and d["max"] == 99.0
    assert abs(d["mean"] - 49.5) < 1e-6
    assert d["log_applied"] is False


def test_numeric_distributions_auto_log_on_skew():
    # Heavy right skew, all positive -> auto log.
    vals = [1.0] * 90 + [1000.0] * 10
    df = pl.DataFrame({"v": vals})
    dists = numeric_distributions(df, ["v"], log_transform="auto")
    assert dists[0]["skew"] > 1.0
    assert dists[0]["log_applied"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k distributions -q`
Expected: FAIL — `ImportError: cannot import name 'numeric_distributions'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/analytics/eda.py`:

```python
def _skew(arr: np.ndarray) -> float:
    arr = arr[~np.isnan(arr)]
    if arr.size < 3:
        return 0.0
    m, sd = arr.mean(), arr.std()
    if sd == 0:
        return 0.0
    return float((((arr - m) / sd) ** 3).mean())


def _bins(arr: np.ndarray, n_bins: int = 20) -> list[dict]:
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return []
    counts, edges = np.histogram(arr, bins=n_bins)
    return [
        {"x0": float(edges[i]), "x1": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def numeric_distributions(
    df: pl.DataFrame, cols: list[str], log_transform: str = "auto", n_bins: int = 20,
) -> list[dict]:
    """Histogram + summary stats per numeric column. log_transform: auto|on|off."""
    out: list[dict] = []
    for c in cols:
        if c not in df.columns or not df[c].dtype.is_numeric():
            continue
        arr = df[c].cast(pl.Float64).to_numpy()
        clean = arr[~np.isnan(arr)]
        if clean.size == 0:
            continue
        skew = _skew(arr)
        want_log = log_transform == "on" or (log_transform == "auto" and skew > 1.0)
        log_applied = bool(want_log and clean.min() >= 0)
        bins_arr = np.log1p(arr) if log_applied else arr
        out.append({
            "column": c,
            "bins": _bins(bins_arr, n_bins),
            "skew": round(skew, 3),
            "log_applied": log_applied,
            "mean": float(clean.mean()),
            "median": float(np.median(clean)),
            "std": float(clean.std()),
            "min": float(clean.min()),
            "max": float(clean.max()),
        })
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k distributions -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/eda.py backend/tests/test_ml_eda.py
git commit -m "feat(eda): numeric_distributions with auto-log on skew" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: `eda.py` — `segment_breakdown`

**Files:**
- Modify: `backend/analytics/eda.py`
- Test: `backend/tests/test_ml_eda.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml_eda.py`:

```python
from analytics.eda import segment_breakdown


def test_segment_breakdown_table_and_scatter():
    df = pl.DataFrame({
        "city": ["A", "A", "B", "B", "C"],
        "rev":  [10.0, 20, 30, 40, 50],
        "qty":  [1.0, 2, 3, 4, 5],
    })
    bd = segment_breakdown(df, "city", ["rev", "qty"], top_n=2, sample_n=100)
    # top_n=2 by row count -> A and B (2 each) before C (1).
    seg_names = {r["segment"] for r in bd["table"]}
    assert seg_names == {"A", "B"}
    a = next(r for r in bd["table"] if r["segment"] == "A")
    assert a["count"] == 2
    assert a["rev_sum"] == 30.0
    # scatter uses first two metrics.
    assert bd["scatter"]["x_col"] == "rev"
    assert bd["scatter"]["y_col"] == "qty"
    assert len(bd["scatter"]["points"]) == 5


def test_segment_breakdown_no_metrics():
    df = pl.DataFrame({"city": ["A", "B"]})
    bd = segment_breakdown(df, "city", [], top_n=10, sample_n=100)
    assert bd["scatter"]["points"] == []
    assert len(bd["table"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k segment -q`
Expected: FAIL — `ImportError: cannot import name 'segment_breakdown'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/analytics/eda.py`:

```python
def segment_breakdown(
    df: pl.DataFrame, seg_col: str, metric_cols: list[str],
    top_n: int = 10, sample_n: int = 2000,
) -> dict:
    """Group-by `seg_col`: count + per-metric sum/mean for the top_n biggest groups.

    Scatter uses the first two metrics; points sampled to <= sample_n.
    """
    metrics = [m for m in metric_cols if m in df.columns and df[m].dtype.is_numeric()]
    aggs = [pl.len().alias("count")]
    for m in metrics:
        aggs.append(pl.col(m).sum().alias(f"{m}_sum"))
        aggs.append(pl.col(m).mean().alias(f"{m}_mean"))
    grouped = df.group_by(seg_col).agg(aggs).sort("count", descending=True).head(top_n)

    table: list[dict] = []
    for row in grouped.iter_rows(named=True):
        rec = {"segment": str(row[seg_col]), "count": int(row["count"])}
        for m in metrics:
            rec[f"{m}_sum"] = float(row[f"{m}_sum"]) if row[f"{m}_sum"] is not None else 0.0
            rec[f"{m}_mean"] = float(row[f"{m}_mean"]) if row[f"{m}_mean"] is not None else 0.0
        table.append(rec)

    scatter: dict = {"x_col": None, "y_col": None, "points": []}
    if len(metrics) >= 2:
        xc, yc = metrics[0], metrics[1]
        sub = df.select([seg_col, xc, yc]).drop_nulls()
        if sub.height > sample_n:
            sub = sub.sample(n=sample_n, seed=42)
        scatter = {
            "x_col": xc, "y_col": yc,
            "points": [
                {"x": float(r[xc]), "y": float(r[yc]), "group": str(r[seg_col])}
                for r in sub.iter_rows(named=True)
            ],
        }
    return {"table": table, "scatter": scatter}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k segment -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/eda.py backend/tests/test_ml_eda.py
git commit -m "feat(eda): segment_breakdown table + scatter" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: `eda.py` — `derive_rule_insights`

**Files:**
- Modify: `backend/analytics/eda.py`
- Test: `backend/tests/test_ml_eda.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ml_eda.py`:

```python
from analytics.eda import derive_rule_insights


def test_derive_rule_insights_shape_and_content():
    profile = [
        {"name": "rev", "role": "metric", "null_pct": 0.0, "is_constant": False, "cardinality": 50},
        {"name": "note", "role": "dimension", "null_pct": 80.0, "is_constant": False, "cardinality": 5},
    ]
    corr = {"columns": ["rev", "qty"], "matrix": [[1.0, 0.95], [0.95, 1.0]], "excluded_columns": []}
    dists = [{"column": "rev", "skew": 3.2, "log_applied": True, "mean": 10, "median": 2,
              "std": 5, "min": 0, "max": 100, "bins": []}]
    segs = {"table": [{"segment": "A", "count": 80}, {"segment": "B", "count": 20}],
            "scatter": {"x_col": None, "y_col": None, "points": []}}
    ins = derive_rule_insights(profile, corr, dists, segs, total_rows=100, max_insights=5)
    assert 1 <= len(ins) <= 5
    for it in ins:
        assert set(it.keys()) >= {"finding", "so_what", "action", "severity"}
    blob = " ".join(i["finding"] for i in ins)
    assert "note" in blob          # high-null column flagged
    assert "rev" in blob           # skew or correlation flagged


def test_derive_rule_insights_never_empty():
    profile = [{"name": "x", "role": "dimension", "null_pct": 0.0, "is_constant": False, "cardinality": 3}]
    corr = {"columns": [], "matrix": [], "excluded_columns": []}
    ins = derive_rule_insights(profile, corr, [], {"table": [], "scatter": {}}, total_rows=10)
    assert len(ins) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k rule_insights -q`
Expected: FAIL — `ImportError: cannot import name 'derive_rule_insights'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/analytics/eda.py`:

```python
def derive_rule_insights(
    profile: list[dict], corr: dict, distributions: list[dict],
    segments: dict, total_rows: int, max_insights: int = 5,
) -> list[dict]:
    """Rule-based Finding -> So-what -> Action insights (AI-free fallback)."""
    out: list[dict] = []

    # 1. Highest-null column.
    nullable = [c for c in profile if c.get("null_pct", 0) > 0]
    if nullable:
        worst = max(nullable, key=lambda c: c["null_pct"])
        if worst["null_pct"] >= 20:
            out.append({
                "finding": f"Cột '{worst['name']}' thiếu {worst['null_pct']:.0f}% dữ liệu.",
                "so_what": "Phân tích/biểu đồ trên cột này dễ sai lệch, mẫu hữu dụng bị thu nhỏ.",
                "action": f"Bổ sung nguồn cho '{worst['name']}' hoặc loại khỏi báo cáo nếu không cứu được.",
                "severity": "high" if worst["null_pct"] >= 50 else "medium",
            })

    # 2. Strongest correlation pair.
    cols, mat = corr.get("columns", []), corr.get("matrix", [])
    best = None
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = mat[i][j]
            if r is None:
                continue
            if best is None or abs(r) > abs(best[2]):
                best = (cols[i], cols[j], r)
    if best and abs(best[2]) >= 0.7:
        direction = "cùng chiều" if best[2] > 0 else "ngược chiều"
        out.append({
            "finding": f"'{best[0]}' và '{best[1]}' tương quan {direction} mạnh (r={best[2]:.2f}).",
            "so_what": "Hai chỉ số gắn chặt — có thể trùng thông tin hoặc một bên dự báo bên kia.",
            "action": f"Dùng '{best[0]}' để giải thích/forecast '{best[1]}', tránh đếm trùng khi báo cáo.",
            "severity": "medium",
        })

    # 3. Most skewed metric.
    skewed = [d for d in distributions if abs(d.get("skew", 0)) >= 1.0]
    if skewed:
        s = max(skewed, key=lambda d: abs(d["skew"]))
        out.append({
            "finding": f"'{s['column']}' lệch mạnh (skew={s['skew']:.1f}); trung vị {s['median']:.0f} «" 
                       f" trung bình {s['mean']:.0f}.",
            "so_what": "Vài giá trị lớn kéo trung bình lên — dùng trung bình sẽ hiểu sai 'điển hình'.",
            "action": f"Báo cáo theo trung vị/percentile cho '{s['column']}', xem lại nhóm giá trị cực đại.",
            "severity": "medium",
        })

    # 4. Dominant segment.
    table = segments.get("table", [])
    if table and total_rows:
        top = table[0]
        share = 100.0 * top["count"] / total_rows
        if share >= 40:
            out.append({
                "finding": f"Nhóm '{top['segment']}' chiếm {share:.0f}% số dòng.",
                "so_what": "Dữ liệu tập trung một nhóm — kết luận chung dễ bị nhóm này chi phối.",
                "action": f"Phân tích riêng '{top['segment']}' và phần còn lại; cân nhắc chuẩn hóa theo nhóm.",
                "severity": "medium",
            })

    # 5. Constant columns.
    consts = [c["name"] for c in profile if c.get("is_constant")]
    if consts:
        out.append({
            "finding": f"{len(consts)} cột chỉ có một giá trị: {', '.join(consts[:3])}.",
            "so_what": "Cột hằng số không mang thông tin phân tích.",
            "action": "Loại các cột này khỏi mô hình/biểu đồ để giảm nhiễu.",
            "severity": "low",
        })

    # Guarantee at least one insight.
    if not out:
        out.append({
            "finding": f"Dữ liệu có {total_rows} dòng, {len(profile)} cột, chất lượng cơ bản ổn.",
            "so_what": "Không phát hiện vấn đề null/lệch/tập trung nổi bật ở mức cảnh báo.",
            "action": "Tiến hành phân tích chuyên sâu theo câu hỏi nghiệp vụ cụ thể.",
            "severity": "low",
        })
    return out[:max_insights]
```

> Note: remove the stray `«` glyph if your editor flags it — it's only illustrative. Use a plain comparison phrase like `"trung vị X « trung bình Y"` → write it as `f"...trung vị {s['median']:.0f} so với trung bình {s['mean']:.0f}."` (replace the `«` line accordingly). Keep the f-string on one line.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k rule_insights -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/eda.py backend/tests/test_ml_eda.py
git commit -m "feat(eda): derive_rule_insights Finding/So-what/Action" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 18: `POST /{file_id}/eda` endpoint (compose + AI insight w/ fallback)

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml_eda.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ml_eda.py`:

```python
import io
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


EDA_CSV = (
    b"city,rev,qty,note\n"
    b"A,10,1,x\nA,20,2,\nB,30,3,y\nB,40,4,\nC,50,5,z\n"
)


def test_eda_report_structure(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("e.csv", io.BytesIO(EDA_CSV), "text/csv")},
    ).json()
    resp = client.post(f"/api/ml/{up['file_id']}/eda", json={"segment_col": "city"})
    assert resp.status_code == 200
    d = resp.json()
    for key in ("meta", "profile", "correlation", "distributions",
                "segments", "insights", "insights_source"):
        assert key in d
    assert d["meta"]["rows"] == 5
    assert len(d["profile"]) == 4
    # No API key + no Ollama in CI -> rule-based fallback, never empty.
    assert d["insights_source"] in ("ai", "rule")
    assert len(d["insights"]) >= 1
    assert {"finding", "so_what", "action"} <= set(d["insights"][0].keys())


def test_eda_unknown_file(client):
    assert client.post("/api/ml/bad-id/eda", json={}).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k eda_report -q`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Add the import, models, and endpoint**

In `backend/routers/ml.py`:

1. Extend the eda import near the top:

```python
from analytics.eda import (
    profile_columns, correlation_matrix, numeric_distributions,
    segment_breakdown, derive_rule_insights,
)
```

2. Add models + endpoint (place near the other `/{file_id}/...` routes, e.g. after `download_dataset`):

```python
class EdaIn(BaseModel):
    segment_col: str | None = None
    metric_cols: list[str] | None = None
    top_n: int = 10
    max_insights: int = 5
    log_transform: Literal["auto", "on", "off"] = "auto"


def _ai_insights(meta: dict, profile: list[dict], corr: dict,
                 dists: list[dict], segs: dict) -> list[dict] | None:
    """Try the AI helper; return parsed insights or None to trigger fallback."""
    import json as _json
    prompt = (
        "Bạn là chuyên gia phân tích dữ liệu. Dựa trên hồ sơ EDA sau (JSON), "
        "viết tối đa 5 insight phục vụ RA QUYẾT ĐỊNH KINH DOANH. "
        "Mỗi insight có dạng {\"finding\":..., \"so_what\":..., \"action\":..., "
        "\"severity\":\"low|medium|high\"}. Trả về DUY NHẤT một mảng JSON, tiếng Việt.\n\n"
        f"META={_json.dumps(meta, ensure_ascii=False)}\n"
        f"PROFILE={_json.dumps(profile, ensure_ascii=False)}\n"
        f"CORRELATION={_json.dumps(corr, ensure_ascii=False)}\n"
        f"DISTRIBUTIONS={_json.dumps(dists, ensure_ascii=False)}\n"
        f"SEGMENTS={_json.dumps(segs.get('table', []), ensure_ascii=False)}\n"
    )
    try:
        raw = _call_ai_ml(prompt, max_tokens=1024)
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return None
        parsed = _json.loads(raw[start:end + 1])
        out = []
        for it in parsed:
            if not isinstance(it, dict):
                continue
            if not {"finding", "so_what", "action"} <= set(it.keys()):
                continue
            out.append({
                "finding": str(it["finding"]),
                "so_what": str(it["so_what"]),
                "action": str(it["action"]),
                "severity": str(it.get("severity", "medium")),
            })
        return out or None
    except Exception:
        return None


@router.post("/{file_id}/eda")
def run_eda(file_id: str, body: EdaIn):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])

    profile = profile_columns(df)
    if body.metric_cols:
        metrics = [m for m in body.metric_cols if m in df.columns]
    else:
        metrics = [c["name"] for c in profile if c["role"] == "metric"][:4]

    corr = correlation_matrix(df)
    dists = numeric_distributions(df, metrics, log_transform=body.log_transform)

    seg_col = body.segment_col
    if not seg_col:
        dims = [c["name"] for c in profile if c["role"] == "dimension"]
        seg_col = dims[0] if dims else None
    segs = (segment_breakdown(df, seg_col, metrics, top_n=body.top_n)
            if seg_col else {"table": [], "scatter": {"x_col": None, "y_col": None, "points": []}})

    meta = {"rows": df.height, "cols": df.width, "filename": row["filename"],
            "segment_col": seg_col, "metric_cols": metrics}

    ai = _ai_insights(meta, profile, corr, dists, segs)
    if ai:
        insights, source = ai[:body.max_insights], "ai"
    else:
        insights = derive_rule_insights(profile, corr, dists, segs,
                                        total_rows=df.height, max_insights=body.max_insights)
        source = "rule"

    return {
        "meta": meta, "profile": profile, "correlation": corr,
        "distributions": dists, "segments": segs,
        "insights": insights, "insights_source": source,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend ; uv run pytest tests/test_ml_eda.py -k eda -q`
Expected: PASS.

- [ ] **Step 5: Full backend regression**

Run: `cd backend ; uv run pytest -q`
Expected: all NEW eda/merge tests pass; only the 8 pre-existing `test_sql_sandbox.py` failures remain.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml_eda.py
git commit -m "feat(eda): POST /{file_id}/eda compose + AI insight with rule fallback" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 19: Frontend — EDA types + API client

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/ml.ts`

- [ ] **Step 1: Add types**

In `frontend/src/types.ts`, after the ML Merge types added in Task 9, add:

```typescript
// ─── ML Auto-EDA ──────────────────────────────────────────────────────────────

export interface EdaInsight {
  finding: string
  so_what: string
  action: string
  severity: 'low' | 'medium' | 'high'
}

export interface EdaDistribution {
  column: string
  bins: { x0: number; x1: number; count: number }[]
  skew: number
  log_applied: boolean
  mean: number
  median: number
  std: number
  min: number
  max: number
}

export interface EdaSegmentRow {
  segment: string
  count: number
  [metricAgg: string]: number | string
}

export interface EdaScatterPoint { x: number; y: number; group: string }

export interface EdaReport {
  meta: {
    rows: number; cols: number; filename: string
    segment_col: string | null; metric_cols: string[]
  }
  profile: ProfileColumn[]
  correlation: CorrelationMatrix
  distributions: EdaDistribution[]
  segments: {
    table: EdaSegmentRow[]
    scatter: { x_col: string | null; y_col: string | null; points: EdaScatterPoint[] }
  }
  insights: EdaInsight[]
  insights_source: 'ai' | 'rule'
}
```

- [ ] **Step 2: Add API client function**

In `frontend/src/api/ml.ts`, extend the import from `'../types'` to include `EdaReport`, and add:

```typescript
export async function runEda(
  fileId: string,
  opts: { segment_col?: string; metric_cols?: string[]; log_transform?: 'auto' | 'on' | 'off' } = {},
): Promise<EdaReport> {
  const { data } = await client.post(`/ml/${fileId}/eda`, opts)
  return data
}
```

- [ ] **Step 3: Build gate**

Run: `cd frontend ; npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts
git commit -m "feat(eda): frontend EDA types + runEda client" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 20: Frontend — EDA components (`MlEdaView` + children + `edaMarkdown`)

**Files:**
- Create: `frontend/src/components/ml/edaMarkdown.ts`
- Create: `frontend/src/components/ml/MlEdaProfile.tsx`
- Create: `frontend/src/components/ml/MlEdaDistribution.tsx`
- Create: `frontend/src/components/ml/MlEdaSegments.tsx`
- Create: `frontend/src/components/ml/MlEdaInsights.tsx`
- Create: `frontend/src/components/ml/MlEdaView.tsx`

- [ ] **Step 1: `edaMarkdown.ts`** (pure helper)

```typescript
import type { EdaReport } from '../../types'

export function edaToMarkdown(r: EdaReport): string {
  const lines: string[] = []
  lines.push(`# Auto-EDA — ${r.meta.filename}`)
  lines.push(`${r.meta.rows} dòng × ${r.meta.cols} cột`, '')
  lines.push('## Insights')
  r.insights.forEach((i, n) => {
    lines.push(`${n + 1}. **Finding:** ${i.finding}`)
    lines.push(`   - **So what:** ${i.so_what}`)
    lines.push(`   - **Action:** ${i.action}`)
  })
  lines.push('', '## Hồ sơ cột')
  lines.push('| Cột | Loại | Null % | Cardinality |')
  lines.push('| --- | --- | --- | --- |')
  r.profile.forEach(c =>
    lines.push(`| ${c.name} | ${c.role} | ${c.null_pct}% | ${c.cardinality} |`))
  return lines.join('\n')
}
```

- [ ] **Step 2: `MlEdaProfile.tsx`**

```tsx
import type { ProfileColumn } from '../../types'

export default function MlEdaProfile({ columns }: { columns: ProfileColumn[] }) {
  return (
    <div className="overflow-auto rounded-lg border border-data/20">
      <table className="w-full text-xs">
        <thead className="bg-data/10 text-gray-300">
          <tr>
            <th className="px-2 py-1.5 text-left">Cột</th>
            <th className="px-2 py-1.5 text-left">Loại</th>
            <th className="px-2 py-1.5 text-right">Null %</th>
            <th className="px-2 py-1.5 text-right">Cardinality</th>
            <th className="px-2 py-1.5 text-left">Mẫu</th>
          </tr>
        </thead>
        <tbody>
          {columns.map(c => (
            <tr key={c.name} className="border-t border-data/10">
              <td className="px-2 py-1.5 text-gray-200">{c.name}</td>
              <td className="px-2 py-1.5 text-gray-400">{c.role}</td>
              <td className={`px-2 py-1.5 text-right ${c.null_pct >= 20 ? 'text-amber-400' : 'text-gray-400'}`}>
                {c.null_pct}%
              </td>
              <td className="px-2 py-1.5 text-right text-gray-400">{c.cardinality}</td>
              <td className="px-2 py-1.5 text-gray-500 truncate max-w-[200px]">
                {c.samples.join(', ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: `MlEdaDistribution.tsx`** (recharts histogram per metric)

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { EdaDistribution } from '../../types'

export default function MlEdaDistribution({ dists }: { dists: EdaDistribution[] }) {
  if (dists.length === 0) return <p className="text-xs text-gray-500">Không có cột số để vẽ phân phối.</p>
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {dists.map(d => {
        const data = d.bins.map(b => ({ x: ((b.x0 + b.x1) / 2).toFixed(1), count: b.count }))
        return (
          <div key={d.column} className="rounded-lg border border-data/20 p-3">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-medium text-gray-200">{d.column}</p>
              <p className="text-[10px] text-gray-500">
                skew {d.skew}{d.log_applied ? ' · log' : ''} · median {d.median.toFixed(1)}
              </p>
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={data}>
                <XAxis dataKey="x" tick={{ fontSize: 9, fill: '#9ca3af' }} interval={3} />
                <YAxis tick={{ fontSize: 9, fill: '#9ca3af' }} width={28} />
                <Tooltip contentStyle={{ fontSize: 11, background: '#111827', border: 'none' }} />
                <Bar dataKey="count" fill="#38bdf8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: `MlEdaSegments.tsx`** (table + scatter)

```tsx
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { EdaReport } from '../../types'

export default function MlEdaSegments({ segments }: { segments: EdaReport['segments'] }) {
  const { table, scatter } = segments
  if (table.length === 0) return <p className="text-xs text-gray-500">Không có cột nhóm (dimension) để phân tích.</p>
  const metricKeys = Object.keys(table[0]).filter(k => k !== 'segment' && k !== 'count')
  return (
    <div className="space-y-4">
      <div className="overflow-auto rounded-lg border border-data/20">
        <table className="w-full text-xs">
          <thead className="bg-data/10 text-gray-300">
            <tr>
              <th className="px-2 py-1.5 text-left">Nhóm</th>
              <th className="px-2 py-1.5 text-right">Số dòng</th>
              {metricKeys.map(k => <th key={k} className="px-2 py-1.5 text-right">{k}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.map(r => (
              <tr key={r.segment} className="border-t border-data/10">
                <td className="px-2 py-1.5 text-gray-200">{r.segment}</td>
                <td className="px-2 py-1.5 text-right text-gray-400">{r.count}</td>
                {metricKeys.map(k => (
                  <td key={k} className="px-2 py-1.5 text-right text-gray-400">
                    {typeof r[k] === 'number' ? (r[k] as number).toLocaleString() : r[k]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {scatter.x_col && scatter.y_col && scatter.points.length > 0 && (
        <div className="rounded-lg border border-data/20 p-3">
          <p className="text-xs font-medium text-gray-200 mb-1">
            {scatter.x_col} vs {scatter.y_col}
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart>
              <XAxis type="number" dataKey="x" name={scatter.x_col}
                tick={{ fontSize: 9, fill: '#9ca3af' }} />
              <YAxis type="number" dataKey="y" name={scatter.y_col}
                tick={{ fontSize: 9, fill: '#9ca3af' }} width={36} />
              <Tooltip contentStyle={{ fontSize: 11, background: '#111827', border: 'none' }} />
              <Scatter data={scatter.points} fill="#38bdf8" fillOpacity={0.5} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: `MlEdaInsights.tsx`** (cards + Copy Markdown)

```tsx
import { useState } from 'react'
import { Lightbulb, Target, Hash, Copy, Check } from 'lucide-react'
import type { EdaReport } from '../../types'
import { edaToMarkdown } from './edaMarkdown'

const SEV: Record<string, string> = {
  high: 'border-red-500/40', medium: 'border-amber-500/40', low: 'border-data/20',
}

export default function MlEdaInsights({ report }: { report: EdaReport }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(edaToMarkdown(report))
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Nguồn insight: {report.insights_source === 'ai' ? 'AI' : 'Quy tắc (rule-based)'}
        </p>
        <button onClick={copy}
          className="flex items-center gap-1 rounded-md border border-data/30 px-2 py-1 text-xs text-gray-200 hover:bg-data/10">
          {copied ? <Check size={13} /> : <Copy size={13} />} Copy Markdown
        </button>
      </div>
      {report.insights.map((i, n) => (
        <div key={n} className={`rounded-lg border p-3 space-y-1.5 ${SEV[i.severity] ?? SEV.low}`}>
          <p className="flex items-center gap-1.5 text-xs font-medium text-data">
            <Hash size={13} /> {i.finding}
          </p>
          <p className="flex items-start gap-1.5 text-xs text-gray-300">
            <Lightbulb size={13} className="mt-0.5 shrink-0" /> {i.so_what}
          </p>
          <p className="flex items-start gap-1.5 text-xs text-gray-300">
            <Target size={13} className="mt-0.5 shrink-0" /> {i.action}
          </p>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 6: `MlEdaView.tsx`** (orchestration; reuse `CorrelationHeatmap`)

```tsx
import { useState } from 'react'
import type { DatasetInfo, EdaReport } from '../../types'
import { runEda } from '../../api/ml'
import CorrelationHeatmap from './CorrelationHeatmap'
import MlEdaProfile from './MlEdaProfile'
import MlEdaDistribution from './MlEdaDistribution'
import MlEdaSegments from './MlEdaSegments'
import MlEdaInsights from './MlEdaInsights'

export default function MlEdaView({ dataset }: { dataset: DatasetInfo }) {
  const [report, setReport] = useState<EdaReport | null>(null)
  const [busy, setBusy]     = useState(false)
  const [error, setError]   = useState('')

  async function generate() {
    setBusy(true); setError('')
    try {
      setReport(await runEda(dataset.file_id))
    } catch (e) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Không tạo được báo cáo EDA')
    } finally { setBusy(false) }
  }

  return (
    <div className="p-4 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-200">Auto-EDA</h2>
          <p className="text-xs text-gray-500">
            Hồ sơ dữ liệu · tương quan · phân phối · nhóm · insight Finding→So-what→Action.
          </p>
        </div>
        <button onClick={generate} disabled={busy}
          className="rounded-md bg-data px-4 py-2 text-xs font-medium text-black disabled:opacity-40">
          {busy ? 'Đang phân tích…' : 'Tạo báo cáo'}
        </button>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {report && (
        <div className="space-y-6">
          <section><MlEdaInsights report={report} /></section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Hồ sơ cột</h3>
            <MlEdaProfile columns={report.profile} />
          </section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Tương quan</h3>
            <CorrelationHeatmap data={report.correlation} />
          </section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Phân phối</h3>
            <MlEdaDistribution dists={report.distributions} />
          </section>
          <section>
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Phân tích nhóm</h3>
            <MlEdaSegments segments={report.segments} />
          </section>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 7: Build gate**

Run: `cd frontend ; npm run build`
Expected: PASS. (Confirm `CorrelationHeatmap`'s default export name + prop `data: CorrelationMatrix` matches the import.)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ml/MlEda*.tsx frontend/src/components/ml/edaMarkdown.ts
git commit -m "feat(eda): MlEdaView + profile/dist/segments/insights + markdown" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 21: Frontend — wire the Auto-EDA tab into `MlResultTabs`

**Files:**
- Modify: `frontend/src/components/ml/MlResultTabs.tsx`

> Task 10 deliberately wired only Merge — importing `Telescope`/`MlEdaView` before `MlEdaView` existed would break the build via `noUnusedLocals`. Now that Task 20 created `MlEdaView`, add the EDA tab.

- [ ] **Step 1: Add the `Telescope` icon + `MlEdaView` import**

In `frontend/src/components/ml/MlResultTabs.tsx`, add `Telescope` to the `lucide-react` import (now used by the new TABS entry):

```tsx
import { BarChart2, Table, FlaskConical, TrendingUp, Users, Upload, Combine, Telescope } from 'lucide-react'
```

Add the view import below the existing `MlMergeView` import:

```tsx
import MlEdaView      from './MlEdaView'
```

- [ ] **Step 2: Add the `eda` TABS entry (last) + the render block**

Append the `eda` entry to the `TABS` array (after the `cohort` entry):

```tsx
  { key: 'eda',      label: 'Auto-EDA', Icon: Telescope    },
```

Inside the dataset-guarded fragment (the `{activeTab !== 'merge' && dataset && ( … )}` block), add the EDA div after the `cohort` div:

```tsx
            <div className={activeTab === 'eda'      ? '' : 'hidden'}>
              <MlEdaView dataset={dataset} />
            </div>
```

- [ ] **Step 3: Full frontend build**

Run: `cd frontend ; npm run build`
Expected: PASS (`tsc -b && vite build`). Confirm no unused-import errors — `Telescope` and `MlEdaView` are now both used.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ml/MlResultTabs.tsx
git commit -m "feat(eda): wire Auto-EDA tab into MlResultTabs" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 22: Final verification + delivery to MAIN

**Files:** none (verification + git).

- [ ] **Step 1: Full backend test suite**

Run: `cd backend ; uv run pytest -q`
Expected: All `test_merge.py` + `test_ml_eda.py` tests PASS. Only the 8 pre-existing `test_sql_sandbox.py` failures remain (unrelated — missing `data/vina_brew` fixtures; documented in memory). If any OTHER test fails, stop and fix before delivery.

- [ ] **Step 2: Full frontend build**

Run: `cd frontend ; npm run build`
Expected: PASS, no type/unused errors.

- [ ] **Step 3: Manual smoke (recommended)**

After delivery, run `python run.py` from the MAIN tree and verify the two new tabs end-to-end:
- **Gộp file:** drop 2+ CSVs with overlapping columns → common-field chips highlight → select + mark phone/key → run → summary cards → Download CSV/XLSX → lands on Auto-EDA.
- **Auto-EDA:** "Tạo báo cáo" → insights cards (Finding→So-what→Action) + profile table + correlation heatmap + histograms + segment table/scatter + Copy Markdown.

- [ ] **Step 4: Deliver to MAIN (local FF-merge, NEVER push)**

Announce: "I'm using the finishing-a-development-branch skill to complete this work."

**REQUIRED SUB-SKILL:** Use `superpowers:finishing-a-development-branch`. When presenting options, the correct choice here is **local FF-merge into master in the MAIN working tree** (`D:\assitant_tools\tools_performance\08_Projects\leonie`), because the user runs MAIN, not this worktree.

**HARD CONSTRAINT — do NOT push.** Master history contains real secrets. No `git push` of master or any normal branch. Local commits + local merge only.

---
---

## Self-Review

**1. Spec coverage**

| Spec requirement | Task(s) |
| --- | --- |
| Merge: normalize field names | Task 1 (`normalize_field`) |
| Merge: phone cleaning (notebook) | Task 1 (`clean_phone`), Task 3 (`phone_cols`) |
| Merge: detect COMMON fields (intersection) | Task 2 (`common_fields`), Task 5 (stage exposes them) |
| Merge: chip/button list + pick | Task 11 (`MlMergeChips`) |
| Merge: union differing schemas/nulls/dupes | Task 3 (`align_and_merge`) |
| Merge: dedup + drop-null-key + trim options | Task 3, Task 6, Task 11 |
| Merge: output dataset + download (CSV/XLSX) | Task 6 (dataset), Task 8 (download), Task 11 (buttons) |
| Merge: stage/run/delete session lifecycle | Tasks 5, 6, 7 |
| Merge: read CSV + XLSX (pick sheet) | Task 5 (`_read_upload` sheet param) |
| Merge: parquet staging + read | Task 4, Task 5 |
| EDA: profile (shape, null, dtypes, role) | Task 13 (`profile_columns`), Task 20 (`MlEdaProfile`) |
| EDA: correlation chart | Task 14 (`correlation_matrix`), Task 20 (reuse `CorrelationHeatmap`) |
| EDA: distribution charts + skew/log | Task 15, Task 20 (`MlEdaDistribution`) |
| EDA: cluster via group-by + scatter | Task 16 (`segment_breakdown`), Task 20 (`MlEdaSegments`) |
| EDA: 3-5 insights Finding→So-what→Action | Task 17 (rule), Task 18 (AI+fallback), Task 20 (`MlEdaInsights`) |
| EDA: AI insight + rule fallback | Task 18 (`_ai_insights` → `derive_rule_insights`) |
| EDA: single Generate button | Task 20 (`MlEdaView` "Tạo báo cáo") |
| EDA: export on-screen + Copy Markdown | Task 20 (`edaMarkdown.ts`, `MlEdaInsights`) |
| Exact aggregation on full data; only scatter sampled | Task 16 (`sample_n` only on scatter), Task 18 |
| Both features under ML Studio as tabs | Task 10 (Merge tab + store union) · Task 21 (EDA tab) |
| Merge reachable with no active dataset | Task 10 (short-circuit rework) |
| Merge output flows into Studio | Task 12 (`onDatasetCreated`) |
| Language Vietnamese | All frontend tasks (VN labels) |
| Deliver MAIN, never push | Task 22 |

No spec requirement is left without a task.

**2. Placeholder scan**

- Every code step contains complete code (no `null`/TODO placeholders). `MlResultTabs` is edited in two tasks on purpose: Task 10 wires only Merge (full component body given), and Task 21 adds the EDA tab once `MlEdaView` exists (Task 20). This split keeps `noUnusedLocals` satisfied — no temporary stubs needed. The frontend build gate is deferred to Task 12 (Merge) because Task 10 makes `onDatasetCreated` a required prop that `MlStudio.tsx` only passes in Task 12.
- Task 17 flags the illustrative `«` glyph and gives the exact replacement f-string — fix it inline when typing.

**3. Type consistency**

- `MergeSummary` fields (`total_raw, valid, nulls, duplicates_removed, distinct, complete_records`) are identical across the dataclass (Task 3), `MergeSummaryOut` (Task 6), and the TS `MergeSummary` (Task 9) and the `CARDS` keys (Task 11).
- `align_and_merge` signature (Task 3) matches its call in `merge_run` (Task 6): positional `frames, selected, alias_map` + keyword `dedup_key/drop_null_key/trim/phone_cols`.
- `runMerge(sessionId, selectedFields, aliasMap, options)` (Task 9) matches `MlMergeView`'s call (Task 11) and the backend `MergeRunIn` shape (Task 6).
- EDA report keys returned by `run_eda` (Task 18: `meta, profile, correlation, distributions, segments, insights, insights_source`) match the TS `EdaReport` (Task 19) and every consumer component (Task 20).
- `correlation_matrix` returns `{columns, matrix, excluded_columns}` (Task 14) — matches the TS `CorrelationMatrix` (existing) consumed by `CorrelationHeatmap` (Task 20).
- `profile_columns` dict keys (`name, dtype, role, cardinality, null_pct, is_constant, samples, min?, max?`) match the existing TS `ProfileColumn` reused in Task 19/20.
- `insights` item keys (`finding, so_what, action, severity`) consistent across Task 17, Task 18 (`_ai_insights` validation), TS `EdaInsight` (Task 19), and `MlEdaInsights` (Task 20).
- Tab union `'merge' | 'table' | 'charts' | 'stats' | 'forecast' | 'cohort' | 'eda'` identical in store (Task 10) and `MlResultTabs` local `Tab` (Task 10).

All consistent.
