import polars as pl
import pytest
import random
from modules.ml_pipeline.feature_selector import compute_feature_importance


def _regression_df() -> pl.DataFrame:
    random.seed(42)
    n = 100
    x1 = [float(i) for i in range(n)]
    x2 = [random.random() for _ in range(n)]
    y  = [x1[i] * 2.0 + x2[i] * 0.1 for i in range(n)]
    return pl.DataFrame({"x1": x1, "x2": x2, "target": y})


def test_returns_list_of_dicts():
    result = compute_feature_importance(_regression_df(), "target", "regression")
    assert isinstance(result, list)
    assert all("feature" in r and "score" in r for r in result)


def test_excludes_target_from_features():
    result = compute_feature_importance(_regression_df(), "target", "regression")
    feature_names = [r["feature"] for r in result]
    assert "target" not in feature_names


def test_sorted_descending():
    result = compute_feature_importance(_regression_df(), "target", "regression")
    scores = [r["score"] for r in result]
    assert scores == sorted(scores, reverse=True)


def test_x1_ranked_first_for_regression():
    result = compute_feature_importance(_regression_df(), "target", "regression")
    assert result[0]["feature"] == "x1"


def test_clustering_uses_variance():
    df = pl.DataFrame({
        "big_var":   [float(i * 100) for i in range(50)],
        "small_var": [float(i * 0.01) for i in range(50)],
    })
    result = compute_feature_importance(df, "", "clustering")
    assert result[0]["feature"] == "big_var"
