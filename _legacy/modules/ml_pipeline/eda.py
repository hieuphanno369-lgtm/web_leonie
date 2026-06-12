# modules/ml_pipeline/eda.py
import polars as pl
import polars.selectors as cs


def run_eda(df: pl.DataFrame) -> dict:
    """Full EDA pass: schema, describe, skew/kurtosis, duplicates, outliers, warnings."""
    warnings: list[str] = []

    if df.height == 0:
        return {
            "schema": [],
            "describe": pl.DataFrame(),
            "skew_kurt": {},
            "duplicate_count": 0,
            "outlier_summary": {},
            "warnings": ["DataFrame is empty — no EDA to run."],
        }

    # --- Schema ---
    schema_info = []
    for col in df.columns:
        null_count = df[col].null_count()
        null_pct = null_count / df.height * 100
        unique_count = df[col].n_unique()
        schema_info.append({
            "col": col,
            "dtype": str(df[col].dtype),
            "null_pct": round(null_pct, 2),
            "null_count": null_count,
            "unique_count": unique_count,
        })
        if null_pct > 5:
            warnings.append(f"Column '{col}' has {null_pct:.1f}% null values.")

    # --- Describe (integer + float only, exclude datetime/date) ---
    numeric_df = df.select(cs.integer() | cs.float())
    if numeric_df.width > 0:
        import pandas as pd
        import numpy as np
        pdf = numeric_df.to_pandas()
        raw = pdf.describe().T  # columns: count mean std min 25% 50% 75% max
        raw.insert(0, "column", raw.index)
        raw = raw.reset_index(drop=True)
        # round floats for readability
        for c in ["mean", "std", "min", "25%", "50%", "75%", "max"]:
            if c in raw.columns:
                raw[c] = raw[c].round(4)
        describe_df = pl.from_pandas(raw)
    else:
        describe_df = pl.DataFrame()

    # --- Skewness & Kurtosis (re-select to be safe) ---
    numeric_df = df.select(cs.integer() | cs.float())
    skew_kurt: dict[str, dict] = {}
    for col in numeric_df.columns:
        series = df[col].drop_nulls()
        if series.len() < 3:
            continue
        try:
            skewness = series.skew()
            kurtosis = series.kurtosis()
            skew_kurt[col] = {
                "skewness": round(skewness, 4) if skewness is not None else None,
                "kurtosis": round(kurtosis, 4) if kurtosis is not None else None,
            }
            if skewness is not None and abs(skewness) > 2:
                warnings.append(f"Column '{col}' has high skewness ({skewness:.2f}) — consider log transform.")
        except Exception as e:
            warnings.append(f"Column '{col}': skew/kurtosis failed — {e}")

    # --- Duplicates ---
    duplicate_count = df.height - df.unique().height

    # --- Outlier Summary (IQR method) ---
    outlier_summary: dict[str, dict] = {}
    for col in numeric_df.columns:
        series = df[col].drop_nulls()
        if series.len() < 4:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        if q1 is None or q3 is None:
            continue
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        outlier_summary[col] = {
            "iqr_lower": round(lower, 4),
            "iqr_upper": round(upper, 4),
            "outlier_count": outlier_count,
        }
        if outlier_count > 0:
            pct = outlier_count / series.len() * 100
            if pct > 5:
                warnings.append(f"Column '{col}' has {outlier_count} outliers ({pct:.1f}%) by IQR method.")

    return {
        "schema": schema_info,
        "describe": describe_df,
        "skew_kurt": skew_kurt,
        "duplicate_count": duplicate_count,
        "outlier_summary": outlier_summary,
        "warnings": warnings,
    }
