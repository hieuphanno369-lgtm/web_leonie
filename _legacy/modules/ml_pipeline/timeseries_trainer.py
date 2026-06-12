# modules/ml_pipeline/timeseries_trainer.py
import numpy as np
import polars as pl
from sklearn.metrics import mean_squared_error


def _rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _mape(y_true, y_pred):
    denom = np.where(y_true == 0, 1, y_true)
    return float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)


def _run_sarimax(y, exog, horizon):
    import pmdarima as pm
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    n = len(y)
    exog_arr = np.column_stack(list(exog.values())) if exog else None

    # Seasonal chỉ bật khi đủ dữ liệu
    use_seasonal = n >= 24
    m = 12 if use_seasonal else 1

    # Dùng PP test thay ADF — hoạt động tốt hơn với series ngắn
    try:
        auto = pm.auto_arima(
            y, exogenous=exog_arr,
            seasonal=use_seasonal, m=m,
            stepwise=True, suppress_warnings=True,
            error_action="ignore",
            max_p=2, max_q=2, max_P=1, max_Q=1,
            max_order=4,
            test="pp",
            information_criterion="aic",
        )
        order = auto.order
        seasonal_order = auto.seasonal_order
    except Exception:
        # Fallback ARIMA(1,1,1) khi data quá ngắn
        order = (1, 1, 1)
        seasonal_order = (0, 0, 0, 0)

    model = SARIMAX(y, exog=exog_arr, order=order, seasonal_order=seasonal_order)
    fit = model.fit(disp=False)

    # Exog forecast: tile giá trị cuối nếu không đủ horizon
    if exog_arr is not None:
        exog_fc = np.tile(exog_arr[-1], (horizon, 1))
    else:
        exog_fc = None

    fc = fit.get_forecast(steps=horizon, exog=exog_fc)
    in_sample = fit.fittedvalues
    return fit, {
        "rmse": _rmse(y, in_sample),
        "mape": _mape(y, in_sample),
        "aic": float(fit.aic),
    }, in_sample, fc.predicted_mean, fc.conf_int(alpha=0.05)


def _run_exp_smoothing(y, horizon):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    m = 12 if len(y) >= 24 else max(2, len(y) // 4)
    model = ExponentialSmoothing(y, trend="add", seasonal="add", seasonal_periods=m)
    fit = model.fit()
    forecast = fit.forecast(horizon)
    in_sample = fit.fittedvalues
    return fit, {
        "rmse": _rmse(y, in_sample),
        "mape": _mape(y, in_sample),
    }, in_sample, forecast, None


def _run_prophet(y, dates, exog, horizon):
    import pandas as pd
    from prophet import Prophet

    m = Prophet()
    df_p = pd.DataFrame({"ds": pd.to_datetime([str(d) for d in dates]), "y": y})
    for col, vals in exog.items():
        m.add_regressor(col)
        df_p[col] = vals
    m.fit(df_p)
    future = m.make_future_dataframe(periods=horizon, freq="MS")
    for col in exog:
        last_val = exog[col][-1]
        future[col] = np.where(future.index >= len(dates), last_val, 0)
        future[col][:len(dates)] = exog[col]
    fc = m.predict(future)
    in_sample_pred = fc["yhat"].values[:len(y)]
    forecast_mean = fc["yhat"].values[len(y):]
    conf_int = fc[["yhat_lower", "yhat_upper"]].values[len(y):]
    return m, {
        "rmse": _rmse(y, in_sample_pred),
        "mape": _mape(y, in_sample_pred),
    }, in_sample_pred, forecast_mean, conf_int


def run(
    df: pl.DataFrame,
    target: str,
    date_col: str,
    horizon: int,
    exog_cols: list[str],
    algorithms: list[str],
) -> dict:
    if not algorithms:
        raise ValueError("algorithms list must not be empty")
    # Dedupe: exog_cols không được trùng date_col hoặc target
    safe_exog = [c for c in exog_cols if c not in (date_col, target)]
    cols = list(dict.fromkeys([date_col, target] + safe_exog))
    clean = df.select(cols).drop_nulls().sort(date_col)
    y = clean[target].to_numpy().astype(float)
    dates = clean[date_col].to_list()
    exog = {col: clean[col].to_numpy().astype(float) for col in safe_exog}
    n = len(y)

    results = {}
    for algo in algorithms:
        if algo == "sarimax":
            model, metrics, in_sample, forecast, conf_int = _run_sarimax(y, exog, horizon)
        elif algo == "exp_smoothing":
            model, metrics, in_sample, forecast, conf_int = _run_exp_smoothing(y, horizon)
        elif algo == "prophet":
            model, metrics, in_sample, forecast, conf_int = _run_prophet(y, dates, exog, horizon)
        else:
            raise ValueError(f"Unknown algorithm: {algo}")
        results[algo] = {
            "model": model,
            "metrics": metrics,
            "y_pred": in_sample,
            "y_test": y,
            "forecast": forecast,
            "conf_int": conf_int,
            "forecast_index": list(range(n, n + horizon)),
            "history_dates": dates,
            "feature_names": [target],
            "problem_type": "timeseries",
        }

    winner = min(results, key=lambda a: results[a]["metrics"]["rmse"])
    return {"results": results, "winner": winner, "problem_type": "timeseries"}
