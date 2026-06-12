# Task Manager — Design Spec
**Date:** 2026-05-17
**Status:** Approved
**Sprint:** SP2

---

## Overview

Full CRUD Task Manager cho Leonie Work Hub. Người dùng có thể tạo, xem, sửa, xoá task với priority, deadline, và recurrence. Layout: list bên trái + detail panel bên phải (không dùng modal).

---

## Layout

**Layout C — List + Detail Panel**

```
┌─────────────────────────────────────────────────────┐
│  [ All ] [ Todo ] [ In Progress ] [ Done ]  + New   │  ← filter bar
│  🔍 Search tasks...                                  │
├──────────────────────┬──────────────────────────────┤
│  ☐ Task title A  HIGH│  Task title A                │
│  ☑ Task title B  MED │  ● Todo  🔥 High  📅 17/05   │
│  ✓ Task title C      │  ─────────────────────────── │
│  ☐ Task title D  LOW │  Notes                       │
│                      │  [text content...]            │
│                      │                               │
│                      │  Created: 15/05/2026          │
│                      │  Updated: 16/05/2026          │
│                      │                    [Edit] [🗑]│
└──────────────────────┴──────────────────────────────┘
```

- Left panel: fixed 340px, scrollable task list
- Right panel: flex-1, shows selected task detail or create/edit form
- No modals — everything inline in the right panel

---

## Data Model

Sử dụng bảng `tasks` đã có trong `backend/database.py`:

```sql
tasks (
  id        TEXT PK  -- hex random 8 bytes
  title     TEXT NOT NULL
  status    TEXT     -- 'todo' | 'in_progress' | 'done'
  priority  TEXT     -- 'low' | 'medium' | 'high'
  due_date  TEXT     -- ISO date string, nullable
  recurring TEXT     -- NULL | 'daily' | 'weekly'
  notes     TEXT     -- nullable
  created   TEXT
  updated   TEXT
)
```

TypeScript type đã có trong `frontend/src/types.ts`.

---

## API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List all tasks (optionally filter by `status`) |
| POST | `/tasks` | Create a new task |
| GET | `/tasks/{id}` | Get single task |
| PATCH | `/tasks/{id}` | Update fields (partial) |
| DELETE | `/tasks/{id}` | Delete task |

Request/Response format: JSON. Validation via Pydantic models.

---

## Frontend Components

### `pages/work/TaskManager.tsx`
- Root page component
- Manages state: `tasks[]`, `selectedId`, `mode` (`view` | `create` | `edit`)
- Fetches task list on mount via `api/tasks.ts`

### `components/tasks/TaskList.tsx`
- Props: `tasks`, `selectedId`, `onSelect`, `onToggleDone`
- Renders filter tabs + search input + scrollable list
- Click checkbox → PATCH status toggle (no panel needed)
- Click row → `onSelect(id)`

### `components/tasks/TaskItem.tsx`
- Single row: checkbox, title, priority badge, due date, recurring badge
- Visual states: todo / in_progress / done (strikethrough + opacity)

### `components/tasks/TaskDetail.tsx`
- Props: `task`, `onEdit`, `onDelete`, `onClose`
- View mode: chips (status, priority, due date, recurring) + notes block + Edit/Delete buttons

### `components/tasks/TaskForm.tsx`
- Props: `initial?` (Task for edit, undefined for create), `onSave`, `onCancel`
- Fields: title (required), status, priority, due_date, recurring, notes
- Submit → POST (create) or PATCH (edit)

### `api/tasks.ts`
- `fetchTasks(status?)` → `GET /tasks`
- `createTask(body)` → `POST /tasks`
- `updateTask(id, body)` → `PATCH /tasks/{id}`
- `deleteTask(id)` → `DELETE /tasks/{id}`

---

## Interactions

| Action | Behaviour |
|--------|-----------|
| Click task row | Select → show detail in right panel |
| Click checkbox | Toggle todo ↔ done via PATCH (no panel change) |
| Click "+ New Task" | Right panel → TaskForm (create mode), placeholder row in list |
| Click "Edit" in detail | Right panel → TaskForm (edit mode) pre-filled |
| Save form | API call → refresh list → show detail of saved task |
| Click "Delete" | Confirm inline (button turns red, click again to confirm) → DELETE → deselect |
| Filter tab | Filter list client-side (no API call) |
| Search | Client-side filter on title |

---

## Error Handling

- API errors → inline error message below form or in detail panel (no toast library needed)
- Empty list → friendly empty state with "+ New Task" CTA
- No task selected → right panel shows placeholder "Select a task or create one"

---

## Files to Create / Modify

```
backend/
  routers/
    tasks.py          ← NEW: CRUD endpoints
  main.py             ← MODIFY: include tasks router

frontend/src/
  api/
    tasks.ts          ← NEW: API client functions
  components/
    tasks/
      TaskList.tsx    ← NEW
      TaskItem.tsx    ← NEW
      TaskDetail.tsx  ← NEW
      TaskForm.tsx    ← NEW
  pages/work/
    TaskManager.tsx   ← REPLACE placeholder with real implementation
```

---

## Out of Scope (SP2)

- Drag-and-drop reorder
- Subtasks / checklist inside task
- Attachments
- Multi-user / assign to
- Notifications / Discord integration (separate module)
