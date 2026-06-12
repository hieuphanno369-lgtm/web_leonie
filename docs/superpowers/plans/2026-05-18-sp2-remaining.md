# SP2 Remaining Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement EDA Tracker, WIP Builder, and Discord Notify — the 3 remaining SP2 placeholder pages.

**Architecture:** Three independent features sharing the existing FastAPI + SQLite backend. Each adds its own DB tables (via `database.py`), router, tests, API client, and React components. WIP Builder links to Task Manager tasks via FK. Discord Notify makes external HTTP calls to Discord webhooks using stdlib `urllib.request`.

**Tech Stack:** FastAPI + SQLite (backend), React 19 + TypeScript + Tailwind CSS (frontend), pytest + httpx TestClient (tests). Run tests with `.venv/Scripts/python.exe -m pytest backend/tests/ -v` from repo root.

**Test venv:** Always use `backend/.venv/Scripts/python.exe` (not system Python). Check: `backend/.venv/Scripts/python.exe -c "import fastapi"` should succeed.

---

## Task 1: DB Schema — 4 new tables

**Files:**
- Modify: `backend/database.py`
- Test: `backend/tests/test_database.py` (already exists — add assertions)

- [ ] **Step 1: Write failing tests for new tables**

Add to `backend/tests/test_database.py`:
```python
def test_eda_requests_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(eda_requests)").fetchall()]
    conn.close()
    assert "id" in cols
    assert "requester" in cols
    assert "dataset" in cols

def test_wip_tables_exist(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    wip_cols = [r[1] for r in conn.execute("PRAGMA table_info(wip_items)").fetchall()]
    log_cols = [r[1] for r in conn.execute("PRAGMA table_info(wip_logs)").fetchall()]
    conn.close()
    assert "task_id" in wip_cols
    assert "progress" in wip_cols
    assert "wip_id" in log_cols

def test_discord_settings_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(discord_settings)").fetchall()]
    conn.close()
    assert "webhook_url" in cols
    assert "rule_overdue" in cols
```

- [ ] **Step 2: Run tests to confirm they fail**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_database.py -v
```
Expected: 3 new tests FAIL with "table not found" or empty cols list.

- [ ] **Step 3: Add 4 tables to `backend/database.py`**

Inside the `executescript("""...""")` call, after the `uploaded_datasets` table block, add:

```python
        CREATE TABLE IF NOT EXISTS eda_requests (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title     TEXT NOT NULL,
            requester TEXT NOT NULL,
            dataset   TEXT NOT NULL,
            priority  TEXT NOT NULL DEFAULT 'medium'
                          CHECK(priority IN ('low', 'medium', 'high')),
            status    TEXT NOT NULL DEFAULT 'todo'
                          CHECK(status IN ('todo', 'in_progress', 'done')),
            due_date  TEXT,
            notes     TEXT,
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wip_items (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            task_id   TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            progress  INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wip_logs (
            id      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            wip_id  TEXT NOT NULL REFERENCES wip_items(id) ON DELETE CASCADE,
            date    TEXT NOT NULL,
            note    TEXT NOT NULL,
            created TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS discord_settings (
            id           INTEGER PRIMARY KEY DEFAULT 1,
            webhook_url  TEXT,
            rule_overdue INTEGER NOT NULL DEFAULT 1,
            rule_done    INTEGER NOT NULL DEFAULT 0,
            rule_summary INTEGER NOT NULL DEFAULT 0,
            last_checked TEXT
        );
```

- [ ] **Step 4: Run tests — all pass**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_database.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/tests/test_database.py
git commit -m "feat(db): add eda_requests, wip_items, wip_logs, discord_settings tables"
```

---

## Task 2: EDA Backend Router + Tests

**Files:**
- Create: `backend/routers/eda.py`
- Create: `backend/tests/test_eda.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests — `backend/tests/test_eda.py`**

```python
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

EDA_MIN  = {"title": "EDA T04", "requester": "Alice", "dataset": "SF_ColosBaby"}
EDA_FULL = {
    "title": "Full EDA", "requester": "Bob", "dataset": "SF_Optimum",
    "priority": "high", "status": "in_progress",
    "due_date": "2026-05-25", "notes": "Focus on cohort",
}

def test_list_empty(client):
    assert client.get("/eda").json() == []

def test_list_returns_created(client):
    client.post("/eda", json=EDA_MIN)
    client.post("/eda", json={**EDA_MIN, "title": "EDA 2"})
    assert len(client.get("/eda").json()) == 2

def test_list_filter_by_status(client):
    client.post("/eda", json={**EDA_MIN, "status": "todo"})
    client.post("/eda", json={**EDA_MIN, "title": "Done EDA", "status": "done"})
    data = client.get("/eda?status=todo").json()
    assert len(data) == 1 and data[0]["title"] == "EDA T04"

def test_create_minimal(client):
    resp = client.post("/eda", json=EDA_MIN)
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"] == "EDA T04"
    assert d["requester"] == "Alice"
    assert d["dataset"] == "SF_ColosBaby"
    assert d["status"] == "todo"
    assert d["priority"] == "medium"
    assert d["id"]

def test_create_full(client):
    d = client.post("/eda", json=EDA_FULL).json()
    assert d["priority"] == "high"
    assert d["status"] == "in_progress"
    assert d["due_date"] == "2026-05-25"
    assert d["notes"] == "Focus on cohort"

def test_get_eda(client):
    created = client.post("/eda", json=EDA_MIN).json()
    resp = client.get(f"/eda/{created['id']}")
    assert resp.status_code == 200 and resp.json()["id"] == created["id"]

def test_get_not_found(client):
    assert client.get("/eda/nope").status_code == 404

def test_patch_status(client):
    created = client.post("/eda", json=EDA_MIN).json()
    resp = client.patch(f"/eda/{created['id']}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["title"] == "EDA T04"

def test_patch_not_found(client):
    assert client.patch("/eda/x", json={"status": "done"}).status_code == 404

def test_patch_empty_returns_eda(client):
    created = client.post("/eda", json=EDA_MIN).json()
    assert client.patch(f"/eda/{created['id']}", json={}).json()["title"] == "EDA T04"

def test_delete(client):
    created = client.post("/eda", json=EDA_MIN).json()
    assert client.delete(f"/eda/{created['id']}").status_code == 204
    assert client.get(f"/eda/{created['id']}").status_code == 404

def test_delete_not_found(client):
    assert client.delete("/eda/nope").status_code == 404
```

- [ ] **Step 2: Run — confirm all FAIL**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_eda.py -v
```
Expected: all FAIL with "404 Not Found" or connection error (router not registered).

- [ ] **Step 3: Create `backend/routers/eda.py`**

```python
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/eda", tags=["eda"])

EDAStatus   = Literal["todo", "in_progress", "done"]
EDAPriority = Literal["low", "medium", "high"]


class EDACreate(BaseModel):
    title: str
    requester: str
    dataset: str
    priority: EDAPriority = "medium"
    status: EDAStatus = "todo"
    due_date: str | None = None
    notes: str | None = None


class EDAUpdate(BaseModel):
    title: str | None = None
    requester: str | None = None
    dataset: str | None = None
    priority: EDAPriority | None = None
    status: EDAStatus | None = None
    due_date: str | None = None
    notes: str | None = None


class EDAOut(BaseModel):
    id: str
    title: str
    requester: str
    dataset: str
    priority: EDAPriority
    status: EDAStatus
    due_date: str | None
    notes: str | None
    created: str
    updated: str


def _row(row) -> EDAOut:
    return EDAOut(**dict(row))


@router.get("", response_model=list[EDAOut])
def list_eda(status: EDAStatus | None = Query(default=None)):
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM eda_requests WHERE status = ? ORDER BY created DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM eda_requests ORDER BY created DESC").fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.post("", response_model=EDAOut, status_code=201)
def create_eda(body: EDACreate):
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO eda_requests (title, requester, dataset, priority, status, due_date, notes)
           VALUES (:title, :requester, :dataset, :priority, :status, :due_date, :notes)""",
        body.model_dump(),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM eda_requests WHERE rowid = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return _row(row)


@router.get("/{eda_id}", response_model=EDAOut)
def get_eda(eda_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM eda_requests WHERE id = ?", (eda_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="EDA request not found")
    conn.close()
    return _row(row)


@router.patch("/{eda_id}", response_model=EDAOut)
def update_eda(eda_id: str, body: EDAUpdate):
    conn = get_connection()
    row = conn.execute("SELECT * FROM eda_requests WHERE id = ?", (eda_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="EDA request not found")
    _ALLOWED = {"title", "requester", "dataset", "priority", "status", "due_date", "notes"}
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in _ALLOWED}
    if updates:
        set_parts = [f"{k} = ?" for k in updates]
        set_parts.append("updated = datetime('now')")
        conn.execute(
            f"UPDATE eda_requests SET {', '.join(set_parts)} WHERE id = ?",
            list(updates.values()) + [eda_id],
        )
        conn.commit()
        row = conn.execute("SELECT * FROM eda_requests WHERE id = ?", (eda_id,)).fetchone()
    conn.close()
    return _row(row)


@router.delete("/{eda_id}", status_code=204)
def delete_eda(eda_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM eda_requests WHERE id = ?", (eda_id,))
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="EDA request not found")
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Wire router into `backend/main.py`**

Add after the existing tasks router import/include:
```python
from routers.eda import router as eda_router
# ...
app.include_router(eda_router)
```

Full updated `backend/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routers.tasks import router as tasks_router
from routers.eda   import router as eda_router

APP_VERSION = "1.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="Leonie API", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5177"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(eda_router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}
```

- [ ] **Step 5: Run tests — all pass**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_eda.py -v
```
Expected: 12 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/eda.py backend/tests/test_eda.py backend/main.py
git commit -m "feat(eda): CRUD router + 12 tests passing"
```

---

## Task 3: WIP Backend Router + Tests

**Files:**
- Create: `backend/routers/wip.py`
- Create: `backend/tests/test_wip.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests — `backend/tests/test_wip.py`**

```python
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def task_id(client):
    return client.post("/tasks", json={"title": "My task"}).json()["id"]

def test_list_empty(client):
    assert client.get("/wip").json() == []

def test_create_wip(client, task_id):
    resp = client.post("/wip", json={"task_id": task_id, "progress": 30})
    assert resp.status_code == 201
    d = resp.json()
    assert d["task_id"] == task_id
    assert d["task_title"] == "My task"
    assert d["progress"] == 30
    assert d["id"]

def test_create_wip_task_not_found(client):
    assert client.post("/wip", json={"task_id": "no-such-task"}).status_code == 404

def test_list_includes_task_title(client, task_id):
    client.post("/wip", json={"task_id": task_id})
    data = client.get("/wip").json()
    assert len(data) == 1
    assert data[0]["task_title"] == "My task"

def test_get_wip(client, task_id):
    created = client.post("/wip", json={"task_id": task_id}).json()
    resp = client.get(f"/wip/{created['id']}")
    assert resp.status_code == 200 and resp.json()["id"] == created["id"]

def test_get_not_found(client):
    assert client.get("/wip/nope").status_code == 404

def test_update_progress(client, task_id):
    created = client.post("/wip", json={"task_id": task_id, "progress": 10}).json()
    resp = client.patch(f"/wip/{created['id']}", json={"progress": 75})
    assert resp.status_code == 200 and resp.json()["progress"] == 75

def test_delete_wip(client, task_id):
    created = client.post("/wip", json={"task_id": task_id}).json()
    assert client.delete(f"/wip/{created['id']}").status_code == 204
    assert client.get(f"/wip/{created['id']}").status_code == 404

def test_delete_not_found(client):
    assert client.delete("/wip/nope").status_code == 404

def test_add_and_list_logs(client, task_id):
    wip_id = client.post("/wip", json={"task_id": task_id}).json()["id"]
    client.post(f"/wip/{wip_id}/logs", json={"date": "2026-05-18", "note": "First log"})
    logs = client.get(f"/wip/{wip_id}/logs").json()
    assert len(logs) == 1
    assert logs[0]["note"] == "First log"
    assert logs[0]["date"] == "2026-05-18"

def test_delete_log(client, task_id):
    wip_id = client.post("/wip", json={"task_id": task_id}).json()["id"]
    log_id = client.post(f"/wip/{wip_id}/logs", json={"date": "2026-05-18", "note": "Del me"}).json()["id"]
    assert client.delete(f"/wip/{wip_id}/logs/{log_id}").status_code == 204
    assert client.get(f"/wip/{wip_id}/logs").json() == []

def test_delete_wip_cascades_logs(client, task_id):
    wip_id = client.post("/wip", json={"task_id": task_id}).json()["id"]
    client.post(f"/wip/{wip_id}/logs", json={"date": "2026-05-18", "note": "cascade test"})
    client.delete(f"/wip/{wip_id}")
    # wip gone → logs gone (CASCADE); verify via 404 on wip
    assert client.get(f"/wip/{wip_id}").status_code == 404
```

- [ ] **Step 2: Run — confirm all FAIL**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_wip.py -v
```
Expected: all FAIL.

- [ ] **Step 3: Create `backend/routers/wip.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/wip", tags=["wip"])

_WIP_JOIN = """
    SELECT w.id, w.task_id, t.title AS task_title, w.progress, w.created, w.updated
    FROM wip_items w JOIN tasks t ON t.id = w.task_id
"""

class WIPCreate(BaseModel):
    task_id: str
    progress: int = 0

class WIPUpdate(BaseModel):
    progress: int

class WIPOut(BaseModel):
    id: str
    task_id: str
    task_title: str
    progress: int
    created: str
    updated: str

class WIPLogCreate(BaseModel):
    date: str
    note: str

class WIPLogOut(BaseModel):
    id: str
    wip_id: str
    date: str
    note: str
    created: str

def _wrow(row) -> WIPOut:    return WIPOut(**dict(row))

def _lrow(row) -> WIPLogOut:
    return WIPLogOut(**dict(row))


@router.get("", response_model=list[WIPOut])
def list_wips():
    conn = get_connection()
    rows = conn.execute(_WIP_JOIN + " ORDER BY w.created DESC").fetchall()
    conn.close()
    return [_wrow(r) for r in rows]


@router.post("", response_model=WIPOut, status_code=201)
def create_wip(body: WIPCreate):
    conn = get_connection()
    if not conn.execute("SELECT id FROM tasks WHERE id = ?", (body.task_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    cursor = conn.execute(
        "INSERT INTO wip_items (task_id, progress) VALUES (?, ?)",
        (body.task_id, body.progress),
    )
    conn.commit()
    row = conn.execute(_WIP_JOIN + " WHERE w.rowid = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return _wrow(row)


@router.get("/{wip_id}", response_model=WIPOut)
def get_wip(wip_id: str):
    conn = get_connection()
    row = conn.execute(_WIP_JOIN + " WHERE w.id = ?", (wip_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="WIP not found")
    conn.close()
    return _wrow(row)


@router.patch("/{wip_id}", response_model=WIPOut)
def update_wip(wip_id: str, body: WIPUpdate):
    conn = get_connection()
    if not conn.execute("SELECT id FROM wip_items WHERE id = ?", (wip_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="WIP not found")
    conn.execute(
        "UPDATE wip_items SET progress = ?, updated = datetime('now') WHERE id = ?",
        (body.progress, wip_id),
    )
    conn.commit()
    row = conn.execute(_WIP_JOIN + " WHERE w.id = ?", (wip_id,)).fetchone()
    conn.close()
    return _wrow(row)


@router.delete("/{wip_id}", status_code=204)
def delete_wip(wip_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM wip_items WHERE id = ?", (wip_id,))
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="WIP not found")
    conn.commit()
    conn.close()


@router.get("/{wip_id}/logs", response_model=list[WIPLogOut])
def list_logs(wip_id: str):
    conn = get_connection()
    if not conn.execute("SELECT id FROM wip_items WHERE id = ?", (wip_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="WIP not found")
    rows = conn.execute(
        "SELECT * FROM wip_logs WHERE wip_id = ? ORDER BY date DESC, created DESC",
        (wip_id,),
    ).fetchall()
    conn.close()
    return [_lrow(r) for r in rows]


@router.post("/{wip_id}/logs", response_model=WIPLogOut, status_code=201)
def add_log(wip_id: str, body: WIPLogCreate):
    conn = get_connection()
    if not conn.execute("SELECT id FROM wip_items WHERE id = ?", (wip_id,)).fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="WIP not found")
    cursor = conn.execute(
        "INSERT INTO wip_logs (wip_id, date, note) VALUES (?, ?, ?)",
        (wip_id, body.date, body.note),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM wip_logs WHERE rowid = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return _lrow(row)


@router.delete("/{wip_id}/logs/{log_id}", status_code=204)
def delete_log(wip_id: str, log_id: str):
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM wip_logs WHERE id = ? AND wip_id = ?", (log_id, wip_id)
    )
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Log not found")
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Wire into `backend/main.py`**

```python
from routers.wip import router as wip_router
# ...
app.include_router(wip_router)
```

- [ ] **Step 5: Run tests — all pass**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_wip.py -v
```
Expected: 13 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/wip.py backend/tests/test_wip.py backend/main.py
git commit -m "feat(wip): WIP + logs CRUD router, 13 tests passing"
```

---

## Task 4: Discord Backend Router + Tests

**Files:**
- Create: `backend/routers/discord_notify.py`
- Create: `backend/tests/test_discord.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests — `backend/tests/test_discord.py`**

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

WEBHOOK = "https://discord.com/api/webhooks/123/abc"

def test_get_settings_default(client):
    resp = client.get("/discord/settings")
    assert resp.status_code == 200
    d = resp.json()
    assert d["webhook_url"] is None
    assert d["rule_overdue"] is True
    assert d["rule_done"] is False

def test_upsert_settings(client):
    resp = client.post("/discord/settings", json={"webhook_url": WEBHOOK, "rule_done": True})
    assert resp.status_code == 200
    d = resp.json()
    assert d["webhook_url"] == WEBHOOK
    assert d["rule_done"] is True

def test_send_no_webhook(client):
    resp = client.post("/discord/send", json={"message": "hello"})
    assert resp.status_code == 400

def test_send_message(client):
    client.post("/discord/settings", json={"webhook_url": WEBHOOK})
    with patch("routers.discord_notify._send_webhook") as mock_send:
        resp = client.post("/discord/send", json={"message": "Test msg"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_send.assert_called_once_with(WEBHOOK, "Test msg")

def test_check_no_webhook(client):
    assert client.post("/discord/check").status_code == 400

def test_check_overdue_sends_notification(client):
    client.post("/discord/settings", json={"webhook_url": WEBHOOK, "rule_overdue": True})
    # Create an overdue task
    client.post("/tasks", json={"title": "Old task", "due_date": "2020-01-01", "status": "todo"})
    with patch("routers.discord_notify._send_webhook") as mock_send:
        resp = client.post("/discord/check")
        assert resp.status_code == 200
        assert resp.json()["sent"] >= 1
        mock_send.assert_called()

def test_check_no_overdue_sends_nothing(client):
    client.post("/discord/settings", json={"webhook_url": WEBHOOK, "rule_overdue": True})
    # No tasks created → nothing to notify
    with patch("routers.discord_notify._send_webhook") as mock_send:
        resp = client.post("/discord/check")
        assert resp.json()["sent"] == 0
        mock_send.assert_not_called()

def test_check_updates_last_checked(client):
    client.post("/discord/settings", json={"webhook_url": WEBHOOK})
    with patch("routers.discord_notify._send_webhook"):
        client.post("/discord/check")
    settings = client.get("/discord/settings").json()
    assert settings["last_checked"] is not None
```

- [ ] **Step 2: Run — confirm all FAIL**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_discord.py -v
```
Expected: all FAIL.

- [ ] **Step 3: Create `backend/routers/discord_notify.py`**

```python
import urllib.request
import urllib.error
import json as json_lib
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/discord", tags=["discord"])


class DiscordSettingsIn(BaseModel):
    webhook_url: str | None = None
    rule_overdue: bool = True
    rule_done: bool = False
    rule_summary: bool = False


class DiscordSettingsOut(BaseModel):
    webhook_url: str | None
    rule_overdue: bool
    rule_done: bool
    rule_summary: bool
    last_checked: str | None


class DiscordSendIn(BaseModel):
    message: str


def _send_webhook(webhook_url: str, message: str) -> None:
    payload = json_lib.dumps({"content": message}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except urllib.error.HTTPError as e:
        raise ValueError(f"Discord returned HTTP {e.code}")


def _ensure_row(conn):
    if not conn.execute("SELECT id FROM discord_settings WHERE id = 1").fetchone():
        conn.execute("INSERT INTO discord_settings (id) VALUES (1)")
        conn.commit()
    return conn.execute("SELECT * FROM discord_settings WHERE id = 1").fetchone()


def _to_out(row) -> DiscordSettingsOut:
    return DiscordSettingsOut(
        webhook_url=row["webhook_url"],
        rule_overdue=bool(row["rule_overdue"]),
        rule_done=bool(row["rule_done"]),
        rule_summary=bool(row["rule_summary"]),
        last_checked=row["last_checked"],
    )


@router.get("/settings", response_model=DiscordSettingsOut)
def get_settings():
    conn = get_connection()
    row = _ensure_row(conn)
    conn.close()
    return _to_out(row)


@router.post("/settings", response_model=DiscordSettingsOut)
def upsert_settings(body: DiscordSettingsIn):
    conn = get_connection()
    _ensure_row(conn)
    conn.execute(
        """UPDATE discord_settings
           SET webhook_url = ?, rule_overdue = ?, rule_done = ?, rule_summary = ?
           WHERE id = 1""",
        (body.webhook_url, int(body.rule_overdue), int(body.rule_done), int(body.rule_summary)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM discord_settings WHERE id = 1").fetchone()
    conn.close()
    return _to_out(row)


@router.post("/send")
def send_message(body: DiscordSendIn):
    conn = get_connection()
    row = _ensure_row(conn)
    conn.close()
    if not row["webhook_url"]:
        raise HTTPException(status_code=400, detail="Webhook URL not configured")
    try:
        _send_webhook(row["webhook_url"], body.message)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True}


@router.post("/check")
def check_rules():
    conn = get_connection()
    row = _ensure_row(conn)
    if not row["webhook_url"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Webhook URL not configured")

    sent = 0
    today = date.today().isoformat()
    last_checked = row["last_checked"] or "2000-01-01T00:00:00"

    if row["rule_overdue"]:
        overdue = conn.execute(
            "SELECT title FROM tasks WHERE due_date < ? AND status != 'done' ORDER BY due_date",
            (today,),
        ).fetchall()
        if overdue:
            titles = "\n".join(f"• {r['title']}" for r in overdue)
            _send_webhook(row["webhook_url"], f"⚠️ **Tasks quá deadline:**\n{titles}")
            sent += 1

    if row["rule_done"]:
        done_tasks = conn.execute(
            "SELECT title FROM tasks WHERE status = 'done' AND updated >= ?",
            (last_checked,),
        ).fetchall()
        for t in done_tasks:
            _send_webhook(row["webhook_url"], f"✅ Task hoàn thành: **{t['title']}**")
            sent += 1

    conn.execute(
        "UPDATE discord_settings SET last_checked = datetime('now') WHERE id = 1"
    )
    conn.commit()
    conn.close()
    return {"sent": sent}
```

- [ ] **Step 4: Wire into `backend/main.py`** — final version:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routers.tasks          import router as tasks_router
from routers.eda            import router as eda_router
from routers.wip            import router as wip_router
from routers.discord_notify import router as discord_router

APP_VERSION = "1.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="Leonie API", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5177"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(eda_router)
app.include_router(wip_router)
app.include_router(discord_router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}
```

- [ ] **Step 5: Run all backend tests**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v
```
Expected: all tests PASS (existing 20 + 12 EDA + 13 WIP + 8 Discord = 53 total).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/discord_notify.py backend/tests/test_discord.py backend/main.py
git commit -m "feat(discord): notify router + 8 tests passing; all 53 backend tests green"
```

---

## Task 5: Frontend Types + API Clients

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/eda.ts`
- Create: `frontend/src/api/wip.ts`
- Create: `frontend/src/api/discord.ts`

- [ ] **Step 1: Add types to `frontend/src/types.ts`**

Append after the `Snippet` interface:

```typescript
// ─── EDA Tracker ────────────────────────────────────────────────────────────

export type EDAStatus   = 'todo' | 'in_progress' | 'done'
export type EDAPriority = 'low' | 'medium' | 'high'

export interface EDARequest {
  id: string
  title: string
  requester: string
  dataset: string
  priority: EDAPriority
  status: EDAStatus
  due_date: string | null
  notes: string | null
  created: string
  updated: string
}

// ─── WIP Builder ────────────────────────────────────────────────────────────

export interface WIPItem {
  id: string
  task_id: string
  task_title: string
  progress: number
  created: string
  updated: string
}

export interface WIPLog {
  id: string
  wip_id: string
  date: string
  note: string
  created: string
}

// ─── Discord Notify ──────────────────────────────────────────────────────────

export interface DiscordSettings {
  webhook_url: string | null
  rule_overdue: boolean
  rule_done: boolean
  rule_summary: boolean
  last_checked: string | null
}
```

- [ ] **Step 2: Create `frontend/src/api/eda.ts`**

```typescript
import client from './client'
import type { EDARequest, EDAStatus } from '../types'

export interface EDAPayload {
  title: string
  requester: string
  dataset: string
  status?: EDAStatus
  priority?: 'low' | 'medium' | 'high'
  due_date?: string | null
  notes?: string | null
}

export async function fetchEDA(status?: EDAStatus): Promise<EDARequest[]> {
  const params = status ? { status } : {}
  const { data } = await client.get<EDARequest[]>('/eda', { params })
  return data
}

export async function createEDA(body: EDAPayload): Promise<EDARequest> {
  const { data } = await client.post<EDARequest>('/eda', body)
  return data
}

export async function updateEDA(id: string, body: Partial<EDAPayload>): Promise<EDARequest> {
  const { data } = await client.patch<EDARequest>(`/eda/${id}`, body)
  return data
}

export async function deleteEDA(id: string): Promise<void> {
  await client.delete(`/eda/${id}`)
}
```

- [ ] **Step 3: Create `frontend/src/api/wip.ts`**

```typescript
import client from './client'
import type { WIPItem, WIPLog } from '../types'

export async function fetchWIPs(): Promise<WIPItem[]> {
  const { data } = await client.get<WIPItem[]>('/wip')
  return data
}

export async function createWIP(task_id: string, progress = 0): Promise<WIPItem> {
  const { data } = await client.post<WIPItem>('/wip', { task_id, progress })
  return data
}

export async function updateWIPProgress(id: string, progress: number): Promise<WIPItem> {
  const { data } = await client.patch<WIPItem>(`/wip/${id}`, { progress })
  return data
}

export async function deleteWIP(id: string): Promise<void> {
  await client.delete(`/wip/${id}`)
}

export async function fetchLogs(wip_id: string): Promise<WIPLog[]> {
  const { data } = await client.get<WIPLog[]>(`/wip/${wip_id}/logs`)
  return data
}

export async function addLog(wip_id: string, date: string, note: string): Promise<WIPLog> {
  const { data } = await client.post<WIPLog>(`/wip/${wip_id}/logs`, { date, note })
  return data
}

export async function deleteLog(wip_id: string, log_id: string): Promise<void> {
  await client.delete(`/wip/${wip_id}/logs/${log_id}`)
}
```

- [ ] **Step 4: Create `frontend/src/api/discord.ts`**

```typescript
import client from './client'
import type { DiscordSettings } from '../types'

export async function fetchDiscordSettings(): Promise<DiscordSettings> {
  const { data } = await client.get<DiscordSettings>('/discord/settings')
  return data
}

export async function saveDiscordSettings(body: Partial<DiscordSettings>): Promise<DiscordSettings> {
  const { data } = await client.post<DiscordSettings>('/discord/settings', body)
  return data
}

export async function sendDiscordMessage(message: string): Promise<void> {
  await client.post('/discord/send', { message })
}

export async function checkDiscordRules(): Promise<{ sent: number }> {
  const { data } = await client.post<{ sent: number }>('/discord/check')
  return data
}
```

- [ ] **Step 5: TypeScript check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/eda.ts frontend/src/api/wip.ts frontend/src/api/discord.ts
git commit -m "feat(frontend): types + API clients for EDA, WIP, Discord"
```

---

## Task 6: EDA Frontend — Components + Page

**Files:**
- Create: `frontend/src/components/eda/EDAItem.tsx`
- Create: `frontend/src/components/eda/EDAList.tsx`
- Create: `frontend/src/components/eda/EDADetail.tsx`
- Create: `frontend/src/components/eda/EDAForm.tsx`
- Replace: `frontend/src/pages/work/EDATracker.tsx`

- [ ] **Step 1: Create `frontend/src/components/eda/EDAItem.tsx`**

```tsx
import type { EDARequest } from '../../types'

interface Props {
  eda: EDARequest
  isSelected: boolean
  onSelect: () => void
}

const priorityBadge: Record<string, string> = {
  high:   'bg-danger/10 text-danger border-danger/25',
  medium: 'bg-data/10 text-data border-data/25',
  low:    'bg-white/5 text-gray-500 border-white/10',
}

const statusDot: Record<string, string> = {
  todo:        'bg-warning',
  in_progress: 'bg-data',
  done:        'bg-work',
}

export default function EDAItem({ eda, isSelected, onSelect }: Props) {
  const done = eda.status === 'done'
  return (
    <div
      onClick={onSelect}
      className={`rounded-lg px-3 py-2.5 mb-1 cursor-pointer border transition-all ${
        isSelected
          ? 'bg-work/5 border-work/20'
          : 'border-white/5 hover:bg-white/3 hover:border-white/10'
      } ${done ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot[eda.status]}`} />
        <span className={`text-xs font-medium flex-1 truncate ${done ? 'line-through text-gray-500' : 'text-white'}`}>
          {eda.title}
        </span>
        <span className={`badge border text-[10px] ${priorityBadge[eda.priority]}`}>
          {eda.priority.toUpperCase()}
        </span>
      </div>
      <p className="text-[11px] text-gray-500 truncate pl-4">{eda.requester} · {eda.dataset}</p>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/eda/EDAList.tsx`**

```tsx
import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { EDARequest, EDAStatus } from '../../types'
import EDAItem from './EDAItem'

type FilterTab = 'all' | EDAStatus

interface Props {
  requests: EDARequest[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export default function EDAList({ requests, selectedId, onSelect, onNew }: Props) {
  const [filter, setFilter] = useState<FilterTab>('all')
  const [search, setSearch] = useState('')

  const visible = requests.filter(r => {
    if (filter !== 'all' && r.status !== filter) return false
    if (search && !r.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const count = (f: FilterTab) =>
    f === 'all' ? requests.length : requests.filter(r => r.status === f).length

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all',         label: 'All' },
    { key: 'todo',        label: 'Todo' },
    { key: 'in_progress', label: 'In Progress' },
    { key: 'done',        label: 'Done' },
  ]

  return (
    <div className="w-[340px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">EDA Requests</h2>
          <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> New
          </button>
        </div>
        <div className="flex gap-1 flex-wrap">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-2 py-1 rounded text-[11px] transition-all ${
                filter === key
                  ? 'bg-work/10 text-work border border-work/30'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label} <span className="opacity-50">({count(key)})</span>
            </button>
          ))}
        </div>
      </div>
      <div className="mx-3 my-2">
        <input
          className="input-base text-xs"
          placeholder="Search EDA requests..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {visible.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No requests found</p>
        ) : (
          visible.map(r => (
            <EDAItem
              key={r.id}
              eda={r}
              isSelected={r.id === selectedId}
              onSelect={() => onSelect(r.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/eda/EDADetail.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { Pencil, Trash2 } from 'lucide-react'
import type { EDARequest } from '../../types'

interface Props {
  eda: EDARequest
  onEdit: () => void
  onDelete: (id: string) => void
}

const statusCls: Record<string, string> = {
  todo:        'bg-warning/10 text-warning border-warning/25',
  in_progress: 'bg-data/10 text-data border-data/25',
  done:        'bg-work/10 text-work border-work/25',
}
const priorityCls: Record<string, string> = {
  high:   'bg-danger/10 text-danger border-danger/25',
  medium: 'bg-data/10 text-data border-data/25',
  low:    'bg-white/5 text-gray-500 border-white/10',
}

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

export default function EDADetail({ eda, onEdit, onDelete }: Props) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  useEffect(() => { setConfirmDelete(false) }, [eda.id])

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <div className="flex items-start justify-between gap-3 mb-3">
        <h2 className="text-base font-semibold text-white leading-snug">{eda.title}</h2>
        <div className="flex gap-2 flex-shrink-0">
          <button onClick={onEdit} className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1">
            <Pencil size={12} /> Edit
          </button>
          {confirmDelete ? (
            <button onClick={() => onDelete(eda.id)} className="btn-danger flex items-center gap-1 text-xs px-2.5 py-1">
              <Trash2 size={12} /> Confirm
            </button>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1 hover:text-danger hover:border-danger/30"
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-4">
        <span className={`badge border ${statusCls[eda.status]}`}>{eda.status.replace('_', ' ')}</span>
        <span className={`badge border ${priorityCls[eda.priority]}`}>{eda.priority} priority</span>
        {eda.due_date && (
          <span className="badge bg-white/5 text-gray-400 border border-white/10">
            📅 {fmtDate(eda.due_date)}
          </span>
        )}
      </div>

      <hr className="border-white/5 mb-4" />

      <div className="mb-4">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Requester</p>
        <p className="text-xs text-gray-300">{eda.requester}</p>
      </div>

      <div className="mb-4">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Dataset</p>
        <p className="text-xs text-gray-300 font-mono">{eda.dataset}</p>
      </div>

      <div className="mb-4">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Notes</p>
        <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2.5 text-xs text-gray-400 leading-relaxed min-h-[60px] whitespace-pre-wrap">
          {eda.notes ?? <span className="italic text-gray-600">No notes</span>}
        </div>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Info</p>
        <p className="text-xs text-gray-500 mb-1">Created: <span className="text-gray-400">{fmtDate(eda.created)}</span></p>
        <p className="text-xs text-gray-500">Updated: <span className="text-gray-400">{fmtDate(eda.updated)}</span></p>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/components/eda/EDAForm.tsx`**

```tsx
import { useState } from 'react'
import { Check, X } from 'lucide-react'
import type { EDARequest, EDAStatus, EDAPriority } from '../../types'
import type { EDAPayload } from '../../api/eda'

interface Props {
  initial?: EDARequest
  onSave: (payload: EDAPayload) => Promise<void>
  onCancel: () => void
}

export default function EDAForm({ initial, onSave, onCancel }: Props) {
  const [title,     setTitle]     = useState(initial?.title     ?? '')
  const [requester, setRequester] = useState(initial?.requester ?? '')
  const [dataset,   setDataset]   = useState(initial?.dataset   ?? '')
  const [status,    setStatus]    = useState<EDAStatus>(initial?.status   ?? 'todo')
  const [priority,  setPriority]  = useState<EDAPriority>(initial?.priority ?? 'medium')
  const [dueDate,   setDueDate]   = useState(initial?.due_date  ?? '')
  const [notes,     setNotes]     = useState(initial?.notes     ?? '')
  const [error,     setError]     = useState('')
  const [saving,    setSaving]    = useState(false)

  async function handleSubmit() {
    if (!title.trim())     { setError('Title is required');     return }
    if (!requester.trim()) { setError('Requester is required'); return }
    if (!dataset.trim())   { setError('Dataset is required');   return }
    setError('')
    setSaving(true)
    try {
      await onSave({
        title: title.trim(),
        requester: requester.trim(),
        dataset: dataset.trim(),
        status,
        priority,
        due_date: dueDate || null,
        notes: notes || null,
      })
    } catch {
      setError('Failed to save — check connection')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">
        {initial ? '✏️ Edit EDA Request' : '＋ New EDA Request'}
      </h2>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Title *</label>
        <input className="input-base" placeholder="EDA ColosBaby T04..." value={title} onChange={e => setTitle(e.target.value)} autoFocus />
      </div>

      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Requester *</label>
          <input className="input-base" placeholder="Nguyen Van A" value={requester} onChange={e => setRequester(e.target.value)} />
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Dataset *</label>
          <input className="input-base" placeholder="SF_ColosBaby_2024" value={dataset} onChange={e => setDataset(e.target.value)} />
        </div>
      </div>

      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Status</label>
          <select className="input-base" value={status} onChange={e => setStatus(e.target.value as EDAStatus)}>
            <option value="todo">Todo</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Priority</label>
          <select className="input-base" value={priority} onChange={e => setPriority(e.target.value as EDAPriority)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Due date</label>
        <input type="date" className="input-base" value={dueDate} onChange={e => setDueDate(e.target.value)} />
      </div>

      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Notes</label>
        <textarea className="input-base resize-none" rows={3} placeholder="Optional notes..." value={notes} onChange={e => setNotes(e.target.value)} />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button onClick={handleSubmit} disabled={saving} className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Check size={13} /> {saving ? 'Saving...' : 'Save Request'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
```

- [ ] **Step 5: Replace `frontend/src/pages/work/EDATracker.tsx`**

```tsx
import { useEffect, useState, useCallback } from 'react'
import type { EDARequest } from '../../types'
import { fetchEDA, createEDA, updateEDA, deleteEDA } from '../../api/eda'
import type { EDAPayload } from '../../api/eda'
import EDAList   from '../../components/eda/EDAList'
import EDADetail from '../../components/eda/EDADetail'
import EDAForm   from '../../components/eda/EDAForm'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function EDATracker() {
  const [requests,   setRequests]   = useState<EDARequest[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selected = requests.find(r => r.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      setRequests(await fetchEDA())
      setApiError('')
    } catch {
      setApiError('Cannot reach API — is the backend running?')
    }
  }, [])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) { setSelectedId(id); setMode('detail') }

  async function handleSave(payload: EDAPayload) {
    try {
      if (mode === 'create') {
        const created = await createEDA(payload)
        setRequests(rs => [created, ...rs])
        setSelectedId(created.id)
        setMode('detail')
      } else if (mode === 'edit' && selectedId) {
        const updated = await updateEDA(selectedId, payload)
        setRequests(rs => rs.map(r => r.id === selectedId ? updated : r))
        setMode('detail')
      }
    } catch {
      setApiError('Failed to save — check connection')
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteEDA(id)
      setRequests(rs => rs.filter(r => r.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch {
      setApiError('Failed to delete — check connection')
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <EDAList
        requests={requests}
        selectedId={selectedId}
        onSelect={handleSelect}
        onNew={() => { setSelectedId(null); setMode('create') }}
      />
      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg">
            {apiError}
          </div>
        )}
        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">🔬</span>
            <p>Select a request or create one</p>
          </div>
        )}
        {mode === 'detail' && selected && (
          <EDADetail eda={selected} onEdit={() => setMode('edit')} onDelete={handleDelete} />
        )}
        {(mode === 'create' || mode === 'edit') && (
          <EDAForm
            initial={mode === 'edit' ? (selected ?? undefined) : undefined}
            onSave={handleSave}
            onCancel={() => setMode(selected ? 'detail' : 'empty')}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: TypeScript check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/eda/ frontend/src/pages/work/EDATracker.tsx
git commit -m "feat(eda): EDATracker page + 4 components"
```

---

## Task 7: WIP Frontend — Components + Page

**Files:**
- Create: `frontend/src/components/wip/WIPItem.tsx`
- Create: `frontend/src/components/wip/WIPList.tsx`
- Create: `frontend/src/components/wip/WIPDetail.tsx`
- Create: `frontend/src/components/wip/WIPForm.tsx`
- Replace: `frontend/src/pages/work/WipBuilder.tsx`

- [ ] **Step 1: Create `frontend/src/components/wip/WIPItem.tsx`**

```tsx
import type { WIPItem } from '../../types'

interface Props {
  wip: WIPItem
  isSelected: boolean
  onSelect: () => void
}

function progressColor(p: number) {
  if (p >= 100) return 'bg-work'
  if (p >= 70)  return 'bg-warning'
  return 'bg-data'
}

function progressTextColor(p: number) {
  if (p >= 100) return 'text-work'
  if (p >= 70)  return 'text-warning'
  return 'text-data'
}

export default function WIPItem({ wip, isSelected, onSelect }: Props) {
  return (
    <div
      onClick={onSelect}
      className={`rounded-lg px-3 py-2.5 mb-1 cursor-pointer border transition-all ${
        isSelected
          ? 'bg-data/5 border-data/20'
          : 'border-white/5 hover:bg-white/3 hover:border-white/10'
      }`}
    >
      <p className="text-xs font-medium text-white truncate mb-2">{wip.task_title}</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${progressColor(wip.progress)}`}
            style={{ width: `${wip.progress}%` }}
          />
        </div>
        <span className={`text-[11px] font-semibold tabular-nums ${progressTextColor(wip.progress)}`}>
          {wip.progress}%
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/wip/WIPList.tsx`**

```tsx
import { Plus } from 'lucide-react'
import type { WIPItem } from '../../types'
import WIPItemComponent from './WIPItem'

interface Props {
  wips: WIPItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export default function WIPList({ wips, selectedId, onSelect, onNew }: Props) {
  return (
    <div className="w-[340px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      <div className="px-4 pt-3.5 pb-3 border-b border-white/5 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">WIP Builder</h2>
        <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
          <Plus size={12} /> New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
        {wips.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No WIP items yet</p>
        ) : (
          wips.map(w => (
            <WIPItemComponent
              key={w.id}
              wip={w}
              isSelected={w.id === selectedId}
              onSelect={() => onSelect(w.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/wip/WIPDetail.tsx`**

```tsx
import { useState, useEffect, useCallback } from 'react'
import { Trash2, Plus } from 'lucide-react'
import type { WIPItem, WIPLog } from '../../types'
import { updateWIPProgress, deleteWIP, fetchLogs, addLog, deleteLog } from '../../api/wip'

interface Props {
  wip: WIPItem
  onProgressUpdate: (updated: WIPItem) => void
  onDelete: (id: string) => void
}

function progressColor(p: number) {
  if (p >= 100) return 'accent-work'
  if (p >= 70)  return 'accent-warning'
  return 'accent-data'
}

function progressBarColor(p: number) {
  if (p >= 100) return 'bg-work'
  if (p >= 70)  return 'bg-warning'
  return 'bg-data'
}

export default function WIPDetail({ wip, onProgressUpdate, onDelete }: Props) {
  const [logs,          setLogs]          = useState<WIPLog[]>([])
  const [localProgress, setLocalProgress] = useState(wip.progress)
  const [showLogInput,  setShowLogInput]  = useState(false)
  const [logDate,       setLogDate]       = useState(new Date().toISOString().slice(0, 10))
  const [logNote,       setLogNote]       = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [saving,        setSaving]        = useState(false)
  const [error,         setError]         = useState('')

  useEffect(() => {
    setLocalProgress(wip.progress)
    setConfirmDelete(false)
    setShowLogInput(false)
  }, [wip.id, wip.progress])

  const loadLogs = useCallback(async () => {
    try { setLogs(await fetchLogs(wip.id)) } catch { /* ignore */ }
  }, [wip.id])

  useEffect(() => { loadLogs() }, [loadLogs])

  async function handleSliderRelease() {
    try {
      const updated = await updateWIPProgress(wip.id, localProgress)
      onProgressUpdate(updated)
    } catch {
      setError('Failed to update progress')
    }
  }

  async function handleAddLog() {
    if (!logNote.trim()) return
    setSaving(true)
    try {
      const log = await addLog(wip.id, logDate, logNote.trim())
      setLogs(ls => [log, ...ls])
      setLogNote('')
      setShowLogInput(false)
    } catch {
      setError('Failed to add log')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteLog(log_id: string) {
    try {
      await deleteLog(wip.id, log_id)
      setLogs(ls => ls.filter(l => l.id !== log_id))
    } catch {
      setError('Failed to delete log')
    }
  }

  const fmtDate = (iso: string) =>
    new Date(iso + 'T00:00:00').toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <h2 className="text-base font-semibold text-white leading-snug">{wip.task_title}</h2>
        {confirmDelete ? (
          <button onClick={() => onDelete(wip.id)} className="btn-danger flex items-center gap-1 text-xs px-2.5 py-1 flex-shrink-0">
            <Trash2 size={12} /> Confirm
          </button>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1 hover:text-danger hover:border-danger/30 flex-shrink-0"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>

      {/* Progress */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] uppercase tracking-widest text-gray-600">Progress</p>
          <span className={`text-sm font-bold tabular-nums ${progressBarColor(localProgress).replace('bg-', 'text-')}`}>
            {localProgress}%
          </span>
        </div>
        <div className="h-2 bg-white/5 rounded-full overflow-hidden mb-2">
          <div
            className={`h-full rounded-full transition-all ${progressBarColor(localProgress)}`}
            style={{ width: `${localProgress}%` }}
          />
        </div>
        <input
          type="range"
          min={0} max={100}
          value={localProgress}
          className={`w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/5 ${progressColor(localProgress)}`}
          onChange={e => setLocalProgress(Number(e.target.value))}
          onMouseUp={handleSliderRelease}
          onTouchEnd={handleSliderRelease}
        />
      </div>

      <hr className="border-white/5 mb-4" />

      {/* Log section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] uppercase tracking-widest text-gray-600">Daily Log</p>
          <button
            onClick={() => setShowLogInput(v => !v)}
            className="btn-ghost flex items-center gap-1 text-xs px-2 py-1"
          >
            <Plus size={11} /> Add
          </button>
        </div>

        {showLogInput && (
          <div className="bg-secondary border border-white/8 rounded-lg p-3 mb-3">
            <div className="flex gap-2 mb-2">
              <input
                type="date"
                className="input-base text-xs w-36"
                value={logDate}
                onChange={e => setLogDate(e.target.value)}
              />
            </div>
            <textarea
              className="input-base resize-none text-xs w-full mb-2"
              rows={2}
              placeholder="What did you do today?"
              value={logNote}
              onChange={e => setLogNote(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2">
              <button onClick={handleAddLog} disabled={saving} className="btn-primary text-xs px-3 py-1 disabled:opacity-50">
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setShowLogInput(false)} className="btn-ghost text-xs px-3 py-1">Cancel</button>
            </div>
          </div>
        )}

        {error && <p className="text-danger text-xs mb-2">{error}</p>}

        {logs.length === 0 ? (
          <p className="text-gray-600 text-xs italic">No log entries yet</p>
        ) : (
          <div className="flex flex-col gap-2">
            {logs.map(log => (
              <div key={log.id} className="flex gap-3 group">
                <span className="text-[11px] text-gray-500 tabular-nums flex-shrink-0 pt-0.5">
                  {fmtDate(log.date)}
                </span>
                <p className="text-xs text-gray-300 flex-1 leading-relaxed">{log.note}</p>
                <button
                  onClick={() => handleDeleteLog(log.id)}
                  className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-danger transition-opacity flex-shrink-0"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/components/wip/WIPForm.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import type { Task } from '../../types'
import { fetchTasks } from '../../api/tasks'
import { createWIP } from '../../api/wip'
import type { WIPItem } from '../../types'

interface Props {
  onCreated: (wip: WIPItem) => void
  onCancel: () => void
}

export default function WIPForm({ onCreated, onCancel }: Props) {
  const [tasks,    setTasks]    = useState<Task[]>([])
  const [taskId,   setTaskId]   = useState('')
  const [progress, setProgress] = useState(0)
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)

  useEffect(() => {
    fetchTasks().then(setTasks).catch(() => setError('Failed to load tasks'))
  }, [])

  async function handleSubmit() {
    if (!taskId) { setError('Select a task'); return }
    setError('')
    setSaving(true)
    try {
      const wip = await createWIP(taskId, progress)
      onCreated(wip)
    } catch {
      setError('Failed to create WIP — check connection')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <h2 className="text-sm font-semibold text-white mb-4">＋ New WIP</h2>

      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Task *</label>
        <select className="input-base" value={taskId} onChange={e => setTaskId(e.target.value)}>
          <option value="">— select a task —</option>
          {tasks.filter(t => t.status !== 'done').map(t => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-[10px] uppercase tracking-widest text-gray-600">Initial Progress</label>
          <span className="text-xs font-semibold text-data">{progress}%</span>
        </div>
        <input
          type="range" min={0} max={100}
          value={progress}
          className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/5 accent-data"
          onChange={e => setProgress(Number(e.target.value))}
        />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button onClick={handleSubmit} disabled={saving} className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
        <Check size={13} /> {saving ? 'Creating...' : 'Create WIP'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
```

- [ ] **Step 5: Replace `frontend/src/pages/work/WipBuilder.tsx`**

```tsx
import { useEffect, useState, useCallback } from 'react'
import type { WIPItem } from '../../types'
import { fetchWIPs, deleteWIP } from '../../api/wip'
import WIPList   from '../../components/wip/WIPList'
import WIPDetail from '../../components/wip/WIPDetail'
import WIPForm   from '../../components/wip/WIPForm'

type PanelMode = 'empty' | 'detail' | 'create'

export default function WipBuilder() {
  const [wips,       setWips]       = useState<WIPItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selected = wips.find(w => w.id === selectedId) ?? null

  const load = useCallback(async () => {
    try { setWips(await fetchWIPs()); setApiError('') }
    catch { setApiError('Cannot reach API — is the backend running?') }
  }, [])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) { setSelectedId(id); setMode('detail') }

  function handleCreated(wip: WIPItem) {
    setWips(ws => [wip, ...ws])
    setSelectedId(wip.id)
    setMode('detail')
  }

  function handleProgressUpdate(updated: WIPItem) {
    setWips(ws => ws.map(w => w.id === updated.id ? updated : w))
  }

  async function handleDelete(id: string) {
    try {
      await deleteWIP(id)
      setWips(ws => ws.filter(w => w.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch { setApiError('Failed to delete — check connection') }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <WIPList
        wips={wips}
        selectedId={selectedId}
        onSelect={handleSelect}
        onNew={() => { setSelectedId(null); setMode('create') }}
      />
      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg">
            {apiError}
          </div>
        )}
        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">📋</span>
            <p>Select a WIP or create one</p>
          </div>
        )}
        {mode === 'detail' && selected && (
          <WIPDetail
            wip={selected}
            onProgressUpdate={handleProgressUpdate}
            onDelete={handleDelete}
          />
        )}
        {mode === 'create' && (
          <WIPForm
            onCreated={handleCreated}
            onCancel={() => setMode('empty')}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: TypeScript check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/wip/ frontend/src/pages/work/WipBuilder.tsx
git commit -m "feat(wip): WipBuilder page + 4 components with progress slider + daily log"
```

---

## Task 8: Discord Notify Page

**Files:**
- Replace: `frontend/src/pages/work/DiscordNotify.tsx`

- [ ] **Step 1: Replace `frontend/src/pages/work/DiscordNotify.tsx`**

```tsx
import { useState, useEffect, useCallback } from 'react'
import { Send, Settings, Zap, Check } from 'lucide-react'
import type { DiscordSettings } from '../../types'
import { fetchDiscordSettings, saveDiscordSettings, sendDiscordMessage, checkDiscordRules } from '../../api/discord'

type Tab = 'manual' | 'rules' | 'settings'

const PREFIX_OPTIONS = [
  { value: '',        label: '(no prefix)' },
  { value: '✅ ',    label: '✅ Done' },
  { value: '⚠️ ',   label: '⚠️ Alert' },
  { value: '📊 ',   label: '📊 Report' },
  { value: '🔔 ',   label: '🔔 Reminder' },
]

export default function DiscordNotify() {
  const [tab,          setTab]          = useState<Tab>('manual')
  const [settings,     setSettings]     = useState<DiscordSettings | null>(null)
  const [webhookInput, setWebhookInput] = useState('')
  const [message,      setMessage]      = useState('')
  const [prefix,       setPrefix]       = useState('')
  const [status,       setStatus]       = useState('')   // inline feedback
  const [error,        setError]        = useState('')
  const [saving,       setSaving]       = useState(false)

  const load = useCallback(async () => {
    try {
      const s = await fetchDiscordSettings()
      setSettings(s)
      setWebhookInput(s.webhook_url ?? '')
    } catch { setError('Cannot reach API') }
  }, [])

  useEffect(() => { load() }, [load])

  // Auto-check when visiting Rules tab and webhook is set
  useEffect(() => {
    if (tab === 'rules' && settings?.webhook_url) {
      checkDiscordRules().catch(() => {/* silent — webhook might be invalid */})
    }
  }, [tab, settings?.webhook_url])

  async function handleSend() {
    if (!message.trim()) { setError('Message is empty'); return }
    if (!settings?.webhook_url) { setError('Set webhook URL in Settings first'); return }
    setError(''); setSaving(true)
    try {
      await sendDiscordMessage(prefix + message.trim())
      setStatus('Sent! ✓')
      setMessage('')
      setTimeout(() => setStatus(''), 3000)
    } catch { setError('Failed to send — check webhook URL') }
    finally { setSaving(false) }
  }

  async function handleSaveSettings() {
    setSaving(true); setError('')
    try {
      const updated = await saveDiscordSettings({ webhook_url: webhookInput || null })
      setSettings(updated)
      setStatus('Saved! ✓')
      setTimeout(() => setStatus(''), 3000)
    } catch { setError('Failed to save settings') }
    finally { setSaving(false) }
  }

  async function handleTest() {
    if (!webhookInput) { setError('Enter webhook URL first'); return }
    setSaving(true); setError('')
    try {
      // Save first, then send test
      const updated = await saveDiscordSettings({ webhook_url: webhookInput })
      setSettings(updated)
      await sendDiscordMessage('🔔 Leonie webhook test — OK')
      setStatus('Test sent! ✓')
      setTimeout(() => setStatus(''), 3000)
    } catch { setError('Test failed — check webhook URL') }
    finally { setSaving(false) }
  }

  async function handleToggleRule(rule: 'rule_overdue' | 'rule_done' | 'rule_summary') {
    if (!settings) return
    const updated = { ...settings, [rule]: !settings[rule] }
    setSettings(updated)
    try {
      const saved = await saveDiscordSettings(updated)
      setSettings(saved)
    } catch { setError('Failed to save rule') }
  }

  const tabCls = (t: Tab) =>
    `flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-all ${
      tab === t
        ? 'border-work text-work'
        : 'border-transparent text-gray-500 hover:text-gray-300'
    }`

  const fmtDate = (iso: string | null) => {
    if (!iso) return 'Never'
    return new Date(iso).toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
  }

  return (
    <div className="flex-1 p-5 overflow-y-auto max-w-xl">
      <h1 className="text-base font-semibold text-white mb-4">Discord Notify</h1>

      {!settings?.webhook_url && tab !== 'settings' && (
        <div className="bg-warning/5 border border-warning/20 text-warning text-xs px-3 py-2 rounded-lg mb-4">
          ⚠️ Webhook URL not set — go to <button className="underline" onClick={() => setTab('settings')}>Settings</button> first.
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-white/5 mb-5">
        <button className={tabCls('manual')}  onClick={() => setTab('manual')}>
          <Send size={12} /> Manual
        </button>
        <button className={tabCls('rules')}   onClick={() => setTab('rules')}>
          <Zap size={12} /> Auto Rules
        </button>
        <button className={tabCls('settings')} onClick={() => setTab('settings')}>
          <Settings size={12} /> Settings
        </button>
      </div>

      {error  && <p className="text-danger text-xs mb-3">{error}</p>}
      {status && <p className="text-work text-xs mb-3">{status}</p>}

      {/* ── Manual Tab ── */}
      {tab === 'manual' && (
        <div>
          <div className="mb-3">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Prefix</label>
            <select className="input-base" value={prefix} onChange={e => setPrefix(e.target.value)}>
              {PREFIX_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="mb-4">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Message</label>
            <textarea
              className="input-base resize-none"
              rows={5}
              placeholder="Nhập nội dung notification..."
              value={message}
              onChange={e => setMessage(e.target.value)}
            />
          </div>
          {message && (
            <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2 mb-4">
              <p className="text-[10px] text-gray-600 mb-1">Preview</p>
              <p className="text-xs text-gray-300 whitespace-pre-wrap">{prefix}{message}</p>
            </div>
          )}
          <button
            onClick={handleSend}
            disabled={saving}
            className="btn-primary w-full flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Send size={13} /> {saving ? 'Sending...' : 'Send to Discord'}
          </button>
        </div>
      )}

      {/* ── Rules Tab ── */}
      {tab === 'rules' && settings && (
        <div>
          <p className="text-xs text-gray-500 mb-4">
            Last checked: <span className="text-gray-400">{fmtDate(settings.last_checked)}</span>
          </p>

          {[
            { key: 'rule_overdue' as const, label: 'Task quá deadline', desc: 'Gửi danh sách task chưa done đã quá due_date' },
            { key: 'rule_done'    as const, label: 'Task → Done',        desc: 'Notify mỗi khi có task chuyển sang Done' },
            { key: 'rule_summary' as const, label: 'Daily summary',      desc: 'Tóm tắt hàng ngày (cần mở app)' },
          ].map(({ key, label, desc }) => (
            <div
              key={key}
              className="flex items-center justify-between gap-4 py-3 border-b border-white/5"
            >
              <div>
                <p className="text-sm text-white">{label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
              </div>
              <button
                onClick={() => handleToggleRule(key)}
                className={`w-10 h-5 rounded-full transition-all flex-shrink-0 relative ${
                  settings[key] ? 'bg-work' : 'bg-white/10'
                }`}
              >
                <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all ${
                  settings[key] ? 'left-5' : 'left-0.5'
                }`} />
              </button>
            </div>
          ))}

          <button
            onClick={() => {
              if (!settings.webhook_url) { setError('Set webhook URL first'); return }
              checkDiscordRules()
                .then(r => setStatus(`Check done — ${r.sent} notification(s) sent`))
                .catch(() => setError('Check failed'))
            }}
            className="btn-ghost w-full mt-4 flex items-center justify-center gap-1.5 text-xs"
          >
            <Check size={12} /> Run check now
          </button>
        </div>
      )}

      {/* ── Settings Tab ── */}
      {tab === 'settings' && (
        <div>
          <div className="mb-4">
            <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">
              Discord Webhook URL
            </label>
            <input
              className="input-base font-mono text-xs"
              placeholder="https://discord.com/api/webhooks/..."
              value={webhookInput}
              onChange={e => setWebhookInput(e.target.value)}
            />
            <p className="text-[11px] text-gray-600 mt-1.5">
              Server Settings → Integrations → Webhooks → Copy URL
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="btn-primary flex-1 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Check size={13} /> {saving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={handleTest}
              disabled={saving}
              className="btn-ghost flex-1 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Send size={13} /> Test
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: TypeScript check**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Run full backend test suite one last time**

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v
```
Expected: all 53 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/work/DiscordNotify.tsx
git commit -m "feat(discord): DiscordNotify page — Manual, Auto Rules, Settings tabs"
```

---

## Final Check

- [ ] Start both servers: `run.bat` (or `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev`)
- [ ] Visit http://localhost:5177 → check EDA Tracker, WIP Builder, Discord Notify all render
- [ ] Create one EDA request end-to-end: New → fill form → Save → Edit → Delete
- [ ] Create one WIP linked to an existing task → move slider → add log entry → delete log
- [ ] In Discord Notify Settings: enter a real webhook URL → Test → check Discord channel
