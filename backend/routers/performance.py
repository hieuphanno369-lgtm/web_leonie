import json
from datetime import date, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/performance", tags=["performance"])

_DEFAULT_RULE = {"conditions": [{"type": "tasks_done", "op": "gte", "value": 2}], "logic": "OR"}


class StreakRule(BaseModel):
    streak_rule: dict


class DayStatus(BaseModel):
    date: str
    status: str  # "hit" | "partial" | "miss"


class PerformanceSummary(BaseModel):
    streak: int
    tasks_done: int
    eda_done: int
    kpi_logs: int
    wip_avg_progress: float
    calendar: list[DayStatus]


def _ensure_settings(conn):
    if not conn.execute("SELECT id FROM performance_settings WHERE id = 1").fetchone():
        conn.execute(
            "INSERT INTO performance_settings (id, streak_rule) VALUES (1, ?)",
            (json.dumps(_DEFAULT_RULE),),
        )
        conn.commit()
    return conn.execute("SELECT * FROM performance_settings WHERE id = 1").fetchone()


def _eval_condition(conn, cond: dict, day: str) -> bool:
    t, op, val = cond["type"], cond["op"], cond["value"]
    if t == "tasks_done":
        count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done' AND date(updated)=?", (day,)
        ).fetchone()[0]
    elif t == "eda_done":
        count = conn.execute(
            "SELECT COUNT(*) FROM eda_requests WHERE status='done' AND date(updated)=?", (day,)
        ).fetchone()[0]
    elif t == "kpi_logged":
        count = conn.execute(
            "SELECT COUNT(*) FROM kpi_entries WHERE date=?", (day,)
        ).fetchone()[0]
    elif t == "wip_updated":
        count = conn.execute(
            "SELECT COUNT(*) FROM wip_items WHERE date(updated)=?", (day,)
        ).fetchone()[0]
    else:
        return False
    return (count >= val) if op == "gte" else (count == val)


def _day_status(conn, rule: dict, day: str) -> str:
    conds = rule["conditions"]
    results = [_eval_condition(conn, c, day) for c in conds]
    if all(results):
        return "hit"
    if rule["logic"] == "AND" and any(results):
        return "partial"
    return "miss"


@router.get("/settings")
def get_settings():
    conn = get_connection()
    row = _ensure_settings(conn)
    rule = json.loads(row["streak_rule"])
    conn.close()
    return {"streak_rule": rule}


@router.post("/settings")
def save_settings(body: StreakRule):
    conn = get_connection()
    _ensure_settings(conn)
    conn.execute(
        "UPDATE performance_settings SET streak_rule=? WHERE id=1",
        (json.dumps(body.streak_rule),),
    )
    conn.commit()
    conn.close()
    return {"streak_rule": body.streak_rule}


@router.get("/summary", response_model=PerformanceSummary)
def get_summary():
    conn = get_connection()
    row = _ensure_settings(conn)
    rule = json.loads(row["streak_rule"])

    today = date.today()
    first_of_month = today.replace(day=1).isoformat()

    tasks_done = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='done' AND updated >= ?", (first_of_month,)
    ).fetchone()[0]
    eda_done = conn.execute(
        "SELECT COUNT(*) FROM eda_requests WHERE status='done' AND updated >= ?", (first_of_month,)
    ).fetchone()[0]
    kpi_logs = conn.execute(
        "SELECT COUNT(*) FROM kpi_entries WHERE created >= ?", (first_of_month,)
    ).fetchone()[0]
    wip_avg = conn.execute("SELECT AVG(progress) FROM wip_items").fetchone()[0] or 0.0

    calendar: list[DayStatus] = []
    for i in range(29, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        status = _day_status(conn, rule, day)
        calendar.append(DayStatus(date=day, status=status))

    streak = 0
    for day_status in reversed(calendar):
        if day_status.status == "hit":
            streak += 1
        else:
            break

    conn.close()
    return PerformanceSummary(
        streak=streak,
        tasks_done=tasks_done,
        eda_done=eda_done,
        kpi_logs=kpi_logs,
        wip_avg_progress=round(wip_avg, 1),
        calendar=calendar,
    )
