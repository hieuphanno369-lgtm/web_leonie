import os
import shutil
import tempfile
import time
from datetime import datetime

import duckdb

from automation import ingest, shape, export, notify
from automation.models import AutomationJob, RunResult
from automation.sources.rest import RestFetcher


def make_fetcher(source):
    if getattr(source, "source_type", "rest") == "salesforce":
        from automation.sources.salesforce import SalesforceFetcher
        return SalesforceFetcher(source)
    return RestFetcher(source)


def _open_work():
    work = tempfile.mkdtemp(prefix="automation_")
    try:
        con = duckdb.connect(os.path.join(work, "work.duckdb"))
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return work, con


def run(job: AutomationJob) -> RunResult:
    cfg = job.config
    t0 = time.perf_counter()
    work = con = None
    try:
        work, con = _open_work()
        ingest.ensure_raw(con)
        for page in make_fetcher(cfg.source).fetch_pages():
            ingest.append_page(con, page)
        rows = shape.run(con, cfg.shape_sql)
        if rows == 0:
            status, files, detail = "warning", [], "No rows returned; nothing exported"
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            files, warnings = export.write(con, cfg.export, cfg.name, ts)
            if warnings:
                status, detail = "warning", "; ".join(warnings)
            else:
                status, detail = "ok", None
        result = RunResult(status=status, rows=rows,
                           duration_seconds=time.perf_counter() - t0,
                           output_files=files, error=detail)
    except Exception as e:
        result = RunResult(status="error", rows=0,
                           duration_seconds=time.perf_counter() - t0, error=str(e))
    finally:
        if con is not None:
            con.close()
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)
    notify.send(cfg, result)
    return result


def preview(job: AutomationJob, n_rows: int = 100) -> dict:
    cfg = job.config
    work = con = None
    try:
        work, con = _open_work()
        ingest.ensure_raw(con)
        for page in make_fetcher(cfg.source).fetch_pages(limit_pages=1):
            ingest.append_page(con, page)
        shape.run(con, cfg.shape_sql)
        rel = con.execute(f"SELECT * FROM data LIMIT {int(n_rows)}")
        columns = [d[0] for d in rel.description]
        rows = [list(r) for r in rel.fetchall()]
        return {"columns": columns, "rows": rows}
    finally:
        if con is not None:
            con.close()
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)
