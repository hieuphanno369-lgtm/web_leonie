import polars as pl
import pytest
from modules.ml_pipeline.header_detector import detect_header


def _make_df(rows: list[list]) -> pl.DataFrame:
    """Build a string DataFrame from raw rows (simulates CSV read with no header)."""
    cols = [f"col_{i}" for i in range(len(rows[0]))]
    return pl.DataFrame({c: [str(r[i]) for r in rows] for i, c in enumerate(cols)})


def test_clean_header_at_row0():
    df = _make_df([
        ["name", "age", "revenue"],
        ["Alice", "30", "1000"],
        ["Bob", "25", "2000"],
    ])
    result = detect_header(df)
    assert result["header_row"] == 0
    assert result["skip_rows"] == 0
    assert "name" in result["proposed_columns"]


def test_metadata_rows_before_header():
    df = _make_df([
        ["Sales Report Q1 2026", "", ""],
        ["Generated: 2026-05-09", "", ""],
        ["name", "age", "revenue"],
        ["Alice", "30", "1000"],
    ])
    result = detect_header(df)
    assert result["header_row"] == 2
    assert result["skip_rows"] == 2


def test_duplicate_columns_renamed():
    df = _make_df([
        ["name", "name", "revenue"],
        ["Alice", "X", "1000"],
    ])
    result = detect_header(df)
    cols = result["proposed_columns"]
    assert len(cols) == len(set(cols)), "Duplicate column names not resolved"


def test_empty_columns_renamed():
    df = _make_df([
        ["name", "", "revenue"],
        ["Alice", "X", "1000"],
    ])
    result = detect_header(df)
    cols = result["proposed_columns"]
    assert all(c.strip() != "" for c in cols)


def test_warnings_on_metadata():
    df = _make_df([
        ["Sales Report Q1 2026", "", ""],
        ["name", "age", "revenue"],
        ["Alice", "30", "1000"],
    ])
    result = detect_header(df)
    assert len(result["warnings"]) > 0
