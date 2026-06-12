# modules/ml_pipeline/ai_recommender.py
import json
import polars as pl
import polars.selectors as cs
from modules.ai_client import call_ai


def _build_prompt(df: pl.DataFrame) -> str:
    schema_lines = []
    for col in df.columns:
        schema_lines.append(f"  - {col}: {df[col].dtype}, nulls={df[col].null_count()}")

    numeric_cols = df.select(cs.numeric()).columns
    stat_lines = []
    for col in numeric_cols[:10]:
        s = df[col].drop_nulls()
        if len(s) > 0:
            stat_lines.append(
                f"  - {col}: min={s.min():.2f}, max={s.max():.2f}, mean={s.mean():.2f}"
            )

    return (
        "You are an ML advisor. Analyze the dataset and recommend the best approach.\n\n"
        f"Dataset: {df.height} rows, {df.width} columns\n\n"
        "Columns:\n" + "\n".join(schema_lines) + "\n\n"
        "Numeric stats:\n" + ("\n".join(stat_lines) or "  none") + "\n\n"
        "Reply with ONLY a JSON object — no markdown, no explanation:\n"
        '{"method":"supervised"|"unsupervised"|"timeseries",'
        '"problem_type":"regression"|"classification"|"clustering"|"timeseries",'
        '"target":"column_name_or_empty","features":["col1","col2"],'
        '"algorithm":"one algorithm name","reasoning":"1-2 sentences"}'
    )


def _fallback(df: pl.DataFrame) -> dict:
    numeric = df.select(cs.numeric()).columns
    features = numeric[:-1] if len(numeric) > 1 else numeric
    target = numeric[-1] if numeric else (df.columns[-1] if df.columns else "")
    return {
        "method": "supervised",
        "problem_type": "regression",
        "target": target,
        "features": list(features),
        "algorithm": "XGBoost",
        "reasoning": "Default recommendation — AI unavailable.",
    }


def recommend(df_clean: pl.DataFrame) -> dict:
    prompt = _build_prompt(df_clean)
    try:
        raw = call_ai(prompt, max_tokens=400).strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        required = {"method", "problem_type", "target", "features", "algorithm", "reasoning"}
        if not required.issubset(data.keys()):
            return _fallback(df_clean)
        return data
    except Exception:
        return _fallback(df_clean)
