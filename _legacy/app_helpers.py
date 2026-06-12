from datetime import date


def get_stats(tasks: list[dict]) -> dict:
    today = date.today().isoformat()
    active = [t for t in tasks if t.get("active")]
    done   = [t for t in tasks if not t.get("active")]
    overdue = [t for t in active if t.get("deadline") and t.get("deadline") < today]
    today_tasks = [t for t in active if t.get("deadline") and t.get("deadline") == today]
    return {
        "overdue": len(overdue),
        "active":  len(active),
        "done":    len(done),
        "today":   len(today_tasks),
    }


def group_by_priority(tasks: list[dict]) -> dict:
    groups: dict[str, list] = {"high": [], "medium": [], "low": [], "ad-hoc": []}
    for task in tasks:
        key = task.get("category_raw", "low")
        groups[key if key in groups else "low"].append(task)
    return groups


def filter_tasks(tasks: list[dict], query: str, priority: str) -> list[dict]:
    result = list(tasks)
    if query:
        q = query.lower()
        result = [t for t in result if q in t.get("task_name", "").lower()]
    if priority:
        result = [t for t in result if t.get("category_raw") == priority]
    return result
