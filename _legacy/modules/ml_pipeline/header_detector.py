import re
import polars as pl


def _looks_like_data_value(val: str) -> bool:
    """Returns True if the value looks like actual data (number, date, known pattern)."""
    val = val.strip()
    if not val:
        return False
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val):   # date (exact match only)
        return True
    try:
        float(val.replace(",", ""))
        return True
    except ValueError:
        pass
    return False


def _row_is_metadata(row_values: list[str], total_cols: int) -> bool:
    """
    A row looks like metadata if:
    - Most cells are empty, OR
    - First cell is a long free-text string spanning the row (merged cell simulation)
    """
    non_empty = [v for v in row_values if v.strip()]
    if len(non_empty) == 0:
        return True
    # If only 1 cell has content and it's a long string and rest empty
    if len(non_empty) == 1 and len(non_empty[0]) > 15:
        return True
    # If half or fewer of the cells have content (fixes 2-column edge case)
    if len(non_empty) * 2 <= total_cols:
        return True
    return False


def _row_looks_like_header(row_values: list[str]) -> bool:
    """
    A row looks like a header if:
    - Most values are non-numeric strings
    - At least half cells non-empty
    """
    non_empty = [v for v in row_values if v.strip()]
    if not non_empty:
        return False
    data_like = [v for v in non_empty if _looks_like_data_value(v)]
    # Header has few data-like values
    return len(data_like) / len(non_empty) < 0.3


def _clean_column_names(names: list[str]) -> list[str]:
    """Rename empty or duplicate column names."""
    used: set[str] = set()
    result = []
    for i, name in enumerate(names):
        clean = name.strip()
        if not clean:
            clean = f"col_{i + 1}"
        if clean not in used:
            used.add(clean)
            result.append(clean)
        else:
            counter = 1
            candidate = f"{clean}_{counter}"
            while candidate in used:
                counter += 1
                candidate = f"{clean}_{counter}"
            used.add(candidate)
            result.append(candidate)
    return result


def detect_header(df_raw: pl.DataFrame) -> dict:
    """
    Scan up to the first 5 rows to find the real header row.
    Returns header_row index, skip_rows count, proposed column names, and warnings.
    """
    if df_raw.height == 0 or df_raw.width == 0:
        return {
            "header_row": 0,
            "skip_rows": 0,
            "proposed_columns": list(df_raw.columns),
            "warnings": ["DataFrame is empty — defaulting to row 0."],
        }

    n_rows = min(5, df_raw.height)
    n_cols = df_raw.width
    warnings: list[str] = []
    header_row = 0

    rows_as_str: list[list[str]] = []
    for r in range(n_rows):
        rows_as_str.append([str(df_raw[c][r]) for c in df_raw.columns])

    for r in range(n_rows):
        row = rows_as_str[r]
        if _row_is_metadata(row, n_cols):
            warnings.append(f"Row {r} looks like metadata/title, skipping.")
            header_row = r + 1
        elif _row_looks_like_header(row):
            header_row = r
            break
        # No else: if it looks like data, just stop scanning; keep header_row as-is

    if header_row >= df_raw.height:
        header_row = 0

    raw_col_names = [str(df_raw[c][header_row]) for c in df_raw.columns]
    proposed_columns = _clean_column_names(raw_col_names)

    return {
        "header_row": header_row,
        "skip_rows": header_row,
        "proposed_columns": proposed_columns,
        "warnings": warnings,
    }
