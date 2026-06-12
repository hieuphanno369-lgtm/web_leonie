# modules/ml_pipeline/feature_selector.py
import polars as pl
import polars.selectors as cs
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier


def compute_feature_importance(
    df: pl.DataFrame,
    target: str,
    problem_type: str,
) -> list[dict]:
    """
    Compute feature importance using RandomForest (regression/classification)
    or variance (clustering/no target).
    Returns list of dicts sorted descending by score.
    """
    numeric_df = df.select(cs.numeric())
    feature_cols = [c for c in numeric_df.columns if c != target]

    if not feature_cols:
        return []

    if problem_type == "clustering" or not target or target not in df.columns:
        # Use variance as proxy importance
        results = []
        for col in feature_cols:
            v = df[col].drop_nulls().var()
            var = float(v) if v is not None else 0.0
            results.append({"feature": col, "score": round(var, 6)})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # Drop rows with null in feature or target
    clean_df = df.select(feature_cols + [target]).drop_nulls()
    if clean_df.height < 10:
        if clean_df.height == 0:
            return []
        # Not enough data — fall back to correlation
        results = []
        for col in feature_cols:
            c = clean_df[col].corr(clean_df[target])
            corr = abs(float(c)) if c is not None else 0.0
            results.append({"feature": col, "score": round(corr, 6)})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    X = clean_df.select(feature_cols).to_numpy()
    y = clean_df[target].to_numpy()

    if problem_type == "classification":
        model = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
    else:
        model = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)

    model.fit(X, y)
    importances = model.feature_importances_

    results = [
        {"feature": col, "score": round(float(imp), 6)}
        for col, imp in zip(feature_cols, importances)
    ]
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
