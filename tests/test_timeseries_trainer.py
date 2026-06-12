# tests/test_timeseries_trainer.py
import numpy as np
import polars as pl
import pytest
from modules.ml_pipeline.timeseries_trainer import run


def _ts_df(n=60):
    np.random.seed(42)
    dates = pl.date_range(
        start=pl.date(2019, 1, 1),
        end=pl.date(2023, 12, 1),
        interval="1mo",
        eager=True,
    ).head(n)
    y = np.sin(np.arange(n) * 2 * np.pi / 12) * 10 + 100 + np.random.randn(n) * 1.5
    return pl.DataFrame({"date": dates, "value": y.tolist()})


def test_sarimax_returns_required_keys():
    result = run(_ts_df(), "value", "date", horizon=12, exog_cols=[], algorithms=["sarimax"])
    assert "results" in result
    assert "winner" in result
    assert result["winner"] == "sarimax"
    r = result["results"]["sarimax"]
    assert "metrics" in r
    assert "forecast" in r
    assert len(r["forecast"]) == 12
    assert "rmse" in r["metrics"]


def test_exp_smoothing_runs():
    result = run(_ts_df(), "value", "date", horizon=6, exog_cols=[], algorithms=["exp_smoothing"])
    assert "exp_smoothing" in result["results"]
    assert len(result["results"]["exp_smoothing"]["forecast"]) == 6


def test_multi_algo_winner_has_lower_rmse():
    result = run(_ts_df(), "value", "date", horizon=6, exog_cols=[],
                 algorithms=["sarimax", "exp_smoothing"])
    winner = result["winner"]
    loser = [a for a in result["results"] if a != winner][0]
    assert (result["results"][winner]["metrics"]["rmse"] <=
            result["results"][loser]["metrics"]["rmse"])


def test_sarimax_with_exog():
    np.random.seed(42)
    n = 60
    dates = pl.date_range(
        start=pl.date(2019, 1, 1), end=pl.date(2023, 12, 1),
        interval="1mo", eager=True,
    ).head(n)
    y = np.sin(np.arange(n) * 2 * np.pi / 12) * 10 + 100 + np.random.randn(n)
    exog = np.random.randn(n)
    df = pl.DataFrame({"date": dates, "value": y.tolist(), "extra": exog.tolist()})
    result = run(df, "value", "date", horizon=6, exog_cols=["extra"], algorithms=["sarimax"])
    assert "sarimax" in result["results"]
