import polars as pl
import pytest
from modules.ml_pipeline.cleaner import run_clean


def test_dedupe_removes_duplicate_rows():
    df = pl.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    cleaned, summary = run_clean(df, {"dedupe": True})
    assert cleaned.height == 2
    assert summary["rows_before"] == 3
    assert summary["rows_after"] == 2


def test_fill_null_numeric_with_median():
    df = pl.DataFrame({"score": [10.0, 20.0, None, 40.0]})
    cleaned, summary = run_clean(df, {"fill_null": True})
    assert cleaned["score"].null_count() == 0
    assert summary["nulls_filled"]["score"] == 1


def test_fill_null_categorical_with_mode():
    df = pl.DataFrame({"city": ["HN", "HN", None, "HCM"]})
    cleaned, summary = run_clean(df, {"fill_null": True, "dedupe": False, "encode_categoricals": False})
    assert cleaned["city"].null_count() == 0
    assert cleaned["city"][2] == "HN"   # mode is HN


def test_flag_outliers_adds_bool_col():
    df = pl.DataFrame({"score": [10.0, 20.0, 30.0, 1000.0]})
    cleaned, summary = run_clean(df, {"flag_outliers": True, "dedupe": False})
    assert "score_is_outlier" in cleaned.columns
    assert cleaned["score_is_outlier"].dtype == pl.Boolean
    # The 1000.0 value should be flagged as an outlier
    assert cleaned.filter(pl.col("score") == 1000.0)["score_is_outlier"][0] == True


def test_encode_categorical_label_encodes():
    df = pl.DataFrame({"city": ["HN", "HCM", "HN"], "val": [1, 2, 3]})
    cleaned, summary = run_clean(df, {"encode_categoricals": True})
    assert cleaned["city"].dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt32)
    assert "city" in summary["encoded_cols"]


def test_split_date_column():
    df = pl.DataFrame({"created_at": ["2026-01-15", "2026-03-22"]}).with_columns(
        pl.col("created_at").str.to_date()
    )
    cleaned, summary = run_clean(df, {"split_dates": True})
    assert "created_at_year" in cleaned.columns
    assert "created_at_month" in cleaned.columns
    assert "created_at_day_of_week" in cleaned.columns
    assert "created_at_quarter" in cleaned.columns
    assert "created_at" in summary["date_cols_split"]


def test_clean_returns_new_dataframe():
    df = pl.DataFrame({"a": [1, 2, 3]})
    cleaned, _ = run_clean(df, {})
    assert cleaned is not df
