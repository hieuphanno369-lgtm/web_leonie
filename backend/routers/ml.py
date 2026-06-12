import os
import io
import csv
import re
import json
import shutil
import uuid
import time
import pathlib
import warnings
import urllib.request
import numpy as np
import duckdb
import polars as pl
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel, Field
from scipy import stats as scipy_stats
from database import get_connection, UPLOADS_DIR
from typing import Literal
from analytics.timegrain import aggregate_series, suggest_grain, add_comparisons, Grain, Agg
from analytics.cohort_check import check_suitability
from analytics.forecast_check import check_forecast_suitability
from analytics.codegen import (
    forecast_code, timeseries_code, correlation_code, stats_code, cohort_code,
    describe_code, drilldown_code, merge_code, _DRILL_FMT,
)
from analytics.merge import (
    common_fields, align_and_merge,
    profile_columns as profile_merge_columns, suggest_groups,
)
from analytics.eda import (
    profile_columns, correlation_matrix, numeric_distributions,
    segment_breakdown, derive_rule_insights,
)


# ── AI helper (Claude → Ollama fallback) ────────────────────────────────────

def _call_ai_ml(prompt: str, max_tokens: int = 1024) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    ollama_url   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = json.dumps({"model": ollama_model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["response"].strip()
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")

router = APIRouter(prefix="/ml", tags=["ml"])

MAX_FILE_BYTES = 500 * 1024 * 1024  # 500 MB

MERGE_SESSIONS_DIR = UPLOADS_DIR.parent / "merge_sessions"
MERGE_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class ColumnInfo(BaseModel):
    name: str
    dtype: str


class DatasetInfo(BaseModel):
    file_id: str
    filename: str
    rows: int
    cols: int
    columns: list[ColumnInfo]


class QueryIn(BaseModel):
    file_id: str
    sql: str


class QueryOut(BaseModel):
    columns: list[str]
    rows: list[list]
    duration_ms: float


class StatsIn(BaseModel):
    file_id: str
    test: str   # describe | correlation | ttest | distribution | anova | chi2 | bootstrap | mannwhitney | boxplot
    col_a: str
    col_b: str | None = None
    max_groups: int = Field(default=10, ge=1, le=100)


class ForecastIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7
    method: str = 'linear'          # linear | moving_average | sarimax | supervised | ets
    seasonal_period: int | None = None   # None → derive from grain
    grain: Grain | Literal["auto", "raw"] = "auto"
    agg: Agg = "sum"


class ForecastCompareIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7
    seasonal_period: int = 12
    methods: list[str]
    grain: Grain | Literal["auto", "raw"] = "auto"
    agg: Agg = "sum"


class ForecastInterpretIn(BaseModel):
    method: str
    date_col: str
    value_col: str
    periods: int
    result: dict
    filename: str


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


def _read_source(filepath: str) -> pl.DataFrame:
    """Parse the original upload (parquet/xlsx/xls/csv). Slow for large Excel files."""
    p = pathlib.Path(filepath)
    if p.suffix.lower() == ".parquet":
        return pl.read_parquet(p)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pl.read_excel(p)
    return pl.read_csv(p, infer_schema_length=10000)


def _parquet_sidecar(filepath: str) -> pathlib.Path:
    """Cache path next to the source, e.g. '<id>_Churn.xlsx' -> '<id>_Churn.xlsx.parquet'."""
    p = pathlib.Path(filepath)
    return p.with_name(p.name + ".parquet")


def _sidecar_is_fresh(filepath: str, pq: pathlib.Path) -> bool:
    """A sidecar is usable only if it exists and is at least as new as its source."""
    try:
        return pq.exists() and pq.stat().st_mtime >= os.path.getmtime(filepath)
    except OSError:
        return False


def _load_df(filepath: str) -> pl.DataFrame:
    """Load a dataset, reading a parquet cache when fresh and (re)building it otherwise.

    Parsing a 726k-row xlsx costs ~3s; the parquet sidecar reads in ~50ms, which
    is what keeps every ML operation fast enough to stay under the request timeout.
    Cache reads/writes are best-effort: any failure falls back to the source.
    """
    pq = _parquet_sidecar(filepath)
    if _sidecar_is_fresh(filepath, pq):
        try:
            return pl.read_parquet(pq)
        except Exception:
            pass  # corrupt/partial cache → rebuild from source below
    df = _read_source(filepath)
    try:
        df.write_parquet(pq)
    except Exception:
        pass  # read-only dir or disk full → serve uncached, correctness preserved
    return df


def _schema_cols(filepath: str) -> list[ColumnInfo]:
    """Return column metadata without loading row data when a fresh cache exists."""
    pq = _parquet_sidecar(filepath)
    if _sidecar_is_fresh(filepath, pq):
        try:
            schema = pl.scan_parquet(pq).collect_schema()
            return [ColumnInfo(name=n, dtype=str(t)) for n, t in schema.items()]
        except Exception:
            pass  # fall through to a full load (which also rebuilds the cache)
    df = _load_df(filepath)
    return [ColumnInfo(name=c, dtype=str(df[c].dtype)) for c in df.columns]


def _get_file_row(conn, file_id: str):
    row = conn.execute(
        "SELECT * FROM uploaded_files WHERE file_id = ?", (file_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return row


def _numeric_cols(df: pl.DataFrame) -> list[str]:
    return [c for c in df.columns if df[c].dtype.is_numeric()]


_SUBSTRING_DATE_KEYWORDS = ("date", "time", "year")


def _is_date_id_column(col: str) -> bool:
    lower = col.lower()
    if any(kw in lower for kw in _SUBSTRING_DATE_KEYWORDS):
        return True
    if lower == "id" or lower.endswith("_id") or lower.startswith("id_"):
        return True
    return False


# ── Box Plot helpers ─────────────────────────────────────────────────────────

_TUKEY_IQR_MULTIPLIER    = 1.5
_MIN_BOX_SAMPLES         = 4
_MAX_OUTLIERS_IN_HANDLER = 1000


def _compute_box_stats(arr: np.ndarray, name: str) -> dict | None:
    """Compute Tukey box-plot statistics for a single 1-D numeric array.

    Returns None when the cleaned array has fewer than _MIN_BOX_SAMPLES values
    (cannot compute meaningful quartiles). Returned dict uses raw floats
    (no rounding) and includes uncapped outlier_indices / outlier_values so
    callers can choose how to render.
    """
    arr = arr[~np.isnan(arr)]
    if len(arr) < _MIN_BOX_SAMPLES:
        return None
    q1, med, q3 = np.percentile(arr, [25, 50, 75])
    iqr = float(q3 - q1)
    lo  = float(q1 - _TUKEY_IQR_MULTIPLIER * iqr)
    hi  = float(q3 + _TUKEY_IQR_MULTIPLIER * iqr)
    mask = (arr < lo) | (arr > hi)
    idx  = np.where(mask)[0]
    return {
        "name":            name,
        "n":               int(len(arr)),
        "min":             float(arr.min()),
        "q1":              float(q1),
        "median":          float(med),
        "q3":              float(q3),
        "max":             float(arr.max()),
        "iqr":             iqr,
        "lower_fence":     lo,
        "upper_fence":     hi,
        "outlier_indices": idx,
        "outlier_values":  arr[mask],
    }


def _safe_csv_filename(prefix: str, col: str, original_filename: str) -> str:
    """Build a safe Content-Disposition filename — strips header-breaking chars."""
    safe_col  = re.sub(r"[^A-Za-z0-9._-]", "_", col)[:80]
    safe_orig = re.sub(r"[^A-Za-z0-9._-]", "_", original_filename)[:120]
    return f"{prefix}_{safe_col}_{safe_orig}"


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
    dup_count = df.shape[0] - df.unique().shape[0]
    if dup_count > 0:
        issues.append(QualityIssue(
            type="duplicate",
            column=None,
            detail=f"{dup_count} duplicate rows",
        ))

    # Outliers — modified z-score (MAD-based, robust) > 3.5 for numeric columns
    # Uses median absolute deviation so a single extreme outlier doesn't inflate std
    for col in _numeric_cols(df):
        series = df[col].drop_nulls().cast(pl.Float64)
        if len(series) < 2:
            continue
        median_val = series.median()
        mad = (series - median_val).abs().median()
        if not mad or mad == 0:
            continue
        mod_z = (series - median_val).abs() * 0.6745 / mad
        outlier_count = int((mod_z > 3.5).sum())
        if outlier_count > 0:
            issues.append(QualityIssue(
                type="outlier",
                column=col,
                detail=f"{outlier_count} outlier{'s' if outlier_count != 1 else ''} (modified z > 3.5)",
            ))

    # Constant columns — only 1 unique value (skip if entirely null to avoid double-report)
    for col in df.columns:
        if df[col].null_count() < n_rows and df[col].n_unique() == 1:
            issues.append(QualityIssue(
                type="constant",
                column=col,
                detail="Only 1 unique value",
            ))

    # Dtype mismatch — column name suggests temporal/ID but stored as string
    for col in df.columns:
        if _is_date_id_column(col):
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


@router.get("/datasets", response_model=list[DatasetInfo])
def list_datasets():
    conn = get_connection()
    rows = conn.execute(
        "SELECT file_id, filename, filepath, rows, cols FROM uploaded_files ORDER BY uploaded DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        try:
            cols = _schema_cols(r["filepath"])
        except Exception:
            cols = []
        result.append(DatasetInfo(
            file_id=r["file_id"], filename=r["filename"],
            rows=r["rows"] or 0, cols=r["cols"] or 0, columns=cols,
        ))
    return result


@router.post("/upload", response_model=DatasetInfo, status_code=201)
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 500 MB limit")
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO uploaded_files (filename, filepath, rows, cols) VALUES (?,?,0,0)",
        (file.filename, ""),
    )
    file_id = conn.execute(
        "SELECT file_id FROM uploaded_files WHERE rowid=?", (cur.lastrowid,)
    ).fetchone()[0]
    conn.commit()

    dest = UPLOADS_DIR / f"{file_id}_{file.filename}"
    dest.write_bytes(content)

    try:
        df = _load_df(str(dest))
        rows, cols = df.shape
        cols_info = [ColumnInfo(name=c, dtype=str(df[c].dtype)) for c in df.columns]
    except Exception as e:
        conn.execute("DELETE FROM uploaded_files WHERE file_id=?", (file_id,))
        conn.commit()
        conn.close()
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Cannot parse file: {e}")

    conn.execute(
        "UPDATE uploaded_files SET filepath=?, rows=?, cols=? WHERE file_id=?",
        (str(dest), rows, cols, file_id),
    )
    conn.commit()
    conn.close()
    return DatasetInfo(file_id=file_id, filename=file.filename,
                       rows=rows, cols=cols, columns=cols_info)


# ── Multi-file Merge ─────────────────────────────────────────────────────────

class MergeFileSchema(BaseModel):
    filename: str
    fields: list[str]


class ColumnProfileOut(BaseModel):
    file: str
    name: str
    norm: str
    inferred_type: str
    confidence: float
    samples: list[str]
    non_null: int
    distinct: int
    fill_rate: float


class FieldGroupSuggestionOut(BaseModel):
    canonical: str
    members: list[str]
    inferred_type: str
    confidence: float
    reason: str


class MergeStageOut(BaseModel):
    session_id: str
    files: list[MergeFileSchema]
    common_fields: list[str]
    all_fields: list[str]
    profiles: list[ColumnProfileOut]
    suggestions: list[FieldGroupSuggestionOut]


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
    frames = [pl.read_parquet(sdir / m["parquet"]) for m in manifest]
    fnames = [m["filename"] for m in manifest]
    profiles = profile_merge_columns(frames, fnames)
    suggestions = suggest_groups(profiles)
    return MergeStageOut(
        session_id=sid,
        files=[MergeFileSchema(filename=m["filename"], fields=m["fields"]) for m in manifest],
        common_fields=common_fields(schemas),
        all_fields=seen,
        profiles=[ColumnProfileOut(**p.__dict__) for p in profiles],
        suggestions=[FieldGroupSuggestionOut(**g.__dict__) for g in suggestions],
    )


class MergeOptions(BaseModel):
    dedup_key: str | None = None
    drop_invalid_key: bool = True
    trim: bool = True
    semantic_types: dict[str, str] = {}
    field_groups: dict[str, list[str]] = {}
    required_fields: list[str] = []
    coalesce: bool = True


class MergeRunIn(BaseModel):
    session_id: str
    selected_fields: list[str]
    alias_map: dict[str, str] = {}
    options: MergeOptions = MergeOptions()
    dry_run: bool = False


class MergeSummaryOut(BaseModel):
    total_raw: int
    valid_format: int
    null_or_wrong: int
    distinct: int
    dup_removed_clean: int
    dup_removed_raw: int
    complete: int
    incomplete: int
    rejected: int
    per_field_fill_rate: dict[str, float]
    per_file_contribution: dict[str, int]


class MergeRunOut(BaseModel):
    summary: MergeSummaryOut
    dataset: DatasetInfo | None = None
    preview: list[dict] | None = None
    rejected_url: str | None = None
    code: str | None = None  # Show Code: pipeline Python tái hiện đúng lần gộp này


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
    fnames = [m["filename"] for m in manifest]

    o = body.options
    clean, rejected, summary = align_and_merge(
        frames, body.selected_fields, body.alias_map,
        filenames=fnames,
        field_groups=o.field_groups,
        semantic_types=o.semantic_types,
        dedup_key=o.dedup_key,
        required_fields=o.required_fields,
        coalesce=o.coalesce,
        drop_invalid_key=o.drop_invalid_key,
        trim=o.trim,
    )
    summary_out = MergeSummaryOut(**summary.__dict__)

    # Show Code: chuỗi Python tái hiện đúng pipeline vừa chạy (cả dry-run & thật).
    code = merge_code(
        fnames, body.selected_fields, body.alias_map,
        field_groups=o.field_groups,
        semantic_types=o.semantic_types,
        dedup_key=o.dedup_key,
        required_fields=o.required_fields,
        coalesce=o.coalesce,
        drop_invalid_key=o.drop_invalid_key,
        trim=o.trim,
    )

    # Persist clean + rejected trong CẢ hai nhánh ⇒ nút "Xuất CSV/XLSX" và "Tải bản
    # bị loại" hoạt động ngay ở bước Xem trước (dry-run), không chỉ sau khi tạo dataset.
    clean.write_parquet(sdir / "clean.parquet")
    rejected.write_csv(sdir / "rejected.csv")
    rejected_url = f"/api/ml/merge/{body.session_id}/rejected.csv"

    if body.dry_run:
        preview = clean.head(30).to_dicts()
        return MergeRunOut(summary=summary_out, preview=preview,
                           rejected_url=rejected_url, code=code)

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
    clean.write_parquet(dest)
    rows, cols = clean.shape
    conn.execute(
        "UPDATE uploaded_files SET filepath=?, rows=?, cols=? WHERE file_id=?",
        (str(dest), rows, cols, file_id),
    )
    conn.commit()
    conn.close()

    cols_info = [ColumnInfo(name=c, dtype=str(clean[c].dtype)) for c in clean.columns]
    return MergeRunOut(
        summary=summary_out,
        dataset=DatasetInfo(file_id=file_id, filename=out_name,
                            rows=rows, cols=cols, columns=cols_info),
        rejected_url=rejected_url,
        code=code,
    )


@router.delete("/merge/{session_id}", status_code=204)
def merge_delete(session_id: str):
    sdir = MERGE_SESSIONS_DIR / session_id
    if sdir.exists():
        shutil.rmtree(sdir, ignore_errors=True)


@router.get("/merge/{session_id}/rejected.csv")
def merge_rejected(session_id: str):
    path = MERGE_SESSIONS_DIR / session_id / "rejected.csv"
    if not path.exists():
        raise HTTPException(404, "No rejected rows for this session")
    return Response(
        content=path.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="rejected.csv"'},
    )


@router.get("/merge/{session_id}/download")
def merge_download_clean(session_id: str, fmt: str = "csv"):
    """Tải kết quả gộp ĐÃ LÀM SẠCH (clean.parquet) dạng CSV hoặc XLSX.

    clean.parquet được ghi ở cả dry-run lẫn lần tạo thật ⇒ tải được ngay ở bước
    "Xem & tạo", không cần tạo dataset trước. (3 đoạn path ⇒ không đụng route
    /{file_id}/download chỉ có 2 đoạn.)"""
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(400, "fmt must be 'csv' or 'xlsx'")
    path = MERGE_SESSIONS_DIR / session_id / "clean.parquet"
    if not path.exists():
        raise HTTPException(404, "No merged result for this session yet")
    df = pl.read_parquet(path)
    if fmt == "csv":
        return Response(
            content=df.write_csv().encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="combined_clean.csv"'},
        )
    bio = io.BytesIO()
    df.write_excel(bio)
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="combined_clean.xlsx"'},
    )


@router.post("/query", response_model=QueryOut)
def run_query(body: QueryIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    try:
        df = _load_df(row["filepath"])
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot read dataset: {e}")
    try:
        t0 = time.perf_counter()
        dconn = duckdb.connect()
        dconn.register("data", df)
        result = dconn.execute(body.sql).fetchall()
        desc = dconn.description
        duration_ms = (time.perf_counter() - t0) * 1000
        columns = [d[0] for d in desc]
        rows = [list(r) for r in result[:10_000]]
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    return QueryOut(columns=columns, rows=rows, duration_ms=round(duration_ms, 2))


@router.delete("/{file_id}", status_code=204)
def delete_dataset(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    pathlib.Path(row["filepath"]).unlink(missing_ok=True)
    _parquet_sidecar(row["filepath"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM uploaded_files WHERE file_id=?", (file_id,))
    conn.commit()
    conn.close()


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


@router.get("/{file_id}/correlation")
def get_correlation(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])

    candidates = _numeric_cols(df)[:15]
    excluded: list[dict] = []
    cols: list[str] = []
    for c in candidates:
        s = df[c]
        if s.null_count() == len(s):
            excluded.append({"name": c, "reason": "all_null"})
        elif s.n_unique() <= 1:
            excluded.append({"name": c, "reason": "constant"})
        else:
            cols.append(c)

    if len(cols) < 2:
        raise HTTPException(
            400,
            "Cần ít nhất 2 cột số có biến thiên để tính tương quan "
            f"(đã loại {len(excluded)} cột hằng số/rỗng).",
        )

    matrix: list[list[float | None]] = []
    for c1 in cols:
        row_vals: list[float | None] = []
        for c2 in cols:
            if c1 == c2:
                row_vals.append(1.0)
                continue
            pair = df.select([c1, c2]).drop_nulls()          # pairwise-complete
            if pair.height < 3:
                row_vals.append(None)
                continue
            a = pair[c1].to_numpy()
            b = pair[c2].to_numpy()
            if a.std() == 0 or b.std() == 0:                 # guard NaN from pearsonr
                row_vals.append(None)
                continue
            try:
                r, _ = scipy_stats.pearsonr(a, b)
                row_vals.append(round(float(r), 4) if np.isfinite(r) else None)
            except Exception:
                row_vals.append(None)
        matrix.append(row_vals)

    return {
        "columns": cols, "matrix": matrix, "excluded_columns": excluded,
        "code": correlation_code(cols, row["filename"]),
    }


@router.get("/{file_id}/describe")
def describe_dataset(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    rows = []
    for col in df.columns:
        s = df[col]
        null_pct = round(s.null_count() / max(len(s), 1) * 100, 1)
        entry: dict = {"col": col, "dtype": str(s.dtype), "nulls": null_pct}
        if s.dtype.is_numeric():
            arr = s.drop_nulls().cast(pl.Float64)
            if len(arr) > 0:
                mn = round(float(arr.min()), 4)    # type: ignore[arg-type]
                mx = round(float(arr.max()), 4)    # type: ignore[arg-type]
                entry["min"]    = mn
                entry["max"]    = mx
                entry["mean"]   = round(float(arr.mean()), 4)    # type: ignore[arg-type]
                entry["median"] = round(float(arr.median()), 4)  # type: ignore[arg-type]
                entry["range"]  = round(mx - mn, 4)
                entry["std"]    = round(float(arr.std()), 4)     # type: ignore[arg-type]
        rows.append(entry)
    return {"rows": rows, "code": describe_code(row["filename"])}


def _agg_expr(col: pl.Expr, agg: str) -> pl.Expr:
    return {
        "sum": col.sum(), "mean": col.mean(), "count": col.count(),
        "n_unique": col.n_unique(), "min": col.min(), "max": col.max(),
    }.get(agg, col.sum())


@router.get("/{file_id}/drilldown")
def drilldown_dataset(
    file_id: str, date_col: str, value_col: str,
    agg: Agg = "sum",
    grain: Literal["year", "month", "day"] = "year",
    year: int | None = None, month: int | None = None,
):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    for col in (date_col, value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")
    try:
        parsed = _try_parse_dates(df[date_col])
    except ValueError as e:
        raise HTTPException(400, f"Không thể parse cột ngày '{date_col}': {e}")

    work = df.with_columns(parsed.alias("_d")).drop_nulls(subset=["_d"])
    if year is not None:
        work = work.filter(pl.col("_d").dt.year() == year)
    if month is not None:
        work = work.filter(pl.col("_d").dt.month() == month)

    code = drilldown_code(date_col, value_col, row["filename"], grain, agg, year, month)
    if work.height == 0:
        return {"grain": grain, "labels": [], "values": [],
                "value_col": value_col, "agg": agg, "code": code}

    fmt = _DRILL_FMT[grain]
    grouped = (
        work.with_columns(pl.col("_d").dt.strftime(fmt).alias("_k"))
        .group_by("_k")
        .agg(_agg_expr(pl.col(value_col), agg).alias("_v"))
        .sort("_k")
    )
    return {
        "grain": grain,
        "labels": grouped["_k"].to_list(),
        "values": [None if v is None else round(float(v), 4) for v in grouped["_v"].to_list()],
        "value_col": value_col,
        "agg": agg,
        "code": code,
    }


def _infer_role(col: str, s: pl.Series, nunq: int, n: int, is_num: bool) -> str:
    name = col.lower()
    dt = str(s.dtype).lower()
    # date
    if dt.startswith("date") or dt.startswith("datetime"):
        return "date"
    if not is_num:
        try:
            parsed = _try_parse_dates(s)
            if parsed.null_count() < len(parsed):
                return "date"
        except Exception:
            pass
    # id
    if re.search(r"(^id$|_id$|^id_|\bcode\b|phone|msisdn)", name):
        return "id"
    if (not is_num) and n > 0 and nunq >= 0.9 * n:
        return "id"
    # flag
    if (is_num or dt == "boolean") and nunq <= 2:
        return "flag"
    # metric
    if is_num:
        return "metric"
    # dimension (low-cardinality categorical) — default for the rest
    return "dimension"


@router.get("/profile/{file_id}")
def profile_dataset(file_id: str):
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    n = df.height
    out = []
    for col in df.columns:
        s = df[col]
        nunq = int(s.n_unique())
        is_num = s.dtype.is_numeric()
        entry: dict = {
            "name": col,
            "dtype": str(s.dtype),
            "role": _infer_role(col, s, nunq, n, is_num),
            "cardinality": nunq,
            "null_pct": round(s.null_count() / max(n, 1) * 100, 1),
            "is_constant": bool(s.null_count() < n and nunq <= 1),
            "samples": [str(v) for v in s.drop_nulls().unique().head(3).to_list()],
        }
        if is_num:
            arr = s.drop_nulls().cast(pl.Float64)
            if len(arr) > 0:
                entry["min"] = round(float(arr.min()), 4)   # type: ignore[arg-type]
                entry["max"] = round(float(arr.max()), 4)   # type: ignore[arg-type]
        out.append(entry)
    return {"columns": out, "rows": n}


class TimeseriesIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    grain: Grain | Literal["auto"] = "auto"
    agg: Agg = "sum"
    comparisons: list[str] = []
    rolling_window: int = 7
    cumulative_reset: Literal["month", "quarter", "year"] = "year"
    group_col: str | None = None


@router.post("/timeseries")
def run_timeseries(body: TimeseriesIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    for col in (body.date_col, body.value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        parsed = _try_parse_dates(df[body.date_col])
    except ValueError as e:
        raise HTTPException(400, f"Không thể parse cột ngày '{body.date_col}': {e}")

    df = df.with_columns(parsed.alias("_d")).drop_nulls(subset=["_d"])
    if df.height == 0:
        raise HTTPException(400, "Không có ngày hợp lệ sau khi parse")

    dmin, dmax = df["_d"].min(), df["_d"].max()
    suggested = suggest_grain(dmin, dmax)
    grain = suggested if body.grain == "auto" else body.grain

    series = aggregate_series(df, "_d", body.value_col, grain, body.agg)
    comps = add_comparisons(
        series["period_starts"], series["values"], grain,
        body.comparisons, body.rolling_window, body.cumulative_reset,
    )

    return {
        "grain": grain,
        "agg": body.agg,
        "date_col": body.date_col,
        "value_col": body.value_col,
        "series": {"labels": series["labels"], "values": series["values"]},
        "comparisons": comps,
        "code": timeseries_code(body.date_col, body.value_col, row["filename"],
                                grain, body.agg, body.comparisons,
                                body.rolling_window, body.cumulative_reset),
        "meta": {
            "rows_used": df.height,
            "periods": len(series["labels"]),
            "span_days": (dmax - dmin).days,
            "suggested_grain": suggested,
        },
    }


class CohortIn(BaseModel):
    file_id: str
    date_col: str
    user_col: str
    period: str = "month"      # "month" | "week" | "day"
    filter_col:  str | None = None
    filter_val:  str | None = None
    offset_col:  str | None = None   # pre-aggregated: column holding period index (0,1,2...)
    metric_col:  str | None = None   # pre-aggregated: column to SUM instead of COUNT DISTINCT


_DATE_FORMATS = [
    "%Y-%m-%d",   # 2026-01-15
    "%Y/%m/%d",   # 2026/01/15
    "%d-%m-%Y",   # 15-01-2026
    "%d/%m/%Y",   # 15/01/2026
]

def _try_parse_dates(series: pl.Series) -> pl.Series:
    """Try multiple date formats, return parsed Date series or raise ValueError."""
    raw = series.cast(pl.Utf8)

    # Try explicit formats first
    for fmt in _DATE_FORMATS:
        try:
            parsed = raw.str.to_date(fmt, strict=False)
            if parsed.null_count() < len(parsed):
                return parsed
        except Exception:
            continue

    # YYYY-MM or YYYY/MM (e.g. "2026-01") → pad to "2026-01-01"
    padded = raw.str.replace_all(r"^(\d{4})[-/](\d{1,2})$", "${1}-${2}-01")
    try:
        parsed = padded.str.to_date("%Y-%m-%d", strict=False)
        if parsed.null_count() < len(padded):
            return parsed
    except Exception:
        pass

    # MM-YYYY or MM/YYYY (e.g. "01-2026") → rearrange to "2026-01-01"
    rearranged = raw.str.replace_all(r"^(\d{1,2})[-/](\d{4})$", "${2}-${1}-01")
    try:
        parsed = rearranged.str.to_date("%Y-%m-%d", strict=False)
        if parsed.null_count() < len(rearranged):
            return parsed
    except Exception:
        pass

    samples = raw.drop_nulls()[:3].to_list()
    raise ValueError(f"Cannot parse date column. Samples: {samples}. Expected: YYYY-MM-DD, YYYY-MM, MM-YYYY, DD-MM-YYYY.")


@router.get("/{file_id}/column-values")
def get_column_values(file_id: str, col: str):
    """Return sorted unique values of a column (max 200) for filter dropdowns."""
    conn = get_connection()
    row = _get_file_row(conn, file_id)
    conn.close()
    df = _load_df(row["filepath"])
    if col not in df.columns:
        raise HTTPException(400, f"Column '{col}' not found")
    vals = (
        df[col].drop_nulls().cast(pl.Utf8)
        .unique().sort()[:200].to_list()
    )
    return {"values": vals}


@router.post("/cohort")
def run_cohort(body: CohortIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])
    filename = row["filename"]

    for col in (body.date_col, body.user_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    # Apply dimension filter first
    if body.filter_col and body.filter_val:
        if body.filter_col not in df.columns:
            raise HTTPException(400, f"Filter column '{body.filter_col}' not found")
        df = df.filter(pl.col(body.filter_col).cast(pl.Utf8) == body.filter_val)
        if len(df) == 0:
            raise HTTPException(400, f"No rows match {body.filter_col} = '{body.filter_val}'")

    # ── Pre-aggregated mode ─────────────────────────────────────────────────────
    # When offset_col is set the dataset already has period index (0,1,2...) and
    # an optional metric column to SUM instead of counting distinct users.
    if body.offset_col:
        if body.offset_col not in df.columns:
            raise HTTPException(400, f"Offset column '{body.offset_col}' not found")
        if body.metric_col and body.metric_col not in df.columns:
            raise HTTPException(400, f"Metric column '{body.metric_col}' not found")
        if body.date_col not in df.columns:
            raise HTTPException(400, f"Cohort column '{body.date_col}' not found")

        df = df.with_columns([
            pl.col(body.date_col).cast(pl.Utf8).alias("_cohort_label"),
            pl.col(body.offset_col).cast(pl.Int64).alias("_offset"),
        ])

        value_expr = (
            pl.col(body.metric_col).sum()
            if body.metric_col
            else pl.col(body.user_col).n_unique()
        )
        agg_pre = (
            df.group_by(["_cohort_label", "_offset"])
            .agg(value_expr.alias("value"))
            .sort(["_cohort_label", "_offset"])
        )

        base_pre = {r["_cohort_label"]: r["value"]
                    for r in agg_pre.filter(pl.col("_offset") == 0).to_dicts()}
        cohorts_sorted_pre = sorted(base_pre.keys())
        max_offset_pre = min(int(agg_pre["_offset"].max() or 0), 30)

        agg_dict_pre: dict[str, dict[int, float]] = {}
        for r in agg_pre.to_dicts():
            lbl, o, v = r["_cohort_label"], r["_offset"], r["value"]
            if 0 <= o <= max_offset_pre:
                agg_dict_pre.setdefault(lbl, {})[o] = v

        matrix_pre = []
        for c in cohorts_sorted_pre:
            size = base_pre[c]
            row = []
            for o in range(max_offset_pre + 1):
                v = agg_dict_pre.get(c, {}).get(o)
                row.append(round(v / size * 100, 1) if v is not None and size else None)
            matrix_pre.append(row)

        all_users_pre: list[float | None] = []
        for o in range(max_offset_pre + 1):
            num, den = 0.0, 0.0
            for c in cohorts_sorted_pre:
                if o in agg_dict_pre.get(c, {}):
                    size = base_pre[c]
                    den += size
                    num += agg_dict_pre[c][o]
            all_users_pre.append(round(num / den * 100, 1) if den else None)

        return {
            "cohorts":        cohorts_sorted_pre,
            "periods":        list(range(max_offset_pre + 1)),
            "matrix":         matrix_pre,
            "cohort_sizes":   [base_pre[c] for c in cohorts_sorted_pre],
            "all_users_row":  all_users_pre,
            "all_users_size": sum(base_pre.values()),
            "code": cohort_code(body.period, body.date_col, body.user_col,
                                filename, offset_col=body.offset_col,
                                metric_col=body.metric_col,
                                filter_col=body.filter_col, filter_val=body.filter_val),
        }

    # ── Transactional mode (default) ────────────────────────────────────────────
    try:
        parsed = _try_parse_dates(df[body.date_col])
    except ValueError as e:
        raise HTTPException(400, str(e))

    suit = check_suitability(df, body.date_col, body.user_col, parsed)
    if not suit["suitable"]:
        return suit

    df = df.with_columns(parsed.alias("_date"))
    df = df.drop_nulls(subset=["_date"])
    if len(df) == 0:
        raise HTTPException(400, "No valid dates after parsing")

    if body.period == "week":
        df = df.with_columns(
            (pl.col("_date").dt.year() * 100 + pl.col("_date").dt.week()).alias("_period_num")
        )
    elif body.period == "day":
        df = df.with_columns(
            pl.col("_date").dt.epoch("d").cast(pl.Int64).alias("_period_num")
        )
    elif body.period == "quarter":
        # Monotonic quarter index: year*4 + (0..3) ⇒ consecutive quarters differ by 1
        df = df.with_columns(
            (pl.col("_date").dt.year() * 4 + (pl.col("_date").dt.month() - 1) // 3)
            .cast(pl.Int64).alias("_period_num")
        )
    elif body.period == "year":
        df = df.with_columns(
            pl.col("_date").dt.year().cast(pl.Int64).alias("_period_num")
        )
    else:
        df = df.with_columns(
            (pl.col("_date").dt.year() * 100 + pl.col("_date").dt.month()).alias("_period_num")
        )

    cohort_map = (
        df.group_by(body.user_col)
        .agg(pl.col("_period_num").min().alias("_cohort_num"))
    )
    df = df.join(cohort_map, on=body.user_col, how="left")
    df = df.with_columns(
        (pl.col("_period_num") - pl.col("_cohort_num")).alias("_offset")
    )

    agg = (
        df.group_by(["_cohort_num", "_offset"])
        .agg(pl.col(body.user_col).n_unique().alias("users"))
        .sort(["_cohort_num", "_offset"])
    )

    cohort_sizes = {
        r["_cohort_num"]: r["users"]
        for r in agg.filter(pl.col("_offset") == 0).to_dicts()
    }

    cohorts_sorted = sorted(cohort_sizes.keys())
    max_cap = 30 if body.period == "day" else 11
    max_offset = min(int(agg["_offset"].max() or 0), max_cap)

    agg_dict: dict[int, dict[int, int]] = {}
    for r in agg.to_dicts():
        c, o, u = r["_cohort_num"], r["_offset"], r["users"]
        if o <= max_offset:
            agg_dict.setdefault(c, {})[o] = u

    def fmt_period(p: int) -> str:
        if body.period == "week":
            y, m = divmod(p, 100)
            return f"{y}-W{m:02d}"
        elif body.period == "day":
            d = date(1970, 1, 1) + timedelta(days=int(p))
            return d.strftime("%b %d")
        elif body.period == "quarter":
            y, q = divmod(p, 4)
            return f"{y}-Q{q + 1}"
        elif body.period == "year":
            return str(int(p))
        else:
            y, m = divmod(p, 100)
            return f"{y}-{m:02d}"

    matrix = []
    for c in cohorts_sorted:
        size = cohort_sizes[c]
        row = []
        for o in range(max_offset + 1):
            if o in agg_dict.get(c, {}):
                row.append(round(agg_dict[c][o] / size * 100, 1) if size else None)
            else:
                row.append(None)
        matrix.append(row)

    all_users_row: list[float | None] = []
    for o in range(max_offset + 1):
        num, den = 0, 0
        for c in cohorts_sorted:
            if o in agg_dict.get(c, {}):
                size = cohort_sizes[c]
                den += size
                num += agg_dict[c][o]
        all_users_row.append(round(num / den * 100, 1) if den else None)

    return {
        "cohorts":        [fmt_period(c) for c in cohorts_sorted],
        "periods":        list(range(max_offset + 1)),
        "matrix":         matrix,
        "cohort_sizes":   [cohort_sizes[c] for c in cohorts_sorted],
        "all_users_row":  all_users_row,
        "all_users_size": sum(cohort_sizes.values()),
        "code": cohort_code(body.period, body.date_col, body.user_col,
                            filename, filter_col=body.filter_col,
                            filter_val=body.filter_val),
    }


@router.post("/forecast/compare")
def compare_forecast(body: ForecastCompareIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    for col in (body.date_col, body.value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        parsed_dates = _try_parse_dates(df[body.date_col])
        df = df.with_columns(parsed_dates.alias("_date_parsed"))
    except ValueError as e:
        raise HTTPException(400, f"Cannot parse date column: {e}")

    df_sorted = df.sort("_date_parsed")
    if body.grain == "raw":
        values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
    else:
        dmin, dmax = df_sorted["_date_parsed"].min(), df_sorted["_date_parsed"].max()
        eff_grain = suggest_grain(dmin, dmax) if body.grain == "auto" else body.grain
        _cmp = aggregate_series(df_sorted, "_date_parsed", body.value_col, eff_grain, body.agg)
        values = np.array([v for v in _cmp["values"] if v is not None], dtype=float)
    n = len(values)
    if n < 6:
        raise HTTPException(400, "Need at least 6 data points for comparison")

    split = max(int(n * 0.8), n - 6)
    train_vals, test_vals = values[:split], values[split:]
    n_test = len(test_vals)
    s = body.seasonal_period

    METHOD_LABELS = {
        "linear": "Linear Trend",
        "moving_average": "Moving Average",
        "ets": "ETS (Holt-Winters)",
        "sarimax": "SARIMAX",
        "supervised": "Supervised ML",
    }

    results = []
    for method in body.methods:
        label = METHOD_LABELS.get(method, method)
        try:
            preds = _predict_for_compare(train_vals, n_test, method, s)
            actual = test_vals
            mape = float(np.mean(np.abs((actual - preds) / (np.abs(actual) + 1e-9)))) * 100
            rmse = float(np.sqrt(np.mean((actual - preds) ** 2)))
            results.append({
                "method": method, "label": label,
                "mape": round(mape, 2), "rmse": round(rmse, 4),
                "aic": None, "status": "ok",
            })
        except Exception as e:
            results.append({
                "method": method, "label": label,
                "mape": None, "rmse": None,
                "aic": None, "status": "error", "error": str(e)[:200],
            })

    ok_results = [r for r in results if r["status"] == "ok" and r["mape"] is not None]
    best = (
        min(ok_results, key=lambda r: r["mape"])["method"]
        if ok_results
        else (body.methods[0] if body.methods else "linear")
    )
    return {"results": results, "best": best}


@router.post("/forecast/interpret")
def interpret_forecast(body: ForecastInterpretIn):
    fcast = body.result.get("forecast", [])
    last_vals = fcast[-3:] if len(fcast) >= 3 else fcast
    last_summary = ", ".join(
        f"{f['date']}: {f['value']:,.0f}" for f in last_vals
    )

    extras = {
        k: v for k, v in body.result.items()
        if k not in ("forecast", "history", "method", "slope", "intercept")
        and not isinstance(v, list)
    }
    extras_str = "\n".join(f"  {k}: {v}" for k, v in extras.items())

    first_val = fcast[0]["value"] if fcast else None
    last_val  = fcast[-1]["value"] if fcast else None
    trend_pct = ""
    if first_val and last_val and first_val != 0:
        pct = (last_val - first_val) / abs(first_val) * 100
        trend_pct = f"Từ kỳ 1 đến kỳ {len(fcast)}: {'tăng' if pct > 0 else 'giảm'} {abs(pct):.1f}%."

    prompt = (
        f"Bạn là Senior Data Analyst người Việt với 10 năm kinh nghiệm.\n"
        f"Dataset: {body.filename}\n"
        f"Cột ngày: {body.date_col}, Cột giá trị: {body.value_col}\n"
        f"Phương pháp dự báo: {body.method}, Dự báo {body.periods} kỳ tới.\n"
        f"{extras_str}\n"
        f"Các giá trị dự báo cuối: {last_summary}\n"
        f"{trend_pct}\n\n"
        "Phân tích kết quả dự báo này theo 3 phần, trả về JSON:\n"
        "{\n"
        '  "summary": "Tóm tắt xu hướng dự báo bằng 1-2 câu dễ hiểu",\n'
        '  "trend": "Giải thích xu hướng + mức độ tin cậy của model này",\n'
        '  "actions": "2-3 đề xuất hành động cụ thể dựa trên kết quả"\n'
        "}\n"
        "Viết bằng tiếng Việt, ngắn gọn, thực tế. Chỉ JSON, không giải thích thêm."
    )

    try:
        import json as _json
        raw = _call_ai_ml(prompt, max_tokens=800)
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = _json.loads(raw.strip())
        return result
    except Exception as e:
        raise HTTPException(500, f"AI interpret failed: {e}")


@router.post("/stats")
def run_stats(body: StatsIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    if body.col_a not in df.columns:
        raise HTTPException(400, f"Column '{body.col_a}' not found")

    try:
        a = df[body.col_a].drop_nulls().cast(pl.Float64).to_numpy()
    except Exception:
        raise HTTPException(400, f"Column '{body.col_a}' is not numeric — pick a number column for Column A")

    code = stats_code(body.test, body.col_a, body.col_b, row["filename"])

    if body.test == "describe":
        return {
            "count": len(a), "mean": float(a.mean()), "std": float(a.std()),
            "min": float(a.min()), "max": float(a.max()),
            "q25": float(df[body.col_a].quantile(0.25)),
            "q50": float(df[body.col_a].quantile(0.50)),
            "q75": float(df[body.col_a].quantile(0.75)),
            "code": code,
        }

    if body.test == "bootstrap":
        rng = np.random.default_rng(42)
        # Cap at 10k to avoid OOM on large datasets
        sample = a if len(a) <= 10_000 else rng.choice(a, 10_000, replace=False)
        boot_means = rng.choice(sample, size=(1000, len(sample)), replace=True).mean(axis=1)
        ci_low = float(np.percentile(boot_means, 2.5))
        ci_high = float(np.percentile(boot_means, 97.5))
        return {
            "mean": round(float(a.mean()), 4),
            "ci_lower_95": round(ci_low, 4),
            "ci_upper_95": round(ci_high, 4),
            "n_bootstrap": 1000,
            "n_samples": int(len(a)),
            "sampled": int(len(sample)),
            "code": code,
        }

    if body.test == "distribution":
        counts, edges = np.histogram(a, bins=20)
        return {
            "bins": [{"x0": float(edges[i]), "x1": float(edges[i + 1]), "count": int(counts[i])}
                     for i in range(len(counts))],
            "code": code,
        }

    # Tests requiring col_b
    if body.col_b and body.col_b not in df.columns:
        raise HTTPException(400, f"Column '{body.col_b}' not found")

    if body.test == "correlation":
        b = df[body.col_b].drop_nulls().to_numpy()
        r, p = scipy_stats.pearsonr(a[:len(b)], b[:len(a)])
        return {"r": round(float(r), 4), "p_value": round(float(p), 6),
                "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant",
                "code": code}

    if body.test == "ttest":
        b = df[body.col_b].drop_nulls().to_numpy()
        t, p = scipy_stats.ttest_ind(a, b)
        return {"t_stat": round(float(t), 4), "p_value": round(float(p), 6),
                "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant",
                "code": code}

    if body.test == "mannwhitney":
        if not body.col_b:
            raise HTTPException(400, "Mann-Whitney requires col_b (second numeric column)")
        b = df[body.col_b].drop_nulls().to_numpy()
        u, p = scipy_stats.mannwhitneyu(a, b, alternative='two-sided')
        return {
            "u_statistic": round(float(u), 4),
            "p_value": round(float(p), 6),
            "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant",
            "code": code,
        }

    if body.test == "anova":
        if not body.col_b:
            raise HTTPException(400, "ANOVA requires col_b (grouping column)")
        group_vals = df[body.col_b].unique().drop_nulls().to_list()
        groups = [
            df.filter(pl.col(body.col_b) == v)[body.col_a].drop_nulls().to_numpy()
            for v in group_vals
        ]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            raise HTTPException(400, "ANOVA needs ≥2 groups with ≥2 values each")
        f_stat, p = scipy_stats.f_oneway(*groups)
        return {
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p), 6),
            "n_groups": int(len(groups)),
            "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant",
            "code": code,
        }

    if body.test == "chi2":
        if not body.col_b:
            raise HTTPException(400, "Chi-square requires col_b (second categorical column)")
        vals_a = sorted(df[body.col_a].unique().drop_nulls().to_list())
        vals_b = sorted(df[body.col_b].unique().drop_nulls().to_list())
        if len(vals_a) > 20 or len(vals_b) > 20:
            raise HTTPException(400, "Chi-square: max 20 unique values per column")
        table = [
            [df.filter((pl.col(body.col_a) == va) & (pl.col(body.col_b) == vb)).height
             for vb in vals_b]
            for va in vals_a
        ]
        chi2, p, dof, _ = scipy_stats.chi2_contingency(np.array(table))
        return {
            "chi2": round(float(chi2), 4),
            "p_value": round(float(p), 6),
            "degrees_of_freedom": int(dof),
            "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant",
            "code": code,
        }

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
            "code": code,
        }

    if body.test == "boxplot":
        def _to_api_shape(s: dict) -> dict:
            # Round numeric fields, cap outliers list, expose total_outliers + truncation flag.
            total_out = len(s["outlier_indices"])
            capped = s["outlier_indices"][:_MAX_OUTLIERS_IN_HANDLER]
            capped_vals = s["outlier_values"][:_MAX_OUTLIERS_IN_HANDLER]
            return {
                "name":              s["name"],
                "n":                 s["n"],
                "min":               round(s["min"],         4),
                "q1":                round(s["q1"],          4),
                "median":            round(s["median"],      4),
                "q3":                round(s["q3"],          4),
                "max":               round(s["max"],         4),
                "iqr":               round(s["iqr"],         4),
                "lower_fence":       round(s["lower_fence"], 4),
                "upper_fence":       round(s["upper_fence"], 4),
                "outliers":          [
                    {"idx": int(i), "value": round(float(v), 4)}
                    for i, v in zip(capped, capped_vals)
                ],
                "total_outliers":    total_out,
                "outliers_truncated": total_out > _MAX_OUTLIERS_IN_HANDLER,
            }

        groups: list[dict] = []
        truncated     = False
        total_groups  = 1

        if body.col_b:
            if body.col_b not in df.columns:
                raise HTTPException(400, f"Column '{body.col_b}' not found")
            df_g       = df.with_columns(pl.col(body.col_b).cast(pl.Utf8))
            counts_df  = df_g.group_by(body.col_b).len().sort("len", descending=True)
            all_names  = counts_df[body.col_b].to_list()
            total_groups = len(all_names)
            top_names  = all_names[: body.max_groups]
            truncated  = total_groups > body.max_groups

            for name in top_names:
                sub   = df_g.filter(pl.col(body.col_b) == name)[body.col_a]
                arr_g = sub.drop_nulls().cast(pl.Float64).to_numpy()
                raw   = _compute_box_stats(arr_g, str(name))
                if raw is not None:
                    groups.append(_to_api_shape(raw))
        else:
            raw = _compute_box_stats(a, body.col_a)
            if raw is not None:
                groups.append(_to_api_shape(raw))

        if not groups:
            raise HTTPException(400, "Not enough data to compute box plot (need ≥4 values per group)")

        return {
            "groups":       groups,
            "total_n":      sum(g["n"] for g in groups),
            "total_groups": total_groups,
            "truncated":    truncated,
            "code":         code,
        }

    raise HTTPException(400, f"Unknown test '{body.test}'")


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

    series  = df[body.col_a].cast(pl.Float64)
    mean_   = float(series.mean())
    std_raw = series.std(ddof=0)                                 # ddof=0 matches run_stats (numpy default)
    std_    = float(std_raw) if std_raw is not None else 1e-9   # guard: all-null column
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


# ── Box Plot CSV exports ─────────────────────────────────────────────────────

class BoxPlotCsvIn(BaseModel):
    file_id:    str
    col_a:      str
    col_b:      str | None = None
    max_groups: int        = Field(default=10, ge=1, le=100)


def _boxplot_compute_for_csv(df: "pl.DataFrame", body: "BoxPlotCsvIn"):
    """Compute box stats per group (or single). Returns list of raw dicts (with uncapped outlier_indices + outlier_values) for CSV rendering."""
    if body.col_a not in df.columns:
        raise HTTPException(400, f"Column '{body.col_a}' not found")

    groups = []
    if body.col_b:
        if body.col_b not in df.columns:
            raise HTTPException(400, f"Column '{body.col_b}' not found")
        df_g       = df.with_columns(pl.col(body.col_b).cast(pl.Utf8))
        counts_df  = df_g.group_by(body.col_b).len().sort("len", descending=True)
        top_names  = counts_df[body.col_b].to_list()[: body.max_groups]
        for name in top_names:
            sub = df_g.filter(pl.col(body.col_b) == name)[body.col_a]
            arr = sub.drop_nulls().cast(pl.Float64).to_numpy()
            s = _compute_box_stats(arr, str(name))
            if s is not None:
                groups.append(s)
    else:
        arr = df[body.col_a].drop_nulls().cast(pl.Float64).to_numpy()
        s = _compute_box_stats(arr, body.col_a)
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
    df     = _load_df(row["filepath"])
    groups = _boxplot_compute_for_csv(df, body)

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["row_idx", "group", "value", "distance_iqr"])
    for g in groups:
        for i, v in zip(g["outlier_indices"], g["outlier_values"]):
            if v > g["upper_fence"]:
                dist = (v - g["q3"]) / g["iqr"] if g["iqr"] > 0 else 0.0
            elif v < g["lower_fence"]:
                dist = (v - g["q1"]) / g["iqr"] if g["iqr"] > 0 else 0.0
            else:
                dist = 0.0
            w.writerow([int(i), str(g["name"]), f"{float(v):.4f}", f"{dist:.4f}"])

    filename = _safe_csv_filename("box_outliers", body.col_a, row["filename"])
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/stats/boxplot_stats_csv")
def boxplot_stats_csv(body: BoxPlotCsvIn):
    conn = get_connection()
    row  = _get_file_row(conn, body.file_id)
    conn.close()
    df     = _load_df(row["filepath"])
    groups = _boxplot_compute_for_csv(df, body)

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["group", "n", "min", "q1", "median", "q3", "max",
                "iqr", "lower_fence", "upper_fence", "outlier_count"])
    for g in groups:
        w.writerow([
            str(g["name"]),
            g["n"],
            f"{g['min']:.4f}", f"{g['q1']:.4f}", f"{g['median']:.4f}",
            f"{g['q3']:.4f}", f"{g['max']:.4f}", f"{g['iqr']:.4f}",
            f"{g['lower_fence']:.4f}", f"{g['upper_fence']:.4f}",
            len(g["outlier_indices"]),
        ])

    filename = _safe_csv_filename("box_stats", body.col_a, row["filename"])
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── AI Interpretation ────────────────────────────────────────────────────────

TEST_NAMES_VI = {
    "describe":     "Thống kê mô tả (Describe)",
    "bootstrap":    "Ước tính khoảng tin cậy (Bootstrap CI)",
    "distribution": "Phân phối dữ liệu (Distribution)",
    "correlation":  "Tương quan (Correlation)",
    "ttest":        "Kiểm định T-Test",
    "mannwhitney":  "Kiểm định Mann-Whitney U",
    "anova":        "Phân tích phương sai (ANOVA)",
    "chi2":         "Kiểm định Chi-Square",
    "zscore":       "Phân tích Z-Score (Phát hiện ngoại lệ)",
}


class InterpretIn(BaseModel):
    test: str
    col_a: str
    col_b: str | None = None
    result: dict
    filename: str


@router.post("/stats/interpret")
def interpret_stats(body: InterpretIn):
    test_vi   = TEST_NAMES_VI.get(body.test, body.test)
    col_info  = f"Cột A: {body.col_a}" + (f", Cột B: {body.col_b}" if body.col_b else "")
    result_str = "\n".join(f"  {k}: {v}" for k, v in body.result.items()
                           if k != "bins")  # skip histogram raw data

    prompt = (
        f"Bạn là Senior Data Analyst người Việt với 10 năm kinh nghiệm.\n"
        f"Dataset: {body.filename}\n"
        f"Kiểm định: {test_vi}\n"
        f"{col_info}\n\n"
        f"Kết quả:\n{result_str}\n\n"
        "Hãy phân tích kết quả này theo 3 phần, trả về JSON:\n"
        "{\n"
        '  "numbers": "Giải thích ý nghĩa từng con số một cách đơn giản, không cần biết thống kê vẫn hiểu được",\n'
        '  "insights": "2-3 insight quan trọng nhất rút ra được từ kết quả, liên kết với thực tế kinh doanh",\n'
        '  "actions": "2-3 đề xuất hành động cụ thể cho doanh nghiệp dựa trên kết quả này"\n'
        "}\n"
        "Viết bằng tiếng Việt, ngắn gọn, thực tế. Chỉ JSON, không giải thích thêm."
    )

    try:
        raw = _call_ai_ml(prompt, max_tokens=1024)
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI interpret failed: {e}")


def _predict_for_compare(train: np.ndarray, n_steps: int, method: str, s: int) -> np.ndarray:
    """Fit method on train data, forecast n_steps, return predictions array."""
    n = len(train)

    if method == "linear":
        x = np.arange(n)
        slope, intercept, *_ = scipy_stats.linregress(x, train)
        return np.array([intercept + slope * (n + i) for i in range(n_steps)])

    if method == "moving_average":
        window = max(3, min(7, n // 3))
        ma = np.array([train[max(0, i - window + 1):i + 1].mean() for i in range(n)])
        look_back = min(window, n - 1)
        slope_ma = (ma[-1] - ma[-look_back - 1]) / look_back if look_back > 0 else 0.0
        return np.array([ma[-1] + slope_ma * (i + 1) for i in range(n_steps)])

    if method == "ets":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing as _ETS
        use_seasonal = n >= 2 * s
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = _ETS(
                train,
                trend='add', damped_trend=True,
                seasonal='add' if use_seasonal else None,
                seasonal_periods=s if use_seasonal else None,
            ).fit(optimized=True)
        return np.array(fit.forecast(n_steps))

    if method == "sarimax":
        if n < 2 * s:
            raise ValueError(f"SARIMAX cần ≥ {2*s} điểm, có {n}")
        from statsmodels.tsa.statespace.sarimax import SARIMAX as _SARIMAX
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = _SARIMAX(
                train, order=(1, 1, 1), seasonal_order=(1, 1, 1, s),
                enforce_stationarity=False, enforce_invertibility=False,
            ).fit(disp=False, maxiter=100)
        return np.array(fit.forecast(n_steps))

    if method == "supervised":
        from sklearn.linear_model import Ridge
        lags = min(5, n // 4)
        if n < lags + 2:
            raise ValueError(f"Supervised cần ≥ {lags + 2} điểm")
        X = np.array([train[i - lags:i] for i in range(lags, n)])
        y = train[lags:]
        model = Ridge(alpha=1.0).fit(X, y)
        hist = list(train[-lags:])
        preds = []
        for _ in range(n_steps):
            p = float(model.predict(np.array(hist[-lags:]).reshape(1, -1))[0])
            preds.append(p)
            hist.append(p)
        return np.array(preds)

    raise ValueError(f"Unknown method: {method}")


import calendar as _calendar

GRAIN_SEASONAL = {"day": 7, "week": 52, "month": 12, "quarter": 4, "year": 1}


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    mo = m % 12 + 1
    day = min(d.day, _calendar.monthrange(y, mo)[1])
    return date(y, mo, day)


def _step_date(last: date, i: int, grain: str) -> date:
    if grain == "year":
        return _add_months(last, 12 * i)
    if grain == "quarter":
        return _add_months(last, 3 * i)
    if grain == "month":
        return _add_months(last, i)
    if grain == "week":
        return last + timedelta(days=7 * i)
    return last + timedelta(days=i)        # day | raw


def _seasonal(body: ForecastIn, grain: str) -> int:
    if body.seasonal_period is not None:
        return body.seasonal_period
    return GRAIN_SEASONAL.get(grain, 12)


@router.post("/forecast")
def run_forecast(body: ForecastIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    for col in (body.date_col, body.value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        parsed_dates = _try_parse_dates(df[body.date_col])
        df = df.with_columns(parsed_dates.alias("_date_parsed"))
    except ValueError as e:
        raise HTTPException(400, f"Không thể parse cột ngày '{body.date_col}': {e}")

    df_sorted = df.sort("_date_parsed")
    dmin, dmax = df_sorted["_date_parsed"].min(), df_sorted["_date_parsed"].max()
    if body.grain == "raw":
        eff_grain = "raw"
    elif body.grain == "auto":
        eff_grain = suggest_grain(dmin, dmax) if isinstance(dmin, date) else "day"
    else:
        eff_grain = body.grain
    step_grain = "day" if eff_grain == "raw" else eff_grain

    if eff_grain == "raw":
        values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
        labels = df_sorted[body.date_col].cast(pl.Utf8).to_list()
        try:
            raw_last = df_sorted["_date_parsed"].drop_nulls()[-1]
            last_date = raw_last.item() if hasattr(raw_last, "item") else raw_last
            if not isinstance(last_date, date):
                last_date = date.today()
        except Exception:
            last_date = date.today()
    else:
        agg_series = aggregate_series(df_sorted, "_date_parsed", body.value_col, eff_grain, body.agg)
        values = np.array([v for v in agg_series["values"] if v is not None], dtype=float)
        labels = agg_series["labels"]
        starts = agg_series["period_starts"]
        last_date = starts[-1] if starts else date.today()

    n = len(values)
    s_check = _seasonal(body, step_grain)
    fc_code = forecast_code(body.method, body.date_col, body.value_col,
                            row["filename"], eff_grain, body.agg, s_check,
                            body.periods, n)
    suit = check_forecast_suitability(body.method, n, s_check)
    if not suit["suitable"]:
        return {**suit, "method": body.method, "code": fc_code, "grain": step_grain}

    # ── Anomaly detection (IQR + z-score on full history) ──────────────────
    q1 = float(np.percentile(values, 25))
    q3 = float(np.percentile(values, 75))
    iqr = q3 - q1
    fence_lo = q1 - 1.5 * iqr
    fence_hi = q3 + 1.5 * iqr
    z_scores_arr = np.abs((values - values.mean()) / (values.std() + 1e-9))
    is_anomaly_arr = (values < fence_lo) | (values > fence_hi) | (z_scores_arr > 2.5)

    hist_n = min(n, 60)
    _history = [
        {
            "date":       labels[n - hist_n + i],
            "value":      round(float(values[n - hist_n + i]), 4),
            "is_anomaly": bool(is_anomaly_arr[n - hist_n + i]),
            "z_score":    round(float(z_scores_arr[n - hist_n + i]), 2),
        }
        for i in range(hist_n)
    ]

    if body.method == 'moving_average':
        window = max(3, min(7, n // 3))
        ma = np.array([values[max(0, i - window + 1):i + 1].mean() for i in range(n)])
        look_back = min(window, n - 1)
        slope_ma = (ma[-1] - ma[-look_back - 1]) / look_back if look_back > 0 else 0.0
        local_std = float(values[-min(window * 2, n):].std())

        forecast = []
        for i in range(1, body.periods + 1):
            pred = ma[-1] + slope_ma * i
            ci = local_std * 1.96
            forecast.append({
                "date": _step_date(last_date, i, step_grain).isoformat(),
                "value": round(float(pred), 4),
                "lower": round(float(pred - ci), 4),
                "upper": round(float(pred + ci), 4),
            })
        return {
            "method": "moving_average",
            "slope": round(float(slope_ma), 4),
            "intercept": round(float(ma[-1]), 4),
            "forecast": forecast,
            "history": _history,
            "code": fc_code,
        }

    if body.method == 'sarimax':
        s = _seasonal(body, step_grain)
        train = values[-500:] if n > 500 else values
        if len(train) < 2 * s:
            raise HTTPException(
                400,
                f"SARIMAX cần tối thiểu {2 * s} điểm dữ liệu với seasonal_period={s}. "
                f"Dữ liệu hiện tại: {len(train)} điểm. "
                f"Giải pháp: giảm Seasonal period xuống ≤ {len(train) // 2}, "
                f"hoặc dùng ETS / Linear thay thế."
            )
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX as _SARIMAX
        except ImportError:
            raise HTTPException(500, "statsmodels not installed — run `uv sync`")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                mdl = _SARIMAX(train, order=(1, 1, 1),
                               seasonal_order=(1, 1, 1, s),
                               enforce_stationarity=False,
                               enforce_invertibility=False)
                fit = mdl.fit(disp=False, maxiter=100)
                fcast = fit.get_forecast(steps=body.periods)
                # statsmodels returns numpy arrays here (the model is fit on a
                # numpy array, so there is no pandas index) — index with [i],
                # NOT .iloc. np.asarray also tolerates a pandas return safely.
                mean_pred = np.asarray(fcast.predicted_mean, dtype=float)
                ci_arr    = np.asarray(fcast.conf_int(alpha=0.05), dtype=float)
            except Exception as e:
                raise HTTPException(400, f"SARIMAX failed to converge: {e}")
        # A valid point forecast can come with non-estimable confidence intervals
        # on short/marginal series (covariance → NaN). NaN is not JSON-encodable
        # (→ raw 500). Keep the forecast, null out unusable bounds. Only a non-
        # finite POINT forecast is a genuine failure → friendly 400 (not a 500).
        forecast = []
        for i in range(body.periods):
            pred = float(mean_pred[i])
            if not np.isfinite(pred):
                raise HTTPException(
                    400,
                    f"SARIMAX không tạo được dự báo hợp lệ với seasonal_period={s} "
                    f"trên {len(train)} điểm (kết quả NaN). Hãy giảm Seasonal period "
                    f"hoặc dùng ETS / Linear thay thế."
                )
            lo = float(ci_arr[i, 0])
            hi = float(ci_arr[i, 1])
            forecast.append({
                "date":  _step_date(last_date, i + 1, step_grain).isoformat(),
                "value": round(pred, 4),
                "lower": round(lo, 4) if np.isfinite(lo) else None,
                "upper": round(hi, 4) if np.isfinite(hi) else None,
            })
        aic = round(float(fit.aic), 2) if hasattr(fit, 'aic') else None
        return {
            "method": f"SARIMAX(1,1,1)×(1,1,1,{s})",
            "slope": 0.0, "intercept": 0.0,
            "aic": aic,
            "trained_on": int(len(train)),
            "forecast": forecast,
            "history": _history,
            "code": fc_code,
        }

    if body.method == 'supervised':
        try:
            from sklearn.linear_model import Ridge
        except ImportError:
            raise HTTPException(500, "scikit-learn not installed — run `uv sync`")
        lags = min(5, n // 4)
        if n < lags + 2:
            raise HTTPException(400, f"Need at least {lags + 2} data points for supervised method")
        # Build lag feature matrix
        X = np.array([values[i - lags: i] for i in range(lags, n)])
        y = values[lags:]
        model = Ridge(alpha=1.0).fit(X, y)
        # In-sample residuals for CI
        resid_std = float(np.std(y - model.predict(X)))
        # Recursive multi-step forecast
        history = list(values[-lags:])
        forecast = []
        for i in range(body.periods):
            x_in = np.array(history[-lags:]).reshape(1, -1)
            pred  = float(model.predict(x_in)[0])
            ci    = resid_std * 1.96
            forecast.append({
                "date":  _step_date(last_date, i + 1, step_grain).isoformat(),
                "value": round(pred, 4),
                "lower": round(pred - ci, 4),
                "upper": round(pred + ci, 4),
            })
            history.append(pred)
        r2 = float(model.score(X, y))
        return {
            "method": f"Supervised Ridge (lag={lags})",
            "slope": 0.0, "intercept": round(float(model.intercept_), 4),
            "r2": round(r2, 4),
            "lags_used": lags,
            "forecast": forecast,
            "history": _history,
            "code": fc_code,
        }

    if body.method == 'ets':
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing as _ETS
        except ImportError:
            raise HTTPException(500, "statsmodels not installed — run `uv sync`")

        s = _seasonal(body, step_grain)
        train = values[-500:] if n > 500 else values
        use_seasonal = len(train) >= 2 * s

        try:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore")
                ets_model = _ETS(
                    train,
                    trend='add',
                    damped_trend=True,
                    seasonal='add' if use_seasonal else None,
                    seasonal_periods=s if use_seasonal else None,
                ).fit(optimized=True)
        except Exception as e:
            raise HTTPException(400, f"ETS failed to fit: {e}")

        fcast_vals = ets_model.forecast(body.periods)
        resid_std = float(np.std(ets_model.resid))
        ci = resid_std * 1.96

        ets_forecast = []
        for i, pred in enumerate(fcast_vals):
            ets_forecast.append({
                "date":  _step_date(last_date, i + 1, step_grain).isoformat(),
                "value": round(float(pred), 4),
                "lower": round(float(pred - ci), 4),
                "upper": round(float(pred + ci), 4),
            })

        params = ets_model.params
        return {
            "method":       f"ETS(add,damp,{'add' if use_seasonal else 'none'})",
            "slope":        0.0,
            "intercept":    round(float(params.get("smoothing_level", 0.0)), 4),
            "aic":          round(float(ets_model.aic), 2) if hasattr(ets_model, 'aic') else None,
            "alpha":        round(float(params.get("smoothing_level", 0.0)), 4),
            "beta":         round(float(params.get("smoothing_trend", 0.0)), 4),
            "gamma":        round(float(params.get("smoothing_seasonal", 0.0)), 4) if use_seasonal else None,
            "trained_on":   int(len(train)),
            "forecast":     ets_forecast,
            "history":      _history,
            "code":         fc_code,
        }

    # Default: linear regression
    x = np.arange(n)
    slope, intercept, _, _, _ = scipy_stats.linregress(x, values)
    forecast = []
    for i in range(1, body.periods + 1):
        pred = intercept + slope * (n + i - 1)
        ci = float(values.std()) * 1.96
        forecast.append({
            "date": _step_date(last_date, i, step_grain).isoformat(),
            "value": round(float(pred), 4),
            "lower": round(float(pred - ci), 4),
            "upper": round(float(pred + ci), 4),
        })
    return {
        "method": "linear",
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "forecast": forecast,
        "history": _history,
        "code": fc_code,
    }
