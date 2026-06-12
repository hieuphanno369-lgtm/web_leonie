from datetime import date
import polars as pl
from analytics.cohort_check import check_suitability


def _df(dates, users):
    return pl.DataFrame({"d": dates, "u": users})


def test_suitable_when_entities_recur():
    df = _df(
        [date(2024, 1, 5), date(2024, 2, 5), date(2024, 1, 6), date(2024, 3, 6), date(2024, 2, 10)],
        ["U1", "U1", "U2", "U2", "U3"],
    )
    res = check_suitability(df, "d", "u", df["d"])
    assert res["suitable"] is True
    assert res["reasons"] == []


def test_unsuitable_when_no_recurrence():
    df = _df(
        [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1), date(2024, 4, 1)],
        ["A", "B", "C", "D"],   # each entity appears once
    )
    res = check_suitability(df, "d", "u", df["d"])
    assert res["suitable"] is False
    assert any("kỳ" in r or "giữ chân" in r for r in res["reasons"])
    assert res["role_hint"] == {"date": "d", "user": "u"}


def test_unsuitable_single_period():
    df = _df([date(2024, 1, 1), date(2024, 1, 2)], ["X", "X"])
    res = check_suitability(df, "d", "u", df["d"])
    assert res["suitable"] is False
