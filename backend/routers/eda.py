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
