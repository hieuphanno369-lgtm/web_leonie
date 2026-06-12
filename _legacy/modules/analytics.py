"""Task analytics — pure functions, no Streamlit imports."""
from datetime import date, timedelta
from collections import defaultdict
from typing import Any

DEFAULT_TAGS = [
    "CRM", "Calokid", "CBB", "Ops", "Data", "HR",
    "Report", "Meeting", "Finance", "KPI", "Survey",
]


def get_priority_breakdown(tasks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for t in tasks:
        counts[t.get("category_raw", "low")] += 1
    return dict(counts)


def get_status_breakdown(tasks: list[dict]) -> dict[str, int]:
    active = sum(1 for t in tasks if t.get("active"))
    done   = sum(1 for t in tasks if not t.get("active"))
    return {"active": active, "done": done}


def get_creation_trend(tasks: list[dict], days: int = 30) -> dict[str, int]:
    """Returns {date_str: count} for last N days (creation date)."""
    today = date.today()
    start = today - timedelta(days=days - 1)
    buckets: dict[str, int] = {
        (start + timedelta(i)).isoformat(): 0 for i in range(days)
    }
    for t in tasks:
        created = t.get("created_at", "")
        if created in buckets:
            buckets[created] += 1
    return buckets


def get_upcoming_deadlines(tasks: list[dict], days: int = 14) -> list[dict]:
    today = date.today()
    cutoff = (today + timedelta(days=days)).isoformat()
    today_s = today.isoformat()
    upcoming = [
        t for t in tasks
        if t.get("active") and today_s <= t.get("deadline", "9999") <= cutoff
    ]
    return sorted(upcoming, key=lambda x: x.get("deadline", ""))


def get_overdue(tasks: list[dict]) -> list[dict]:
    today = date.today().isoformat()
    return [t for t in tasks if t.get("active") and t.get("deadline", "9999") < today]


def get_deadline_heatmap(tasks: list[dict]) -> dict[str, int]:
    """Returns {deadline_date: count} for all active tasks."""
    counts: dict[str, int] = defaultdict(int)
    for t in tasks:
        dl = t.get("deadline", "")
        if dl and t.get("active"):
            counts[dl] += 1
    return dict(counts)


def get_priority_label_map() -> dict[str, str]:
    return {
        "high":   "High",
        "medium": "Medium",
        "low":    "Low",
        "ad-hoc": "Ad-hoc",
    }


def get_priority_color_map() -> dict[str, str]:
    return {
        "high":   "#ff2d55",
        "medium": "#ff9f0a",
        "low":    "#30d158",
        "ad-hoc": "#64d2ff",
    }


def get_burndown_data(tasks: list[dict], days: int = 30) -> dict[str, dict]:
    """
    Returns {date_str: {"created": n, "completed": n}} for last N days.
    Uses created_at and completed_at fields.
    """
    today = date.today()
    start = today - timedelta(days=days - 1)
    buckets: dict[str, dict] = {
        (start + timedelta(i)).isoformat(): {"created": 0, "completed": 0}
        for i in range(days)
    }
    for t in tasks:
        c = t.get("created_at", "")
        if c in buckets:
            buckets[c]["created"] += 1
        done_at = t.get("completed_at", "")
        if done_at in buckets:
            buckets[done_at]["completed"] += 1
    return buckets


def get_tag_breakdown(tasks: list[dict]) -> dict[str, int]:
    """Returns {tag: count} for all tasks that have tags."""
    counts: dict[str, int] = defaultdict(int)
    for t in tasks:
        for tag in t.get("tags", []):
            counts[tag] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
