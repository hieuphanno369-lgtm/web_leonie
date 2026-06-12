# Task Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build full CRUD Task Manager — FastAPI backend + React frontend with list/detail-panel layout.

**Architecture:** FastAPI router (`/tasks`) backed by existing SQLite schema; React page with `TaskList` (left 340px) + `TaskDetail`/`TaskForm` (right flex-1) layout; Axios API client layer; Zustand NOT needed — local `useState` in `TaskManager.tsx` is sufficient.

**Tech Stack:** Python 3.13 / FastAPI / Pydantic v2 / SQLite · React 19 / TypeScript / Tailwind CSS / Axios · pytest + httpx TestClient

---

## File Map

```
backend/
  routers/
    __init__.py        CREATE  (empty, makes routers a package)
    tasks.py           CREATE  Pydantic models + CRUD endpoints
  tests/
    __init__.py        CREATE  (empty)
    conftest_tasks.py  CREATE  per-test fresh-DB fixture
    test_tasks.py      CREATE  pytest suite for all 5 endpoints
  main.py              MODIFY  include tasks router

frontend/src/
  api/
    tasks.ts           CREATE  fetchTasks / createTask / updateTask / deleteTask
  components/
    tasks/
      TaskItem.tsx     CREATE  single row (checkbox, title, badges, due date)
      TaskList.tsx     CREATE  filter tabs + search + scrollable list
      TaskDetail.tsx   CREATE  read-only detail panel (chips, notes, edit/delete)
      TaskForm.tsx     CREATE  create/edit inline form
  pages/work/
    TaskManager.tsx    REPLACE placeholder → root page (state + layout)
```

---

## Task 1 — Backend: test fixture + router scaffold

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/tasks.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest_tasks.py`

- [ ] **Step 1: Create routers package**

```
backend/routers/__init__.py   ← empty file
backend/tests/__init__.py     ← empty file
```

- [ ] **Step 2: Create test DB fixture**

Create `backend/tests/conftest_tasks.py`:

```python
"""Per-test SQLite fixture — patches get_connection default to use a fresh temp DB."""
import pytest
import database


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    database.create_tables(db_path)
    orig_defaults = database.get_connection.__defaults__
    database.get_connection.__defaults__ = (db_path,)
    yield db_path
    database.get_connection.__defaults__ = orig_defaults
```

- [ ] **Step 3: Create router scaffold (no logic yet)**

Create `backend/routers/tasks.py`:

```python
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/tasks", tags=["tasks"])

# ── Types ────────────────────────────────────────────────────────────────────

TaskStatus   = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]
TaskRecurring = Literal["daily", "weekly"]


class TaskCreate(BaseModel):
    title: str
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    due_date: str | None = None
    recurring: TaskRecurring | None = None
    notes: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: str | None = None
    recurring: TaskRecurring | None = None
    notes: str | None = None


class TaskOut(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    due_date: str | None
    recurring: str | None
    notes: str | None
    created: str
    updated: str


def _row(row) -> TaskOut:
    return TaskOut(**dict(row))
```

- [ ] **Step 4: Commit scaffold**

```bash
git add backend/routers/ backend/tests/
git commit -m "feat(tasks): router scaffold + test DB fixture"
```

---

## Task 2 — Backend: GET /tasks + POST /tasks

**Files:**
- Modify: `backend/routers/tasks.py` (add list + create endpoints)
- Create: `backend/tests/test_tasks.py`

- [ ] **Step 1: Write failing tests for list + create**

Create `backend/tests/test_tasks.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


# ── List ─────────────────────────────────────────────────────────────────────

def test_list_empty(client):
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_created_tasks(client):
    client.post("/tasks", json={"title": "A"})
    client.post("/tasks", json={"title": "B"})
    assert len(client.get("/tasks").json()) == 2


def test_list_filter_by_status(client):
    client.post("/tasks", json={"title": "Todo task",  "status": "todo"})
    client.post("/tasks", json={"title": "Done task",  "status": "done"})
    data = client.get("/tasks?status=todo").json()
    assert len(data) == 1
    assert data[0]["title"] == "Todo task"


# ── Create ───────────────────────────────────────────────────────────────────

def test_create_minimal(client):
    resp = client.post("/tasks", json={"title": "Do something"})
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"]    == "Do something"
    assert d["status"]   == "todo"
    assert d["priority"] == "medium"
    assert d["id"]


def test_create_full(client):
    resp = client.post("/tasks", json={
        "title": "Full task", "status": "in_progress", "priority": "high",
        "due_date": "2026-05-20", "recurring": "daily", "notes": "note",
    })
    assert resp.status_code == 201
    d = resp.json()
    assert d["status"]    == "in_progress"
    assert d["due_date"]  == "2026-05-20"
    assert d["recurring"] == "daily"
    assert d["notes"]     == "note"
```

- [ ] **Step 2: Run tests — confirm FAIL**

```
cd backend
.venv\Scripts\python.exe -m pytest tests/test_tasks.py -v
```
Expected: `AttributeError` or `404` — endpoints not implemented yet.

- [ ] **Step 3: Implement list + create in `backend/routers/tasks.py`**

Append after `def _row`:

```python
@router.get("", response_model=list[TaskOut])
def list_tasks(status: str | None = Query(default=None)):
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created DESC"
        ).fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate):
    conn = get_connection()
    conn.execute(
        """INSERT INTO tasks (title, status, priority, due_date, recurring, notes)
           VALUES (:title, :status, :priority, :due_date, :recurring, :notes)""",
        body.model_dump(),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM tasks ORDER BY created DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return _row(row)
```

- [ ] **Step 4: Wire router into `backend/main.py`** (needed for TestClient to find routes)

Replace `backend/main.py` content:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routers.tasks import router as tasks_router

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}
```

- [ ] **Step 5: Run tests — confirm PASS**

```
.venv\Scripts\python.exe -m pytest tests/test_tasks.py::test_list_empty tests/test_tasks.py::test_create_minimal tests/test_tasks.py::test_create_full tests/test_tasks.py::test_list_returns_created_tasks tests/test_tasks.py::test_list_filter_by_status -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/tasks.py backend/main.py backend/tests/test_tasks.py
git commit -m "feat(tasks): GET /tasks + POST /tasks with tests"
```

---

## Task 3 — Backend: GET /{id} + PATCH /{id} + DELETE /{id}

**Files:**
- Modify: `backend/routers/tasks.py` (3 new endpoints)
- Modify: `backend/tests/test_tasks.py` (add tests)

- [ ] **Step 1: Write failing tests — append to `backend/tests/test_tasks.py`**

```python
# ── Get by ID ────────────────────────────────────────────────────────────────

def test_get_task(client):
    created = client.post("/tasks", json={"title": "Get me"}).json()
    resp = client.get(f"/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_task_not_found(client):
    assert client.get("/tasks/does-not-exist").status_code == 404


# ── Patch ────────────────────────────────────────────────────────────────────

def test_patch_status(client):
    created = client.post("/tasks", json={"title": "Patch me"}).json()
    resp = client.patch(f"/tasks/{created['id']}", json={"status": "done"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["status"] == "done"
    assert d["title"]  == "Patch me"          # other fields unchanged


def test_patch_not_found(client):
    assert client.patch("/tasks/x", json={"status": "done"}).status_code == 404


def test_patch_empty_body_returns_task(client):
    created = client.post("/tasks", json={"title": "No change"}).json()
    resp = client.patch(f"/tasks/{created['id']}", json={})
    assert resp.status_code == 200
    assert resp.json()["title"] == "No change"


# ── Delete ───────────────────────────────────────────────────────────────────

def test_delete_task(client):
    created = client.post("/tasks", json={"title": "Delete me"}).json()
    resp = client.delete(f"/tasks/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_not_found(client):
    assert client.delete("/tasks/does-not-exist").status_code == 404
```

- [ ] **Step 2: Run — confirm FAIL**

```
.venv\Scripts\python.exe -m pytest tests/test_tasks.py -k "get_task or patch or delete" -v
```
Expected: FAIL (endpoints 404 — not implemented).

- [ ] **Step 3: Implement the 3 endpoints — append to `backend/routers/tasks.py`**

```python
@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _row(row)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskUpdate):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    updates = body.model_dump(exclude_unset=True)
    if updates:
        set_parts = [f"{k} = ?" for k in updates]
        set_parts.append("updated = datetime('now')")
        values = list(updates.values()) + [task_id]
        conn.execute(
            f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = ?", values
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    conn.close()
    return _row(row)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
```

- [ ] **Step 4: Run full suite — all pass**

```
.venv\Scripts\python.exe -m pytest tests/test_tasks.py -v
```
Expected: 12 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/tasks.py backend/tests/test_tasks.py
git commit -m "feat(tasks): GET/PATCH/DELETE /{id} with tests — backend complete"
```

---

## Task 4 — Frontend: API client `api/tasks.ts`

**Files:**
- Create: `frontend/src/api/tasks.ts`

- [ ] **Step 1: Create `frontend/src/api/tasks.ts`**

```typescript
import client from './client'
import type { Task, TaskStatus } from '../types'

export interface TaskPayload {
  title: string
  status?: TaskStatus
  priority?: 'low' | 'medium' | 'high'
  due_date?: string | null
  recurring?: 'daily' | 'weekly' | null
  notes?: string | null
}

export async function fetchTasks(status?: TaskStatus): Promise<Task[]> {
  const params = status ? { status } : {}
  const { data } = await client.get<Task[]>('/tasks', { params })
  return data
}

export async function createTask(body: TaskPayload): Promise<Task> {
  const { data } = await client.post<Task>('/tasks', body)
  return data
}

export async function updateTask(id: string, body: Partial<TaskPayload>): Promise<Task> {
  const { data } = await client.patch<Task>(`/tasks/${id}`, body)
  return data
}

export async function deleteTask(id: string): Promise<void> {
  await client.delete(`/tasks/${id}`)
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/tasks.ts
git commit -m "feat(tasks): frontend API client"
```

---

## Task 5 — Frontend: `TaskItem.tsx` + `TaskList.tsx`

**Files:**
- Create: `frontend/src/components/tasks/TaskItem.tsx`
- Create: `frontend/src/components/tasks/TaskList.tsx`

- [ ] **Step 1: Create `frontend/src/components/tasks/TaskItem.tsx`**

```tsx
import { CheckSquare, Square, Circle } from 'lucide-react'
import type { Task } from '../../types'

interface Props {
  task: Task
  isSelected: boolean
  onSelect: () => void
  onToggleDone: () => void
}

export default function TaskItem({ task, isSelected, onSelect, onToggleDone }: Props) {
  const isDone = task.status === 'done'

  return (
    <div
      onClick={onSelect}
      className={`flex items-start gap-2 px-3 py-2 rounded-lg cursor-pointer border mb-0.5 transition-all
        ${isSelected ? 'bg-work/5 border-work/30' : 'border-transparent hover:bg-white/5 hover:border-white/5'}
        ${isDone ? 'opacity-45' : ''}`}
    >
      <button
        onClick={e => { e.stopPropagation(); onToggleDone() }}
        className="mt-0.5 flex-shrink-0 text-gray-500 hover:text-work transition-colors"
      >
        {isDone
          ? <CheckSquare size={14} className="text-work" />
          : task.status === 'in_progress'
            ? <Circle size={14} className="text-data fill-data/20" />
            : <Square size={14} />}
      </button>

      <div className="flex-1 min-w-0">
        <p className={`text-xs truncate ${isDone ? 'line-through text-gray-500' : 'text-gray-200'}`}>
          {task.title}
        </p>
        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
          <PriorityBadge priority={task.priority} />
          {task.recurring && (
            <span className="badge bg-learn/15 text-learn">{task.recurring}</span>
          )}
          {task.due_date && !isDone && <DueDate date={task.due_date} />}
        </div>
      </div>
    </div>
  )
}

function PriorityBadge({ priority }: { priority: Task['priority'] }) {
  const cls = {
    high:   'bg-warning/15 text-warning',
    medium: 'bg-data/15 text-data',
    low:    'bg-white/5 text-gray-500',
  }[priority]
  return <span className={`badge ${cls}`}>{priority}</span>
}

function DueDate({ date }: { date: string }) {
  const due = new Date(date + 'T00:00:00')
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const overdue = due < today
  const label = due.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
  return (
    <span className={`text-[10px] ${overdue ? 'text-danger' : 'text-gray-600'}`}>
      {overdue ? '⚠ ' : ''}{label}
    </span>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/tasks/TaskList.tsx`**

```tsx
import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { Task, TaskStatus } from '../../types'
import TaskItem from './TaskItem'

type FilterTab = 'all' | TaskStatus

interface Props {
  tasks: Task[]
  selectedId: string | null
  onSelect: (id: string) => void
  onToggleDone: (id: string) => void
  onNewTask: () => void
}

export default function TaskList({ tasks, selectedId, onSelect, onToggleDone, onNewTask }: Props) {
  const [filter, setFilter] = useState<FilterTab>('all')
  const [search, setSearch] = useState('')

  const visible = tasks.filter(t => {
    if (filter !== 'all' && t.status !== filter) return false
    if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const count = (f: FilterTab) =>
    f === 'all' ? tasks.length : tasks.filter(t => t.status === f).length

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all',         label: 'All' },
    { key: 'todo',        label: 'Todo' },
    { key: 'in_progress', label: 'In Progress' },
    { key: 'done',        label: 'Done' },
  ]

  return (
    <div className="w-[340px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">Tasks</h2>
          <button onClick={onNewTask} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
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

      {/* Search */}
      <div className="mx-3 my-2">
        <input
          className="input-base text-xs"
          placeholder="Search tasks..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {visible.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No tasks found</p>
        ) : (
          visible.map(task => (
            <TaskItem
              key={task.id}
              task={task}
              isSelected={task.id === selectedId}
              onSelect={() => onSelect(task.id)}
              onToggleDone={() => onToggleDone(task.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify TypeScript**

```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/tasks/
git commit -m "feat(tasks): TaskItem + TaskList components"
```

---

## Task 6 — Frontend: `TaskDetail.tsx` + `TaskForm.tsx`

**Files:**
- Create: `frontend/src/components/tasks/TaskDetail.tsx`
- Create: `frontend/src/components/tasks/TaskForm.tsx`

- [ ] **Step 1: Create `frontend/src/components/tasks/TaskDetail.tsx`**

```tsx
import { useState } from 'react'
import { Pencil, Trash2 } from 'lucide-react'
import type { Task } from '../../types'

interface Props {
  task: Task
  onEdit: () => void
  onDelete: (id: string) => void
}

export default function TaskDetail({ task, onEdit, onDelete }: Props) {
  const [confirmDelete, setConfirmDelete] = useState(false)

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

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      {/* Title + actions */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h2 className="text-base font-semibold text-white leading-snug">{task.title}</h2>
        <div className="flex gap-2 flex-shrink-0">
          <button onClick={onEdit} className="btn-ghost flex items-center gap-1 text-xs px-2.5 py-1">
            <Pencil size={12} /> Edit
          </button>
          {confirmDelete ? (
            <button
              onClick={() => onDelete(task.id)}
              className="btn-danger flex items-center gap-1 text-xs px-2.5 py-1"
            >
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

      {/* Chips */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        <span className={`badge border ${statusCls[task.status]}`}>
          {task.status.replace('_', ' ')}
        </span>
        <span className={`badge border ${priorityCls[task.priority]}`}>
          {task.priority} priority
        </span>
        {task.due_date && (
          <span className="badge bg-white/5 text-gray-400 border border-white/10">
            📅 {fmtDate(task.due_date)}
          </span>
        )}
        {task.recurring && (
          <span className="badge bg-learn/10 text-learn border border-learn/25">
            🔁 {task.recurring}
          </span>
        )}
      </div>

      <hr className="border-white/5 mb-4" />

      {/* Notes */}
      <div className="mb-4">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Notes</p>
        <div className="bg-secondary border border-white/5 rounded-lg px-3 py-2.5 text-xs text-gray-400 leading-relaxed min-h-[72px] whitespace-pre-wrap">
          {task.notes ?? <span className="italic text-gray-600">No notes</span>}
        </div>
      </div>

      {/* Meta */}
      <div>
        <p className="text-[10px] uppercase tracking-widest text-gray-600 mb-2">Info</p>
        <p className="text-xs text-gray-500 mb-1">Created: <span className="text-gray-400">{fmtDate(task.created)}</span></p>
        <p className="text-xs text-gray-500">Updated: <span className="text-gray-400">{fmtDate(task.updated)}</span></p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/tasks/TaskForm.tsx`**

```tsx
import { useState } from 'react'
import { Check, X } from 'lucide-react'
import type { Task, TaskStatus } from '../../types'
import type { TaskPayload } from '../../api/tasks'

interface Props {
  initial?: Task          // undefined → create mode
  onSave: (payload: TaskPayload) => Promise<void>
  onCancel: () => void
}

export default function TaskForm({ initial, onSave, onCancel }: Props) {
  const [title,     setTitle]     = useState(initial?.title     ?? '')
  const [status,    setStatus]    = useState<TaskStatus>(initial?.status   ?? 'todo')
  const [priority,  setPriority]  = useState<Task['priority']>(initial?.priority ?? 'medium')
  const [dueDate,   setDueDate]   = useState(initial?.due_date  ?? '')
  const [recurring, setRecurring] = useState(initial?.recurring ?? '')
  const [notes,     setNotes]     = useState(initial?.notes     ?? '')
  const [error,     setError]     = useState('')
  const [saving,    setSaving]    = useState(false)

  async function handleSubmit() {
    if (!title.trim()) { setError('Title is required'); return }
    setError('')
    setSaving(true)
    try {
      await onSave({
        title:     title.trim(),
        status,
        priority,
        due_date:  dueDate   || null,
        recurring: (recurring as 'daily' | 'weekly') || null,
        notes:     notes     || null,
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
        {initial ? '✏️ Edit Task' : '＋ New Task'}
      </h2>

      {/* Title */}
      <div className="mb-3">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">
          Title *
        </label>
        <input
          className="input-base"
          placeholder="What needs to be done?"
          value={title}
          onChange={e => setTitle(e.target.value)}
          autoFocus
        />
      </div>

      {/* Status + Priority */}
      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Status</label>
          <select className="input-base" value={status} onChange={e => setStatus(e.target.value as TaskStatus)}>
            <option value="todo">Todo</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Priority</label>
          <select className="input-base" value={priority} onChange={e => setPriority(e.target.value as Task['priority'])}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      {/* Due date + Recurring */}
      <div className="flex gap-3 mb-3">
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Due date</label>
          <input
            type="date"
            className="input-base"
            value={dueDate}
            onChange={e => setDueDate(e.target.value)}
          />
        </div>
        <div className="flex-1">
          <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Recurring</label>
          <select className="input-base" value={recurring} onChange={e => setRecurring(e.target.value)}>
            <option value="">None</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>
      </div>

      {/* Notes */}
      <div className="mb-4">
        <label className="block text-[10px] uppercase tracking-widest text-gray-600 mb-1.5">Notes</label>
        <textarea
          className="input-base resize-none"
          rows={4}
          placeholder="Optional notes..."
          value={notes}
          onChange={e => setNotes(e.target.value)}
        />
      </div>

      {error && <p className="text-danger text-xs mb-3">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={saving}
        className="btn-primary w-full mb-2 flex items-center justify-center gap-1.5 disabled:opacity-50"
      >
        <Check size={13} /> {saving ? 'Saving...' : 'Save Task'}
      </button>
      <button onClick={onCancel} className="btn-ghost w-full flex items-center justify-center gap-1.5">
        <X size={13} /> Cancel
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Verify TypeScript**

```
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/tasks/
git commit -m "feat(tasks): TaskDetail + TaskForm components"
```

---

## Task 7 — Frontend: `TaskManager.tsx` — wire everything

**Files:**
- Replace: `frontend/src/pages/work/TaskManager.tsx`

- [ ] **Step 1: Replace placeholder with full implementation**

```tsx
import { useEffect, useState, useCallback } from 'react'
import type { Task } from '../../types'
import { fetchTasks, createTask, updateTask, deleteTask } from '../../api/tasks'
import type { TaskPayload } from '../../api/tasks'
import TaskList   from '../../components/tasks/TaskList'
import TaskDetail from '../../components/tasks/TaskDetail'
import TaskForm   from '../../components/tasks/TaskForm'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function TaskManager() {
  const [tasks,      setTasks]      = useState<Task[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const selectedTask = tasks.find(t => t.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      const data = await fetchTasks()
      setTasks(data)
      setApiError('')
    } catch {
      setApiError('Cannot reach API — is the backend running?')
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── Handlers ───────────────────────────────────────────────────────────────

  function handleSelect(id: string) {
    setSelectedId(id)
    setMode('detail')
  }

  async function handleToggleDone(id: string) {
    const task = tasks.find(t => t.id === id)
    if (!task) return
    const newStatus = task.status === 'done' ? 'todo' : 'done'
    const updated = await updateTask(id, { status: newStatus })
    setTasks(ts => ts.map(t => t.id === id ? updated : t))
  }

  async function handleSave(payload: TaskPayload) {
    if (mode === 'create') {
      const created = await createTask(payload)
      setTasks(ts => [created, ...ts])
      setSelectedId(created.id)
      setMode('detail')
    } else if (mode === 'edit' && selectedId) {
      const updated = await updateTask(selectedId, payload)
      setTasks(ts => ts.map(t => t.id === selectedId ? updated : t))
      setMode('detail')
    }
  }

  async function handleDelete(id: string) {
    await deleteTask(id)
    setTasks(ts => ts.filter(t => t.id !== id))
    setSelectedId(null)
    setMode('empty')
  }

  function handleCancel() {
    setMode(selectedTask ? 'detail' : 'empty')
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden">
      <TaskList
        tasks={tasks}
        selectedId={selectedId}
        onSelect={handleSelect}
        onToggleDone={handleToggleDone}
        onNewTask={() => { setSelectedId(null); setMode('create') }}
      />

      <div className="flex-1 flex overflow-hidden">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg">
            {apiError}
          </div>
        )}

        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">☐</span>
            <p>Select a task or create one</p>
          </div>
        )}

        {mode === 'detail' && selectedTask && (
          <TaskDetail
            task={selectedTask}
            onEdit={() => setMode('edit')}
            onDelete={handleDelete}
          />
        )}

        {(mode === 'create' || mode === 'edit') && (
          <TaskForm
            initial={mode === 'edit' ? (selectedTask ?? undefined) : undefined}
            onSave={handleSave}
            onCancel={handleCancel}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript — no errors**

```
npx tsc --noEmit
```

- [ ] **Step 3: Manual smoke test**

Start backend:
```
cd backend
.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

Start frontend (separate terminal):
```
cd frontend
npm run dev
```

Open http://localhost:5177/work/tasks — verify:
1. Empty state shows "Select a task or create one"
2. Click "+ New" → form appears on the right
3. Fill title + priority → Save → task appears in list
4. Click task row → detail panel shows
5. Click "Edit" → form pre-filled
6. Click checkbox → status toggles
7. Click 🗑 twice → task deleted

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/work/TaskManager.tsx
git commit -m "feat(tasks): wire TaskManager page — SP2 complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ List + filter tabs (All/Todo/In Progress/Done) → TaskList.tsx
- ✅ Search → TaskList.tsx `search` state
- ✅ Click task → detail panel → handleSelect
- ✅ Click checkbox → toggle done → handleToggleDone
- ✅ "+ New Task" → create form → handleSave (create branch)
- ✅ Edit button → edit form → handleSave (edit branch)
- ✅ Delete (2-click confirm) → handleDelete
- ✅ Backend CRUD: GET, POST, PATCH, DELETE all implemented + tested
- ✅ Due date overdue indicator → DueDate component
- ✅ Recurring badge → TaskItem
- ✅ Error handling → apiError banner + form error message

**No placeholders:** all code blocks are complete and runnable.

**Type consistency:**
- `TaskPayload` defined in `api/tasks.ts`, imported in `TaskForm.tsx` and `TaskManager.tsx` ✅
- `Task` type from `types.ts` used consistently ✅
- `PanelMode` type local to `TaskManager.tsx` ✅
- `fetchTasks / createTask / updateTask / deleteTask` named consistently across plan ✅
