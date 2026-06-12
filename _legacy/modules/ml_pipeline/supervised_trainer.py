# modules/ml_pipeline/supervised_trainer.py
import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.svm import SVR, SVC
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, f1_score, roc_auc_score,
)
import xgboost as xgb


def _reg_metrics(y_test, y_pred):
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
    }


def _cls_metrics(y_test, y_pred, model, X_test):
    n_classes = len(np.unique(y_test))
    auc = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_test)
        try:
            if n_classes == 2:
                auc = float(roc_auc_score(y_test, proba[:, 1]))
            else:
                auc = float(roc_auc_score(y_test, proba, multi_class="ovr"))
        except Exception:
            auc = None
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred, average="weighted")),
        "auc_roc": auc,
    }


def _build_reg(algo: str, nn_config: dict):
    if algo == "xgboost":
        return xgb.XGBRegressor(n_estimators=200, learning_rate=0.05, random_state=42, verbosity=0)
    if algo == "random_forest":
        return RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    if algo == "svm":
        return SVR(kernel="rbf")
    if algo == "mlp":
        return MLPRegressor(
            hidden_layer_sizes=tuple(nn_config.get("hidden_layer_sizes", [100, 50])),
            max_iter=nn_config.get("max_iter", 300),
            learning_rate_init=nn_config.get("learning_rate_init", 0.001),
            random_state=42,
        )
    raise ValueError(f"Unknown regression algorithm: {algo}")


def _build_cls(algo: str, nn_config: dict):
    if algo == "xgboost":
        return xgb.XGBClassifier(n_estimators=200, learning_rate=0.05, random_state=42,
                                  verbosity=0, eval_metric="logloss")
    if algo == "random_forest":
        return RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    if algo == "svm":
        return SVC(kernel="rbf", probability=True)
    if algo == "mlp":
        return MLPClassifier(
            hidden_layer_sizes=tuple(nn_config.get("hidden_layer_sizes", [100, 50])),
            max_iter=nn_config.get("max_iter", 300),
            learning_rate_init=nn_config.get("learning_rate_init", 0.001),
            random_state=42,
        )
    raise ValueError(f"Unknown classification algorithm: {algo}")


def _regression(df, features, target, algorithms, nn_config):
    if not algorithms:
        raise ValueError("algorithms list must not be empty")
    clean = df.select(features + [target]).drop_nulls()
    X = clean.select(features).to_numpy()
    y = clean[target].to_numpy()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}
    for algo in algorithms:
        model = _build_reg(algo, nn_config)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        fi = getattr(model, "feature_importances_", None)
        results[algo] = {
            "model": model,
            "metrics": _reg_metrics(y_test, y_pred),
            "y_pred": y_pred,
            "y_test": y_test,
            "feature_names": features,
            "feature_importances": fi.tolist() if fi is not None else None,
            "problem_type": "regression",
        }

    winner = min(results, key=lambda a: results[a]["metrics"]["rmse"])
    return {"results": results, "winner": winner, "problem_type": "regression"}


def _classification(df, features, target, algorithms, nn_config):
    if not algorithms:
        raise ValueError("algorithms list must not be empty")
    clean = df.select(features + [target]).drop_nulls()
    X = clean.select(features).to_numpy()
    y = clean[target].to_numpy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    results = {}
    for algo in algorithms:
        model = _build_cls(algo, nn_config)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        fi = getattr(model, "feature_importances_", None)
        results[algo] = {
            "model": model,
            "metrics": _cls_metrics(y_test, y_pred, model, X_test),
            "y_pred": y_pred,
            "y_test": y_test,
            "feature_names": features,
            "feature_importances": fi.tolist() if fi is not None else None,
            "problem_type": "classification",
        }

    winner = max(results, key=lambda a: results[a]["metrics"]["f1"])
    return {"results": results, "winner": winner, "problem_type": "classification"}


def run(
    df: pl.DataFrame,
    features: list[str],
    target: str,
    problem_type: str,
    algorithms: list[str],
    nn_config: dict = {},
) -> dict:
    if problem_type == "regression":
        return _regression(df, features, target, algorithms, nn_config)
    return _classification(df, features, target, algorithms, nn_config)
