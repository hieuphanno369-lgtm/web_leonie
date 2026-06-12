# modules/ml_pipeline/result_plotter.py
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

_THEME = "plotly_dark"


def _regression_figures(r: dict) -> list[dict]:
    y_test = r["y_test"]
    y_pred = r["y_pred"]
    feature_names = r["feature_names"]

    # Actual vs Predicted scatter
    fig1 = px.scatter(
        x=y_test, y=y_pred,
        labels={"x": "Actual", "y": "Predicted"},
        title="Actual vs Predicted",
        template=_THEME,
    )
    fig1.add_shape(type="line", x0=float(y_test.min()), y0=float(y_test.min()),
                   x1=float(y_test.max()), y1=float(y_test.max()),
                   line=dict(color="red", dash="dash"))

    # Feature importance
    model = r["primary_model"]
    importances = model.feature_importances_
    fig2 = px.bar(
        x=importances, y=feature_names,
        orientation="h",
        title="Feature Importance",
        template=_THEME,
    )
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})

    # Residual histogram
    residuals = y_test - y_pred
    fig3 = px.histogram(x=residuals, nbins=30, title="Residual Distribution", template=_THEME)

    return [
        {"title": "Actual vs Predicted", "fig": fig1},
        {"title": "Feature Importance", "fig": fig2},
        {"title": "Residuals", "fig": fig3},
    ]


def _classification_figures(r: dict) -> list[dict]:
    from sklearn.metrics import confusion_matrix
    y_test = r["y_test"]
    y_pred = r["y_pred"]
    feature_names = r["feature_names"]

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    fig1 = px.imshow(cm, text_auto=True, title="Confusion Matrix", template=_THEME,
                     color_continuous_scale="Blues")

    # Feature importance
    model = r["primary_model"]
    importances = model.feature_importances_
    fig2 = px.bar(
        x=importances, y=feature_names,
        orientation="h", title="Feature Importance", template=_THEME,
    )
    fig2.update_layout(yaxis={"categoryorder": "total ascending"})

    return [
        {"title": "Confusion Matrix", "fig": fig1},
        {"title": "Feature Importance", "fig": fig2},
    ]


def _clustering_figures(r: dict) -> list[dict]:
    labels = r["cluster_labels"]
    metrics = r["metrics"]
    ks = metrics["elbow_ks"]
    inertias = metrics["elbow_inertias"]
    X_2d = metrics.get("X_2d")

    # Elbow curve
    fig1 = px.line(x=ks, y=inertias, markers=True,
                   labels={"x": "K", "y": "Inertia"},
                   title="Elbow Curve", template=_THEME)
    fig1.add_vline(x=r["k"], line_dash="dash", line_color="red",
                   annotation_text=f"K={r['k']}")

    figs = [{"title": "Elbow Curve", "fig": fig1}]
    if X_2d is not None:
        fig2 = px.scatter(
            x=X_2d[:, 0], y=X_2d[:, 1],
            color=[str(l) for l in labels],
            title="PCA 2D — Cluster View",
            labels={"x": "PC1", "y": "PC2"},
            template=_THEME,
        )
        figs.append({"title": "Cluster PCA", "fig": fig2})

    return figs


def _timeseries_figures(r: dict) -> list[dict]:
    y_hist = r["y_test"]
    forecast = r["forecast"]
    conf_int = r["conf_int"]
    n_hist = len(y_hist)
    n_fc = len(forecast)

    x_hist = list(range(n_hist))
    x_fc   = list(range(n_hist, n_hist + n_fc))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_hist, y=y_hist.tolist(), name="Historical", mode="lines"))
    fig.add_trace(go.Scatter(x=x_fc, y=forecast.tolist(), name="Forecast",
                             mode="lines", line=dict(color="orange")))
    if conf_int is not None:
        ci_arr = np.array(conf_int)
        fig.add_trace(go.Scatter(
            x=x_fc + x_fc[::-1],
            y=ci_arr[:, 1].tolist() + ci_arr[:, 0].tolist()[::-1],
            fill="toself", fillcolor="rgba(255,165,0,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="95% CI",
        ))
    fig.update_layout(title="Historical + Forecast", template=_THEME)

    return [{"title": "Forecast", "fig": fig}]


def _reg_figs_for_algo(r: dict) -> list[dict]:
    y_test = r["y_test"]
    y_pred = r["y_pred"]
    feature_names = r["feature_names"]
    importances = r.get("feature_importances")

    fig1 = px.scatter(x=y_test, y=y_pred,
                      labels={"x": "Actual", "y": "Predicted"},
                      title="Actual vs Predicted", template=_THEME)
    fig1.add_shape(type="line",
                   x0=float(np.array(y_test).min()), y0=float(np.array(y_test).min()),
                   x1=float(np.array(y_test).max()), y1=float(np.array(y_test).max()),
                   line=dict(color="red", dash="dash"))
    figs = [{"title": "Actual vs Predicted", "fig": fig1}]

    if importances is not None:
        fig2 = px.bar(x=importances, y=feature_names, orientation="h",
                      title="Feature Importance", template=_THEME)
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        figs.append({"title": "Feature Importance", "fig": fig2})

    residuals = np.array(y_test) - np.array(y_pred)
    fig3 = px.histogram(x=residuals, nbins=30, title="Residual Distribution", template=_THEME)
    figs.append({"title": "Residuals", "fig": fig3})
    return figs


def _cls_figs_for_algo(r: dict) -> list[dict]:
    from sklearn.metrics import confusion_matrix
    y_test = r["y_test"]
    y_pred = r["y_pred"]
    feature_names = r["feature_names"]
    importances = r.get("feature_importances")

    cm = confusion_matrix(y_test, y_pred)
    fig1 = px.imshow(cm, text_auto=True, title="Confusion Matrix",
                     template=_THEME, color_continuous_scale="Blues")
    figs = [{"title": "Confusion Matrix", "fig": fig1}]

    if importances is not None:
        fig2 = px.bar(x=importances, y=feature_names, orientation="h",
                      title="Feature Importance", template=_THEME)
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        figs.append({"title": "Feature Importance", "fig": fig2})
    return figs


def _cluster_figs_for_algo(r: dict) -> list[dict]:
    labels = r["cluster_labels"]
    metrics = r["metrics"]
    ks = metrics.get("elbow_ks", [])
    inertias = metrics.get("elbow_inertias", [])
    X_2d = r.get("X_2d")
    figs = []

    if ks:
        fig1 = px.line(x=ks, y=inertias, markers=True,
                       labels={"x": "K", "y": "Inertia"},
                       title="Elbow Curve", template=_THEME)
        fig1.add_vline(x=r["k"], line_dash="dash", line_color="red",
                       annotation_text=f"K={r['k']}")
        figs.append({"title": "Elbow Curve", "fig": fig1})

    if X_2d is not None:
        fig2 = px.scatter(x=X_2d[:, 0], y=X_2d[:, 1],
                          color=[str(lb) for lb in labels],
                          title="PCA 2D — Cluster View",
                          labels={"x": "PC1", "y": "PC2"}, template=_THEME)
        figs.append({"title": "Cluster PCA", "fig": fig2})
    return figs


def _ts_figs_for_algo(r: dict) -> list[dict]:
    y_hist = np.array(r["y_test"])
    forecast = np.array(r["forecast"])
    conf_int = r.get("conf_int")
    n_hist = len(y_hist)
    n_fc = len(forecast)
    x_hist = list(range(n_hist))
    x_fc = list(range(n_hist, n_hist + n_fc))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_hist, y=y_hist.tolist(), name="Historical", mode="lines"))
    fig.add_trace(go.Scatter(x=x_fc, y=forecast.tolist(), name="Forecast",
                             mode="lines", line=dict(color="orange")))
    if conf_int is not None:
        ci_arr = np.array(conf_int)
        fig.add_trace(go.Scatter(
            x=x_fc + x_fc[::-1],
            y=ci_arr[:, 1].tolist() + ci_arr[:, 0].tolist()[::-1],
            fill="toself", fillcolor="rgba(255,165,0,0.15)",
            line=dict(color="rgba(255,255,255,0)"), name="95% CI",
        ))
    fig.update_layout(title="Historical + Forecast", template=_THEME)
    return [{"title": "Forecast", "fig": fig}]


def get_figures_for_algo(algo_result: dict) -> list[dict]:
    """Generate charts for a single per-algorithm result dict."""
    pt = algo_result.get("problem_type", "")
    if pt == "regression":
        return _reg_figs_for_algo(algo_result)
    if pt == "classification":
        return _cls_figs_for_algo(algo_result)
    if pt == "clustering":
        return _cluster_figs_for_algo(algo_result)
    if pt == "timeseries":
        return _ts_figs_for_algo(algo_result)
    return []


def get_result_figures(train_result: dict) -> list[dict]:
    problem_type = train_result.get("problem_type", "")
    if problem_type == "regression":
        return _regression_figures(train_result)
    elif problem_type == "classification":
        return _classification_figures(train_result)
    elif problem_type == "clustering":
        return _clustering_figures(train_result)
    elif problem_type == "timeseries":
        return _timeseries_figures(train_result)
    return []
