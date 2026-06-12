import urllib.request
import urllib.error
import json as json_lib
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/discord", tags=["discord"])


class DiscordSettingsIn(BaseModel):
    webhook_url: str | None = None
    rule_overdue: bool = True
    rule_done: bool = False
    rule_summary: bool = False


class DiscordSettingsOut(BaseModel):
    webhook_url: str | None
    rule_overdue: bool
    rule_done: bool
    rule_summary: bool
    last_checked: str | None


class DiscordSendIn(BaseModel):
    message: str


def _send_webhook(webhook_url: str, message: str) -> None:
    payload = json_lib.dumps({"content": message}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except urllib.error.HTTPError as e:
        raise ValueError(f"Discord returned HTTP {e.code}")


def _ensure_row(conn):
    if not conn.execute("SELECT id FROM discord_settings WHERE id = 1").fetchone():
        conn.execute("INSERT INTO discord_settings (id) VALUES (1)")
        conn.commit()
    return conn.execute("SELECT * FROM discord_settings WHERE id = 1").fetchone()


def _to_out(row) -> DiscordSettingsOut:
    return DiscordSettingsOut(
        webhook_url=row["webhook_url"],
        rule_overdue=bool(row["rule_overdue"]),
        rule_done=bool(row["rule_done"]),
        rule_summary=bool(row["rule_summary"]),
        last_checked=row["last_checked"],
    )


@router.get("/settings", response_model=DiscordSettingsOut)
def get_settings():
    conn = get_connection()
    row = _ensure_row(conn)
    conn.close()
    return _to_out(row)


@router.post("/settings", response_model=DiscordSettingsOut)
def upsert_settings(body: DiscordSettingsIn):
    conn = get_connection()
    _ensure_row(conn)
    conn.execute(
        """UPDATE discord_settings
           SET webhook_url = ?, rule_overdue = ?, rule_done = ?, rule_summary = ?
           WHERE id = 1""",
        (body.webhook_url, int(body.rule_overdue), int(body.rule_done), int(body.rule_summary)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM discord_settings WHERE id = 1").fetchone()
    conn.close()
    return _to_out(row)


@router.post("/send")
def send_message(body: DiscordSendIn):
    conn = get_connection()
    row = _ensure_row(conn)
    conn.close()
    if not row["webhook_url"]:
        raise HTTPException(status_code=400, detail="Webhook URL not configured")
    try:
        _send_webhook(row["webhook_url"], body.message)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True}


@router.post("/check")
def check_rules():
    conn = get_connection()
    row = _ensure_row(conn)
    if not row["webhook_url"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Webhook URL not configured")

    sent = 0
    today = date.today().isoformat()
    last_checked = row["last_checked"] or "2000-01-01T00:00:00"

    if row["rule_overdue"]:
        overdue = conn.execute(
            "SELECT title FROM tasks WHERE due_date < ? AND status != 'done' ORDER BY due_date",
            (today,),
        ).fetchall()
        if overdue:
            titles = "\n".join(f"• {r['title']}" for r in overdue)
            _send_webhook(row["webhook_url"], f"⚠️ **Tasks quá deadline:**\n{titles}")
            sent += 1

    if row["rule_done"]:
        done_tasks = conn.execute(
            "SELECT title FROM tasks WHERE status = 'done' AND updated >= ?",
            (last_checked,),
        ).fetchall()
        for t in done_tasks:
            _send_webhook(row["webhook_url"], f"✅ Task hoàn thành: **{t['title']}**")
            sent += 1

    conn.execute(
        "UPDATE discord_settings SET last_checked = datetime('now') WHERE id = 1"
    )
    conn.commit()
    conn.close()
    return {"sent": sent}
