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

def _wrow(row) -> WIPOut:
    return WIPOut(**dict(row))

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
