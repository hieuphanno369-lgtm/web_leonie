import json
import os
import tempfile

import duckdb


def ensure_raw(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS raw (rec JSON)")


def append_page(con: duckdb.DuckDBPyConnection, page: list[dict]) -> int:
    """Stream one page of records into `raw` as one JSON value per row."""
    if not page:
        return 0
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for rec in page:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        posix = path.replace("\\", "/")
        con.execute(
            "INSERT INTO raw SELECT json FROM "
            f"read_json('{posix}', format='newline_delimited', records='false')"
        )
        return len(page)
    finally:
        os.unlink(path)
