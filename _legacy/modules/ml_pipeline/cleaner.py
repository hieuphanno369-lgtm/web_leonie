import polars as pl
import polars.selectors as cs


def run_clean(df: pl.DataFrame, config: dict) -> tuple[pl.DataFrame, dict]:
    """Apply cleaning steps based on config flags.

    config keys (all optional, default True):
      dedupe: bool
      fill_null: bool
      flag_outliers: bool      # adds {col}_is_outlier bool columns
      encode_categoricals: bool
      split_dates: bool        # splits date cols → year/month/day_of_week/quarter

    Returns (cleaned_df, summary_dict)
    summary_dict = {
      "rows_before": int, "rows_after": int,
      "nulls_filled": dict,    # {col: count_filled}
      "outliers_flagged": dict, # {col: count_flagged}
      "encoded_cols": list[str],
      "date_cols_split": list[str],
    }
    """
    dedupe           = config.get("dedupe", True)
    fill_null        = config.get("fill_null", True)
    flag_outliers    = config.get("flag_outliers", True)
    encode_cats      = config.get("encode_categoricals", True)
    split_dates_flag = config.get("split_dates", True)

    rows_before = df.height
    nulls_filled: dict[str, int] = {}
    outliers_flagged: dict[str, int] = {}
    encoded_cols: list[str] = []
    date_cols_split: list[str] = []

    result = df.clone()

    # 1. Deduplicate
    if dedupe:
        result = result.unique()

    # 2. Fill nulls
    if fill_null:
        for col in result.columns:
            null_count = result[col].null_count()
            if null_count == 0:
                continue
            if result[col].dtype in (pl.Float32, pl.Float64, pl.Int8, pl.Int16,
                                      pl.Int32, pl.Int64, pl.UInt8, pl.UInt16,
                                      pl.UInt32, pl.UInt64):
                median_val = result[col].drop_nulls().median()
                if median_val is not None:
                    result = result.with_columns(
                        pl.col(col).fill_null(pl.lit(median_val).cast(result[col].dtype))
                    )
                    nulls_filled[col] = null_count
            elif result[col].dtype in (pl.Utf8, pl.String):
                mode_series = result[col].drop_nulls().mode()
                if mode_series.len() > 0:
                    mode_val = mode_series[0]
                    result = result.with_columns(pl.col(col).fill_null(mode_val))
                    nulls_filled[col] = null_count

    # 3. Flag outliers (IQR × 1.5) — adds {col}_is_outlier bool column
    if flag_outliers:
        numeric_cols = result.select(cs.numeric()).columns
        for col in numeric_cols:
            series = result[col].drop_nulls()
            if series.len() < 4:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            if q1 is None or q3 is None:
                continue
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            flag_col = f"{col}_is_outlier"
            result = result.with_columns(
                ((pl.col(col) < lower) | (pl.col(col) > upper)).alias(flag_col)
            )
            outliers_flagged[col] = int(result[flag_col].fill_null(False).sum())

    # 4. Encode categoricals (label encode: string → integer codes)
    if encode_cats:
        for col in result.columns:
            if result[col].dtype in (pl.Utf8, pl.String):
                categories = result[col].drop_nulls().unique().sort().to_list()
                mapping = {v: i for i, v in enumerate(categories)}
                result = result.with_columns(
                    pl.col(col).map_elements(lambda x: mapping.get(x, 0), return_dtype=pl.Int32)
                )
                encoded_cols.append(col)

    # 5. Split date columns → year, month, day_of_week, quarter
    if split_dates_flag:
        for col in result.columns:
            if result[col].dtype == pl.Date:
                result = result.with_columns([
                    pl.col(col).dt.year().alias(f"{col}_year"),
                    pl.col(col).dt.month().alias(f"{col}_month"),
                    pl.col(col).dt.weekday().alias(f"{col}_day_of_week"),
                    pl.col(col).dt.quarter().alias(f"{col}_quarter"),
                ])
                date_cols_split.append(col)

    summary = {
        "rows_before": rows_before,
        "rows_after": result.height,
        "nulls_filled": nulls_filled,
        "outliers_flagged": outliers_flagged,
        "encoded_cols": encoded_cols,
        "date_cols_split": date_cols_split,
    }
    return result, summary
