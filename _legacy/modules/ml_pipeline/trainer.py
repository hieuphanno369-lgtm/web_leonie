# modules/ml_pipeline/trainer.py
import polars as pl
from modules.ml_pipeline import supervised_trainer, unsupervised_trainer, timeseries_trainer


def train_model(
    method: str,
    problem_type: str,
    algorithms: list[str],
    df: pl.DataFrame,
    features: list[str],
    target: str = "",
    date_col: str = "",
    horizon: int = 30,
    exog_cols: list[str] = [],
    nn_config: dict = {},
    dbscan_eps: float = 0.5,
    dbscan_min_samples: int = 5,
    hierarchical_k: int = 3,
) -> dict:
    if method == "supervised":
        return supervised_trainer.run(df, features, target, problem_type, algorithms, nn_config)
    if method == "unsupervised":
        return unsupervised_trainer.run(
            df, features, algorithms, dbscan_eps, dbscan_min_samples, hierarchical_k
        )
    if method == "timeseries":
        return timeseries_trainer.run(df, target, date_col, horizon, exog_cols, algorithms)
    raise ValueError(f"Unknown method: {method}")
