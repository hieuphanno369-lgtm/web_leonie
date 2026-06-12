import re
import shutil
import time
from pathlib import Path

import duckdb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection, UPLOADS_DIR

router = APIRouter(prefix="/sql", tags=["sql"])

VINA_BREW_DIR    = Path(__file__).parent.parent.parent / "data" / "vina_brew"
VINA_BREW_TABLES = {
    "dim_date", "dim_product", "dim_channel",
    "dim_store", "fact_sales", "fact_transactions",
}


# ── Pydantic models ───────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name:  str
    dtype: str


class TableInfo(BaseModel):
    file_id:    str
    table_name: str
    filename:   str
    rows:       int
    cols:       int
    columns:    list[ColumnInfo]
    source:     str   # "vina_brew" | "user"


class SqlQueryIn(BaseModel):
    sql: str


class SqlQueryOut(BaseModel):
    columns:     list[str]
    rows:        list[list]
    duration_ms: float
    tables:      list[str]


class ExerciseCheckIn(BaseModel):
    exercise_id:      str
    sql:              str
    expected_columns: list[str]


class ExerciseCheckOut(BaseModel):
    passed:           bool
    actual_columns:   list[str]
    expected_columns: list[str]
    error:            str | None = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _clean_identifier(name: str) -> str:
    """Turn an arbitrary filename stem into a safe lower-snake SQL table name."""
    s = re.sub(r"[^0-9a-z]+", "_", name.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "table"
    if s[0].isdigit():
        s = f"t_{s}"
    return s


def _assign_table_names(files: list[dict]) -> dict[str, str]:
    """Map each ``file_id`` → a clean, de-duplicated DuckDB table name.

    Derived from the *original* filename rather than the on-disk
    ``{file_id}_`` prefix, so users see ``q1_sales`` instead of
    ``a1b2c3…_q1 sales``. Collisions get a numeric suffix (``_2``, ``_3``…).
    """
    used:    set[str]      = set()
    mapping: dict[str, str] = {}
    for row in files:
        base = _clean_identifier(Path(row["filename"]).stem)
        name = base
        i    = 2
        while name in used:
            name = f"{base}_{i}"
            i += 1
        used.add(name)
        mapping[row["file_id"]] = name
    return mapping


def _build_duckdb(files: list[dict]) -> tuple[duckdb.DuckDBPyConnection, list[str]]:
    """Create an in-memory DuckDB with every registered file loaded as a table."""
    dconn  = duckdb.connect(":memory:")
    loaded = []
    names  = _assign_table_names(files)
    for row in files:
        fp         = Path(row["filepath"])
        table_name = names[row["file_id"]]
        if fp.exists():
            try:
                dconn.execute(
                    f"CREATE TABLE \"{table_name}\" AS "
                    f"SELECT * FROM read_csv_auto('{fp.as_posix()}')"
                )
                loaded.append(table_name)
            except Exception:
                pass
    return dconn, loaded


def _get_all_files() -> list[dict]:
    conn  = get_connection()
    rows  = conn.execute(
        "SELECT file_id, filename, filepath, rows, cols FROM uploaded_files"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _col_info(dconn: duckdb.DuckDBPyConnection, table_name: str) -> list[ColumnInfo]:
    desc = dconn.execute(f'DESCRIBE "{table_name}"').fetchall()
    return [ColumnInfo(name=c[0], dtype=c[1]) for c in desc]


# ── GET /api/sql/tables ───────────────────────────────────────────────────────

@router.get("/tables", response_model=list[TableInfo])
def list_tables():
    files  = _get_all_files()
    names  = _assign_table_names(files)
    result = []
    for row in files:
        fp = Path(row["filepath"])
        if not fp.exists():
            continue
        table_name = names[row["file_id"]]
        source     = "vina_brew" if table_name in VINA_BREW_TABLES else "user"
        try:
            dconn   = duckdb.connect(":memory:")
            dconn.execute(
                f"CREATE TABLE t AS SELECT * FROM read_csv_auto('{fp.as_posix()}')"
            )
            columns = [ColumnInfo(name=c[0], dtype=c[1])
                       for c in dconn.execute("DESCRIBE t").fetchall()]
            dconn.close()
        except Exception:
            columns = []

        result.append(TableInfo(
            file_id=row["file_id"],
            table_name=table_name,
            filename=row["filename"],
            rows=row["rows"] or 0,
            cols=row["cols"] or 0,
            columns=columns,
            source=source,
        ))
    return result


# ── POST /api/sql/query ───────────────────────────────────────────────────────

@router.post("/query", response_model=SqlQueryOut)
def run_query(body: SqlQueryIn):
    if not body.sql.strip():
        raise HTTPException(status_code=400, detail="Empty SQL")

    files        = _get_all_files()
    dconn, loaded = _build_duckdb(files)

    t0 = time.perf_counter()
    try:
        rel         = dconn.execute(body.sql)
        columns     = [d[0] for d in rel.description]
        rows        = [list(r) for r in rel.fetchall()]
        duration_ms = (time.perf_counter() - t0) * 1000
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        dconn.close()

    sql_up      = body.sql.upper()
    used_tables = [t for t in loaded if t.upper() in sql_up]

    return SqlQueryOut(columns=columns, rows=rows,
                       duration_ms=duration_ms, tables=used_tables)


# ── DELETE /api/sql/dataset/{file_id} ─────────────────────────────────────────

@router.delete("/dataset/{file_id}")
def delete_dataset(file_id: str):
    conn = get_connection()
    row  = conn.execute(
        "SELECT filename, filepath FROM uploaded_files WHERE file_id = ?",
        (file_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Dataset not found")

    table_name = Path(row["filepath"]).stem
    if table_name in VINA_BREW_TABLES:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="VINA BREW tables cannot be deleted. Use seed endpoint to reset."
        )

    conn.execute("DELETE FROM uploaded_files WHERE file_id = ?", (file_id,))
    conn.commit()
    conn.close()

    fp = Path(row["filepath"])
    if fp.exists():
        fp.unlink(missing_ok=True)

    return {"deleted": file_id}


# ── POST /api/sql/seed-vina-brew ──────────────────────────────────────────────

@router.post("/seed-vina-brew")
def seed_vina_brew():
    if not VINA_BREW_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail="VINA BREW CSV files not found. Run scripts/generate_vina_brew.py first."
        )

    conn   = get_connection()
    seeded = []

    for tname in VINA_BREW_TABLES:
        src = VINA_BREW_DIR / f"{tname}.csv"
        if not src.exists():
            continue

        existing = conn.execute(
            "SELECT file_id FROM uploaded_files WHERE filename = ?",
            (f"{tname}.csv",)
        ).fetchone()
        if existing:
            seeded.append(tname)
            continue

        dest = UPLOADS_DIR / f"{tname}.csv"
        shutil.copy2(src, dest)

        dconn = duckdb.connect(":memory:")
        dconn.execute(
            f"CREATE TABLE t AS SELECT * FROM read_csv_auto('{dest.as_posix()}')"
        )
        nrows = dconn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        ncols = len(dconn.execute("DESCRIBE t").fetchall())
        dconn.close()

        conn.execute(
            "INSERT INTO uploaded_files (filename, filepath, rows, cols) VALUES (?,?,?,?)",
            (f"{tname}.csv", str(dest), nrows, ncols)
        )
        seeded.append(tname)

    conn.commit()
    conn.close()
    return {"seeded": seeded, "total": len(seeded)}


# ── POST /api/sql/exercises/check ────────────────────────────────────────────

@router.post("/exercises/check", response_model=ExerciseCheckOut)
def check_exercise(body: ExerciseCheckIn):
    if not body.sql.strip():
        return ExerciseCheckOut(
            passed=False,
            actual_columns=[],
            expected_columns=body.expected_columns,
            error="Empty SQL",
        )

    files         = _get_all_files()
    dconn, _loaded = _build_duckdb(files)

    try:
        rel            = dconn.execute(body.sql)
        actual_columns = [d[0] for d in rel.description]
        error          = None
    except duckdb.Error as e:
        dconn.close()
        return ExerciseCheckOut(
            passed=False,
            actual_columns=[],
            expected_columns=body.expected_columns,
            error=str(e),
        )
    finally:
        dconn.close()

    passed = actual_columns == body.expected_columns
    return ExerciseCheckOut(
        passed=passed,
        actual_columns=actual_columns,
        expected_columns=body.expected_columns,
    )
