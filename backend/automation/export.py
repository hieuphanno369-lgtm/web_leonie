import os

import duckdb

from automation.models import ExportSpec


def _posix(p: str) -> str:
    return p.replace("\\", "/")


def _cell(v):
    return v if isinstance(v, (str, int, float, bool)) or v is None else str(v)


def _copy(con, final_path: str, fmt_clause: str) -> str:
    tmp = final_path + ".tmp"
    try:
        con.execute(f"COPY (SELECT * FROM data) TO '{_posix(tmp)}' {fmt_clause}")
        os.replace(tmp, final_path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return final_path


def _xlsx(con, final_path: str) -> str:
    from openpyxl import Workbook
    tmp = final_path + ".tmp"
    cols = [d[0] for d in con.execute("DESCRIBE data").fetchall()]
    cur = con.execute("SELECT * FROM data")
    try:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        ws.append(cols)
        while True:
            batch = cur.fetchmany(10_000)
            if not batch:
                break
            for r in batch:
                ws.append([_cell(v) for v in r])
        wb.save(tmp)
        os.replace(tmp, final_path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return final_path


def _duckdb(con, final_path: str, mode: str) -> str:
    if mode == "overwrite":
        tmp = final_path + ".tmp"
        for p in (tmp, tmp + ".wal"):
            if os.path.exists(p):
                os.unlink(p)
        try:
            con.execute(f"ATTACH '{_posix(tmp)}' AS exp")
            try:
                con.execute("CREATE TABLE exp.data AS SELECT * FROM data")
            finally:
                con.execute("DETACH exp")
            os.replace(tmp, final_path)
        except Exception:
            for p in (tmp, tmp + ".wal"):
                if os.path.exists(p):
                    os.unlink(p)
            raise
        stale_wal = final_path + ".wal"   # old WAL would be inconsistent with the new file
        if os.path.exists(stale_wal):
            os.unlink(stale_wal)
    else:  # append
        con.execute(f"ATTACH '{_posix(final_path)}' AS exp")
        began = False
        try:
            exists = con.execute(
                "SELECT count(*) FROM duckdb_tables() "
                "WHERE database_name='exp' AND table_name='data'"
            ).fetchone()[0]
            con.execute("BEGIN")
            began = True
            if exists:
                con.execute("INSERT INTO exp.data SELECT * FROM data")
            else:
                con.execute("CREATE TABLE exp.data AS SELECT * FROM data")
            con.execute("COMMIT")
        except Exception:
            if began:
                con.execute("ROLLBACK")
            raise
        finally:
            con.execute("DETACH exp")
    return final_path


def write(con, spec: ExportSpec, job_name: str, timestamp: str) -> tuple[list[str], list[str]]:
    """Write `data` to each requested format. Returns (files, warnings)."""
    os.makedirs(spec.dest_dir, exist_ok=True)
    rows = con.execute("SELECT count(*) FROM data").fetchone()[0]
    files: list[str] = []
    warnings: list[str] = []
    snap = f"{job_name}_{timestamp}"
    for fmt in spec.formats:
        if fmt == "parquet":
            files.append(_copy(con, os.path.join(spec.dest_dir, snap + ".parquet"), "(FORMAT parquet)"))
        elif fmt == "csv":
            files.append(_copy(con, os.path.join(spec.dest_dir, snap + ".csv"), "(FORMAT csv, HEADER)"))
        elif fmt == "xlsx":
            if rows > spec.xlsx_row_guard:
                warnings.append(f"xlsx skipped: {rows} rows exceeds guard {spec.xlsx_row_guard}")
            else:
                files.append(_xlsx(con, os.path.join(spec.dest_dir, snap + ".xlsx")))
        elif fmt == "duckdb":
            files.append(_duckdb(con, os.path.join(spec.dest_dir, job_name + ".duckdb"), spec.duckdb_mode))
    return files, warnings
