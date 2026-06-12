from database import get_connection
from automation.models import JobConfig, AutomationJob, RunResult


def _to_job(row) -> AutomationJob:
    return AutomationJob(
        id=row["id"],
        config=JobConfig.model_validate_json(row["config"]),
        last_status=row["last_status"],
        last_run_at=row["last_run_at"],
        last_rows=row["last_rows"],
        last_error=row["last_error"],
        created=row["created"],
        updated=row["updated"],
    )


def create_job(config: JobConfig) -> AutomationJob:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO automation_jobs (name, config) VALUES (?, ?)",
        (config.name, config.model_dump_json()),
    )
    row = conn.execute("SELECT * FROM automation_jobs WHERE rowid = ?",
                       (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return _to_job(row)


def get_job(job_id: str) -> AutomationJob | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM automation_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return _to_job(row) if row else None


def list_jobs() -> list[AutomationJob]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM automation_jobs ORDER BY created DESC").fetchall()
    conn.close()
    return [_to_job(r) for r in rows]


def update_job(job_id: str, config: JobConfig) -> AutomationJob | None:
    conn = get_connection()
    cur = conn.execute(
        "UPDATE automation_jobs SET name = ?, config = ?, updated = datetime('now') WHERE id = ?",
        (config.name, config.model_dump_json(), job_id),
    )
    conn.commit()
    changed = cur.rowcount
    row = conn.execute("SELECT * FROM automation_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return _to_job(row) if (changed and row) else None


def delete_job(job_id: str) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM automation_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def set_running(job_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE automation_jobs SET last_status='running', last_error=NULL, "
        "updated=datetime('now') WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def set_run_status(job_id: str, result: RunResult) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE automation_jobs SET last_status=?, last_rows=?, last_error=?, "
        "last_run_at=datetime('now'), updated=datetime('now') WHERE id = ?",
        (result.status, result.rows, result.error, job_id),
    )
    conn.commit()
    conn.close()
