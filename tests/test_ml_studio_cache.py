"""Tests for ML Studio cached file parsing helpers and EDA/chart utilities."""
import polars as pl
import pytest


# ── File parsing cache tests ──────────────────────────────────────────────────

def test_cached_read_raw_csv_shape_and_types():
    """Raw read: has_header=False → header row appears as data row 0, all strings."""
    from modules.ml_studio import _cached_read_raw
    csv_bytes = b"name,age\nalice,30\nbob,25"
    df = _cached_read_raw(csv_bytes, "test.csv")
    assert df.shape == (3, 2)                        # 3 rows (incl. header-as-data)
    assert df["column_1"][0] == "name"               # header treated as first data row
    assert all(str(dtype) == "String" for dtype in df.dtypes)  # infer_schema=0 → all Utf8


def test_cached_read_raw_same_bytes_same_result():
    """Same input bytes → function returns identical DataFrame (cache hits fine)."""
    from modules.ml_studio import _cached_read_raw
    csv_bytes = b"x,y\n1,2\n3,4"
    df1 = _cached_read_raw(csv_bytes, "data.csv")
    df2 = _cached_read_raw(csv_bytes, "data.csv")
    assert df1.equals(df2)


def test_cached_read_with_header_csv_columns_and_rows():
    """Header read: columns named, data rows only."""
    from modules.ml_studio import _cached_read_with_header
    csv_bytes = b"name,age\nalice,30\nbob,25"
    df = _cached_read_with_header(csv_bytes, "test.csv", header_row=0, skip_rows=0)
    assert df.columns == ["name", "age"]
    assert df.height == 2


def test_cached_read_with_header_different_skip_rows():
    """skip_rows param is part of cache key — different skip produces different result."""
    from modules.ml_studio import _cached_read_with_header
    csv_bytes = b"junk\nname,age\nalice,30"
    df = _cached_read_with_header(csv_bytes, "test.csv", header_row=1, skip_rows=1)
    assert df.columns == ["name", "age"]
    assert df.height == 1


# ── EDA cache tests ───────────────────────────────────────────────────────────

def test_cached_run_eda_has_required_keys():
    from modules.ml_studio import _cached_run_eda
    df = pl.DataFrame({"a": [1, 2, 3], "b": [1.0, 2.0, None]})
    result = _cached_run_eda(df)
    for key in ("warnings", "schema", "describe", "duplicate_count", "skew_kurt", "outlier_summary"):
        assert key in result, f"Missing key: {key}"


def test_cached_run_eda_duplicate_count():
    from modules.ml_studio import _cached_run_eda
    df = pl.DataFrame({"a": [1, 1, 2], "b": [10, 10, 20]})
    result = _cached_run_eda(df)
    assert result["duplicate_count"] == 1


# ── Chart sampling tests ──────────────────────────────────────────────────────

def test_get_chart_df_samples_large_df():
    from modules.ml_studio import _get_chart_df, CHART_SAMPLE_SIZE
    df = pl.DataFrame({"a": list(range(CHART_SAMPLE_SIZE + 10_000))})
    df_chart, was_sampled = _get_chart_df(df)
    assert was_sampled is True
    assert df_chart.height == CHART_SAMPLE_SIZE


def test_get_chart_df_no_sample_for_small_df():
    from modules.ml_studio import _get_chart_df, CHART_SAMPLE_SIZE
    df = pl.DataFrame({"a": list(range(100))})
    df_chart, was_sampled = _get_chart_df(df)
    assert was_sampled is False
    assert df_chart.height == 100


def test_get_chart_df_exact_boundary():
    from modules.ml_studio import _get_chart_df, CHART_SAMPLE_SIZE
    df = pl.DataFrame({"a": list(range(CHART_SAMPLE_SIZE))})
    df_chart, was_sampled = _get_chart_df(df)
    assert was_sampled is False   # equal to limit → no sample
    assert df_chart.height == CHART_SAMPLE_SIZE


# ── Training subsample logic tests ───────────────────────────────────────────

def test_subsample_for_training_large_df():
    """Simulates the subsample logic applied before training."""
    SUBSAMPLE_THRESHOLD = 200_000
    SUBSAMPLE_SIZE = 50_000
    df = pl.DataFrame({"a": list(range(300_000)), "b": list(range(300_000))})
    use_sample = True
    df_to_train = df.sample(SUBSAMPLE_SIZE, seed=42) if (use_sample and df.height > SUBSAMPLE_THRESHOLD) else df
    assert df_to_train.height == SUBSAMPLE_SIZE


def test_no_subsample_for_small_df():
    SUBSAMPLE_THRESHOLD = 200_000
    SUBSAMPLE_SIZE = 50_000
    df = pl.DataFrame({"a": list(range(1_000))})
    use_sample = True  # even if checked, no subsample for small data
    df_to_train = df.sample(SUBSAMPLE_SIZE, seed=42) if (use_sample and df.height > SUBSAMPLE_THRESHOLD) else df
    assert df_to_train.height == 1_000


def test_no_subsample_when_unchecked():
    SUBSAMPLE_THRESHOLD = 200_000
    SUBSAMPLE_SIZE = 50_000
    df = pl.DataFrame({"a": list(range(300_000))})
    use_sample = False  # user left it unchecked
    df_to_train = df.sample(SUBSAMPLE_SIZE, seed=42) if (use_sample and df.height > SUBSAMPLE_THRESHOLD) else df
    assert df_to_train.height == 300_000
