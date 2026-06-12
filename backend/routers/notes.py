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
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row(r) for r in rows]
    finally:
        conn.close()


@router.post("", response_model=NoteOut, status_code=201)
def create_note(body: NoteCreate):
    conn = get_connection()
    try:
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
        return _row(row)
    finally:
        conn.close()


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
    try:
        row = conn.execute(
            "SELECT * FROM quick_notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")

        _ALLOWED = {"title", "content", "date", "category", "task_id", "eda_id"}
        updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in _ALLOWED}

        _check_fk(conn, updates.get("task_id"), updates.get("eda_id"))

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
        return _row(row)
    finally:
        conn.close()


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM quick_notes WHERE id = ?", (note_id,))
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")
    conn.commit()
    conn.close()
