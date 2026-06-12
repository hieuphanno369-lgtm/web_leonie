# Automation (Backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend engine + REST API for the Automation feature: pull data from a REST API → ingest raw JSON into DuckDB → shape with user SQL → export (`.duckdb`/parquet/csv/xlsx, streaming) → notify (Discord/Email).

**Architecture:** Approach A — declarative `JobConfig` (JSON) executed by a streaming server-side runner. A `backend/automation/` package with one responsibility per module (models, store, sources, ingest, shape, export, notify, codegen, runner) + a thin FastAPI router. Source is an interface (`Source.fetch_pages`) so T-SQL can be added later without touching ingest/shape/export/notify.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLite (job store), DuckDB 1.5 (ingest/shape/export), httpx (fetch), openpyxl (xlsx), stdlib smtplib/urllib (notify), pytest + httpx.MockTransport (tests).

**Spec:** `docs/superpowers/specs/2026-06-04-automation-design.md` (sections 6, 8, 9, 10, 11).
**Scope of THIS plan:** Backend only (spec §6, §8–§11). Frontend (spec §7) is a separate follow-up plan.

### Conventions
- All commands run **from `backend/`**. Test runner: `.venv\Scripts\python.exe -m pytest <path> -v`.
- Imports root is `backend/` (via `backend/conftest.py`): use `from automation.x import …`, `from database import …`, `from main import app`.
- Tests get an isolated temp SQLite via the autouse `fresh_db` fixture in `backend/tests/conftest.py` (no setup needed).
- DuckDB file paths inside SQL **must use forward slashes** (`str.replace("\\", "/")`).
- **Do NOT** stage/modify any do-not-touch file (sql_sandbox/snippets/fabric_views/action_plan routers & tests, `frontend/src/{api/sql.ts,components/sql,data}`, `data/vina_brew`, `scripts/generate_vina_brew.py`, `.claude/*`). Each commit stages only the files listed in its task.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `backend/database.py` *(modify)* | Add `_migrate_v6` + `automation_jobs` table |
| `backend/tests/test_database.py` *(modify)* | Update table-count assertion 12→13; add table test |
| `backend/automation/__init__.py` *(create)* | Package marker |
| `backend/automation/models.py` *(create)* | Pydantic models (the config contract) |
| `backend/automation/store.py` *(create)* | CRUD `automation_jobs` + last-run status |
| `backend/automation/sources/__init__.py` *(create)* | Package marker |
| `backend/automation/sources/base.py` *(create)* | `Source` Protocol (interface seam) |
| `backend/automation/sources/rest.py` *(create)* | `RestFetcher`: httpx + pagination + `${VAR}` + retry |
| `backend/automation/ingest.py` *(create)* | Stream pages → DuckDB `raw(rec JSON)` |
| `backend/automation/shape.py` *(create)* | User SQL on `raw` → `data` table |
| `backend/automation/export.py` *(create)* | 4 formats, atomic, guard, append |
| `backend/automation/notify.py` *(create)* | Discord (.env) + Email (SMTP) |
| `backend/automation/codegen.py` *(create)* | Read-only Python + SQL from config |
| `backend/automation/runner.py` *(create)* | Orchestrate run + preview |
| `backend/routers/automation.py` *(create)* | FastAPI router (8 endpoints) |
| `backend/main.py` *(modify)* | Register router |
| `backend/pyproject.toml` *(modify)* | Promote `httpx` to runtime dependency |
| `backend/tests/test_automation.py` *(create)* | Unit + API tests |

**Naming contract (used across tasks):** models `RestAuth, Pagination, RestSource, ExportSpec, EmailSpec, NotifySpec, JobConfig, RunResult, AutomationJob`; fetcher class `RestFetcher` (consumes the `RestSource` model); store fns `create_job/get_job/list_jobs/update_job/delete_job/set_running/set_run_status`; runner seam `make_fetcher(source)`; export `write(con, spec, job_name, timestamp) -> (files, warnings)`; the working DuckDB always has tables `raw` then `data`.

---

## Task 1: DB migration `_migrate_v6` + `automation_jobs`

**Files:**
- Modify: `backend/database.py` (add `_migrate_v6`, call it in `create_tables`)
- Modify: `backend/tests/test_database.py` (count 12→13, add table test)

- [ ] **Step 1: Update + add failing tests** in `backend/tests/test_database.py`

Change the count assertion in `test_create_tables_is_idempotent`:
```python
    assert count == 13  # 12 prior + automation_jobs (v6)
```
Append a new test:
```python
def test_automation_jobs_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(automation_jobs)").fetchall()}
    conn.close()
    assert {"id", "name", "config", "last_status", "last_run_at",
            "last_rows", "last_error", "created", "updated"} <= cols
```

- [ ] **Step 2: Run to verify it fails**

From `backend/`: `.venv\Scripts\python.exe -m pytest tests/test_database.py -v`
Expected: FAIL — `test_automation_jobs_table_exists` (no such table) and the count test (12 ≠ 13).

- [ ] **Step 3: Implement** in `backend/database.py`

Add the call at the end of `create_tables()` (right after `_migrate_v5(conn)`):
```python
    _migrate_v6(conn)
```
Add the function (place after `_migrate_v5`):
```python
def _migrate_v6(conn) -> None:
    """Add automation_jobs table (Automation feature)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS automation_jobs (
            id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            name        TEXT NOT NULL,
            config      TEXT NOT NULL,
            last_status TEXT,
            last_run_at TEXT,
            last_rows   INTEGER,
            last_error  TEXT,
            created     TEXT NOT NULL DEFAULT (datetime('now')),
            updated     TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
```

- [ ] **Step 4: Run to verify it passes**

From `backend/`: `.venv\Scripts\python.exe -m pytest tests/test_database.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**
```bash
git add backend/database.py backend/tests/test_database.py
git commit -m "feat(automation): add automation_jobs table via _migrate_v6"
```

---

## Task 2: Pydantic models (`automation/models.py`)

**Files:**
- Create: `backend/automation/__init__.py` (empty)
- Create: `backend/automation/models.py`
- Test: `backend/tests/test_automation.py`

- [ ] **Step 1: Write the failing test** — create `backend/tests/test_automation.py`
```python
from automation.models import (
    RestAuth, Pagination, RestSource, ExportSpec, EmailSpec,
    NotifySpec, JobConfig, RunResult, AutomationJob,
)


def test_model_defaults():
    s = RestSource(url="https://api.test/x")
    assert s.method == "GET"
    assert s.auth.type == "none"
    assert s.records_path == ""
    assert s.timeout_seconds == 30 and s.max_retries == 3
    assert s.pagination is None

    e = ExportSpec(formats=["parquet"], dest_dir="/tmp/out")
    assert e.duckdb_mode == "overwrite" and e.xlsx_row_guard == 1_000_000

    n = NotifySpec()
    assert n.discord_enabled is False and n.email.enabled is False
    assert n.email.attach_max_bytes == 10_485_760


def test_jobconfig_json_round_trip():
    cfg = JobConfig(
        name="daily",
        source=RestSource(url="https://api.test/x",
                          auth=RestAuth(type="bearer", value_ref="TOK"),
                          pagination=Pagination(param="page", start=1)),
        shape_sql="SELECT * FROM raw",
        export=ExportSpec(formats=["duckdb", "csv"], dest_dir="/tmp/out", duckdb_mode="append"),
    )
    again = JobConfig.model_validate_json(cfg.model_dump_json())
    assert again.source.auth.value_ref == "TOK"
    assert again.export.duckdb_mode == "append"
    assert again.source.pagination.param == "page"
```

- [ ] **Step 2: Run to verify it fails**

From `backend/`: `.venv\Scripts\python.exe -m pytest tests/test_automation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'automation'`.

- [ ] **Step 3: Implement** — create `backend/automation/__init__.py` (empty file) and `backend/automation/models.py`
```python
from typing import Literal
from pydantic import BaseModel, Field


class RestAuth(BaseModel):
    type: Literal["none", "api_key", "basic", "bearer"] = "none"
    header_name: str | None = None   # api_key: header to set (e.g. "X-API-Key")
    value_ref: str | None = None     # api_key/bearer: env var NAME holding the secret
    user_ref: str | None = None      # basic: env var name for username
    pass_ref: str | None = None      # basic: env var name for password


class Pagination(BaseModel):
    param: str = "page"
    start: int = 1


class RestSource(BaseModel):
    url: str
    method: Literal["GET"] = "GET"
    headers: dict[str, str] = Field(default_factory=dict)   # values may contain ${VAR}
    params: dict[str, str] = Field(default_factory=dict)
    auth: RestAuth = Field(default_factory=RestAuth)
    records_path: str = ""           # dotted path to the array, e.g. "data.items"
    pagination: Pagination | None = None
    timeout_seconds: int = 30
    max_retries: int = 3


class ExportSpec(BaseModel):
    formats: list[Literal["duckdb", "parquet", "csv", "xlsx"]] = Field(default_factory=list)
    dest_dir: str
    duckdb_mode: Literal["overwrite", "append"] = "overwrite"
    xlsx_row_guard: int = 1_000_000


class EmailSpec(BaseModel):
    enabled: bool = False
    recipients: list[str] = Field(default_factory=list)
    attach_max_bytes: int = 10_485_760   # 10 MB


class NotifySpec(BaseModel):
    discord_enabled: bool = False
    email: EmailSpec = Field(default_factory=EmailSpec)


class JobConfig(BaseModel):
    name: str
    source: RestSource
    shape_sql: str = ""              # DuckDB SQL over `raw`; "" = passthrough
    export: ExportSpec
    notify: NotifySpec = Field(default_factory=NotifySpec)


class RunResult(BaseModel):
    status: Literal["ok", "warning", "error", "running"]
    rows: int = 0
    duration_seconds: float = 0.0
    output_files: list[str] = Field(default_factory=list)
    error: str | None = None


class AutomationJob(BaseModel):
    id: str
    config: JobConfig
    last_status: str | None = None
    last_run_at: str | None = None
    last_rows: int | None = None
    last_error: str | None = None
    created: str
    updated: str
```

- [ ] **Step 4: Run to verify it passes** — same command. Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/automation/__init__.py backend/automation/models.py backend/tests/test_automation.py
git commit -m "feat(automation): add Pydantic config models"
```

---

## Task 3: Job store (`automation/store.py`)

**Files:**
- Create: `backend/automation/store.py`
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing test** (append to `test_automation.py`)
```python
from automation import store
from automation.models import RunResult as _RR


def _make_cfg(name="job"):
    return JobConfig(name=name,
                     source=RestSource(url="https://api.test/x"),
                     export=ExportSpec(formats=["parquet"], dest_dir="/tmp/out"))


def test_store_crud_and_status():
    job = store.create_job(_make_cfg("first"))
    assert job.id and job.config.name == "first"
    assert job.last_status is None

    assert store.get_job(job.id).config.name == "first"
    assert [j.id for j in store.list_jobs()] == [job.id]

    updated = store.update_job(job.id, _make_cfg("renamed"))
    assert updated.config.name == "renamed"

    store.set_running(job.id)
    assert store.get_job(job.id).last_status == "running"

    store.set_run_status(job.id, _RR(status="ok", rows=42, duration_seconds=1.2,
                                     output_files=["/tmp/out/x.parquet"]))
    done = store.get_job(job.id)
    assert done.last_status == "ok" and done.last_rows == 42
    assert done.last_run_at is not None

    assert store.delete_job(job.id) is True
    assert store.get_job(job.id) is None
    assert store.delete_job("nonexistent") is False
```

- [ ] **Step 2: Run to verify it fails** — `.venv\Scripts\python.exe -m pytest tests/test_automation.py::test_store_crud_and_status -v`. Expected: FAIL (no module `store`).

- [ ] **Step 3: Implement** — create `backend/automation/store.py`
```python
from database import get_connection
from automation.models import JobConfig, AutomationJob, RunResult


def _to_job(row) -> AutomationJob:
    return AutomationJob(
        id=row["id"],
        config=JobConfig.model_validate_json(row["config"]),
        last_status=row["last_status"],
        last_run_at=row["last_run_at"],
        last_rows=row["last_rows"],
        last_error=row["last_error"],
        created=row["created"],
        updated=row["updated"],
    )


def create_job(config: JobConfig) -> AutomationJob:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO automation_jobs (name, config) VALUES (?, ?)",
        (config.name, config.model_dump_json()),
    )
    row = conn.execute("SELECT * FROM automation_jobs WHERE rowid = ?",
                       (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return _to_job(row)


def get_job(job_id: str) -> AutomationJob | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM automation_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return _to_job(row) if row else None


def list_jobs() -> list[AutomationJob]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM automation_jobs ORDER BY created DESC").fetchall()
    conn.close()
    return [_to_job(r) for r in rows]


def update_job(job_id: str, config: JobConfig) -> AutomationJob | None:
    conn = get_connection()
    cur = conn.execute(
        "UPDATE automation_jobs SET name = ?, config = ?, updated = datetime('now') WHERE id = ?",
        (config.name, config.model_dump_json(), job_id),
    )
    conn.commit()
    changed = cur.rowcount
    row = conn.execute("SELECT * FROM automation_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return _to_job(row) if (changed and row) else None


def delete_job(job_id: str) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM automation_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def set_running(job_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE automation_jobs SET last_status='running', last_error=NULL, "
        "updated=datetime('now') WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def set_run_status(job_id: str, result: RunResult) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE automation_jobs SET last_status=?, last_rows=?, last_error=?, "
        "last_run_at=datetime('now'), updated=datetime('now') WHERE id = ?",
        (result.status, result.rows, result.error, job_id),
    )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run to verify it passes** — same test. Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/automation/store.py backend/tests/test_automation.py
git commit -m "feat(automation): add job store (CRUD + last-run status)"
```

---

## Task 4: REST source (`automation/sources/rest.py`) + promote httpx

**Files:**
- Create: `backend/automation/sources/__init__.py` (empty)
- Create: `backend/automation/sources/base.py`
- Create: `backend/automation/sources/rest.py`
- Modify: `backend/pyproject.toml` (move `httpx` to `[project].dependencies`)
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing tests** (append)
```python
import httpx
import pytest
from unittest.mock import patch
from automation.sources.rest import RestFetcher


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_pagination_stops_on_empty():
    pages = {1: [{"id": 1}], 2: [{"id": 2}], 3: []}
    def handler(req):
        return httpx.Response(200, json=pages[int(req.url.params["page"])])
    src = RestSource(url="https://api.test/items", pagination=Pagination(param="page", start=1))
    out = list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert out == [[{"id": 1}], [{"id": 2}]]


def test_records_path_nested():
    def handler(req):
        page = int(req.url.params.get("page", 1))
        body = {"data": {"items": [{"id": 1}] if page == 1 else []}}
        return httpx.Response(200, json=body)
    src = RestSource(url="https://api.test/x", records_path="data.items",
                     pagination=Pagination(param="page", start=1))
    assert list(RestFetcher(src).fetch_pages(client=_client(handler))) == [[{"id": 1}]]


def test_retry_on_503_then_success():
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200, json=[{"id": 1}])
    src = RestSource(url="https://api.test/x", max_retries=2)
    with patch("automation.sources.rest.time.sleep"):
        out = list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert out == [[{"id": 1}]] and calls["n"] == 2


def test_4xx_raises_without_retry():
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(404)
    src = RestSource(url="https://api.test/x", max_retries=3)
    with patch("automation.sources.rest.time.sleep"), pytest.raises(httpx.HTTPStatusError):
        list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert calls["n"] == 1


def test_bearer_env_var_resolution(monkeypatch):
    monkeypatch.setenv("TOK", "secret123")
    seen = {}
    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json=[])
    src = RestSource(url="https://api.test/x", auth=RestAuth(type="bearer", value_ref="TOK"))
    list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert seen["auth"] == "Bearer secret123"


def test_missing_env_var_raises():
    src = RestSource(url="https://api.test/x", auth=RestAuth(type="bearer", value_ref="NOPE_X"))
    with pytest.raises(Exception):
        list(RestFetcher(src).fetch_pages(client=_client(lambda r: httpx.Response(200, json=[]))))
```

- [ ] **Step 2: Run to verify it fails** — `.venv\Scripts\python.exe -m pytest tests/test_automation.py -k "pagination or records_path or retry or 4xx or bearer or missing_env" -v`. Expected: FAIL (no module `rest`).

- [ ] **Step 3a: Implement** — create `backend/automation/sources/__init__.py` (empty) and `backend/automation/sources/base.py`
```python
from typing import Iterator, Protocol


class Source(Protocol):
    def fetch_pages(self, limit_pages: int | None = None) -> Iterator[list[dict]]:
        ...
```

- [ ] **Step 3b: Implement** — create `backend/automation/sources/rest.py`
```python
import os
import re
import time
from typing import Iterator

import httpx

from automation.models import RestSource

_VAR = re.compile(r"\$\{(\w+)\}")


class MissingEnvVar(Exception):
    pass


def _env(name: str) -> str:
    if name not in os.environ:
        raise MissingEnvVar(f"Missing env var {name}")
    return os.environ[name]


def _resolve(template: str) -> str:
    return _VAR.sub(lambda m: _env(m.group(1)), template)


def _dig(obj, path: str):
    if not path:
        return obj
    for part in path.split("."):
        obj = obj.get(part) if isinstance(obj, dict) else None
    return obj


class RestFetcher:
    """Consumes a RestSource config and yields pages of raw records."""

    def __init__(self, source: RestSource):
        self.s = source

    def _auth_and_headers(self):
        headers = {k: _resolve(v) for k, v in self.s.headers.items()}
        auth = None
        a = self.s.auth
        if a.type == "api_key" and a.header_name and a.value_ref:
            headers[a.header_name] = _env(a.value_ref)
        elif a.type == "bearer" and a.value_ref:
            headers["Authorization"] = "Bearer " + _env(a.value_ref)
        elif a.type == "basic" and a.user_ref and a.pass_ref:
            auth = httpx.BasicAuth(_env(a.user_ref), _env(a.pass_ref))
        return headers, auth

    def _get(self, client, url, params, headers, auth):
        delay = 0.5
        for attempt in range(self.s.max_retries + 1):
            resp = client.get(url, params=params, headers=headers, auth=auth)
            if resp.status_code < 400:
                return resp
            retryable = resp.status_code == 429 or resp.status_code >= 500
            if retryable and attempt < self.s.max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
        return resp

    def fetch_pages(self, limit_pages: int | None = None, client=None) -> Iterator[list[dict]]:
        headers, auth = self._auth_and_headers()   # resolves ${VAR} up front (may raise)
        url = _resolve(self.s.url)
        base_params = {k: _resolve(v) for k, v in self.s.params.items()}
        own = client is None
        cl = client or httpx.Client(timeout=self.s.timeout_seconds)
        try:
            page_num = self.s.pagination.start if self.s.pagination else None
            count = 0
            while True:
                params = dict(base_params)
                if self.s.pagination:
                    params[self.s.pagination.param] = page_num
                resp = self._get(cl, url, params, headers, auth)
                records = _dig(resp.json(), self.s.records_path)
                if records is None:
                    records = []
                if not isinstance(records, list):
                    records = [records]
                if not records:
                    break
                yield records
                count += 1
                if limit_pages and count >= limit_pages:
                    break
                if not self.s.pagination:
                    break
                page_num += 1
        finally:
            if own:
                cl.close()
```

- [ ] **Step 3c: Promote httpx** — in `backend/pyproject.toml`, add `"httpx>=0.27.0",` to the `[project].dependencies` list (keep the dev-group entry too; it's harmless).

- [ ] **Step 4: Run to verify it passes** — re-run the `-k` command. Expected: PASS (6 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/automation/sources/__init__.py backend/automation/sources/base.py backend/automation/sources/rest.py backend/pyproject.toml backend/tests/test_automation.py
git commit -m "feat(automation): add REST source (pagination, retry, env-var auth)"
```

---

## Task 5: Ingest (`automation/ingest.py`)

**Files:**
- Create: `backend/automation/ingest.py`
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing test** (append)
```python
import duckdb
from automation import ingest


def test_ingest_preserves_nested_json(tmp_path):
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    ingest.ensure_raw(con)
    n = ingest.append_page(con, [{"id": 1, "meta": {"r": "north"}},
                                 {"id": 2, "meta": {"r": "south"}}])
    assert n == 2
    assert con.execute("SELECT count(*) FROM raw").fetchone()[0] == 2
    regions = con.execute(
        "SELECT rec->>'$.meta.r' FROM raw ORDER BY CAST(rec->>'$.id' AS INT)"
    ).fetchall()
    assert [r[0] for r in regions] == ["north", "south"]
    assert ingest.append_page(con, []) == 0   # empty page is a no-op
    con.close()
```

- [ ] **Step 2: Run to verify it fails** — `.venv\Scripts\python.exe -m pytest tests/test_automation.py::test_ingest_preserves_nested_json -v`. Expected: FAIL (no module `ingest`).

- [ ] **Step 3: Implement** — create `backend/automation/ingest.py`
```python
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
```

- [ ] **Step 4: Run to verify it passes** — same test. Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/automation/ingest.py backend/tests/test_automation.py
git commit -m "feat(automation): add streaming JSON ingest into DuckDB"
```

---

## Task 6: Shape (`automation/shape.py`)

**Files:**
- Create: `backend/automation/shape.py`
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing test** (append)
```python
from automation import shape


def test_shape_passthrough_and_custom(tmp_path):
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    ingest.ensure_raw(con)
    ingest.append_page(con, [{"id": 1}, {"id": 2}])

    # Empty SQL => passthrough: data == raw (single `rec` column)
    assert shape.run(con, "") == 2
    assert [d[0] for d in con.execute("DESCRIBE data").fetchall()] == ["rec"]

    # Custom SQL over raw
    n = shape.run(con, "SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw "
                       "WHERE CAST(rec->>'$.id' AS INT) = 1")
    assert n == 1
    assert con.execute("SELECT id FROM data").fetchone()[0] == 1
    con.close()
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_automation.py::test_shape_passthrough_and_custom -v`. Expected: FAIL (no module `shape`).

- [ ] **Step 3: Implement** — create `backend/automation/shape.py`
```python
import duckdb


def run(con: duckdb.DuckDBPyConnection, shape_sql: str) -> int:
    """(Re)build the `data` table from user SQL over `raw`. Returns row count."""
    con.execute("DROP TABLE IF EXISTS data")
    sql = shape_sql.strip() or "SELECT * FROM raw"
    con.execute(f"CREATE TABLE data AS {sql}")
    return con.execute("SELECT count(*) FROM data").fetchone()[0]
```

- [ ] **Step 4: Run to verify it passes** — same test. Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/automation/shape.py backend/tests/test_automation.py
git commit -m "feat(automation): add DuckDB shaping step (raw -> data)"
```

---

## Task 7: Export (`automation/export.py`)

**Files:**
- Create: `backend/automation/export.py`
- Test: `backend/tests/test_automation.py` (append)

**Naming rule:** snapshot formats (`parquet`/`csv`/`xlsx`) → `<job>_<timestamp>.<ext>`; `.duckdb` → stable `<job>.duckdb` (so `append` accumulates and `overwrite` replaces the same store).

- [ ] **Step 1: Write the failing tests** (append)
```python
import os
from automation import export
from automation.models import ExportSpec


def _prep(tmp_path, rows=3):
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    ingest.ensure_raw(con)
    ingest.append_page(con, [{"id": i} for i in range(rows)])
    shape.run(con, "SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw")
    return con


def test_export_parquet_csv_atomic(tmp_path):
    con = _prep(tmp_path)
    dest = tmp_path / "out"
    files, warns = export.write(
        con, ExportSpec(formats=["parquet", "csv"], dest_dir=str(dest)),
        "job", "20260604_120000")
    assert len(files) == 2 and all(os.path.exists(f) for f in files)
    assert not any(name.endswith(".tmp") for name in os.listdir(dest))
    assert warns == []
    con.close()


def test_export_xlsx_guard_skips(tmp_path):
    con = _prep(tmp_path, rows=5)
    dest = tmp_path / "out"
    files, warns = export.write(
        con, ExportSpec(formats=["xlsx"], dest_dir=str(dest), xlsx_row_guard=2),
        "job", "20260604_120000")
    assert files == [] and any("xlsx" in w for w in warns)
    con.close()


def test_export_duckdb_append_accumulates(tmp_path):
    con = _prep(tmp_path, rows=3)
    dest = tmp_path / "out"
    spec = ExportSpec(formats=["duckdb"], dest_dir=str(dest), duckdb_mode="append")
    export.write(con, spec, "acc", "t1")
    export.write(con, spec, "acc", "t2")
    dbf = os.path.join(str(dest), "acc.duckdb").replace("\\", "/")
    c2 = duckdb.connect()
    c2.execute(f"ATTACH '{dbf}' AS s")
    assert c2.execute("SELECT count(*) FROM s.data").fetchone()[0] == 6
    c2.close()
    con.close()
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_automation.py -k export -v`. Expected: FAIL (no module `export`).

- [ ] **Step 3: Implement** — create `backend/automation/export.py`
```python
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
        con.execute(f"ATTACH '{_posix(tmp)}' AS exp")
        try:
            con.execute("CREATE TABLE exp.data AS SELECT * FROM data")
        finally:
            con.execute("DETACH exp")
        os.replace(tmp, final_path)
        stale_wal = final_path + ".wal"   # old WAL would be inconsistent with the new file
        if os.path.exists(stale_wal):
            os.unlink(stale_wal)
    else:  # append
        con.execute(f"ATTACH '{_posix(final_path)}' AS exp")
        try:
            exists = con.execute(
                "SELECT count(*) FROM duckdb_tables() "
                "WHERE database_name='exp' AND table_name='data'"
            ).fetchone()[0]
            con.execute("BEGIN")
            if exists:
                con.execute("INSERT INTO exp.data SELECT * FROM data")
            else:
                con.execute("CREATE TABLE exp.data AS SELECT * FROM data")
            con.execute("COMMIT")
        except Exception:
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
```

- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_automation.py -k export -v`. Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/automation/export.py backend/tests/test_automation.py
git commit -m "feat(automation): add streaming export (parquet/csv/xlsx/duckdb, atomic, append)"
```

---

## Task 8: Notify (`automation/notify.py`)

**Files:**
- Create: `backend/automation/notify.py`
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing tests** (append)
```python
from automation import notify


def _notify_cfg(**nk):
    return JobConfig(name="J", source=RestSource(url="http://x"),
                     export=ExportSpec(formats=[], dest_dir="."),
                     notify=NotifySpec(**nk))


def test_notify_discord_called_with_summary():
    cfg = _notify_cfg(discord_enabled=True)
    res = _RR(status="ok", rows=5, duration_seconds=1.0, output_files=[])
    with patch("automation.notify._discord") as m:
        warns = notify.send(cfg, res)
    m.assert_called_once()
    assert "Rows: 5" in m.call_args[0][0]
    assert warns == []


def test_notify_failure_is_collected_not_raised():
    cfg = _notify_cfg(discord_enabled=True)
    res = _RR(status="error", rows=0, duration_seconds=0.0, error="boom")
    with patch("automation.notify._discord", side_effect=RuntimeError("down")):
        warns = notify.send(cfg, res)
    assert any("Discord" in w for w in warns)
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_automation.py -k notify -v`. Expected: FAIL (no module `notify`).

- [ ] **Step 3: Implement** — create `backend/automation/notify.py`
```python
import json as json_lib
import os
import smtplib
import urllib.request
from email.message import EmailMessage

from automation.models import JobConfig, RunResult


def _discord(message: str) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        raise RuntimeError("DISCORD_WEBHOOK_URL not set")
    payload = json_lib.dumps({"content": message}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10):
        pass


def _email(subject: str, body: str, recipients: list[str], attachments: list[str]) -> None:
    host = os.getenv("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST not set")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pw = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", user or "")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)
    for path in attachments:
        with open(path, "rb") as fh:
            data = fh.read()
        msg.add_attachment(data, maintype="application", subtype="octet-stream",
                           filename=os.path.basename(path))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        if user:
            s.login(user, pw)
        s.send_message(msg)


def _format(config: JobConfig, result: RunResult) -> tuple[str, str]:
    status = result.status.upper()
    subject = f"[Automation] {config.name} — {status}"
    lines = [f"Job: {config.name}", f"Status: {status}",
             f"Rows: {result.rows}", f"Duration: {result.duration_seconds:.1f}s"]
    if result.output_files:
        lines.append("Files:\n" + "\n".join(result.output_files))
    if result.error:
        lines.append(f"Detail: {result.error}")
    return subject, "\n".join(lines)


def send(config: JobConfig, result: RunResult) -> list[str]:
    """Send Discord + Email notifications. Never raises; returns warnings."""
    warnings: list[str] = []
    subject, body = _format(config, result)
    if config.notify.discord_enabled:
        try:
            _discord(body)
        except Exception as e:
            warnings.append(f"Discord notify failed: {e}")
    email = config.notify.email
    if email.enabled and email.recipients:
        attachments = []
        for f in result.output_files:
            try:
                if os.path.getsize(f) <= email.attach_max_bytes:
                    attachments.append(f)
            except OSError:
                pass
        try:
            _email(subject, body, email.recipients, attachments)
        except Exception as e:
            warnings.append(f"Email notify failed: {e}")
    return warnings
```

- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_automation.py -k notify -v`. Expected: PASS (2 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/automation/notify.py backend/tests/test_automation.py
git commit -m "feat(automation): add Discord + Email notifications"
```

---

## Task 9: Codegen (`automation/codegen.py`)

**Files:**
- Create: `backend/automation/codegen.py`
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing test** (append)
```python
from automation import codegen


def test_codegen_compiles_and_hides_secrets():
    cfg = JobConfig(
        name="J",
        source=RestSource(url="https://api/x", records_path="data",
                          auth=RestAuth(type="bearer", value_ref="TOK"),
                          pagination=Pagination(param="page", start=1)),
        shape_sql="SELECT * FROM raw",
        export=ExportSpec(formats=["parquet"], dest_dir="out"))
    script = codegen.python_script(cfg)
    compile(script, "<gen>", "exec")               # raises if not valid Python
    assert "httpx" in script and "read_json" in script
    assert "os.environ" in script                  # secrets via env, not literals
    assert "CREATE TABLE data" in script
    assert codegen.shape_sql_text(cfg) == "SELECT * FROM raw"
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_automation.py::test_codegen_compiles_and_hides_secrets -v`. Expected: FAIL (no module `codegen`).

- [ ] **Step 3: Implement** — create `backend/automation/codegen.py`
```python
from automation.models import JobConfig


def shape_sql_text(config: JobConfig) -> str:
    return config.shape_sql.strip() or "SELECT * FROM raw"


def python_script(config: JobConfig) -> str:
    """Render a read-only, runnable reference script from the job config.

    Secrets are referenced via os.environ — never embedded as literals.
    """
    s = config.source
    a = s.auth
    sql = shape_sql_text(config)
    has_page = s.pagination is not None
    start = s.pagination.start if has_page else 0
    page_param = s.pagination.param if has_page else "page"

    L: list[str] = []
    L.append("import os, json, tempfile")
    L.append("import httpx, duckdb")
    L.append("")
    L.append(f"# Read-only reference script for job {config.name!r}.")
    L.append("# Secrets are read from environment variables (never hard-coded).")
    L.append(f"URL = {s.url!r}")
    L.append(f"RECORDS_PATH = {s.records_path!r}")
    L.append(f"TIMEOUT = {s.timeout_seconds}")
    L.append("")
    # headers / auth
    L.append(f"headers = {dict(s.headers)!r}")
    if a.type == "api_key" and a.header_name and a.value_ref:
        L.append(f"headers[{a.header_name!r}] = os.environ[{a.value_ref!r}]")
        L.append("auth = None")
    elif a.type == "bearer" and a.value_ref:
        L.append(f"headers['Authorization'] = 'Bearer ' + os.environ[{a.value_ref!r}]")
        L.append("auth = None")
    elif a.type == "basic" and a.user_ref and a.pass_ref:
        L.append(f"auth = httpx.BasicAuth(os.environ[{a.user_ref!r}], os.environ[{a.pass_ref!r}])")
    else:
        L.append("auth = None")
    L.append("")
    L.append("def dig(obj, path):")
    L.append("    if not path:")
    L.append("        return obj")
    L.append("    for part in path.split('.'):")
    L.append("        obj = obj.get(part) if isinstance(obj, dict) else None")
    L.append("    return obj")
    L.append("")
    L.append("def fetch_pages():")
    L.append("    with httpx.Client(timeout=TIMEOUT) as client:")
    L.append(f"        page = {start}")
    L.append("        while True:")
    L.append("            params = {}")
    if has_page:
        L.append(f"            params[{page_param!r}] = page")
    L.append("            resp = client.get(URL, params=params, headers=headers, auth=auth)")
    L.append("            resp.raise_for_status()")
    L.append("            records = dig(resp.json(), RECORDS_PATH) or []")
    L.append("            if not isinstance(records, list):")
    L.append("                records = [records]")
    L.append("            if not records:")
    L.append("                break")
    L.append("            yield records")
    if has_page:
        L.append("            page += 1")
    else:
        L.append("            break")
    L.append("")
    L.append("con = duckdb.connect('work.duckdb')")
    L.append("con.execute('CREATE TABLE IF NOT EXISTS raw (rec JSON)')")
    L.append("for pg in fetch_pages():")
    L.append("    fd, path = tempfile.mkstemp(suffix='.json')")
    L.append("    with os.fdopen(fd, 'w', encoding='utf-8') as fh:")
    L.append("        for rec in pg:")
    L.append("            fh.write(json.dumps(rec) + chr(10))")
    L.append("    p = path.replace(chr(92), '/')")
    L.append("    con.execute(\"INSERT INTO raw SELECT json FROM \"")
    L.append("                \"read_json('\" + p + \"', format='newline_delimited', records='false')\")")
    L.append("    os.unlink(path)")
    L.append("")
    L.append("con.execute('DROP TABLE IF EXISTS data')")
    L.append(f"con.execute({('CREATE TABLE data AS ' + sql)!r})")
    L.append("")
    for fmt in config.export.formats:
        if fmt == "parquet":
            L.append(f"con.execute(\"COPY (SELECT * FROM data) TO '{config.export.dest_dir}/{config.name}.parquet' (FORMAT parquet)\")")
        elif fmt == "csv":
            L.append(f"con.execute(\"COPY (SELECT * FROM data) TO '{config.export.dest_dir}/{config.name}.csv' (FORMAT csv, HEADER)\")")
    L.append("print('rows:', con.execute('SELECT count(*) FROM data').fetchone()[0])")
    return "\n".join(L) + "\n"
```

- [ ] **Step 4: Run to verify it passes** — same test. Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/automation/codegen.py backend/tests/test_automation.py
git commit -m "feat(automation): add read-only Python/SQL codegen"
```

---

## Task 10: Runner (`automation/runner.py`)

**Files:**
- Create: `backend/automation/runner.py`
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing tests** (append)
```python
from automation import runner


class _FakeFetcher:
    def __init__(self, pages):
        self.pages = pages

    def fetch_pages(self, limit_pages=None):
        for i, p in enumerate(self.pages):
            if limit_pages is not None and i >= limit_pages:
                break
            yield p


def _run_job(tmp_path, sql="SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw", fmts=("parquet",)):
    cfg = JobConfig(name="job", source=RestSource(url="http://x"), shape_sql=sql,
                    export=ExportSpec(formats=list(fmts), dest_dir=str(tmp_path / "out")))
    return AutomationJob(id="abc", config=cfg, created="t", updated="t")


def test_runner_run_ok(tmp_path):
    job = _run_job(tmp_path)
    with patch("automation.runner.make_fetcher", return_value=_FakeFetcher([[{"id": 1}, {"id": 2}]])), \
         patch("automation.notify.send") as nsend:
        res = runner.run(job)
    assert res.status == "ok" and res.rows == 2 and len(res.output_files) == 1
    nsend.assert_called_once()


def test_runner_zero_rows_warns_no_export(tmp_path):
    job = _run_job(tmp_path, sql="SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw WHERE 1=0")
    with patch("automation.runner.make_fetcher", return_value=_FakeFetcher([[{"id": 1}]])), \
         patch("automation.notify.send"):
        res = runner.run(job)
    assert res.status == "warning" and res.rows == 0 and res.output_files == []


def test_runner_error_path_notifies(tmp_path):
    job = _run_job(tmp_path)
    boom = _FakeFetcher([[{"id": 1}]])
    def explode(*_a, **_k):
        raise RuntimeError("fetch down")
    boom.fetch_pages = explode
    with patch("automation.runner.make_fetcher", return_value=boom), \
         patch("automation.notify.send") as nsend:
        res = runner.run(job)
    assert res.status == "error" and "fetch down" in res.error
    nsend.assert_called_once()


def test_runner_preview_one_page_no_export(tmp_path):
    job = _run_job(tmp_path)
    with patch("automation.runner.make_fetcher",
               return_value=_FakeFetcher([[{"id": 1}, {"id": 2}], [{"id": 3}]])):
        out = runner.preview(job, n_rows=10)
    assert out["columns"] == ["id"] and len(out["rows"]) == 2   # only first page
    assert not (tmp_path / "out").exists()                      # nothing exported
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_automation.py -k runner -v`. Expected: FAIL (no module `runner`).

- [ ] **Step 3: Implement** — create `backend/automation/runner.py`
```python
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
    """Seam: returns a Source for the given config. (T-SQL plugs in here later.)"""
    return RestFetcher(source)


def _open_work():
    work = tempfile.mkdtemp(prefix="automation_")
    con = duckdb.connect(os.path.join(work, "work.duckdb"))
    return work, con


def run(job: AutomationJob) -> RunResult:
    cfg = job.config
    t0 = time.perf_counter()
    work, con = _open_work()
    try:
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
        con.close()
        shutil.rmtree(work, ignore_errors=True)
    notify.send(cfg, result)
    return result


def preview(job: AutomationJob, n_rows: int = 100) -> dict:
    cfg = job.config
    work, con = _open_work()
    try:
        ingest.ensure_raw(con)
        for page in make_fetcher(cfg.source).fetch_pages(limit_pages=1):
            ingest.append_page(con, page)
        shape.run(con, cfg.shape_sql)
        rel = con.execute(f"SELECT * FROM data LIMIT {int(n_rows)}")
        columns = [d[0] for d in rel.description]
        rows = [list(r) for r in rel.fetchall()]
        return {"columns": columns, "rows": rows}
    finally:
        con.close()
        shutil.rmtree(work, ignore_errors=True)
```

- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_automation.py -k runner -v`. Expected: PASS (4 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/automation/runner.py backend/tests/test_automation.py
git commit -m "feat(automation): add runner (orchestrate run + preview)"
```

---

## Task 11: Router (`routers/automation.py`) + register

**Files:**
- Create: `backend/routers/automation.py`
- Modify: `backend/main.py` (import + include_router)
- Test: `backend/tests/test_automation.py` (append)

- [ ] **Step 1: Write the failing tests** (append)
```python
from fastapi.testclient import TestClient
from main import app

api = TestClient(app)


def _cfg_json(tmp_path, name="J"):
    return {"name": name, "source": {"url": "http://x"},
            "export": {"formats": ["parquet"], "dest_dir": str(tmp_path / "o")}}


def test_api_crud(tmp_path):
    r = api.post("/api/automation/jobs", json=_cfg_json(tmp_path))
    assert r.status_code == 200
    jid = r.json()["id"]
    assert api.get("/api/automation/jobs").json()[0]["id"] == jid
    assert api.get(f"/api/automation/jobs/{jid}").json()["config"]["name"] == "J"
    upd = _cfg_json(tmp_path, name="J2")
    assert api.put(f"/api/automation/jobs/{jid}", json=upd).json()["config"]["name"] == "J2"
    assert api.delete(f"/api/automation/jobs/{jid}").json()["ok"] is True
    assert api.get(f"/api/automation/jobs/{jid}").status_code == 404


def test_api_run_returns_running_then_409(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]
    with patch("routers.automation._spawn") as sp:
        r1 = api.post(f"/api/automation/jobs/{jid}/run")
        assert r1.status_code == 200 and r1.json()["status"] == "running"
        sp.assert_called_once()
        assert api.post(f"/api/automation/jobs/{jid}/run").status_code == 409


def test_api_code_endpoint(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]
    body = api.get(f"/api/automation/jobs/{jid}/code").json()
    assert "httpx" in body["python"] and "sql" in body


def test_api_preview(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]

    class _F:
        def fetch_pages(self, limit_pages=None):
            yield [{"id": 1}]

    with patch("automation.runner.make_fetcher", return_value=_F()):
        r = api.post(f"/api/automation/jobs/{jid}/preview", json={"n_rows": 5})
    assert r.status_code == 200 and len(r.json()["rows"]) == 1
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_automation.py -k api_ -v`. Expected: FAIL (router not registered → 404).

- [ ] **Step 3a: Implement** — create `backend/routers/automation.py`
```python
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from automation import store, runner, codegen
from automation.models import JobConfig, AutomationJob

router = APIRouter(prefix="/automation", tags=["automation"])


class PreviewIn(BaseModel):
    n_rows: int = 100


@router.get("/jobs", response_model=list[AutomationJob])
def list_jobs():
    return store.list_jobs()


@router.post("/jobs", response_model=AutomationJob)
def create_job(config: JobConfig):
    return store.create_job(config)


@router.get("/jobs/{job_id}", response_model=AutomationJob)
def get_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/jobs/{job_id}", response_model=AutomationJob)
def update_job(job_id: str, config: JobConfig):
    job = store.update_job(job_id, config)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    if not store.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.post("/jobs/{job_id}/preview")
def preview_job(job_id: str, body: PreviewIn):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return runner.preview(job, body.n_rows)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _run_bg(job_id: str) -> None:
    job = store.get_job(job_id)
    if job:
        result = runner.run(job)
        store.set_run_status(job_id, result)


def _spawn(job_id: str) -> None:
    threading.Thread(target=_run_bg, args=(job_id,), daemon=True).start()


@router.post("/jobs/{job_id}/run")
def run_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.last_status == "running":
        raise HTTPException(status_code=409, detail="Job already running")
    store.set_running(job_id)
    _spawn(job_id)
    return {"status": "running"}


@router.get("/jobs/{job_id}/code")
def get_code(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"python": codegen.python_script(job.config),
            "sql": codegen.shape_sql_text(job.config)}
```

- [ ] **Step 3b: Register** — in `backend/main.py`:
  - Add after the other router imports (near line 26): `from routers.automation import router as automation_router`
  - Add after the last `app.include_router(...)` (near line 60): `app.include_router(automation_router, prefix="/api")`

- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_automation.py -k api_ -v`. Expected: PASS (4 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/routers/automation.py backend/main.py backend/tests/test_automation.py
git commit -m "feat(automation): add API router + register in app"
```

---

## Task 12: Full suite + smoke run

**Files:** none (verification only)

- [ ] **Step 1: Run the whole backend suite**

From `backend/`: `.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS — prior 136 tests + new automation/database tests, **zero failures**. If any prior test broke, fix the cause (do not edit unrelated do-not-touch files).

- [ ] **Step 2: Smoke-launch the API** (per the `run` skill — drive it, don't just import)

From `backend/`: `.venv\Scripts\python.exe -m uvicorn main:app --port 8000` (background), then:
```bash
curl -s -X POST localhost:8000/api/automation/jobs -H "Content-Type: application/json" \
  -d "{\"name\":\"smoke\",\"source\":{\"url\":\"https://jsonplaceholder.typicode.com/posts\"},\"shape_sql\":\"SELECT CAST(rec->>'$.id' AS INT) AS id, rec->>'$.title' AS title FROM raw\",\"export\":{\"formats\":[\"csv\"],\"dest_dir\":\"./_smoke_out\"}}"
```
Capture the returned `id`, then:
```bash
curl -s -X POST localhost:8000/api/automation/jobs/<id>/preview -H "Content-Type: application/json" -d "{\"n_rows\":3}"
```
Expected: preview returns `{"columns":["id","title"], "rows":[...3 rows...]}`. Then `GET /jobs/<id>/code` returns a `python` field containing `httpx`. Stop uvicorn. (Clean up `./_smoke_out` if created.)

- [ ] **Step 3: Commit** (only if smoke required a code fix; otherwise skip)
```bash
git add backend/
git commit -m "fix(automation): smoke-run corrections"
```

---

## Self-Review (completed during planning)

**1. Spec coverage** (spec §6/§8/§9/§10/§11):
- §6.1 package structure → Tasks 2–11. §6.2 models → Task 2. §6.3 `_migrate_v6` → Task 1. §6.4 runtime flow → Task 10. §6.5 module behavior → Tasks 4–9. §6.6 endpoints → Task 11.
- §8 error handling: retry 429/5xx not 4xx → Task 4; atomic export + append txn → Task 7; 0-rows warning → Task 10; preview 400 inline → Task 11; missing env var → Task 4.
- §9 security: `${VAR}` from env, no secret literals → Task 4 + codegen Task 9 (asserts `os.environ`, no literals); no code exec (codegen is text only) → Task 9.
- §10 testing: every module has hermetic tests (MockTransport / temp DuckDB / patched notify) → Tasks 2–11; full-suite gate → Task 12.
- §11 decisions: background+poll → Task 11 (`_spawn` thread, 409 guard); `records_path` → Task 4; `.duckdb` overwrite/append → Task 7; SMTP from `.env` → Task 8; email attach <10MB → Task 8.
- **Carve-out:** ML "Query failed" fix is explicitly out of this plan (spec §12).

**2. Placeholder scan:** none — every code step is complete; commands have expected output.

**3. Type/name consistency:** model names, `RestFetcher` vs `RestSource` (config), `make_fetcher` seam, `write(...)->(files,warnings)`, `_spawn`/`_run_bg`, tables `raw`/`data` — consistent across Tasks 2–11. `RunResult.error` carries the warning/error detail string (status ∈ ok/warning/error/running) — used consistently in runner (Task 10) and notify (Task 8).

**Decision deferred to execution:** the SMTP `.env` keys (`SMTP_HOST/PORT/USER/PASS/FROM`) are read at notify time; document them in `.env.example` if that file is updated (not required for tests, which patch `_email`).
