from datetime import date, timedelta
import pytest
from app_helpers import get_stats, group_by_priority, filter_tasks


def _today():
    return date.today().isoformat()

def _days(n):
    return (date.today() + timedelta(days=n)).isoformat()


def test_get_stats_empty():
    assert get_stats([]) == {"overdue": 0, "active": 0, "done": 0, "today": 0}


def test_get_stats_overdue():
    tasks = [{"active": True, "deadline": _days(-1)}]
    stats = get_stats(tasks)
    assert stats["overdue"] == 1
    assert stats["active"] == 1


def test_get_stats_today():
    tasks = [{"active": True, "deadline": _today()}]
    stats = get_stats(tasks)
    assert stats["today"] == 1
    assert stats["overdue"] == 0


def test_get_stats_done():
    tasks = [{"active": False, "deadline": _days(-5)}]
    stats = get_stats(tasks)
    assert stats["done"] == 1
    assert stats["active"] == 0


def test_get_stats_mixed():
    tasks = [
        {"active": True,  "deadline": _days(-1)},   # overdue
        {"active": True,  "deadline": _today()},     # today
        {"active": True,  "deadline": _days(3)},     # future active
        {"active": False, "deadline": _days(-2)},    # done
    ]
    s = get_stats(tasks)
    assert s["overdue"] == 1
    assert s["today"]   == 1
    assert s["active"]  == 3
    assert s["done"]    == 1


def test_group_by_priority_all_groups():
    tasks = [
        {"category_raw": "high"},
        {"category_raw": "high"},
        {"category_raw": "medium"},
        {"category_raw": "low"},
        {"category_raw": "ad-hoc"},
    ]
    groups = group_by_priority(tasks)
    assert len(groups["high"])   == 2
    assert len(groups["medium"]) == 1
    assert len(groups["low"])    == 1
    assert len(groups["ad-hoc"]) == 1


def test_group_by_priority_unknown_goes_to_low():
    tasks = [{"category_raw": "unknown"}]
    groups = group_by_priority(tasks)
    assert len(groups["low"]) == 1


def test_filter_tasks_by_name_case_insensitive():
    tasks = [
        {"task_name": "Báo cáo Q2", "category_raw": "high"},
        {"task_name": "Review code", "category_raw": "medium"},
    ]
    result = filter_tasks(tasks, "báo cáo", "")
    assert len(result) == 1
    assert result[0]["task_name"] == "Báo cáo Q2"


def test_filter_tasks_by_priority():
    tasks = [
        {"task_name": "T1", "category_raw": "high"},
        {"task_name": "T2", "category_raw": "medium"},
    ]
    result = filter_tasks(tasks, "", "high")
    assert len(result) == 1
    assert result[0]["task_name"] == "T1"


def test_filter_tasks_no_filter_returns_all():
    tasks = [
        {"task_name": "T1", "category_raw": "high"},
        {"task_name": "T2", "category_raw": "medium"},
    ]
    assert len(filter_tasks(tasks, "", "")) == 2


def test_filter_tasks_combined():
    tasks = [
        {"task_name": "Report high", "category_raw": "high"},
        {"task_name": "Report med",  "category_raw": "medium"},
        {"task_name": "Fix bug",     "category_raw": "high"},
    ]
    result = filter_tasks(tasks, "report", "high")
    assert len(result) == 1
    assert result[0]["task_name"] == "Report high"


def test_get_stats_missing_deadline_not_overdue():
    tasks = [{"active": True}]  # No deadline field
    stats = get_stats(tasks)
    assert stats["overdue"] == 0


def test_filter_tasks_returns_new_list():
    tasks = [{"task_name": "test", "category_raw": "high"}]
    result = filter_tasks(tasks, "", "")
    assert result is not tasks
