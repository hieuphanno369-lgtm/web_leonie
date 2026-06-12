from datetime import date
import polars as pl
from analytics.timegrain import (
    truncate_dates, aggregate_series, suggest_grain, add_comparisons,
)


def _df(rows):
    return pl.DataFrame({"d": [r[0] for r in rows], "v": [r[1] for r in rows]})


def test_truncate_month_and_quarter():
    s = pl.Series("d", [date(2024, 2, 20), date(2024, 11, 5)])
    assert truncate_dates(s, "month").to_list() == [date(2024, 2, 1), date(2024, 11, 1)]
    assert truncate_dates(s, "quarter").to_list() == [date(2024, 1, 1), date(2024, 10, 1)]


def test_aggregate_series_monthly_sum():
    df = _df([
        (date(2024, 1, 5), 10), (date(2024, 1, 20), 20),
        (date(2024, 2, 10), 30), (date(2024, 2, 15), 5),
        (date(2024, 3, 1), 40),
    ])
    out = aggregate_series(df, "d", "v", "month", "sum")
    assert out["labels"] == ["2024-01", "2024-02", "2024-03"]
    assert out["values"] == [30.0, 35.0, 40.0]
    assert out["period_starts"][0] == date(2024, 1, 1)


def test_aggregate_drops_null_dates():
    df = pl.DataFrame({"d": [date(2024, 1, 1), None], "v": [5, 99]})
    out = aggregate_series(df, "d", "v", "month", "sum")
    assert out["values"] == [5.0]


def test_suggest_grain_picks_month_for_two_years():
    g = suggest_grain(date(2022, 1, 1), date(2024, 6, 6))  # ~887 days
    assert g == "month"


def test_suggest_grain_day_for_short_span():
    assert suggest_grain(date(2024, 1, 1), date(2024, 1, 5)) == "day"


def test_add_comparisons_pop_and_yoy():
    starts = [date(2023, 1, 1), date(2023, 2, 1), date(2024, 1, 1), date(2024, 2, 1)]
    vals = [100.0, 200.0, 150.0, 180.0]
    out = add_comparisons(starts, vals, "month", ["pop", "yoy"])
    assert out["pop"]["values"] == [None, 100.0, 200.0, 150.0]
    assert out["yoy"]["values"] == [None, None, 100.0, 200.0]
    assert out["yoy"]["delta_pct"] == [None, None, 50.0, -10.0]


def test_add_comparisons_rolling_and_cumulative():
    starts = [date(2024, m, 1) for m in range(1, 5)]
    vals = [10.0, 20.0, 30.0, 40.0]
    out = add_comparisons(starts, vals, "month", ["rolling", "cumulative"],
                          rolling_window=2, cumulative_reset="year")
    assert out["rolling"]["window"] == 2
    assert out["rolling"]["values"] == [10.0, 15.0, 25.0, 35.0]
    assert out["cumulative"]["values"] == [10.0, 30.0, 60.0, 100.0]
