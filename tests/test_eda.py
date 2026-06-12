import polars as pl
import pytest
from modules.ml_pipeline.eda import run_eda


def _sample_df() -> pl.DataFrame:
    return pl.DataFrame({
        "age":      [25, 30, 35, None, 1000],   # 1 null, 1 outlier
        "revenue":  [1000, 2000, 3000, 4000, 5000],
        "city":     ["HN", "HCM", "HN", "HCM", "HN"],
        "dup_flag": [1, 1, 1, 1, 1],
    })


def test_schema_has_all_cols():
    result = run_eda(_sample_df())
    col_names = [r["col"] for r in result["schema"]]
    assert "age" in col_names
    assert "revenue" in col_names
    assert "city" in col_names


def test_null_pct_correct():
    result = run_eda(_sample_df())
    age_info = next(r for r in result["schema"] if r["col"] == "age")
    assert age_info["null_pct"] == pytest.approx(20.0, abs=0.1)


def test_duplicate_count():
    df = pl.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    result = run_eda(df)
    assert result["duplicate_count"] == 1


def test_no_duplicates():
    df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = run_eda(df)
    assert result["duplicate_count"] == 0


def test_outlier_detected():
    result = run_eda(_sample_df())
    assert "age" in result["outlier_summary"]
    assert result["outlier_summary"]["age"]["outlier_count"] >= 1


def test_skew_kurt_only_numeric():
    result = run_eda(_sample_df())
    assert "city" not in result["skew_kurt"]
    assert "age" in result["skew_kurt"] and "revenue" in result["skew_kurt"]


def test_warnings_on_high_null():
    df = pl.DataFrame({"a": [1, None, None, None, None, None]})
    result = run_eda(df)
    assert any("null" in w.lower() for w in result["warnings"])


def test_describe_returns_polars_df():
    result = run_eda(_sample_df())
    assert isinstance(result["describe"], pl.DataFrame)
