import json
import time
import calendar
from pathlib import Path
from datetime import date

TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"


def load_tasks() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_tasks(tasks: list[dict]) -> None:
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def add_task(task: dict) -> dict:
    task["task_id"] = f"task_{int(time.time() * 1000)}"
    task["created_at"] = date.today().isoformat()
    task["active"] = True
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    return task


def get_active_tasks() -> list[dict]:
    today = date.today().isoformat()
    return [t for t in load_tasks() if t.get("active") and t.get("deadline", "") >= today]


def update_task(task_id: str, fields: dict) -> bool:
    tasks = load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            t.update(fields)
            save_tasks(tasks)
            return True
    return False


def delete_task(task_id: str) -> bool:
    tasks = load_tasks()
    new_tasks = [t for t in tasks if t["task_id"] != task_id]
    if len(new_tasks) == len(tasks):
        return False
    save_tasks(new_tasks)
    return True


def _add_months(d: date, n: int) -> date:
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def deactivate_expired() -> tuple[int, int]:
    """Archive expired tasks, auto-renew recurring ones.
    Returns (archived, renewed).
    """
    from modules.deadline import calculate_deadline

    today = date.today().isoformat()
    tasks = load_tasks()
    archived = 0
    renewed = 0

    for t in tasks:
        if not (t.get("active") and t.get("deadline", "") < today):
            continue

        recur = t.get("recur")
        if recur in ("monthly", "yearly"):
            try:
                start = date.fromisoformat(t["start_date"])
                end = date.fromisoformat(t["end_date"])
                if recur == "monthly":
                    new_start = _add_months(start, 1)
                    new_end = _add_months(end, 1)
                else:
                    new_start = _add_years(start, 1)
                    new_end = _add_years(end, 1)
                new_deadline = calculate_deadline(new_end.isoformat(), t.get("category_raw", "low"))
                t["start_date"] = new_start.isoformat()
                t["end_date"] = new_end.isoformat()
                t["deadline"] = new_deadline
                t["active"] = True
                renewed += 1
            except Exception:
                t["active"] = False
                archived += 1
        else:
            t["active"] = False
            archived += 1

    if archived + renewed:
        save_tasks(tasks)
    return archived, renewed
