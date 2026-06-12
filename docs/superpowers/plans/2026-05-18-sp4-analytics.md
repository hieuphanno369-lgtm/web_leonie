# SP4 Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build three Analytics pages — KPI Tracker, Performance, ML Studio — on top of the existing FastAPI + SQLite backend, with DuckDB + Polars powering ML Studio.

**Architecture:** Extend existing backend with 3 new routers (`/kpi`, `/performance`, `/ml`). DuckDB runs in-process per query (no persistent file). Polars reads uploaded CSV/Excel files. Frontend uses Recharts for all charts; Lucide icons throughout (no emoji as functional UI elements).

**Tech Stack:** Python 3.13, FastAPI, SQLite, DuckDB ≥1.0, Polars ≥0.20, SciPy, Recharts, React 19, TypeScript, Tailwind CSS

---

## File Map

**Backend — new/modified:**
```
backend/pyproject.toml              ← add duckdb, polars, openpyxl, scipy
backend/database.py                 ← add migrate_v2() for new tables/columns
backend/main.py                     ← register 3 new routers
backend/routers/kpi.py              ← new: /kpi CRUD
backend/routers/performance.py      ← new: /performance/summary, /settings
backend/routers/ml.py               ← new: /ml/upload, /query, /stats, /forecast
backend/tests/test_kpi.py           ← new
backend/tests/test_performance.py   ← new
backend/tests/test_ml.py            ← new
data/uploads/                       ← new: ML file storage (gitignored)
```

**Frontend — new/modified:**
```
frontend/package.json               ← add recharts
frontend/src/types.ts               ← add KpiEntry, PerformanceSummary, DatasetInfo, etc.
frontend/src/api/kpi.ts             ← new
frontend/src/api/performance.ts     ← new
frontend/src/api/ml.ts              ← new
frontend/src/pages/analytics/KpiTracker.tsx    ← replace placeholder
frontend/src/pages/analytics/Performance.tsx   ← replace placeholder
frontend/src/pages/analytics/MlStudio.tsx      ← replace placeholder
frontend/src/components/kpi/KpiList.tsx        ← new
frontend/src/components/kpi/KpiItem.tsx        ← new
frontend/src/components/kpi/KpiForm.tsx        ← new
frontend/src/components/kpi/KpiChart.tsx       ← new
frontend/src/components/performance/StreakCard.tsx    ← new
frontend/src/components/performance/RuleEditor.tsx   ← new
frontend/src/components/performance/OutputGrid.tsx   ← new
frontend/src/components/performance/CalendarHeatmap.tsx ← new
frontend/src/components/ml/MlUpload.tsx        ← new
frontend/src/components/ml/MlSqlEditor.tsx     ← new
frontend/src/components/ml/MlResultTabs.tsx    ← new
frontend/src/components/ml/MlChartView.tsx     ← new
frontend/src/components/ml/MlTableView.tsx     ← new
frontend/src/components/ml/MlStatsView.tsx     ← new
frontend/src/components/ml/MlForecastView.tsx  ← new
```

---

## Task 1: Backend dependencies + DB migration

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/database.py`

- [ ] **Add new Python deps to pyproject.toml**

Replace the `dependencies` list in `backend/pyproject.toml`:
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "python-dotenv>=1.0.0",
    "python-multipart>=0.0.12",
    "duckdb>=1.0.0",
    "polars>=0.20.0",
    "openpyxl>=3.1.0",
    "scipy>=1.13.0",
]
```

- [ ] **Sync deps**

Run from `backend/`:
```bash
uv sync
```
Expected: packages installed, no errors.

- [ ] **Add migrate_v2 and new tables to database.py**

In `backend/database.py`, add `migrate_v2` after the existing `create_tables` function and call it from `create_tables`:

```python
def _migrate_v2(conn) -> None:
    """Safe idempotent migrations for v2 schema additions."""
    # Add category column to kpi_entries if missing
    existing = {r[1] for r in conn.execute("PRAGMA table_info(kpi_entries)").fetchall()}
    if "category" not in existing:
        conn.execute(
            "ALTER TABLE kpi_entries ADD COLUMN "
            "category TEXT NOT NULL DEFAULT 'da_output'"
        )
    # New tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS performance_settings (
            id          INTEGER PRIMARY KEY DEFAULT 1,
            streak_rule TEXT NOT NULL DEFAULT
                '{"conditions":[{"type":"tasks_done","op":"gte","value":2}],"logic":"OR"}'
        );

        CREATE TABLE IF NOT EXISTS uploaded_files (
            file_id   TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            filename  TEXT NOT NULL,
            filepath  TEXT NOT NULL,
            rows      INTEGER,
            cols      INTEGER,
            uploaded  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
```

Then update `create_tables` to call it:
```python
def create_tables(db_path: str = _DEFAULT_DB) -> None:
    """Create all application tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks ( ... );  # keep existing
        ...  # all existing tables unchanged
    """)
    conn.commit()
    _migrate_v2(conn)
    conn.close()
```

Also add at the top of database.py:
```python
import pathlib

UPLOADS_DIR = pathlib.Path(__file__).parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Create uploads directory + gitignore entry**

```bash
mkdir -p data/uploads
echo "data/uploads/" >> .gitignore
```

- [ ] **Verify migration runs clean**

```bash
cd backend && uv run python -c "from database import create_tables; create_tables(); print('OK')"
```
Expected: `OK` with no errors.

- [ ] **Commit**

```bash
git add backend/pyproject.toml backend/database.py .gitignore uv.lock
git commit -m "feat(db): add duckdb/polars deps, migrate kpi_entries + new tables"
```

---

## Task 2: KPI backend router + tests

**Files:**
- Create: `backend/routers/kpi.py`
- Create: `backend/tests/test_kpi.py`
- Modify: `backend/main.py`

- [ ] **Write failing tests first**

Create `backend/tests/test_kpi.py`:
```python
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_list_empty(client):
    assert client.get("/kpi").json() == []

def test_create_da_output(client):
    resp = client.post("/kpi", json={
        "metric": "Queries viết", "value": 12, "date": "2026-05-18",
        "category": "da_output"
    })
    assert resp.status_code == 201
    d = resp.json()
    assert d["metric"] == "Queries viết"
    assert d["value"] == 12.0
    assert d["category"] == "da_output"
    assert d["id"]

def test_create_business(client):
    resp = client.post("/kpi", json={
        "metric": "GMV ColosBaby", "value": 12400000000,
        "date": "2026-05-18", "category": "business"
    })
    assert resp.status_code == 201
    assert resp.json()["category"] == "business"

def test_invalid_category(client):
    resp = client.post("/kpi", json={
        "metric": "X", "value": 1, "date": "2026-05-18",
        "category": "invalid"
    })
    assert resp.status_code == 422

def test_filter_by_category(client):
    client.post("/kpi", json={"metric": "A", "value": 1, "date": "2026-05-18", "category": "da_output"})
    client.post("/kpi", json={"metric": "B", "value": 2, "date": "2026-05-18", "category": "business"})
    result = client.get("/kpi?category=business").json()
    assert len(result) == 1
    assert result[0]["metric"] == "B"

def test_filter_by_metric(client):
    client.post("/kpi", json={"metric": "Queries", "value": 5, "date": "2026-05-17", "category": "da_output"})
    client.post("/kpi", json={"metric": "Queries", "value": 8, "date": "2026-05-18", "category": "da_output"})
    client.post("/kpi", json={"metric": "GMV", "value": 1e9, "date": "2026-05-18", "category": "business"})
    result = client.get("/kpi?metric=Queries").json()
    assert len(result) == 2

def test_list_metrics(client):
    client.post("/kpi", json={"metric": "Queries", "value": 5, "date": "2026-05-18", "category": "da_output"})
    client.post("/kpi", json={"metric": "GMV", "value": 1e9, "date": "2026-05-18", "category": "business"})
    result = client.get("/kpi/metrics").json()
    assert set(result) == {"Queries", "GMV"}

def test_delete_kpi(client):
    created = client.post("/kpi", json={"metric": "X", "value": 1, "date": "2026-05-18", "category": "da_output"}).json()
    assert client.delete(f"/kpi/{created['id']}").status_code == 204
    assert client.get("/kpi").json() == []

def test_delete_not_found(client):
    assert client.delete("/kpi/does-not-exist").status_code == 404
```

- [ ] **Run tests — expect failures**

```bash
cd backend && uv run pytest tests/test_kpi.py -v
```
Expected: `ImportError` or `404` — router not registered yet.

- [ ] **Create KPI router**

Create `backend/routers/kpi.py`:
```python
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/kpi", tags=["kpi"])

KpiCategory = Literal["da_output", "business"]

class KpiCreate(BaseModel):
    metric: str
    value: float
    date: str
    category: KpiCategory = "da_output"
    note: str | None = None

class KpiOut(BaseModel):
    id: str
    metric: str
    value: float
    date: str
    category: str
    note: str | None
    created: str

def _row(r) -> KpiOut:
    return KpiOut(**dict(r))


@router.get("", response_model=list[KpiOut])
def list_kpi(metric: str | None = None, category: KpiCategory | None = None,
             from_date: str | None = None, to_date: str | None = None):
    conn = get_connection()
    sql = "SELECT * FROM kpi_entries WHERE 1=1"
    params: list = []
    if metric:
        sql += " AND metric = ?"; params.append(metric)
    if category:
        sql += " AND category = ?"; params.append(category)
    if from_date:
        sql += " AND date >= ?"; params.append(from_date)
    if to_date:
        sql += " AND date <= ?"; params.append(to_date)
    sql += " ORDER BY date DESC, created DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.get("/metrics", response_model=list[str])
def list_metrics():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT metric FROM kpi_entries ORDER BY metric"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


@router.post("", response_model=KpiOut, status_code=201)
def create_kpi(body: KpiCreate):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO kpi_entries (metric, value, date, category, note) VALUES (?,?,?,?,?)",
        (body.metric, body.value, body.date, body.category, body.note),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM kpi_entries WHERE rowid = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row(row)


@router.delete("/{entry_id}", status_code=204)
def delete_kpi(entry_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM kpi_entries WHERE id = ?", (entry_id,))
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Entry not found")
    conn.commit()
    conn.close()
```

- [ ] **Register router in main.py**

In `backend/main.py`, add after existing imports:
```python
from routers.kpi import router as kpi_router
```
And after existing `app.include_router(...)` calls:
```python
app.include_router(kpi_router)
```

- [ ] **Run tests — expect pass**

```bash
cd backend && uv run pytest tests/test_kpi.py -v
```
Expected: all 9 tests PASS.

- [ ] **Commit**

```bash
git add backend/routers/kpi.py backend/tests/test_kpi.py backend/main.py
git commit -m "feat(kpi): /kpi router with CRUD, category filter, metrics list"
```

---

## Task 3: Performance backend router + tests

**Files:**
- Create: `backend/routers/performance.py`
- Create: `backend/tests/test_performance.py`
- Modify: `backend/main.py`

- [ ] **Write failing tests**

Create `backend/tests/test_performance.py`:
```python
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_settings_default(client):
    resp = client.get("/performance/settings")
    assert resp.status_code == 200
    d = resp.json()
    assert "streak_rule" in d
    assert d["streak_rule"]["logic"] in ("AND", "OR")

def test_save_settings(client):
    rule = {"conditions": [{"type": "tasks_done", "op": "gte", "value": 1}], "logic": "AND"}
    resp = client.post("/performance/settings", json={"streak_rule": rule})
    assert resp.status_code == 200
    assert resp.json()["streak_rule"]["logic"] == "AND"

def test_summary_empty_db(client):
    resp = client.get("/performance/summary")
    assert resp.status_code == 200
    d = resp.json()
    assert d["streak"] == 0
    assert d["tasks_done"] == 0
    assert d["eda_done"] == 0
    assert d["kpi_logs"] == 0
    assert isinstance(d["wip_avg_progress"], float)
    assert len(d["calendar"]) == 30

def test_summary_calendar_structure(client):
    resp = client.get("/performance/summary")
    cal = resp.json()["calendar"]
    assert len(cal) == 30
    for day in cal:
        assert "date" in day
        assert day["status"] in ("hit", "partial", "miss")

def test_summary_counts_done_tasks(client):
    # Create a done task updated today
    from datetime import date
    today = date.today().isoformat()
    client2 = TestClient(app)
    client2.post("/tasks", json={"title": "Done today", "status": "done"})
    resp = client.get("/performance/summary")
    assert resp.json()["tasks_done"] >= 1
```

- [ ] **Run tests — expect failures**

```bash
cd backend && uv run pytest tests/test_performance.py -v
```
Expected: FAIL — router not registered.

- [ ] **Create Performance router**

Create `backend/routers/performance.py`:
```python
import json
from datetime import date, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/performance", tags=["performance"])

_DEFAULT_RULE = {"conditions": [{"type": "tasks_done", "op": "gte", "value": 2}], "logic": "OR"}


class StreakRule(BaseModel):
    streak_rule: dict


class DayStatus(BaseModel):
    date: str
    status: str  # "hit" | "partial" | "miss"


class PerformanceSummary(BaseModel):
    streak: int
    tasks_done: int
    eda_done: int
    kpi_logs: int
    wip_avg_progress: float
    calendar: list[DayStatus]


def _ensure_settings(conn):
    if not conn.execute("SELECT id FROM performance_settings WHERE id = 1").fetchone():
        conn.execute(
            "INSERT INTO performance_settings (id, streak_rule) VALUES (1, ?)",
            (json.dumps(_DEFAULT_RULE),),
        )
        conn.commit()
    return conn.execute("SELECT * FROM performance_settings WHERE id = 1").fetchone()


def _eval_condition(conn, cond: dict, day: str) -> bool:
    t, op, val = cond["type"], cond["op"], cond["value"]
    if t == "tasks_done":
        count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done' AND date(updated)=?", (day,)
        ).fetchone()[0]
    elif t == "eda_done":
        count = conn.execute(
            "SELECT COUNT(*) FROM eda_requests WHERE status='done' AND date(updated)=?", (day,)
        ).fetchone()[0]
    elif t == "kpi_logged":
        count = conn.execute(
            "SELECT COUNT(*) FROM kpi_entries WHERE date=?", (day,)
        ).fetchone()[0]
    elif t == "wip_updated":
        count = conn.execute(
            "SELECT COUNT(*) FROM wip_items WHERE date(updated)=?", (day,)
        ).fetchone()[0]
    else:
        return False
    return (count >= val) if op == "gte" else (count == val)


def _day_status(conn, rule: dict, day: str) -> str:
    conds = rule["conditions"]
    results = [_eval_condition(conn, c, day) for c in conds]
    if all(results):
        return "hit"
    if rule["logic"] == "AND" and any(results):
        return "partial"
    return "miss"


@router.get("/settings")
def get_settings(conn=None):
    conn = get_connection()
    row = _ensure_settings(conn)
    rule = json.loads(row["streak_rule"])
    conn.close()
    return {"streak_rule": rule}


@router.post("/settings")
def save_settings(body: StreakRule):
    conn = get_connection()
    _ensure_settings(conn)
    conn.execute(
        "UPDATE performance_settings SET streak_rule=? WHERE id=1",
        (json.dumps(body.streak_rule),),
    )
    conn.commit()
    conn.close()
    return {"streak_rule": body.streak_rule}


@router.get("/summary", response_model=PerformanceSummary)
def get_summary():
    conn = get_connection()
    row = _ensure_settings(conn)
    rule = json.loads(row["streak_rule"])

    today = date.today()
    first_of_month = today.replace(day=1).isoformat()

    # Output metrics
    tasks_done = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='done' AND updated >= ?", (first_of_month,)
    ).fetchone()[0]
    eda_done = conn.execute(
        "SELECT COUNT(*) FROM eda_requests WHERE status='done' AND updated >= ?", (first_of_month,)
    ).fetchone()[0]
    kpi_logs = conn.execute(
        "SELECT COUNT(*) FROM kpi_entries WHERE created >= ?", (first_of_month,)
    ).fetchone()[0]
    wip_avg = conn.execute("SELECT AVG(progress) FROM wip_items").fetchone()[0] or 0.0

    # 30-day calendar
    calendar: list[DayStatus] = []
    for i in range(29, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        status = _day_status(conn, rule, day)
        calendar.append(DayStatus(date=day, status=status))

    # Streak = consecutive "hit" days ending today
    streak = 0
    for day_status in reversed(calendar):
        if day_status.status == "hit":
            streak += 1
        else:
            break

    conn.close()
    return PerformanceSummary(
        streak=streak,
        tasks_done=tasks_done,
        eda_done=eda_done,
        kpi_logs=kpi_logs,
        wip_avg_progress=round(wip_avg, 1),
        calendar=calendar,
    )
```

- [ ] **Register router in main.py**

```python
# Add import:
from routers.performance import router as performance_router
# Add include:
app.include_router(performance_router)
```

- [ ] **Run tests — expect pass**

```bash
cd backend && uv run pytest tests/test_performance.py -v
```
Expected: all 5 tests PASS.

- [ ] **Commit**

```bash
git add backend/routers/performance.py backend/tests/test_performance.py backend/main.py
git commit -m "feat(performance): /performance/summary + /settings with custom streak rule"
```

---

## Task 4: ML backend — upload + query

**Files:**
- Create: `backend/routers/ml.py`
- Create: `backend/tests/test_ml.py` (partial)
- Modify: `backend/main.py`

- [ ] **Write failing tests for upload + query**

Create `backend/tests/test_ml.py`:
```python
import io
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

CSV_CONTENT = b"name,value,date\nAlice,100,2026-01-01\nBob,200,2026-01-02\nCarol,150,2026-01-03\n"

def test_upload_csv(client, tmp_path):
    resp = client.post(
        "/ml/upload",
        files={"file": ("test.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    )
    assert resp.status_code == 201
    d = resp.json()
    assert d["filename"] == "test.csv"
    assert d["rows"] == 3
    assert d["cols"] == 3
    assert len(d["columns"]) == 3
    assert d["file_id"]

def test_query_basic(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("q.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    resp = client.post("/ml/query", json={
        "file_id": upload["file_id"],
        "sql": "SELECT name, value FROM data ORDER BY value DESC",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["columns"] == ["name", "value"]
    assert d["rows"][0] == ["Bob", 200]
    assert "duration_ms" in d

def test_query_invalid_sql(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("e.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    resp = client.post("/ml/query", json={
        "file_id": upload["file_id"],
        "sql": "SELECT * FROM nonexistent_table",
    })
    assert resp.status_code == 400

def test_query_unknown_file(client):
    resp = client.post("/ml/query", json={"file_id": "bad-id", "sql": "SELECT 1"})
    assert resp.status_code == 404

def test_list_datasets(client):
    client.post("/ml/upload", files={"file": ("a.csv", io.BytesIO(CSV_CONTENT), "text/csv")})
    resp = client.get("/ml/datasets")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

def test_delete_dataset(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("del.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    assert client.delete(f"/ml/{upload['file_id']}").status_code == 204
    datasets = client.get("/ml/datasets").json()
    ids = [d["file_id"] for d in datasets]
    assert upload["file_id"] not in ids
```

- [ ] **Run — expect failures**

```bash
cd backend && uv run pytest tests/test_ml.py -v
```
Expected: FAIL — router not registered.

- [ ] **Create ML router (upload + query section)**

Create `backend/routers/ml.py`:
```python
import time
import shutil
import pathlib
import duckdb
import polars as pl
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from database import get_connection, UPLOADS_DIR

router = APIRouter(prefix="/ml", tags=["ml"])

MAX_FILE_BYTES = 500 * 1024 * 1024  # 500 MB


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


def _load_df(filepath: str) -> pl.DataFrame:
    p = pathlib.Path(filepath)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pl.read_excel(p)
    return pl.read_csv(p, infer_schema_length=10000)


def _get_file_row(conn, file_id: str):
    row = conn.execute(
        "SELECT * FROM uploaded_files WHERE file_id = ?", (file_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return row


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
            df = _load_df(r["filepath"])
            cols = [ColumnInfo(name=c, dtype=str(df[c].dtype)) for c in df.columns]
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
    conn.execute("DELETE FROM uploaded_files WHERE file_id=?", (file_id,))
    conn.commit()
    conn.close()
```

- [ ] **Register router in main.py**

```python
from routers.ml import router as ml_router
app.include_router(ml_router)
```

- [ ] **Run tests — expect pass**

```bash
cd backend && uv run pytest tests/test_ml.py -v
```
Expected: all 6 tests PASS.

- [ ] **Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py backend/main.py
git commit -m "feat(ml): /ml upload + query via DuckDB + Polars"
```

---

## Task 5: ML backend — stats + forecast

**Files:**
- Modify: `backend/routers/ml.py`
- Modify: `backend/tests/test_ml.py`

- [ ] **Append stats + forecast tests to test_ml.py**

Add to end of `backend/tests/test_ml.py`:
```python
NUMERIC_CSV = b"a,b,date\n1,10,2026-01-01\n2,20,2026-01-02\n3,30,2026-01-03\n4,40,2026-01-04\n5,50,2026-01-05\n"

def test_stats_describe(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("num.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.post("/ml/stats", json={
        "file_id": upload["file_id"], "test": "describe", "col_a": "a"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "mean" in d
    assert d["mean"] == pytest.approx(3.0)

def test_stats_correlation(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("num2.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.post("/ml/stats", json={
        "file_id": upload["file_id"], "test": "correlation",
        "col_a": "a", "col_b": "b"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["r"] == pytest.approx(1.0, abs=0.01)
    assert d["p_value"] < 0.05

def test_forecast(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("ts.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.post("/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "a", "periods": 3
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["forecast"]) == 3
    assert "date" in d["forecast"][0]
    assert "value" in d["forecast"][0]
```

- [ ] **Run — expect failures**

```bash
cd backend && uv run pytest tests/test_ml.py::test_stats_describe tests/test_ml.py::test_stats_correlation tests/test_ml.py::test_forecast -v
```
Expected: FAIL — endpoints not implemented.

- [ ] **Add stats + forecast endpoints to ml.py**

Append to `backend/routers/ml.py` (after existing code):
```python
from datetime import date, timedelta
from scipy import stats as scipy_stats


class StatsIn(BaseModel):
    file_id: str
    test: str   # "describe" | "correlation" | "ttest" | "distribution"
    col_a: str
    col_b: str | None = None


class ForecastIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7


@router.post("/stats")
def run_stats(body: StatsIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    if body.col_a not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{body.col_a}' not found")

    a = df[body.col_a].drop_nulls().to_numpy()

    if body.test == "describe":
        return {
            "count": len(a), "mean": float(a.mean()), "std": float(a.std()),
            "min": float(a.min()), "max": float(a.max()),
            "q25": float(df[body.col_a].quantile(0.25)),
            "q50": float(df[body.col_a].quantile(0.50)),
            "q75": float(df[body.col_a].quantile(0.75)),
        }

    if body.col_b and body.col_b not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{body.col_b}' not found")

    if body.test == "correlation":
        b = df[body.col_b].drop_nulls().to_numpy()
        r, p = scipy_stats.pearsonr(a[:len(b)], b[:len(a)])
        return {"r": round(float(r), 4), "p_value": round(float(p), 6),
                "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant"}

    if body.test == "ttest":
        b = df[body.col_b].drop_nulls().to_numpy()
        t, p = scipy_stats.ttest_ind(a, b)
        return {"t_stat": round(float(t), 4), "p_value": round(float(p), 6),
                "interpretation": "significant (p<0.05)" if p < 0.05 else "not significant"}

    if body.test == "distribution":
        counts, edges = __import__("numpy").histogram(a, bins=20)
        return {
            "bins": [{"x0": float(edges[i]), "x1": float(edges[i+1]), "count": int(counts[i])}
                     for i in range(len(counts))]
        }

    raise HTTPException(status_code=400, detail=f"Unknown test '{body.test}'")


@router.post("/forecast")
def run_forecast(body: ForecastIn):
    import numpy as np
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    for col in (body.date_col, body.value_col):
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' not found")

    df_sorted = df.sort(body.date_col)
    values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
    n = len(values)
    if n < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 data points")

    x = np.arange(n)
    slope, intercept, _, _, _ = scipy_stats.linregress(x, values)

    # Parse last date
    try:
        last_date = date.fromisoformat(str(df_sorted[body.date_col][-1]))
    except Exception:
        last_date = date.today()

    forecast = []
    for i in range(1, body.periods + 1):
        pred = intercept + slope * (n + i - 1)
        ci = float(values.std()) * 1.96
        forecast.append({
            "date": (last_date + timedelta(days=i)).isoformat(),
            "value": round(float(pred), 4),
            "lower": round(float(pred - ci), 4),
            "upper": round(float(pred + ci), 4),
        })

    return {"slope": round(float(slope), 4), "intercept": round(float(intercept), 4), "forecast": forecast}
```

- [ ] **Run all ML tests — expect pass**

```bash
cd backend && uv run pytest tests/test_ml.py -v
```
Expected: all 9 tests PASS.

- [ ] **Run full test suite**

```bash
cd backend && uv run pytest tests/ -v
```
Expected: all tests PASS (55+ existing + 20 new).

- [ ] **Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(ml): stats tests (describe/correlation/ttest/distribution) + linear forecast"
```

---

## Task 6: Frontend setup — recharts + types + API clients

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/kpi.ts`
- Create: `frontend/src/api/performance.ts`
- Create: `frontend/src/api/ml.ts`

- [ ] **Install recharts**

```bash
cd frontend && npm install recharts
```
Expected: `recharts` appears in `package.json` dependencies.

- [ ] **Add new types to types.ts**

Append to end of `frontend/src/types.ts`:
```typescript
// ─── KPI Tracker ─────────────────────────────────────────────────────────────

export type KpiCategory = 'da_output' | 'business'

export interface KpiEntry {
  id: string
  metric: string
  value: number
  date: string
  category: KpiCategory
  note: string | null
  created: string
}

// ─── Performance ─────────────────────────────────────────────────────────────

export interface DayStatus {
  date: string
  status: 'hit' | 'partial' | 'miss'
}

export interface StreakCondition {
  type: 'tasks_done' | 'eda_done' | 'kpi_logged' | 'wip_updated'
  op: 'gte'
  value: number
}

export interface StreakRule {
  conditions: StreakCondition[]
  logic: 'AND' | 'OR'
}

export interface PerformanceSummary {
  streak: number
  tasks_done: number
  eda_done: number
  kpi_logs: number
  wip_avg_progress: number
  calendar: DayStatus[]
}

// ─── ML Studio ───────────────────────────────────────────────────────────────

export interface ColumnInfo {
  name: string
  dtype: string
}

export interface DatasetInfo {
  file_id: string
  filename: string
  rows: number
  cols: number
  columns: ColumnInfo[]
}

export interface QueryResult {
  columns: string[]
  rows: unknown[][]
  duration_ms: number
}

export interface StatsResult {
  [key: string]: number | string
}

export interface ForecastPoint {
  date: string
  value: number
  lower: number
  upper: number
}

export interface ForecastResult {
  slope: number
  intercept: number
  forecast: ForecastPoint[]
}
```

- [ ] **Create api/kpi.ts**

```typescript
import client from './client'
import type { KpiEntry, KpiCategory } from '../types'

export interface KpiPayload {
  metric: string
  value: number
  date: string
  category: KpiCategory
  note?: string | null
}

export async function fetchKpi(params?: {
  metric?: string; category?: KpiCategory; from_date?: string; to_date?: string
}): Promise<KpiEntry[]> {
  const { data } = await client.get<KpiEntry[]>('/kpi', { params })
  return data
}

export async function fetchKpiMetrics(): Promise<string[]> {
  const { data } = await client.get<string[]>('/kpi/metrics')
  return data
}

export async function createKpi(body: KpiPayload): Promise<KpiEntry> {
  const { data } = await client.post<KpiEntry>('/kpi', body)
  return data
}

export async function deleteKpi(id: string): Promise<void> {
  await client.delete(`/kpi/${id}`)
}
```

- [ ] **Create api/performance.ts**

```typescript
import client from './client'
import type { PerformanceSummary, StreakRule } from '../types'

export async function fetchPerformanceSummary(): Promise<PerformanceSummary> {
  const { data } = await client.get<PerformanceSummary>('/performance/summary')
  return data
}

export async function fetchStreakRule(): Promise<{ streak_rule: StreakRule }> {
  const { data } = await client.get<{ streak_rule: StreakRule }>('/performance/settings')
  return data
}

export async function saveStreakRule(rule: StreakRule): Promise<{ streak_rule: StreakRule }> {
  const { data } = await client.post<{ streak_rule: StreakRule }>('/performance/settings', { streak_rule: rule })
  return data
}
```

- [ ] **Create api/ml.ts**

```typescript
import client from './client'
import type { DatasetInfo, QueryResult, StatsResult, ForecastResult } from '../types'

export async function uploadFile(file: File): Promise<DatasetInfo> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<DatasetInfo>('/ml/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function fetchDatasets(): Promise<DatasetInfo[]> {
  const { data } = await client.get<DatasetInfo[]>('/ml/datasets')
  return data
}

export async function deleteDataset(file_id: string): Promise<void> {
  await client.delete(`/ml/${file_id}`)
}

export async function runQuery(file_id: string, sql: string): Promise<QueryResult> {
  const { data } = await client.post<QueryResult>('/ml/query', { file_id, sql })
  return data
}

export async function runStats(
  file_id: string, test: string, col_a: string, col_b?: string
): Promise<StatsResult> {
  const { data } = await client.post<StatsResult>('/ml/stats', { file_id, test, col_a, col_b })
  return data
}

export async function runForecast(
  file_id: string, date_col: string, value_col: string, periods: number
): Promise<ForecastResult> {
  const { data } = await client.post<ForecastResult>('/ml/forecast', {
    file_id, date_col, value_col, periods,
  })
  return data
}
```

- [ ] **Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/types.ts frontend/src/api/kpi.ts frontend/src/api/performance.ts frontend/src/api/ml.ts
git commit -m "feat(frontend): recharts + types + API clients for KPI/Performance/ML"
```

---

## Task 7: KPI Tracker frontend

**Files:**
- Create: `frontend/src/components/kpi/KpiList.tsx`
- Create: `frontend/src/components/kpi/KpiItem.tsx`
- Create: `frontend/src/components/kpi/KpiForm.tsx`
- Create: `frontend/src/components/kpi/KpiChart.tsx`
- Modify: `frontend/src/pages/analytics/KpiTracker.tsx`

- [ ] **Create KpiItem.tsx**

```tsx
import { Trash2 } from 'lucide-react'
import type { KpiEntry } from '../../types'

interface Props {
  entry: KpiEntry
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
}

const catColor: Record<string, string> = {
  da_output: 'bg-work/10 text-work border-work/25',
  business:  'bg-data/10 text-data border-data/25',
}
const catLabel: Record<string, string> = { da_output: 'DA', business: 'BIZ' }

export default function KpiItem({ entry, isSelected, onSelect, onDelete }: Props) {
  return (
    <div
      onClick={onSelect}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer border mb-0.5 transition-all group
        ${isSelected ? 'bg-analytics/5 border-analytics/30' : 'border-transparent hover:bg-white/5 hover:border-white/5'}`}
    >
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-200 truncate">{entry.metric}</p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className={`badge border text-[9px] ${catColor[entry.category]}`}>
            {catLabel[entry.category]}
          </span>
          <span className="text-[10px] text-gray-600">{entry.date}</span>
        </div>
      </div>
      <span className="text-sm font-semibold text-analytics tabular-nums flex-shrink-0">
        {entry.value.toLocaleString('vi-VN')}
      </span>
      <button
        onClick={e => { e.stopPropagation(); onDelete() }}
        className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-danger transition-opacity flex-shrink-0"
      >
        <Trash2 size={12} />
      </button>
    </div>
  )
}
```

- [ ] **Create KpiList.tsx**

```tsx
import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { KpiEntry, KpiCategory } from '../../types'
import KpiItem from './KpiItem'

type FilterTab = 'all' | KpiCategory

interface Props {
  entries: KpiEntry[]
  selectedId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNew: () => void
}

export default function KpiList({ entries, selectedId, onSelect, onDelete, onNew }: Props) {
  const [filter, setFilter] = useState<FilterTab>('all')

  const visible = filter === 'all' ? entries : entries.filter(e => e.category === filter)

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all',       label: 'All' },
    { key: 'da_output', label: 'DA Output' },
    { key: 'business',  label: 'Business' },
  ]

  return (
    <div className="w-[300px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">KPI Entries</h2>
          <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> Log
          </button>
        </div>
        <div className="flex gap-1">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                filter === key
                  ? 'bg-analytics/10 text-analytics border border-analytics/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
        {visible.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No entries</p>
        ) : (
          visible.map(e => (
            <KpiItem
              key={e.id}
              entry={e}
              isSelected={e.id === selectedId}
              onSelect={() => onSelect(e.id)}
              onDelete={() => onDelete(e.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Create KpiForm.tsx**

```tsx
import { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import type { KpiCategory } from '../../types'
import { fetchKpiMetrics, createKpi } from '../../api/kpi'
import type { KpiEntry } from '../../types'

interface Props {
  onCreated: (entry: KpiEntry) => void
  onCancel: () => void
}

export default function KpiForm({ onCreated, onCancel }: Props) {
  const [metric,   setMetric]   = useState('')
  const [value,    setValue]    = useState('')
  const [date,     setDate]     = useState(new Date().toISOString().slice(0, 10))
  const [category, setCategory] = useState<KpiCategory>('da_output')
  const [note,     setNote]     = useState('')
  const [metrics,  setMetrics]  = useState<string[]>([])
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)

  useEffect(() => {
    fetchKpiMetrics().then(setMetrics).catch(() => {})
  }, [])

  async function handleSubmit() {
    if (!metric.trim()) { setError('Metric name required'); return }
    if (!value || isNaN(Number(value))) { setError('Valid number required'); return }
    setError(''); setSaving(true)
    try {
      const entry = await createKpi({
        metric: metric.trim(), value: Number(value),
        date, category, note: note || null,
      })
      onCreated(entry)
    } catch { setError('Failed to save — check connection') }
    finally { setSaving(false) }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">＋ Log KPI</h2>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Metric *</label>
        <input
          className="input-base" list="metrics-list"
          placeholder="Queries viết, GMV ColosBaby..."
          value={metric} onChange={e => setMetric(e.target.value)}
          autoFocus
        />
        <datalist id="metrics-list">
          {metrics.map(m => <option key={m} value={m} />)}
        </datalist>
      </div>

      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Value *</label>
          <input className="input-base" type="number" placeholder="0" value={value} onChange={e => setValue(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Date</label>
          <input className="input-base" type="date" value={date} onChange={e => setDate(e.target.value)} />
        </div>
      </div>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Category</label>
        <select className="input-base" value={category} onChange={e => setCategory(e.target.value as KpiCategory)}>
          <option value="da_output">DA Output</option>
          <option value="business">Business</option>
        </select>
      </div>

      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Note</label>
        <input className="input-base" placeholder="Optional..." value={note} onChange={e => setNote(e.target.value)} />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button onClick={handleSubmit} disabled={saving} className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Check size={13} /> {saving ? 'Saving...' : 'Save Entry'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
```

- [ ] **Create KpiChart.tsx**

```tsx
import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { KpiEntry } from '../../types'

interface Props {
  entries: KpiEntry[]
}

type Range = '7d' | '30d' | '90d' | 'all'

function filterByRange(entries: KpiEntry[], range: Range): KpiEntry[] {
  if (range === 'all') return entries
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const cutoffStr = cutoff.toISOString().slice(0, 10)
  return entries.filter(e => e.date >= cutoffStr)
}

export default function KpiChart({ entries }: Props) {
  const metrics = [...new Set(entries.map(e => e.metric))]
  const [metric, setMetric] = useState(metrics[0] ?? '')
  const [range,  setRange]  = useState<Range>('30d')

  const metricEntries = filterByRange(
    entries.filter(e => e.metric === metric).sort((a, b) => a.date.localeCompare(b.date)),
    range,
  )

  const chartData = metricEntries.map(e => ({ date: e.date.slice(5), value: e.value }))
  const avg = metricEntries.length
    ? metricEntries.reduce((s, e) => s + e.value, 0) / metricEntries.length
    : 0
  const prev = entries.filter(e => e.metric === metric && !metricEntries.includes(e))
  const prevAvg = prev.length ? prev.reduce((s, e) => s + e.value, 0) / prev.length : 0
  const delta = prevAvg > 0 ? ((avg - prevAvg) / prevAvg) * 100 : null

  if (entries.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
        Log your first KPI entry to see the chart
      </div>
    )
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto flex flex-col gap-4">
      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          className="input-base text-xs flex-1 min-w-0"
          value={metric} onChange={e => setMetric(e.target.value)}
        >
          {metrics.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <div className="flex gap-1">
          {(['7d','30d','90d','all'] as Range[]).map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                range === r
                  ? 'bg-analytics/10 text-analytics border border-analytics/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="bg-secondary border border-white/5 rounded-lg p-4 flex-1 min-h-[200px]">
        {chartData.length < 2 ? (
          <p className="text-gray-600 text-xs text-center mt-8">Not enough data for this range</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={40} />
              <Tooltip
                contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: '#e5e7eb' }}
              />
              <ReferenceLine y={avg} stroke="#fbbf24" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="value" stroke="#fbbf24" strokeWidth={2} dot={{ r: 3, fill: '#fbbf24' }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Avg / entry', value: avg.toLocaleString('vi-VN', { maximumFractionDigits: 1 }) },
          { label: 'vs prev period', value: delta != null ? `${delta > 0 ? '+' : ''}${delta.toFixed(1)}%` : '—' },
          { label: 'Entries', value: metricEntries.length },
        ].map(({ label, value }) => (
          <div key={label} className="bg-secondary border border-white/5 rounded-lg p-3 text-center">
            <p className="text-analytics text-base font-bold">{value}</p>
            <p className="text-gray-600 text-[10px] mt-0.5">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Replace KpiTracker.tsx page**

```tsx
import { useEffect, useState, useCallback } from 'react'
import type { KpiEntry } from '../../types'
import { fetchKpi, deleteKpi } from '../../api/kpi'
import KpiList  from '../../components/kpi/KpiList'
import KpiForm  from '../../components/kpi/KpiForm'
import KpiChart from '../../components/kpi/KpiChart'

type Panel = 'chart' | 'form'

export default function KpiTracker() {
  const [entries,    setEntries]    = useState<KpiEntry[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [panel,      setPanel]      = useState<Panel>('chart')
  const [apiError,   setApiError]   = useState('')

  const load = useCallback(async () => {
    try { setEntries(await fetchKpi()); setApiError('') }
    catch { setApiError('Cannot reach API — is the backend running?') }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    try {
      await deleteKpi(id)
      setEntries(es => es.filter(e => e.id !== id))
      if (selectedId === id) setSelectedId(null)
    } catch { setApiError('Failed to delete — check connection') }
  }

  function handleCreated(entry: KpiEntry) {
    setEntries(es => [entry, ...es])
    setSelectedId(entry.id)
    setPanel('chart')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <KpiList
        entries={entries}
        selectedId={selectedId}
        onSelect={id => { setSelectedId(id); setPanel('chart') }}
        onDelete={handleDelete}
        onNew={() => setPanel('form')}
      />
      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg z-10">
            {apiError}
          </div>
        )}
        {panel === 'form' ? (
          <KpiForm onCreated={handleCreated} onCancel={() => setPanel('chart')} />
        ) : (
          <KpiChart entries={entries} />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Check TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Commit**

```bash
git add frontend/src/components/kpi/ frontend/src/pages/analytics/KpiTracker.tsx
git commit -m "feat(kpi): KPI Tracker page — list, log form, line chart, stats"
```

---

## Task 8: Performance frontend

**Files:**
- Create: `frontend/src/components/performance/StreakCard.tsx`
- Create: `frontend/src/components/performance/RuleEditor.tsx`
- Create: `frontend/src/components/performance/OutputGrid.tsx`
- Create: `frontend/src/components/performance/CalendarHeatmap.tsx`
- Modify: `frontend/src/pages/analytics/Performance.tsx`

- [ ] **Create StreakCard.tsx**

```tsx
import { useState } from 'react'
import { Flame, Settings } from 'lucide-react'
import type { StreakRule } from '../../types'

interface Props {
  streak: number
  rule: StreakRule
  onEditRule: () => void
}

function ruleText(rule: StreakRule): string {
  const parts = rule.conditions.map(c => {
    const labels: Record<string, string> = {
      tasks_done: 'tasks done', eda_done: 'EDA done',
      kpi_logged: 'KPI logged', wip_updated: 'WIP updated',
    }
    return `≥${c.value} ${labels[c.type] ?? c.type}`
  })
  return parts.join(` ${rule.logic} `)
}

export default function StreakCard({ streak, rule, onEditRule }: Props) {
  return (
    <div className="w-[200px] flex-shrink-0 bg-secondary border border-white/5 rounded-xl p-5 flex flex-col items-center justify-center gap-3">
      <Flame size={36} className="text-warning" />
      <div className="text-center">
        <p className="text-warning text-4xl font-extrabold leading-none">{streak}</p>
        <p className="text-gray-500 text-xs mt-1">day streak</p>
      </div>
      <div className="text-center">
        <p className="text-[10px] text-gray-600 leading-relaxed">{ruleText(rule)}</p>
      </div>
      <button
        onClick={onEditRule}
        className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1"
      >
        <Settings size={11} /> Edit Rule
      </button>
    </div>
  )
}
```

- [ ] **Create RuleEditor.tsx**

```tsx
import { useState } from 'react'
import { Plus, Trash2, Check, X } from 'lucide-react'
import type { StreakRule, StreakCondition } from '../../types'

interface Props {
  rule: StreakRule
  onSave: (rule: StreakRule) => void
  onCancel: () => void
}

const CONDITION_TYPES: { value: StreakCondition['type']; label: string }[] = [
  { value: 'tasks_done',  label: 'Tasks done' },
  { value: 'eda_done',    label: 'EDA done' },
  { value: 'kpi_logged',  label: 'KPI logged' },
  { value: 'wip_updated', label: 'WIP updated' },
]

export default function RuleEditor({ rule, onSave, onCancel }: Props) {
  const [conditions, setConditions] = useState<StreakCondition[]>(rule.conditions)
  const [logic, setLogic] = useState<'AND' | 'OR'>(rule.logic)

  function addCondition() {
    setConditions(cs => [...cs, { type: 'tasks_done', op: 'gte', value: 1 }])
  }

  function removeCondition(i: number) {
    setConditions(cs => cs.filter((_, j) => j !== i))
  }

  function updateCondition(i: number, patch: Partial<StreakCondition>) {
    setConditions(cs => cs.map((c, j) => j === i ? { ...c, ...patch } : c))
  }

  return (
    <div className="bg-secondary border border-white/8 rounded-xl p-4 w-full max-w-sm">
      <h3 className="text-sm font-semibold text-white mb-3">Edit Streak Rule</h3>

      <div className="space-y-2 mb-3">
        {conditions.map((c, i) => (
          <div key={i} className="flex items-center gap-2">
            <select
              className="input-base text-xs flex-1"
              value={c.type}
              onChange={e => updateCondition(i, { type: e.target.value as StreakCondition['type'] })}
            >
              {CONDITION_TYPES.map(ct => <option key={ct.value} value={ct.value}>{ct.label}</option>)}
            </select>
            <span className="text-gray-600 text-xs">≥</span>
            <input
              type="number" min={1} className="input-base text-xs w-14"
              value={c.value}
              onChange={e => updateCondition(i, { value: Number(e.target.value) })}
            />
            <button onClick={() => removeCondition(i)} className="text-gray-600 hover:text-danger">
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>

      {conditions.length > 1 && (
        <div className="flex gap-2 mb-3">
          <span className="text-gray-600 text-xs">Combine with:</span>
          {(['AND', 'OR'] as const).map(l => (
            <button
              key={l}
              onClick={() => setLogic(l)}
              className={`text-xs px-2 py-0.5 rounded border transition-all ${
                logic === l ? 'bg-analytics/10 text-analytics border-analytics/30' : 'text-gray-500 border-white/10'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      )}

      <button
        onClick={addCondition}
        className="btn-ghost w-full text-xs flex items-center justify-center gap-1 mb-3"
      >
        <Plus size={11} /> Add condition
      </button>

      <div className="flex gap-2">
        <button
          onClick={() => onSave({ conditions, logic })}
          disabled={conditions.length === 0}
          className="btn-primary flex-1 flex items-center justify-center gap-1 text-xs disabled:opacity-50"
        >
          <Check size={12} /> Save
        </button>
        <button onClick={onCancel} className="btn-ghost flex-1 flex items-center justify-center gap-1 text-xs">
          <X size={12} /> Cancel
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Create OutputGrid.tsx**

```tsx
import type { PerformanceSummary } from '../../types'

interface Props {
  summary: PerformanceSummary
}

export default function OutputGrid({ summary }: Props) {
  const items = [
    { label: 'Tasks done',    value: summary.tasks_done,        color: 'text-work',      note: 'this month' },
    { label: 'EDA completed', value: summary.eda_done,          color: 'text-data',      note: 'this month' },
    { label: 'KPI logs',      value: summary.kpi_logs,          color: 'text-learn',     note: 'entries logged' },
    { label: 'WIP avg',       value: `${summary.wip_avg_progress}%`, color: 'text-analytics', note: 'progress' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map(({ label, value, color, note }) => (
        <div key={label} className="bg-secondary border border-white/5 rounded-lg p-4">
          <p className="text-gray-600 text-[10px] uppercase tracking-widest mb-1">{label}</p>
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
          <p className="text-gray-600 text-[10px] mt-0.5">{note}</p>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Create CalendarHeatmap.tsx**

```tsx
import type { DayStatus } from '../../types'

interface Props {
  calendar: DayStatus[]
}

const statusColor: Record<string, string> = {
  hit:     'bg-work opacity-90',
  partial: 'bg-warning opacity-80',
  miss:    'bg-white/5',
}

export default function CalendarHeatmap({ calendar }: Props) {
  return (
    <div className="bg-secondary border border-white/5 rounded-lg p-4">
      <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-3">Last 30 days</p>
      <div className="flex flex-wrap gap-1.5">
        {calendar.map(({ date, status }) => (
          <div
            key={date}
            title={`${date}: ${status}`}
            className={`w-5 h-5 rounded-sm cursor-default ${statusColor[status]}`}
          />
        ))}
      </div>
      <div className="flex gap-4 mt-3">
        {[
          { color: 'bg-work',    label: 'Hit' },
          { color: 'bg-warning', label: 'Partial' },
          { color: 'bg-white/5', label: 'Miss' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded-sm ${color}`} />
            <span className="text-[10px] text-gray-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Replace Performance.tsx page**

```tsx
import { useEffect, useState, useCallback } from 'react'
import type { PerformanceSummary, StreakRule } from '../../types'
import { fetchPerformanceSummary, fetchStreakRule, saveStreakRule } from '../../api/performance'
import StreakCard      from '../../components/performance/StreakCard'
import RuleEditor      from '../../components/performance/RuleEditor'
import OutputGrid      from '../../components/performance/OutputGrid'
import CalendarHeatmap from '../../components/performance/CalendarHeatmap'

export default function Performance() {
  const [summary,    setSummary]    = useState<PerformanceSummary | null>(null)
  const [rule,       setRule]       = useState<StreakRule | null>(null)
  const [editingRule, setEditingRule] = useState(false)
  const [apiError,   setApiError]   = useState('')

  const load = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([fetchPerformanceSummary(), fetchStreakRule()])
      setSummary(s)
      setRule(r.streak_rule)
      setApiError('')
    } catch { setApiError('Cannot reach API — is the backend running?') }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleSaveRule(newRule: StreakRule) {
    try {
      await saveStreakRule(newRule)
      setRule(newRule)
      setEditingRule(false)
      await load()
    } catch { setApiError('Failed to save rule') }
  }

  if (!summary || !rule) {
    return (
      <div className="flex-1 flex items-center justify-center">
        {apiError
          ? <p className="text-danger text-sm">{apiError}</p>
          : <div className="w-6 h-6 border-2 border-analytics/30 border-t-analytics rounded-full animate-spin" />}
      </div>
    )
  }

  return (
    <div className="p-5 max-w-2xl">
      <h1 className="text-base font-semibold text-white mb-5">Performance</h1>

      {apiError && (
        <div className="bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg mb-4">
          {apiError}
        </div>
      )}

      <div className="flex gap-4 mb-5 items-start">
        <StreakCard streak={summary.streak} rule={rule} onEditRule={() => setEditingRule(v => !v)} />
        <div className="flex-1 flex flex-col gap-3">
          {editingRule && (
            <RuleEditor rule={rule} onSave={handleSaveRule} onCancel={() => setEditingRule(false)} />
          )}
          {!editingRule && <OutputGrid summary={summary} />}
        </div>
      </div>

      <CalendarHeatmap calendar={summary.calendar} />
    </div>
  )
}
```

- [ ] **Check TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Commit**

```bash
git add frontend/src/components/performance/ frontend/src/pages/analytics/Performance.tsx
git commit -m "feat(performance): Performance page — streak, rule editor, output grid, heatmap"
```

---

## Task 9: ML Studio frontend

**Files:**
- Create: `frontend/src/components/ml/MlUpload.tsx`
- Create: `frontend/src/components/ml/MlSqlEditor.tsx`
- Create: `frontend/src/components/ml/MlResultTabs.tsx`
- Create: `frontend/src/components/ml/MlChartView.tsx`
- Create: `frontend/src/components/ml/MlTableView.tsx`
- Create: `frontend/src/components/ml/MlStatsView.tsx`
- Create: `frontend/src/components/ml/MlForecastView.tsx`
- Modify: `frontend/src/pages/analytics/MlStudio.tsx`

- [ ] **Create MlUpload.tsx**

```tsx
import { useRef } from 'react'
import { Upload, Trash2 } from 'lucide-react'
import type { DatasetInfo } from '../../types'

interface Props {
  dataset: DatasetInfo | null
  uploading: boolean
  onUpload: (file: File) => void
  onClear: () => void
}

export default function MlUpload({ dataset, uploading, onUpload, onClear }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) onUpload(file)
  }

  return (
    <div className="flex flex-col gap-3">
      {!dataset ? (
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => inputRef.current?.click()}
          className="border border-dashed border-data/30 rounded-lg p-5 text-center cursor-pointer hover:border-data/50 hover:bg-data/3 transition-all"
        >
          <input
            ref={inputRef} type="file" accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) onUpload(f) }}
          />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-5 h-5 border-2 border-data/30 border-t-data rounded-full animate-spin" />
              <p className="text-data text-xs">Reading with Polars...</p>
            </div>
          ) : (
            <>
              <Upload size={22} className="text-data mx-auto mb-2 opacity-60" />
              <p className="text-gray-400 text-xs">Drop CSV / Excel</p>
              <p className="text-gray-600 text-[10px] mt-1">Polars · max 500 MB</p>
            </>
          )}
        </div>
      ) : (
        <div className="bg-secondary border border-white/5 rounded-lg p-3">
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="text-white text-xs font-semibold truncate">{dataset.filename}</p>
            <button onClick={onClear} className="text-gray-600 hover:text-danger flex-shrink-0">
              <Trash2 size={12} />
            </button>
          </div>
          <p className="text-gray-600 text-[10px] mb-2">
            {dataset.rows.toLocaleString()} rows · {dataset.cols} cols
          </p>
          <div className="flex flex-wrap gap-1 max-h-16 overflow-hidden">
            {dataset.columns.slice(0, 8).map(c => (
              <span key={c.name} className="bg-data/10 text-data text-[9px] px-1.5 py-0.5 rounded">
                {c.name}
              </span>
            ))}
            {dataset.columns.length > 8 && (
              <span className="text-gray-600 text-[9px]">+{dataset.columns.length - 8} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Create MlSqlEditor.tsx**

```tsx
import { useState } from 'react'
import { Play } from 'lucide-react'

interface Props {
  disabled: boolean
  running: boolean
  error: string
  onRun: (sql: string) => void
}

const DEFAULT_SQL = 'SELECT *\nFROM data\nLIMIT 100'

export default function MlSqlEditor({ disabled, running, error, onRun }: Props) {
  const [sql, setSql] = useState(DEFAULT_SQL)

  return (
    <div className="flex flex-col gap-2">
      <label className="text-[10px] uppercase tracking-widest text-gray-600">SQL Query</label>
      <textarea
        className="input-base font-mono text-xs resize-none leading-relaxed"
        rows={6}
        value={sql}
        onChange={e => setSql(e.target.value)}
        placeholder="SELECT * FROM data LIMIT 100"
        disabled={disabled}
        spellCheck={false}
      />
      {error && <p className="text-danger text-[10px] leading-snug">{error}</p>}
      <button
        onClick={() => onRun(sql)}
        disabled={disabled || running}
        className="btn-primary flex items-center justify-center gap-1.5 text-xs disabled:opacity-40"
      >
        <Play size={12} /> {running ? 'Running...' : 'Run Query'}
      </button>
    </div>
  )
}
```

- [ ] **Create MlChartView.tsx**

```tsx
import { useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { QueryResult } from '../../types'

interface Props { result: QueryResult }

type ChartType = 'bar' | 'line' | 'scatter'

export default function MlChartView({ result }: Props) {
  const [xCol, setXCol] = useState(result.columns[0] ?? '')
  const [yCol, setYCol] = useState(result.columns[1] ?? result.columns[0] ?? '')
  const [type, setType] = useState<ChartType>('bar')

  const data = result.rows.slice(0, 500).map(row => ({
    x: row[result.columns.indexOf(xCol)],
    y: Number(row[result.columns.indexOf(yCol)]) || 0,
  }))

  return (
    <div className="flex flex-col gap-3 p-4">
      {/* Controls */}
      <div className="flex gap-2 flex-wrap items-end">
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">X axis</label>
          <select className="input-base text-xs" value={xCol} onChange={e => setXCol(e.target.value)}>
            {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Y axis</label>
          <select className="input-base text-xs" value={yCol} onChange={e => setYCol(e.target.value)}>
            {result.columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="flex gap-1 pb-0.5">
          {(['bar','line','scatter'] as ChartType[]).map(t => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={`px-2 py-1 rounded text-[11px] border transition-all ${
                type === t ? 'bg-data/10 text-data border-data/30' : 'text-gray-500 border-transparent hover:text-gray-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="bg-secondary border border-white/5 rounded-lg p-3" style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === 'bar' ? (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={40} />
              <Tooltip contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }} />
              <Bar dataKey="y" fill="#60a5fa" radius={[3,3,0,0]} />
            </BarChart>
          ) : type === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={40} />
              <Tooltip contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }} />
              <Line type="monotone" dataKey="y" stroke="#60a5fa" strokeWidth={2} dot={false} />
            </LineChart>
          ) : (
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="x" name={xCol} tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis dataKey="y" name={yCol} tick={{ fill: '#6b7280', fontSize: 10 }} width={40} />
              <Tooltip contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }} cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={data} fill="#60a5fa" fillOpacity={0.7} />
            </ScatterChart>
          )}
        </ResponsiveContainer>
      </div>
      <p className="text-gray-600 text-[10px]">
        {result.rows.length} rows · {result.duration_ms.toFixed(1)}ms · DuckDB
      </p>
    </div>
  )
}
```

- [ ] **Create MlTableView.tsx**

```tsx
import type { QueryResult } from '../../types'

interface Props { result: QueryResult }

export default function MlTableView({ result }: Props) {
  const display = result.rows.slice(0, 500)

  return (
    <div className="p-4 overflow-auto h-full">
      <p className="text-gray-600 text-[10px] mb-2">
        {result.rows.length} rows · {result.duration_ms.toFixed(1)}ms
        {result.rows.length > 500 && ' · showing first 500'}
      </p>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {result.columns.map(c => (
              <th key={c} className="text-left text-[10px] text-gray-500 uppercase tracking-wider px-3 py-1.5 border-b border-white/5 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {display.map((row, i) => (
            <tr key={i} className="hover:bg-white/3 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-1.5 text-gray-300 border-b border-white/3 whitespace-nowrap max-w-[200px] truncate">
                  {cell == null ? <span className="text-gray-600 italic">null</span> : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Create MlStatsView.tsx**

```tsx
import { useState } from 'react'
import { FlaskConical } from 'lucide-react'
import type { DatasetInfo, StatsResult } from '../../types'
import { runStats } from '../../api/ml'

interface Props {
  dataset: DatasetInfo
}

type TestType = 'describe' | 'correlation' | 'ttest' | 'distribution'

const TESTS: { value: TestType; label: string; needsColB: boolean }[] = [
  { value: 'describe',     label: 'Describe',     needsColB: false },
  { value: 'correlation',  label: 'Correlation',  needsColB: true  },
  { value: 'ttest',        label: 'T-Test',       needsColB: true  },
  { value: 'distribution', label: 'Distribution', needsColB: false },
]

export default function MlStatsView({ dataset }: Props) {
  const cols = dataset.columns.map(c => c.name)
  const [test,   setTest]   = useState<TestType>('describe')
  const [colA,   setColA]   = useState(cols[0] ?? '')
  const [colB,   setColB]   = useState(cols[1] ?? '')
  const [result, setResult] = useState<StatsResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error,  setError]  = useState('')

  const needsColB = TESTS.find(t => t.value === test)?.needsColB ?? false

  async function handleRun() {
    setRunning(true); setError(''); setResult(null)
    try {
      const r = await runStats(dataset.file_id, test, colA, needsColB ? colB : undefined)
      setResult(r)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Stats failed')
    } finally { setRunning(false) }
  }

  return (
    <div className="p-4 flex flex-col gap-4">
      {/* Controls */}
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Test</label>
          <select className="input-base text-xs" value={test} onChange={e => setTest(e.target.value as TestType)}>
            {TESTS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Column A</label>
          <select className="input-base text-xs" value={colA} onChange={e => setColA(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        {needsColB && (
          <div>
            <label className="block text-[10px] text-gray-600 mb-1">Column B</label>
            <select className="input-base text-xs" value={colB} onChange={e => setColB(e.target.value)}>
              {cols.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}
        <button
          onClick={handleRun}
          disabled={running}
          className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"
        >
          <FlaskConical size={12} /> {running ? 'Running...' : 'Run'}
        </button>
      </div>

      {error && <p className="text-danger text-xs">{error}</p>}

      {result && (
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
    </div>
  )
}
```

- [ ] **Create MlForecastView.tsx**

```tsx
import { useState } from 'react'
import { TrendingUp } from 'lucide-react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { DatasetInfo, ForecastResult } from '../../types'
import { runForecast } from '../../api/ml'

interface Props { dataset: DatasetInfo }

export default function MlForecastView({ dataset }: Props) {
  const cols = dataset.columns.map(c => c.name)
  const [dateCol,  setDateCol]  = useState(cols[0] ?? '')
  const [valueCol, setValueCol] = useState(cols[1] ?? '')
  const [periods,  setPeriods]  = useState(7)
  const [result,   setResult]   = useState<ForecastResult | null>(null)
  const [running,  setRunning]  = useState(false)
  const [error,    setError]    = useState('')

  async function handleRun() {
    setRunning(true); setError(''); setResult(null)
    try {
      setResult(await runForecast(dataset.file_id, dateCol, valueCol, periods))
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Forecast failed')
    } finally { setRunning(false) }
  }

  const chartData = result?.forecast.map(f => ({
    date: f.date.slice(5),
    value: f.value,
    lower: f.lower,
    upper: f.upper,
    range: [f.lower, f.upper] as [number, number],
  })) ?? []

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex gap-3 flex-wrap items-end">
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Date column</label>
          <select className="input-base text-xs" value={dateCol} onChange={e => setDateCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Value column</label>
          <select className="input-base text-xs" value={valueCol} onChange={e => setValueCol(e.target.value)}>
            {cols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-gray-600 mb-1">Periods</label>
          <input
            type="number" min={1} max={90} className="input-base text-xs w-16"
            value={periods} onChange={e => setPeriods(Number(e.target.value))}
          />
        </div>
        <button
          onClick={handleRun} disabled={running}
          className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"
        >
          <TrendingUp size={12} /> {running ? 'Running...' : 'Forecast'}
        </button>
      </div>

      {error && <p className="text-danger text-xs">{error}</p>}

      {result && (
        <>
          <div className="bg-secondary border border-white/5 rounded-lg p-4" style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} width={40} />
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }} />
                <Area type="monotone" dataKey="range" fill="#60a5fa" fillOpacity={0.15} stroke="none" />
                <Line type="monotone" dataKey="value" stroke="#60a5fa" strokeWidth={2} dot={{ r: 3, fill: '#60a5fa' }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="text-gray-600 text-[10px]">
            Linear trend · slope {result.slope > 0 ? '+' : ''}{result.slope} per period · shaded = 95% CI
          </p>
        </>
      )}
    </div>
  )
}
```

- [ ] **Create MlResultTabs.tsx**

```tsx
import { BarChart2, Table, FlaskConical, TrendingUp } from 'lucide-react'
import type { DatasetInfo, QueryResult } from '../../types'
import MlChartView    from './MlChartView'
import MlTableView    from './MlTableView'
import MlStatsView    from './MlStatsView'
import MlForecastView from './MlForecastView'

type Tab = 'charts' | 'table' | 'stats' | 'forecast'

interface Props {
  result: QueryResult | null
  dataset: DatasetInfo | null
  activeTab: Tab
  onTabChange: (t: Tab) => void
}

const TABS: { key: Tab; label: string; Icon: React.ElementType }[] = [
  { key: 'charts',   label: 'Charts',   Icon: BarChart2    },
  { key: 'table',    label: 'Table',    Icon: Table        },
  { key: 'stats',    label: 'Stats',    Icon: FlaskConical },
  { key: 'forecast', label: 'Forecast', Icon: TrendingUp   },
]

export default function MlResultTabs({ result, dataset, activeTab, onTabChange }: Props) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Tab bar */}
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

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'charts' && (
          result
            ? <MlChartView result={result} />
            : <Empty text="Run a query to see charts" />
        )}
        {activeTab === 'table' && (
          result
            ? <MlTableView result={result} />
            : <Empty text="Run a query to see results" />
        )}
        {activeTab === 'stats' && (
          dataset
            ? <MlStatsView dataset={dataset} />
            : <Empty text="Upload a dataset first" />
        )}
        {activeTab === 'forecast' && (
          dataset
            ? <MlForecastView dataset={dataset} />
            : <Empty text="Upload a dataset first" />
        )}
      </div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex-1 flex items-center justify-center h-full text-gray-600 text-sm">
      {text}
    </div>
  )
}
```

- [ ] **Replace MlStudio.tsx page**

```tsx
import { useState, useCallback } from 'react'
import type { DatasetInfo, QueryResult } from '../../types'
import { uploadFile, deleteDataset, runQuery } from '../../api/ml'
import MlUpload     from '../../components/ml/MlUpload'
import MlSqlEditor  from '../../components/ml/MlSqlEditor'
import MlResultTabs from '../../components/ml/MlResultTabs'

type Tab = 'charts' | 'table' | 'stats' | 'forecast'

export default function MlStudio() {
  const [dataset,   setDataset]   = useState<DatasetInfo | null>(null)
  const [result,    setResult]    = useState<QueryResult | null>(null)
  const [uploading, setUploading] = useState(false)
  const [running,   setRunning]   = useState(false)
  const [sqlError,  setSqlError]  = useState('')
  const [apiError,  setApiError]  = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('charts')

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true); setApiError('')
    try {
      setDataset(await uploadFile(file))
      setResult(null)
    } catch { setApiError('Upload failed — check file format or size') }
    finally { setUploading(false) }
  }, [])

  async function handleClear() {
    if (dataset) {
      try { await deleteDataset(dataset.file_id) } catch { /* ignore */ }
    }
    setDataset(null); setResult(null); setSqlError('')
  }

  async function handleRun(sql: string) {
    if (!dataset) return
    setRunning(true); setSqlError(''); setResult(null)
    try {
      setResult(await runQuery(dataset.file_id, sql))
      setActiveTab('charts')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSqlError(detail ?? 'Query failed')
    } finally { setRunning(false) }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left sidebar */}
      <div className="w-[280px] border-r border-white/5 flex flex-col gap-4 p-4 flex-shrink-0 overflow-y-auto">
        <h2 className="text-sm font-semibold text-white">ML Studio</h2>
        {apiError && <p className="text-danger text-xs">{apiError}</p>}
        <MlUpload
          dataset={dataset}
          uploading={uploading}
          onUpload={handleUpload}
          onClear={handleClear}
        />
        <MlSqlEditor
          disabled={!dataset}
          running={running}
          error={sqlError}
          onRun={handleRun}
        />
      </div>

      {/* Right panel */}
      <MlResultTabs
        result={result}
        dataset={dataset}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
    </div>
  )
}
```

- [ ] **Check TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Commit**

```bash
git add frontend/src/components/ml/ frontend/src/pages/analytics/MlStudio.tsx
git commit -m "feat(ml): ML Studio — upload, SQL editor, charts, table, stats, forecast"
```

---

## Task 10: Integration smoke test + final cleanup

**Files:**
- All existing

- [ ] **Start backend**

```bash
cd backend && uv run uvicorn main:app --reload --port 8000
```

- [ ] **Start frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Manual smoke test checklist**

Open http://localhost:5177 and verify:

1. **KPI Tracker** (`/analytics/kpi`):
   - [ ] Click "+ Log" → form opens, autocomplete works for metric
   - [ ] Create a DA Output entry → appears in list with correct badge
   - [ ] Create a Business entry → filter tabs work
   - [ ] Chart renders after 2+ entries for same metric
   - [ ] Delete entry → removed from list

2. **Performance** (`/analytics/perf`):
   - [ ] Streak card shows flame icon + count
   - [ ] "Edit Rule" → RuleEditor opens, can add/remove conditions, save
   - [ ] Output grid shows real counts from DB
   - [ ] Calendar heatmap renders 30 cells

3. **ML Studio** (`/analytics/ml`):
   - [ ] Drop a CSV → upload progress → dataset info shows
   - [ ] Run `SELECT * FROM data LIMIT 10` → table tab works
   - [ ] Switch to Charts → bar/line/scatter work
   - [ ] Stats tab → Describe on a numeric column
   - [ ] Forecast tab → select date+value cols, run → chart shows
   - [ ] Invalid SQL → error shown under editor

- [ ] **Run full test suite**

```bash
cd backend && uv run pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat(sp4): analytics complete — KPI Tracker, Performance, ML Studio"
```
