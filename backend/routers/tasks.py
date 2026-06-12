from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/tasks", tags=["tasks"])

# ── Types ────────────────────────────────────────────────────────────────────

TaskStatus   = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]
TaskRecurring = Literal["daily", "weekly"]
TaskType      = Literal["task", "eda"]


class TaskCreate(BaseModel):
    title: str
    type: TaskType = "task"
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    due_date: str | None = None
    recurring: TaskRecurring | None = None
    notes: str | None = None
    requester: str | None = None
    dataset: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    type: TaskType | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: str | None = None
    recurring: TaskRecurring | None = None
    notes: str | None = None
    requester: str | None = None
    dataset: str | None = None


class TaskOut(BaseModel):
    id: str
    title: str
    type: str
    status: TaskStatus
    priority: TaskPriority
    due_date: str | None
    recurring: TaskRecurring | None
    notes: str | None
    requester: str | None
    dataset: str | None
    created: str
    updated: str


def _row(row) -> TaskOut:
    return TaskOut(**dict(row))


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status: TaskStatus | None = Query(default=None),
    type: TaskType | None = Query(default=None),
):
    conn = get_connection()
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status = ?"; params.append(status)
    if type:
        sql += " AND type = ?"; params.append(type)
    sql += " ORDER BY created DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate):
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO tasks (title, type, status, priority, due_date, recurring, notes, requester, dataset)
           VALUES (:title, :type, :status, :priority, :due_date, :recurring, :notes, :requester, :dataset)""",
        body.model_dump(),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM tasks WHERE rowid = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return _row(row)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    conn.close()
    return _row(row)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskUpdate):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    _ALLOWED = {'title', 'type', 'status', 'priority', 'due_date', 'recurring', 'notes', 'requester', 'dataset'}
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in _ALLOWED}
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
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    conn.commit()
    conn.close()
