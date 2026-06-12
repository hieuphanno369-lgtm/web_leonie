# tests/test_unsupervised_trainer.py
import numpy as np
import polars as pl
import pytest
from modules.ml_pipeline.unsupervised_trainer import run


def _cluster_df():
    np.random.seed(42)
    c1 = np.random.randn(60, 2)
    c2 = np.random.randn(60, 2) + 6
    X = np.vstack([c1, c2])
    return pl.DataFrame({"x1": X[:, 0], "x2": X[:, 1]})


def test_kmeans_returns_required_keys():
    result = run(_cluster_df(), ["x1", "x2"], ["kmeans"])
    assert "results" in result
    assert "winner" in result
    assert result["winner"] == "kmeans"
    r = result["results"]["kmeans"]
    assert "model" in r
    assert "metrics" in r
    assert "cluster_labels" in r
    assert "X_2d" in r
    assert "silhouette" in r["metrics"]


def test_dbscan_runs():
    result = run(_cluster_df(), ["x1", "x2"], ["dbscan"])
    assert "dbscan" in result["results"]
    assert "silhouette" in result["results"]["dbscan"]["metrics"]


def test_hierarchical_runs():
    result = run(_cluster_df(), ["x1", "x2"], ["hierarchical"], hierarchical_k=2)
    assert "hierarchical" in result["results"]
    assert result["results"]["hierarchical"]["metrics"]["silhouette"] > 0


def test_multi_algo_winner_has_best_silhouette():
    result = run(_cluster_df(), ["x1", "x2"], ["kmeans", "hierarchical"])
    winner = result["winner"]
    loser = [a for a in result["results"] if a != winner][0]
    assert (result["results"][winner]["metrics"]["silhouette"] >=
            result["results"][loser]["metrics"]["silhouette"])


def test_dbscan_custom_params():
    result = run(_cluster_df(), ["x1", "x2"], ["dbscan"], dbscan_eps=1.0, dbscan_min_samples=3)
    assert "dbscan" in result["results"]
