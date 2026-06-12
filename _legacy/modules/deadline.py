from datetime import date, timedelta

BUFFER_DAYS = {
    "high":   2,
    "medium": 2,
    "low":    2,
    "ad-hoc": 2,
}

CATEGORY_LABEL = {
    "high":   "🔴 High",
    "medium": "🟡 Medium",
    "low":    "🟢 Low",
    "ad-hoc": "⚡ Ad-hoc",
}


def calculate_deadline(end_date: str, category: str) -> str:
    """Return ISO deadline string after applying buffer days for category."""
    base = date.fromisoformat(end_date)
    delta = BUFFER_DAYS.get(category, 0)
    return (base + timedelta(days=delta)).isoformat()


def get_label(category: str) -> str:
    return CATEGORY_LABEL.get(category, category)
