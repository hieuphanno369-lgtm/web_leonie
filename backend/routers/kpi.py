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
