# Quick Notes / Daily Log — Design Spec

**Date:** 2026-05-24  
**Feature:** Quick Notes (Feature A)  
**Location:** `/work/notes` — WORK section  

---

## Overview

A dedicated page for fast daily note-taking, with optional links to tasks or EDA requests. Notes are persistent in SQLite and filterable by date range and category.

---

## Data Layer

### Table: `quick_notes`

```sql
CREATE TABLE IF NOT EXISTS quick_notes (
    id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    title      TEXT,
    content    TEXT NOT NULL,
    date       TEXT NOT NULL,                -- YYYY-MM-DD
    category   TEXT,                         -- free label: daily/meeting/idea/bug
    task_id    TEXT REFERENCES tasks(id) ON DELETE SET NULL,
    eda_id     TEXT REFERENCES eda_requests(id) ON DELETE SET NULL,
    created    TEXT NOT NULL DEFAULT (datetime('now')),
    updated    TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Migration:** idempotent `CREATE TABLE IF NOT EXISTS` added to `_migrate_v3()` in `backend/database.py`.

### API Endpoints — `/notes` router

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notes` | List notes; query params: `date_from`, `date_to`, `category`, `task_id`, `eda_id` |
| POST | `/notes` | Create note |
| GET | `/notes/{id}` | Get single note |
| PATCH | `/notes/{id}` | Update note |
| DELETE | `/notes/{id}` | Delete note |

**Validation:**
- `content` required, non-empty
- `date` required, format `YYYY-MM-DD`
- `task_id` / `eda_id`: if provided, must exist in their respective tables — backend returns 400 if FK target not found
- 404 returned if note `id` not found on GET/PATCH/DELETE

---

## Frontend Architecture

### New files

```
frontend/src/
  api/notes.ts
  pages/work/QuickNotes.tsx
  components/notes/
    NoteList.tsx
    NoteItem.tsx
    NoteDetail.tsx
    NoteForm.tsx
```

### Modified files

| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Add route `work/notes` |
| `frontend/src/components/layout/Sidebar.tsx` | Add "Quick Notes" nav item under WORK with `NotebookPen` icon (Lucide, green `#34d399`) |
| `backend/database.py` | Add `_migrate_v3()` with `quick_notes` table |
| `backend/main.py` | Mount `/notes` router |

### UI Layout

```
┌─────────────────────────────────────────────────────┐
│  Quick Notes                        [+ New Note]     │
│  Filter: [date from] → [date to]  [category ▾]       │
├──────────────────────┬──────────────────────────────┤
│  NoteList            │  NoteDetail / NoteForm        │
│  • 2026-05-24 · idea │                               │
│    EDA fix approach  │  title, date, content,        │
│  • 2026-05-23 · daily│  category, linked task/EDA    │
│    Stand-up notes    │                               │
└──────────────────────┴──────────────────────────────┘
```

- **NoteItem:** title (or content preview if no title), date badge, category badge
- **Category badge colours:** `daily` → green, `meeting` → yellow, `idea` → purple, `bug` → red, custom → grey
- **Linked task/EDA:** shown as small chip on NoteItem and NoteDetail if present; NoteForm has optional dropdowns loading from `/tasks` and `/eda`
- **Icons:** all Lucide — `NotebookPen` (nav), `Tag` (category), `Link2` (linked item), `Plus` (new note), `Trash2` (delete) — consistent with existing sidebar icon set

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `QuickNotes.tsx` | Page state: notes list, selected note, panel mode (empty/detail/create/edit), date filter state, apiError |
| `NoteList.tsx` | Renders list + date range filter header + category dropdown |
| `NoteItem.tsx` | Single row: title/preview, date, category badge, linked chip |
| `NoteDetail.tsx` | Read-only detail panel with Edit/Delete buttons |
| `NoteForm.tsx` | Create/edit form: title input, textarea, date picker, category input, task/eda dropdowns |
| `api/notes.ts` | `fetchNotes(params)`, `createNote`, `getNote`, `updateNote`, `deleteNote` |

---

## Error Handling

- API unreachable → `apiError` banner (same pattern as TaskManager)
- 404 on note → show "Note not found" in detail panel
- 400 on invalid FK → form-level error message
- Empty state: "No notes yet — click + New Note to start"
- Empty filter result: "No notes match the selected filters"

---

## Testing

File: `backend/tests/test_notes.py`

| Test | Description |
|------|-------------|
| `test_list_notes_empty` | GET /notes returns [] on fresh DB |
| `test_create_note_minimal` | POST with only content + date |
| `test_create_note_full` | POST with all fields |
| `test_filter_by_date_range` | GET with date_from / date_to |
| `test_filter_by_category` | GET with category param |
| `test_update_note` | PATCH updates fields, updated timestamp changes |
| `test_delete_note` | DELETE returns 204, note gone |
| `test_note_not_found_404` | GET/PATCH/DELETE unknown id → 404 |
| `test_link_task_id` | POST with valid task_id succeeds |
| `test_invalid_task_id_400` | POST with non-existent task_id → 400 |

---

## Out of Scope (this sprint)

- Markdown rendering
- Full-text search
- Note export
- Dashboard widget (can add in later sprint)
