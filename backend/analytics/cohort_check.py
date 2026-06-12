"""Cohort data-suitability pre-check (pure functions).

Cohort retention needs the same entity recurring across multiple periods.
check_suitability flags daily-aggregate / one-shot data before we render a
misleading '1 user / 100%' matrix. Cohort period = year-month.
"""
from __future__ import annotations

import polars as pl


def _result(suitable: bool, reasons: list[str], date_col: str, user_col: str) -> dict:
    return {
        "suitable": suitable,
        "reasons": reasons,
        "needs": "Cần cột định danh khách hàng lặp lại qua nhiều kỳ + cột ngày sự kiện.",
        "role_hint": {"date": date_col, "user": user_col},
    }


def check_suitability(df: pl.DataFrame, date_col: str, user_col: str,
                      parsed_dates: pl.Series) -> dict:
    """parsed_dates: date_col already parsed to Date (aligned to df rows)."""
    reasons: list[str] = []

    null_pct = df[user_col].null_count() / max(df.height, 1)
    if null_pct > 0.5:
        reasons.append(
            f"Cột '{user_col}' rỗng {null_pct * 100:.0f}% — không đủ để theo dõi khách hàng."
        )

    work = df.with_columns(parsed_dates.alias("_d")).drop_nulls(subset=["_d"])
    if work.height == 0:
        reasons.append("Không có ngày hợp lệ sau khi parse cột ngày.")
        return _result(False, reasons, date_col, user_col)

    work = work.with_columns(
        (pl.col("_d").dt.year() * 100 + pl.col("_d").dt.month()).alias("_p")
    )

    per_user = work.group_by(user_col).agg(pl.col("_p").n_unique().alias("_np"))
    recurring = per_user.filter(pl.col("_np") >= 2).height
    if recurring == 0:
        reasons.append(
            "Mỗi khách chỉ xuất hiện trong 1 kỳ — không đo được tỉ lệ giữ chân (retention)."
        )

    if work["_p"].n_unique() < 2:
        reasons.append("Dữ liệu chỉ có 1 kỳ — cần ít nhất 2 kỳ để tạo cohort.")

    return _result(len(reasons) == 0, reasons, date_col, user_col)
