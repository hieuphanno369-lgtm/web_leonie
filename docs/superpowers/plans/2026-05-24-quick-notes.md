# Quick Notes / Daily Log — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/work/notes` page where the user can create, filter, and link daily notes to tasks or EDA requests, persisted in SQLite.

**Architecture:** New `quick_notes` table in `leonie.db`, a FastAPI `/notes` router following the same pattern as `/tasks`, and a React page (`QuickNotes`) with list+side-panel layout matching `TaskManager`/`WipBuilder`.

**Tech Stack:** Python 3.11 · FastAPI · SQLite (sqlite3) · Pydantic v2 · pytest · React 18 · TypeScript · Tailwind CSS · Lucide React · Axios

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/database.py` | Add `_migrate_v3()` with `quick_notes` table |
| Create | `backend/routers/notes.py` | CRUD + filter endpoints for `/notes` |
| Modify | `backend/main.py` | Mount notes router |
| Create | `backend/tests/test_notes.py` | All backend tests |
| Modify | `frontend/src/types.ts` | Add `QuickNote` interface |
| Create | `frontend/src/api/notes.ts` | fetch helpers |
| Create | `frontend/src/components/notes/NoteItem.tsx` | Single row in list |
| Create | `frontend/src/components/notes/NoteList.tsx` | List + date/category filter header |
| Create | `frontend/src/components/notes/NoteForm.tsx` | Create/edit form |
| Create | `frontend/src/components/notes/NoteDetail.tsx` | Read-only detail panel |
| Create | `frontend/src/pages/work/QuickNotes.tsx` | Page: state, layout, handlers |
| Modify | `frontend/src/App.tsx` | Add `work/notes` route |
| Modify | `frontend/src/components/layout/Sidebar.tsx` | Add "Quick Notes" nav item |

---

## Task 1: DB Migration

**Files:**
- Modify: `backend/database.py`
- Test: `backend/tests/test_database.py` (already exists — add one assertion)

- [ ] **Step 1: Write a failing test**

Open `backend/tests/test_database.py`. Add at the end:

```python
def test_quick_notes_table_exists(fresh_db):
    import database
    conn = database.get_connection()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "quick_notes" in tables
```

- [ ] **Step 2: Run to verify it fails**

```
cd backend
python -m pytest tests/test_database.py::test_quick_notes_table_exists -v
```

Expected: `FAILED` — `quick_notes` not in tables.

- [ ] **Step 3: Implement migration**

In `backend/database.py`, after the existing `_migrate_v2` call at line 109, add a call to `_migrate_v3`. Then append the function:

```python
    _migrate_v2(conn)
    _migrate_v3(conn)
    conn.close()
```

Add at the end of the file:

```python
def _migrate_v3(conn) -> None:
    """Safe idempotent migrations for v3 schema additions."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS quick_notes (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title     TEXT,
            content   TEXT NOT NULL,
            date      TEXT NOT NULL,
            category  TEXT,
            task_id   TEXT REFERENCES tasks(id) ON DELETE SET NULL,
            eda_id    TEXT REFERENCES eda_requests(id) ON DELETE SET NULL,
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest tests/test_database.py::test_quick_notes_table_exists -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/tests/test_database.py
git commit -m "feat(notes): add quick_notes table migration"
```

---

## Task 2: Backend Router — Tests First

**Files:**
- Create: `backend/tests/test_notes.py`
- Create: `backend/routers/notes.py`

- [ ] **Step 1: Create the test file**

Create `backend/tests/test_notes.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


# ── helpers ──────────────────────────────────────────────────────────────────

def _note(client, **kwargs):
    body = {"content": "test content", "date": "2026-05-24", **kwargs}
    return client.post("/notes", json=body)


# ── List ─────────────────────────────────────────────────────────────────────

def test_list_notes_empty(client):
    resp = client.get("/notes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_created_notes(client):
    _note(client)
    _note(client)
    assert len(client.get("/notes").json()) == 2


# ── Create ───────────────────────────────────────────────────────────────────

def test_create_note_minimal(client):
    resp = _note(client)
    assert resp.status_code == 201
    d = resp.json()
    assert d["content"] == "test content"
    assert d["date"] == "2026-05-24"
    assert d["title"] is None
    assert d["category"] is None
    assert d["task_id"] is None
    assert d["eda_id"] is None
    assert d["id"]


def test_create_note_full(client):
    resp = _note(client, title="Stand-up", category="daily")
    assert resp.status_code == 201
    d = resp.json()
    assert d["title"] == "Stand-up"
    assert d["category"] == "daily"


def test_create_note_missing_content_422(client):
    resp = client.post("/notes", json={"date": "2026-05-24"})
    assert resp.status_code == 422


def test_create_note_missing_date_422(client):
    resp = client.post("/notes", json={"content": "hello"})
    assert resp.status_code == 422


# ── FK validation ─────────────────────────────────────────────────────────────

def test_create_note_invalid_task_id_400(client):
    resp = _note(client, task_id="nonexistent-id")
    assert resp.status_code == 400
    assert "task_id" in resp.json()["detail"]


def test_create_note_invalid_eda_id_400(client):
    resp = _note(client, eda_id="nonexistent-id")
    assert resp.status_code == 400
    assert "eda_id" in resp.json()["detail"]


def test_create_note_valid_task_id(client):
    task = client.post("/tasks", json={"title": "Linked task"}).json()
    resp = _note(client, task_id=task["id"])
    assert resp.status_code == 201
    assert resp.json()["task_id"] == task["id"]


# ── Filters ───────────────────────────────────────────────────────────────────

def test_filter_by_date_range(client):
    _note(client, date="2026-05-20")
    _note(client, date="2026-05-23")
    _note(client, date="2026-05-25")
    data = client.get("/notes?date_from=2026-05-22&date_to=2026-05-24").json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-05-23"


def test_filter_by_category(client):
    _note(client, category="daily")
    _note(client, category="meeting")
    data = client.get("/notes?category=daily").json()
    assert len(data) == 1
    assert data[0]["category"] == "daily"


# ── Get / Patch / Delete ──────────────────────────────────────────────────────

def test_get_note(client):
    created = _note(client).json()
    resp = client.get(f"/notes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_note_not_found(client):
    assert client.get("/notes/does-not-exist").status_code == 404


def test_update_note(client):
    created = _note(client).json()
    resp = client.patch(f"/notes/{created['id']}", json={"title": "Updated"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["title"] == "Updated"
    assert d["content"] == "test content"   # unchanged
    assert d["updated"] >= d["created"]


def test_update_note_not_found(client):
    assert client.patch("/notes/x", json={"title": "X"}).status_code == 404


def test_delete_note(client):
    created = _note(client).json()
    resp = client.delete(f"/notes/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/notes/{created['id']}").status_code == 404


def test_delete_note_not_found(client):
    assert client.delete("/notes/does-not-exist").status_code == 404
```

- [ ] **Step 2: Run to verify all tests fail**

```
cd backend
python -m pytest tests/test_notes.py -v
```

Expected: all tests fail with import error (router not mounted yet).

- [ ] **Step 3: Create the router**

Create `backend/routers/notes.py`:

```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreate(BaseModel):
    title: str | None = None
    content: str
    date: str
    category: str | None = None
    task_id: str | None = None
    eda_id: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    date: str | None = None
    category: str | None = None
    task_id: str | None = None
    eda_id: str | None = None


class NoteOut(BaseModel):
    id: str
    title: str | None
    content: str
    date: str
    category: str | None
    task_id: str | None
    eda_id: str | None
    created: str
    updated: str


def _row(row) -> NoteOut:
    return NoteOut(**dict(row))


def _check_fk(conn, task_id: str | None, eda_id: str | None) -> None:
    if task_id:
        exists = conn.execute(
            "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=400, detail="Invalid task_id: not found")
    if eda_id:
        exists = conn.execute(
            "SELECT 1 FROM eda_requests WHERE id = ?", (eda_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=400, detail="Invalid eda_id: not found")


@router.get("", response_model=list[NoteOut])
def list_notes(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    category: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    eda_id: str | None = Query(default=None),
):
    conn = get_connection()
    sql = "SELECT * FROM quick_notes WHERE 1=1"
    params: list = []
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if task_id:
        sql += " AND task_id = ?"
        params.append(task_id)
    if eda_id:
        sql += " AND eda_id = ?"
        params.append(eda_id)
    sql += " ORDER BY date DESC, created DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.post("", response_model=NoteOut, status_code=201)
def create_note(body: NoteCreate):
    conn = get_connection()
    _check_fk(conn, body.task_id, body.eda_id)
    cursor = conn.execute(
        """INSERT INTO quick_notes (title, content, date, category, task_id, eda_id)
           VALUES (:title, :content, :date, :category, :task_id, :eda_id)""",
        body.model_dump(),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM quick_notes WHERE rowid = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return _row(row)


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM quick_notes WHERE id = ?", (note_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return _row(row)


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(note_id: str, body: NoteUpdate):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM quick_notes WHERE id = ?", (note_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    _ALLOWED = {"title", "content", "date", "category", "task_id", "eda_id"}
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in _ALLOWED}
    if updates:
        set_parts = [f"{k} = ?" for k in updates]
        set_parts.append("updated = datetime('now')")
        values = list(updates.values()) + [note_id]
        conn.execute(
            f"UPDATE quick_notes SET {', '.join(set_parts)} WHERE id = ?", values
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM quick_notes WHERE id = ?", (note_id,)
        ).fetchone()
    conn.close()
    return _row(row)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM quick_notes WHERE id = ?", (note_id,))
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Mount the router in `backend/main.py`**

Add these two lines following the existing pattern (after `ml_router`):

```python
from routers.notes import router as notes_router
```

And in the `include_router` section:

```python
app.include_router(notes_router)
```

- [ ] **Step 5: Run all notes tests**

```
cd backend
python -m pytest tests/test_notes.py -v
```

Expected: all 18 tests `PASSED`.

- [ ] **Step 6: Run full suite to check no regressions**

```
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/notes.py backend/tests/test_notes.py backend/main.py
git commit -m "feat(notes): backend router with CRUD and date/category filters"
```

---

## Task 3: Frontend Types + API Helper

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/notes.ts`

- [ ] **Step 1: Add `QuickNote` to types**

Open `frontend/src/types.ts`. At the end of the file, append:

```typescript
// ─── Quick Notes ──────────────────────────────────────────────────────────────

export interface QuickNote {
  id: string
  title: string | null
  content: string
  date: string          // YYYY-MM-DD
  category: string | null
  task_id: string | null
  eda_id: string | null
  created: string
  updated: string
}
```

- [ ] **Step 2: Create `frontend/src/api/notes.ts`**

```typescript
import client from './client'
import type { QuickNote } from '../types'

export interface NoteParams {
  date_from?: string
  date_to?: string
  category?: string
  task_id?: string
  eda_id?: string
}

export interface NotePayload {
  title?: string | null
  content: string
  date: string
  category?: string | null
  task_id?: string | null
  eda_id?: string | null
}

export async function fetchNotes(params?: NoteParams): Promise<QuickNote[]> {
  const filtered = params
    ? Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    : {}
  const { data } = await client.get<QuickNote[]>('/notes', { params: filtered })
  return data
}

export async function createNote(body: NotePayload): Promise<QuickNote> {
  const { data } = await client.post<QuickNote>('/notes', body)
  return data
}

export async function updateNote(id: string, body: Partial<NotePayload>): Promise<QuickNote> {
  const { data } = await client.patch<QuickNote>(`/notes/${id}`, body)
  return data
}

export async function deleteNote(id: string): Promise<void> {
  await client.delete(`/notes/${id}`)
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend
npm run build 2>&1 | tail -20
```

Expected: no type errors related to notes.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/notes.ts
git commit -m "feat(notes): frontend types and API helper"
```

---

## Task 4: NoteItem Component

**Files:**
- Create: `frontend/src/components/notes/NoteItem.tsx`

- [ ] **Step 1: Create `frontend/src/components/notes/NoteItem.tsx`**

```typescript
import { Tag, Link2 } from 'lucide-react'
import type { QuickNote } from '../../types'

const CATEGORY_STYLES: Record<string, string> = {
  daily:   'text-green-400 bg-green-400/10 border-green-400/20',
  meeting: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  idea:    'text-purple-400 bg-purple-400/10 border-purple-400/20',
  bug:     'text-red-400 bg-red-400/10 border-red-400/20',
}

interface Props {
  note: QuickNote
  isSelected: boolean
  onSelect: () => void
}

export default function NoteItem({ note, isSelected, onSelect }: Props) {
  const categoryStyle = note.category
    ? (CATEGORY_STYLES[note.category] ?? 'text-gray-400 bg-gray-400/10 border-gray-400/20')
    : null

  const preview = note.title
    ?? (note.content.length > 60 ? note.content.slice(0, 60) + '…' : note.content)

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 transition-all ${
        isSelected
          ? 'bg-white/5 border border-white/10'
          : 'hover:bg-white/5 border border-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-white truncate flex-1">{preview}</p>
        {(note.task_id || note.eda_id) && (
          <Link2 size={11} className="text-gray-500 mt-0.5 flex-shrink-0" />
        )}
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-[11px] text-gray-500 font-mono">{note.date}</span>
        {note.category && categoryStyle && (
          <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${categoryStyle}`}>
            <Tag size={9} />
            {note.category}
          </span>
        )}
      </div>
    </button>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/notes/NoteItem.tsx
git commit -m "feat(notes): NoteItem component"
```

---

## Task 5: NoteList Component

**Files:**
- Create: `frontend/src/components/notes/NoteList.tsx`

- [ ] **Step 1: Create `frontend/src/components/notes/NoteList.tsx`**

```typescript
import { Plus } from 'lucide-react'
import type { QuickNote } from '../../types'
import NoteItem from './NoteItem'

interface Props {
  notes: QuickNote[]
  selectedId: string | null
  dateFrom: string
  dateTo: string
  category: string
  onSelect: (id: string) => void
  onNew: () => void
  onDateFromChange: (v: string) => void
  onDateToChange: (v: string) => void
  onCategoryChange: (v: string) => void
}

const CATEGORIES = ['', 'daily', 'meeting', 'idea', 'bug']

export default function NoteList({
  notes, selectedId, dateFrom, dateTo, category,
  onSelect, onNew, onDateFromChange, onDateToChange, onCategoryChange,
}: Props) {
  return (
    <div className="w-[340px] border-r border-white/5 flex flex-col flex-shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-3.5 pb-2.5 border-b border-white/5">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold text-white">Quick Notes</h2>
          <button onClick={onNew} className="btn-primary flex items-center gap-1 text-xs px-2.5 py-1">
            <Plus size={12} /> New
          </button>
        </div>
        {/* Date filter */}
        <div className="flex items-center gap-1.5 mb-1.5">
          <input
            type="date"
            value={dateFrom}
            onChange={e => onDateFromChange(e.target.value)}
            className="input-base text-[11px] flex-1 px-2 py-1"
          />
          <span className="text-gray-600 text-xs">→</span>
          <input
            type="date"
            value={dateTo}
            onChange={e => onDateToChange(e.target.value)}
            className="input-base text-[11px] flex-1 px-2 py-1"
          />
        </div>
        {/* Category filter */}
        <select
          value={category}
          onChange={e => onCategoryChange(e.target.value)}
          className="input-base text-[11px] w-full px-2 py-1"
        >
          <option value="">All categories</option>
          {CATEGORIES.filter(Boolean).map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-3 pt-1">
        {notes.length === 0 ? (
          <p className="text-center text-gray-600 text-xs mt-8">No notes found</p>
        ) : (
          notes.map(note => (
            <NoteItem
              key={note.id}
              note={note}
              isSelected={note.id === selectedId}
              onSelect={() => onSelect(note.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/notes/NoteList.tsx
git commit -m "feat(notes): NoteList component with date and category filters"
```

---

## Task 6: NoteForm Component

**Files:**
- Create: `frontend/src/components/notes/NoteForm.tsx`

- [ ] **Step 1: Create `frontend/src/components/notes/NoteForm.tsx`**

```typescript
import { useState } from 'react'
import { X } from 'lucide-react'
import type { QuickNote, Task, EDARequest } from '../../types'
import { createNote, updateNote } from '../../api/notes'
import type { NotePayload } from '../../api/notes'

interface Props {
  initial?: QuickNote | null
  tasks: Task[]
  edas: EDARequest[]
  onSaved: (note: QuickNote) => void
  onCancel: () => void
}

const CATEGORIES = ['daily', 'meeting', 'idea', 'bug']

export default function NoteForm({ initial, tasks, edas, onSaved, onCancel }: Props) {
  const today = new Date().toISOString().slice(0, 10)

  const [title,    setTitle]    = useState(initial?.title    ?? '')
  const [content,  setContent]  = useState(initial?.content  ?? '')
  const [date,     setDate]     = useState(initial?.date     ?? today)
  const [category, setCategory] = useState(initial?.category ?? '')
  const [taskId,   setTaskId]   = useState(initial?.task_id  ?? '')
  const [edaId,    setEdaId]    = useState(initial?.eda_id   ?? '')
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!content.trim()) { setError('Content is required'); return }
    if (!date)           { setError('Date is required');    return }

    const payload: NotePayload = {
      title:    title.trim()    || null,
      content:  content.trim(),
      date,
      category: category.trim() || null,
      task_id:  taskId          || null,
      eda_id:   edaId           || null,
    }

    setSaving(true)
    setError('')
    try {
      const saved = initial
        ? await updateNote(initial.id, payload)
        : await createNote(payload)
      onSaved(saved)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? 'Failed to save note'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-white">
          {initial ? 'Edit Note' : 'New Note'}
        </h2>
        <button onClick={onCancel} className="text-gray-500 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 flex flex-col px-5 py-4 gap-4">
        {/* Title */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Title (optional)</label>
          <input
            className="input-base text-sm w-full"
            placeholder="Short title..."
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col">
          <label className="text-[11px] text-gray-400 mb-1 block">Content *</label>
          <textarea
            className="input-base text-sm w-full flex-1 resize-none min-h-[140px]"
            placeholder="Write your note..."
            value={content}
            onChange={e => setContent(e.target.value)}
          />
        </div>

        {/* Date + Category row */}
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-[11px] text-gray-400 mb-1 block">Date *</label>
            <input
              type="date"
              className="input-base text-sm w-full"
              value={date}
              onChange={e => setDate(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="text-[11px] text-gray-400 mb-1 block">Category</label>
            <select
              className="input-base text-sm w-full"
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              <option value="">None</option>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        {/* Link to Task */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Link to Task (optional)</label>
          <select
            className="input-base text-sm w-full"
            value={taskId}
            onChange={e => { setTaskId(e.target.value); if (e.target.value) setEdaId('') }}
          >
            <option value="">None</option>
            {tasks.map(t => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
        </div>

        {/* Link to EDA */}
        <div>
          <label className="text-[11px] text-gray-400 mb-1 block">Link to EDA Request (optional)</label>
          <select
            className="input-base text-sm w-full"
            value={edaId}
            onChange={e => { setEdaId(e.target.value); if (e.target.value) setTaskId('') }}
          >
            <option value="">None</option>
            {edas.map(e => (
              <option key={e.id} value={e.id}>{e.title}</option>
            ))}
          </select>
        </div>

        {/* Error */}
        {error && (
          <p className="text-danger text-xs bg-danger/10 border border-danger/20 px-3 py-2 rounded-lg">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={saving} className="btn-primary flex-1 text-sm py-2">
            {saving ? 'Saving…' : initial ? 'Save Changes' : 'Create Note'}
          </button>
          <button type="button" onClick={onCancel} className="btn-ghost flex-1 text-sm py-2">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/notes/NoteForm.tsx
git commit -m "feat(notes): NoteForm component"
```

---

## Task 7: NoteDetail Component

**Files:**
- Create: `frontend/src/components/notes/NoteDetail.tsx`

- [ ] **Step 1: Create `frontend/src/components/notes/NoteDetail.tsx`**

```typescript
import { Pencil, Trash2, Tag, Link2 } from 'lucide-react'
import type { QuickNote } from '../../types'

const CATEGORY_STYLES: Record<string, string> = {
  daily:   'text-green-400 bg-green-400/10 border-green-400/20',
  meeting: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  idea:    'text-purple-400 bg-purple-400/10 border-purple-400/20',
  bug:     'text-red-400 bg-red-400/10 border-red-400/20',
}

interface Props {
  note: QuickNote
  taskTitle?: string | null
  edaTitle?: string | null
  onEdit: () => void
  onDelete: (id: string) => void
}

export default function NoteDetail({ note, taskTitle, edaTitle, onEdit, onDelete }: Props) {
  const categoryStyle = note.category
    ? (CATEGORY_STYLES[note.category] ?? 'text-gray-400 bg-gray-400/10 border-gray-400/20')
    : null

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 border-b border-white/5 flex items-start justify-between flex-shrink-0">
        <div className="flex-1 min-w-0">
          {note.title && (
            <h2 className="text-base font-semibold text-white mb-1 truncate">{note.title}</h2>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-gray-400 font-mono">{note.date}</span>
            {note.category && categoryStyle && (
              <span className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${categoryStyle}`}>
                <Tag size={9} />
                {note.category}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-3 flex-shrink-0">
          <button
            onClick={onEdit}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-all"
            title="Edit"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(note.id)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-danger hover:bg-danger/10 transition-all"
            title="Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="px-5 py-4 flex-1">
        <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
          {note.content}
        </p>
      </div>

      {/* Linked item */}
      {(taskTitle || edaTitle) && (
        <div className="px-5 py-3 border-t border-white/5 flex-shrink-0">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Link2 size={12} />
            <span>{taskTitle ? `Task: ${taskTitle}` : `EDA: ${edaTitle}`}</span>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/notes/NoteDetail.tsx
git commit -m "feat(notes): NoteDetail component"
```

---

## Task 8: QuickNotes Page

**Files:**
- Create: `frontend/src/pages/work/QuickNotes.tsx`

- [ ] **Step 1: Create `frontend/src/pages/work/QuickNotes.tsx`**

```typescript
import { useEffect, useState, useCallback } from 'react'
import type { QuickNote, Task, EDARequest } from '../../types'
import { fetchNotes, deleteNote } from '../../api/notes'
import { fetchTasks } from '../../api/tasks'
import { fetchEDAs } from '../../api/eda'
import NoteList   from '../../components/notes/NoteList'
import NoteDetail from '../../components/notes/NoteDetail'
import NoteForm   from '../../components/notes/NoteForm'

type PanelMode = 'empty' | 'detail' | 'create' | 'edit'

export default function QuickNotes() {
  const [notes,      setNotes]      = useState<QuickNote[]>([])
  const [tasks,      setTasks]      = useState<Task[]>([])
  const [edas,       setEdas]       = useState<EDARequest[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [mode,       setMode]       = useState<PanelMode>('empty')
  const [apiError,   setApiError]   = useState('')

  const [dateFrom,   setDateFrom]   = useState('')
  const [dateTo,     setDateTo]     = useState('')
  const [category,   setCategory]   = useState('')

  const selected = notes.find(n => n.id === selectedId) ?? null

  const load = useCallback(async () => {
    try {
      const [n, t, e] = await Promise.all([
        fetchNotes({ date_from: dateFrom, date_to: dateTo, category }),
        fetchTasks(),
        fetchEDAs(),
      ])
      setNotes(n)
      setTasks(t)
      setEdas(e)
      setApiError('')
    } catch {
      setApiError('Cannot reach API — is the backend running?')
    }
  }, [dateFrom, dateTo, category])

  useEffect(() => { load() }, [load])

  function handleSelect(id: string) {
    setSelectedId(id)
    setMode('detail')
  }

  function handleSaved(note: QuickNote) {
    setNotes(ns =>
      ns.some(n => n.id === note.id)
        ? ns.map(n => n.id === note.id ? note : n)
        : [note, ...ns]
    )
    setSelectedId(note.id)
    setMode('detail')
  }

  async function handleDelete(id: string) {
    try {
      await deleteNote(id)
      setNotes(ns => ns.filter(n => n.id !== id))
      setSelectedId(null)
      setMode('empty')
    } catch {
      setApiError('Failed to delete — check connection')
    }
  }

  const taskTitle = selected?.task_id
    ? (tasks.find(t => t.id === selected.task_id)?.title ?? null)
    : null
  const edaTitle = selected?.eda_id
    ? (edas.find(e => e.id === selected.eda_id)?.title ?? null)
    : null

  return (
    <div className="flex h-screen overflow-hidden">
      <NoteList
        notes={notes}
        selectedId={selectedId}
        dateFrom={dateFrom}
        dateTo={dateTo}
        category={category}
        onSelect={handleSelect}
        onNew={() => { setSelectedId(null); setMode('create') }}
        onDateFromChange={v => { setDateFrom(v); setSelectedId(null); setMode('empty') }}
        onDateToChange={v => { setDateTo(v);   setSelectedId(null); setMode('empty') }}
        onCategoryChange={v => { setCategory(v); setSelectedId(null); setMode('empty') }}
      />

      <div className="flex-1 flex overflow-hidden relative">
        {apiError && (
          <div className="absolute top-4 right-4 bg-danger/10 border border-danger/30 text-danger text-xs px-3 py-2 rounded-lg z-10">
            {apiError}
          </div>
        )}

        {mode === 'empty' && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span className="text-3xl opacity-20">📝</span>
            <p>Select a note or create one</p>
          </div>
        )}

        {mode === 'detail' && selected && (
          <NoteDetail
            note={selected}
            taskTitle={taskTitle}
            edaTitle={edaTitle}
            onEdit={() => setMode('edit')}
            onDelete={handleDelete}
          />
        )}

        {(mode === 'create' || mode === 'edit') && (
          <NoteForm
            initial={mode === 'edit' ? selected : null}
            tasks={tasks}
            edas={edas}
            onSaved={handleSaved}
            onCancel={() => setMode(selected ? 'detail' : 'empty')}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify `fetchEDAs` exists in `frontend/src/api/eda.ts`**

```
grep -n "fetchEDAs\|export.*fetch" frontend/src/api/eda.ts
```

If the function is named differently (e.g. `fetchEdaRequests`), update the import in `QuickNotes.tsx` to match.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/work/QuickNotes.tsx
git commit -m "feat(notes): QuickNotes page"
```

---

## Task 9: Nav + Route Wiring

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add route in `App.tsx`**

Add the lazy import after the `WipBuilder` import line (around line 7):

```typescript
const QuickNotes     = lazy(() => import('./pages/work/QuickNotes'))
```

Add the route after `work/discord` (around line 44):

```typescript
<Route path="work/notes"    element={<QuickNotes />} />
```

- [ ] **Step 2: Add nav item in `Sidebar.tsx`**

Add `NotebookPen` to the import from lucide-react (line 1–20):

```typescript
import {
  LayoutDashboard,
  CheckSquare,
  FlaskConical,
  Hammer,
  BellRing,
  Database,
  Code2,
  Layers,
  GitBranch,
  TrendingUp,
  BrainCircuit,
  Activity,
  Map,
  BookOpen,
  FolderGit2,
  Link2,
  Sparkles,
  NotebookPen,
} from 'lucide-react'
```

Add `NotebookPen` to `ICON_MAP`:

```typescript
export const ICON_MAP = {
  LayoutDashboard, CheckSquare, FlaskConical, Hammer, BellRing,
  Database, Code2, Layers, GitBranch, TrendingUp, BrainCircuit,
  Activity, Map, BookOpen, FolderGit2, Link2, Sparkles, NotebookPen,
}
```

Add the nav item inside the `work` category items array, after the `WIP Builder` entry:

```typescript
{ path: '/work/notes',   label: 'Quick Notes',    iconName: 'NotebookPen', color: '#34d399' },
```

- [ ] **Step 3: Build to verify no TS errors**

```
cd frontend
npm run build 2>&1 | tail -30
```

Expected: build succeeds, no type errors.

- [ ] **Step 4: Start dev servers and verify in browser**

Terminal 1:
```
cd backend && uvicorn main:app --reload
```

Terminal 2:
```
cd frontend && npm run dev
```

Open `http://localhost:5177`. Check:
- "Quick Notes" appears in sidebar under WORK with `NotebookPen` icon in green
- Navigating to `/work/notes` loads the page
- Creating a note works (minimal: content + date)
- Creating a note with all fields including category badge
- Date filter narrows the list
- Category filter works
- Edit a note → changes appear
- Delete a note → disappears from list
- Linking a note to a task → chip shows in NoteDetail

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(notes): wire Quick Notes route and nav item"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** table schema ✓, all 5 API endpoints ✓, all 10 tests ✓, list+side-panel layout ✓, date filter ✓, category filter ✓, task/EDA link ✓, Lucide icons ✓, category badge colours ✓, FK validation 400 ✓
- [x] **No placeholders:** all steps have complete code
- [x] **Type consistency:** `QuickNote` defined in Task 3, used in Tasks 4–8; `NotePayload` defined in Task 3 `api/notes.ts`, used in `NoteForm` Task 6; `_check_fk` defined and called in Task 2 backend; `CATEGORY_STYLES` defined identically in `NoteItem` (Task 4) and `NoteDetail` (Task 7)
- [x] **`fetchEDAs` check:** Task 8 Step 2 explicitly instructs verification of function name before commit
