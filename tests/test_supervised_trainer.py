# tests/test_supervised_trainer.py
import numpy as np
import polars as pl
import pytest
from modules.ml_pipeline.supervised_trainer import run


def _reg_df():
    np.random.seed(42)
    n = 120
    x1 = np.random.randn(n)
    x2 = np.random.randn(n)
    y = 2 * x1 + 3 * x2 + np.random.randn(n) * 0.1
    return pl.DataFrame({"x1": x1, "x2": x2, "target": y})


def _cls_df():
    np.random.seed(42)
    n = 120
    x1 = np.random.randn(n)
    x2 = np.random.randn(n)
    y = ((x1 + x2) > 0).astype(int)
    return pl.DataFrame({"x1": x1, "x2": x2, "label": y})


def test_regression_returns_required_keys():
    result = run(_reg_df(), ["x1", "x2"], "target", "regression", ["xgboost"])
    assert "results" in result
    assert "winner" in result
    assert "problem_type" in result
    assert result["winner"] == "xgboost"


def test_regression_algo_result_keys():
    result = run(_reg_df(), ["x1", "x2"], "target", "regression", ["xgboost"])
    r = result["results"]["xgboost"]
    assert "model" in r
    assert "metrics" in r
    assert "y_pred" in r
    assert "y_test" in r
    assert "feature_names" in r
    assert "feature_importances" in r
    assert "rmse" in r["metrics"]
    assert "mae" in r["metrics"]
    assert "r2" in r["metrics"]


def test_regression_multi_algo_winner():
    result = run(_reg_df(), ["x1", "x2"], "target", "regression", ["xgboost", "random_forest"])
    assert result["winner"] in ["xgboost", "random_forest"]
    assert len(result["results"]) == 2
    winner = result["winner"]
    loser = [a for a in result["results"] if a != winner][0]
    assert result["results"][winner]["metrics"]["rmse"] <= result["results"][loser]["metrics"]["rmse"]


def test_classification_returns_f1():
    result = run(_cls_df(), ["x1", "x2"], "label", "classification", ["xgboost"])
    r = result["results"]["xgboost"]
    assert "accuracy" in r["metrics"]
    assert "f1" in r["metrics"]
    assert "auc_roc" in r["metrics"]


def test_mlp_regression_with_config():
    nn_config = {"hidden_layer_sizes": [50, 25], "max_iter": 100, "learning_rate_init": 0.01}
    result = run(_reg_df(), ["x1", "x2"], "target", "regression", ["mlp"], nn_config=nn_config)
    assert "mlp" in result["results"]
    assert result["results"]["mlp"]["metrics"]["rmse"] > 0


def test_svm_classification():
    result = run(_cls_df(), ["x1", "x2"], "label", "classification", ["svm"])
    assert "svm" in result["results"]
    assert result["results"]["svm"]["metrics"]["accuracy"] > 0
