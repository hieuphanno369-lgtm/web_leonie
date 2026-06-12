"""Time-grain aggregation + period-comparison math for ML Studio.

Pure functions over Polars frames/series — no FastAPI, no DB. Shared by the
/timeseries and /forecast endpoints so comparison math lives in exactly one
place. Callers must pass a date_col that is already a Date/Datetime dtype
(parse upstream with routers.ml._try_parse_dates).
"""
from __future__ import annotations

import math
from datetime import date
from typing import Literal

import polars as pl

Grain = Literal["day", "week", "month", "quarter", "year"]
Agg = Literal["sum", "mean", "count", "n_unique", "min", "max"]

_TRUNC: dict[str, str] = {
    "day": "1d", "week": "1w", "month": "1mo", "quarter": "1q", "year": "1y",
}

_AGG = {
    "sum": lambda c: c.sum(),
    "mean": lambda c: c.mean(),
    "count": lambda c: c.count(),
    "n_unique": lambda c: c.n_unique(),
    "min": lambda c: c.min(),
    "max": lambda c: c.max(),
}


def truncate_dates(dates: pl.Series, grain: Grain) -> pl.Series:
    """Map each date to its period-start (week → ISO Monday)."""
    return dates.dt.truncate(_TRUNC[grain])


def _finite_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _label(d: date, grain: Grain) -> str:
    if grain == "year":
        return f"{d.year}"
    if grain == "quarter":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if grain == "month":
        return f"{d.year}-{d.month:02d}"
    if grain == "week":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return d.isoformat()


def aggregate_series(df: pl.DataFrame, date_col: str, value_col: str,
                     grain: Grain, agg: Agg) -> dict:
    """Truncate date_col to grain, group, aggregate value_col, sort by period.

    Returns {"period_starts": [date], "labels": [str], "values": [float|None]}.
    Rows with a null period (null/unparseable date) are dropped.
    """
    period = truncate_dates(df[date_col], grain).alias("_period")
    work = df.with_columns(period).drop_nulls(subset=["_period"])
    grouped = (
        work.group_by("_period")
        .agg(_AGG[agg](pl.col(value_col)).alias("_value"))
        .sort("_period")
    )
    starts = grouped["_period"].to_list()
    values = [_finite_or_none(v) for v in grouped["_value"].to_list()]
    labels = [_label(d, grain) for d in starts]
    return {"period_starts": starts, "labels": labels, "values": values}


def suggest_grain(period_min: date, period_max: date) -> Grain:
    """Coarsest grain giving ~<=60 buckets; finest fallback = day."""
    span = (period_max - period_min).days
    if span <= 0:
        return "day"
    for grain, approx in (("day", 1), ("week", 7), ("month", 30),
                          ("quarter", 91), ("year", 365)):
        if span / approx <= 60:
            return grain  # type: ignore[return-value]
    return "year"


# ── comparison math ─────────────────────────────────────────────────────────

def _delta_pct(cur, prior):
    if cur is None or prior is None or prior == 0:
        return None
    d = (cur - prior) / prior * 100
    return round(d, 2) if math.isfinite(d) else None


def _period_key(d: date, grain: Grain):
    if grain == "year":
        return date(d.year, 1, 1)
    if grain == "quarter":
        return date(d.year, (d.month - 1) // 3 * 3 + 1, 1)
    if grain == "month":
        return date(d.year, d.month, 1)
    if grain == "day":
        return d
    iso = d.isocalendar()
    return ("W", iso[0], iso[1])


def _prior_year_key(d: date, grain: Grain):
    if grain == "year":
        return date(d.year - 1, 1, 1)
    if grain == "quarter":
        return date(d.year - 1, (d.month - 1) // 3 * 3 + 1, 1)
    if grain == "month":
        return date(d.year - 1, d.month, 1)
    if grain == "day":
        try:
            return date(d.year - 1, d.month, d.day)
        except ValueError:           # Feb 29 → Feb 28
            return date(d.year - 1, d.month, 28)
    iso = d.isocalendar()
    return ("W", iso[0] - 1, iso[1])


def _yoy(period_starts, values, grain):
    index = {_period_key(d, grain): v for d, v in zip(period_starts, values)}
    yoy_vals, deltas = [], []
    for d, v in zip(period_starts, values):
        prior = index.get(_prior_year_key(d, grain))
        yoy_vals.append(prior)
        deltas.append(_delta_pct(v, prior))
    return {"values": yoy_vals, "delta_pct": deltas}


def _pop(values):
    vals, deltas = [], []
    for i, v in enumerate(values):
        prior = values[i - 1] if i > 0 else None
        vals.append(prior)
        deltas.append(_delta_pct(v, prior))
    return {"values": vals, "delta_pct": deltas}


def _rolling(values, window):
    out = []
    for i in range(len(values)):
        chunk = [x for x in values[max(0, i - window + 1):i + 1] if x is not None]
        out.append(round(sum(chunk) / len(chunk), 4) if chunk else None)
    return out


def _reset_key(d: date, reset: str):
    if reset == "month":
        return (d.year, d.month)
    if reset == "quarter":
        return (d.year, (d.month - 1) // 3)
    return d.year


def _cumulative(period_starts, values, reset):
    out, run, cur_key = [], 0.0, None
    for d, v in zip(period_starts, values):
        key = _reset_key(d, reset)
        if key != cur_key:
            cur_key, run = key, 0.0
        if v is not None:
            run += v
        out.append(round(run, 4))
    return out


def _index100(values):
    base = next((v for v in values if v not in (None, 0)), None)
    if base is None:
        return [None] * len(values)
    return [round(v / base * 100, 2) if v is not None else None for v in values]


def _share(values):
    total = sum(v for v in values if v is not None)
    if not total:
        return [None] * len(values)
    return [round(v / total * 100, 2) if v is not None else None for v in values]


def add_comparisons(period_starts: list[date], values: list, grain: Grain,
                    comparisons: list[str], rolling_window: int = 7,
                    cumulative_reset: str = "year") -> dict:
    """Return only the requested comparison keys."""
    out: dict = {}
    if "yoy" in comparisons:
        out["yoy"] = _yoy(period_starts, values, grain)
    if "pop" in comparisons:
        out["pop"] = _pop(values)
    if "rolling" in comparisons:
        out["rolling"] = {"window": rolling_window,
                          "values": _rolling(values, rolling_window)}
    if "cumulative" in comparisons:
        out["cumulative"] = {"reset": cumulative_reset,
                             "values": _cumulative(period_starts, values, cumulative_reset)}
    if "index100" in comparisons:
        out["index100"] = {"values": _index100(values)}
    if "share" in comparisons:
        out["share"] = {"values": _share(values)}
    return out
