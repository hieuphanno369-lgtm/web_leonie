# backend/analytics/codegen.py
"""Sinh mã Python tái hiện đúng pipeline ML Studio đã chạy.

Backend tự sinh chuỗi `code` (Show Code) cho TẤT CẢ surface — forecast / stats /
timeseries / correlation / cohort — rồi trả kèm response, thay vì để frontend tự
ghép chuỗi (vốn không thấy bước tiền xử lý và đang sinh thiếu/sai).

Nguyên tắc (xem docs/superpowers/plans/2026-06-06-ml-studio-polish.md):
  • KHÔNG f-string trong code SINH RA — chỉ print('nhãn =', giá_trị) ngăn bằng dấu
    phẩy ⇒ không có '{' '}' cần escape (lớp lỗi đã làm hỏng Show Code cũ).
  • Code SINH RA dùng list song song (forecast/lower/upper) thay vì list-of-dict
    ⇒ không dấu ngoặc nhọn ⇒ generator nội suy {periods}/{seasonal} an toàn.
  • Trung thực với routers/ml.py + analytics/timegrain.py; mỗi chuỗi compile() được.

Polars là thư viện backend thật sự dùng (đọc/parse/gộp) ⇒ code sinh ra cũng dùng
polars để chạy lại được trong môi trường người dùng.
"""
from __future__ import annotations

# Khớp analytics/timegrain.py (_TRUNC) và routers/ml.py.
_TRUNC = {"day": "1d", "week": "1w", "month": "1mo", "quarter": "1q", "year": "1y"}
_AGG_METHOD = {"sum": "sum", "mean": "mean", "count": "count",
               "n_unique": "n_unique", "min": "min", "max": "max"}

_HEADER = (
    "# Pipeline tái hiện đúng logic ML Studio đã chạy.\n"
    "# (Bỏ qua lớp cache parquet nội bộ — đọc thẳng file gốc; đặt file cạnh script.)\n\n"
)


def _read_call(filename: str) -> str:
    low = filename.lower()
    if low.endswith(".xlsx") or low.endswith(".xls"):
        return f"pl.read_excel({filename!r})"
    return f"pl.read_csv({filename!r})"


def _load_block(filename: str, date_col: str) -> str:
    return (
        "import polars as pl\n"
        "import numpy as np\n\n"
        f"df = {_read_call(filename)}\n"
        "# Lưu ý: app thử lần lượt nhiều định dạng ngày cụ thể (_DATE_FORMATS) rồi mới\n"
        "# fallback; ở đây dùng parser tự động của polars cho gọn nên kết quả parse có\n"
        "# thể lệch nhẹ với dữ liệu ngày mơ hồ (vd day-first vs month-first).\n"
        "df = df.with_columns(\n"
        f"    pl.col({date_col!r}).cast(pl.Utf8).str.to_datetime(strict=False).alias('_date_parsed')\n"
        ").drop_nulls('_date_parsed').sort('_date_parsed')\n\n"
    )


def _aggregate_block(date_col: str, value_col: str, grain: str, agg: str,
                     keep_nulls: bool = False) -> str:
    every = _TRUNC.get(grain, "1mo")
    method = _AGG_METHOD.get(agg, "sum")
    block = (
        "# Gộp theo đơn vị thời gian: truncate -> group_by -> agg -> sort\n"
        "# (giống analytics.timegrain.aggregate_series của app)\n"
        "grouped = (\n"
        f"    df.with_columns(pl.col('_date_parsed').dt.truncate({every!r}).alias('_period'))\n"
        "    .drop_nulls('_period')\n"
        "    .group_by('_period')\n"
        f"    .agg(pl.col({value_col!r}).{method}().alias('_value'))\n"
        "    .sort('_period')\n"
        ")\n"
        "labels = grouped['_period'].dt.strftime('%Y-%m-%d').to_list()\n"
        "period_starts = grouped['_period'].to_list()\n"
    )
    if keep_nulls:
        block += "values = grouped['_value'].to_list()  # giữ None để khớp add_comparisons\n\n"
    else:
        block += (
            "values = np.array([v for v in grouped['_value'].to_list() if v is not None], dtype=float)\n"
            "n = len(values)\n\n"
        )
    return block


def _raw_block(date_col: str, value_col: str) -> str:
    return (
        "# Grain = raw: dùng từng dòng, không gộp\n"
        f"values = df[{value_col!r}].drop_nulls().cast(pl.Float64).to_numpy()\n"
        f"labels = df[{date_col!r}].cast(pl.Utf8).to_list()\n"
        "n = len(values)\n\n"
    )


# ── Forecast: mỗi method tái hiện đúng routers/ml.py:1581-1763 ────────────────

def _fc_linear(periods: int, seasonal: int) -> str:
    return (
        "from scipy import stats as scipy_stats\n"
        "slope, intercept, *_ = scipy_stats.linregress(np.arange(n), values)\n"
        f"forecast = [round(float(intercept + slope * (n + i - 1)), 4) for i in range(1, {periods} + 1)]\n"
        "ci = float(values.std()) * 1.96\n"
        "lower = [round(v - ci, 4) for v in forecast]\n"
        "upper = [round(v + ci, 4) for v in forecast]\n"
        "print('slope =', round(float(slope), 4), 'intercept =', round(float(intercept), 4))\n"
        "print('forecast =', forecast)\n"
    )


def _fc_moving_average(periods: int, seasonal: int) -> str:
    return (
        "window = max(3, min(7, n // 3))\n"
        "ma = np.array([values[max(0, i - window + 1):i + 1].mean() for i in range(n)])\n"
        "look_back = min(window, n - 1)\n"
        "slope_ma = (ma[-1] - ma[-look_back - 1]) / look_back if look_back > 0 else 0.0\n"
        "local_std = float(values[-min(window * 2, n):].std())\n"
        f"forecast = [round(float(ma[-1] + slope_ma * i), 4) for i in range(1, {periods} + 1)]\n"
        "ci = local_std * 1.96\n"
        "lower = [round(v - ci, 4) for v in forecast]\n"
        "upper = [round(v + ci, 4) for v in forecast]\n"
        "print('forecast =', forecast)\n"
    )


def _fc_ets(periods: int, seasonal: int) -> str:
    return (
        "from statsmodels.tsa.holtwinters import ExponentialSmoothing\n"
        f"s = {seasonal}\n"
        "train = values[-500:] if len(values) > 500 else values\n"
        "use_seasonal = len(train) >= 2 * s\n"
        "model = ExponentialSmoothing(\n"
        "    train, trend='add', damped_trend=True,\n"
        "    seasonal='add' if use_seasonal else None,\n"
        "    seasonal_periods=s if use_seasonal else None,\n"
        ").fit(optimized=True)\n"
        f"forecast = [round(float(v), 4) for v in model.forecast({periods})]\n"
        "ci = float(np.std(model.resid)) * 1.96\n"
        "lower = [round(v - ci, 4) for v in forecast]\n"
        "upper = [round(v + ci, 4) for v in forecast]\n"
        "print('AIC =', round(float(model.aic), 2))\n"
        "print('forecast =', forecast)\n"
    )


def _fc_sarimax(periods: int, seasonal: int) -> str:
    return (
        "import warnings\n"
        "from statsmodels.tsa.statespace.sarimax import SARIMAX\n"
        f"s = {seasonal}\n"
        "train = values[-500:] if len(values) > 500 else values\n"
        "with warnings.catch_warnings():\n"
        "    warnings.simplefilter('ignore')\n"
        "    fit = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, s),\n"
        "                  enforce_stationarity=False, enforce_invertibility=False\n"
        "                  ).fit(disp=False, maxiter=100)\n"
        f"fcast = fit.get_forecast(steps={periods})\n"
        "# Model fit trên numpy array (không index pandas) => predicted_mean / conf_int\n"
        "# trả numpy array, KHÔNG dùng .iloc. np.asarray cũng an toàn nếu là pandas.\n"
        "mean_pred = np.asarray(fcast.predicted_mean, dtype=float)\n"
        "ci_arr = np.asarray(fcast.conf_int(alpha=0.05), dtype=float)\n"
        "# Chuỗi ngắn/biên: point forecast hữu hạn nhưng conf_int có thể NaN (hiệp\n"
        "# phương sai không ước lượng được) -> null hoá cận không hữu hạn cho an toàn.\n"
        f"forecast = [round(float(mean_pred[i]), 4) for i in range({periods})]\n"
        f"lower = [round(float(ci_arr[i, 0]), 4) if np.isfinite(ci_arr[i, 0]) else None for i in range({periods})]\n"
        f"upper = [round(float(ci_arr[i, 1]), 4) if np.isfinite(ci_arr[i, 1]) else None for i in range({periods})]\n"
        "print('AIC =', round(float(fit.aic), 2))\n"
        "print('forecast =', forecast)\n"
    )


def _fc_supervised(periods: int, seasonal: int) -> str:
    return (
        "from sklearn.linear_model import Ridge\n"
        "lags = min(5, n // 4)\n"
        "X = np.array([values[i - lags:i] for i in range(lags, n)])\n"
        "y = values[lags:]\n"
        "model = Ridge(alpha=1.0).fit(X, y)\n"
        "resid_std = float(np.std(y - model.predict(X)))\n"
        "history = list(values[-lags:])\n"
        "forecast, lower, upper = [], [], []\n"
        f"for _ in range({periods}):\n"
        "    x_in = np.array(history[-lags:]).reshape(1, -1)\n"
        "    pred = float(model.predict(x_in)[0])\n"
        "    ci = resid_std * 1.96\n"
        "    forecast.append(round(pred, 4)); lower.append(round(pred - ci, 4)); upper.append(round(pred + ci, 4))\n"
        "    history.append(pred)\n"
        "print('R2 =', round(float(model.score(X, y)), 4), 'lags =', lags)\n"
        "print('forecast =', forecast)\n"
    )


_FORECAST = {
    "linear": _fc_linear,
    "moving_average": _fc_moving_average,
    "ets": _fc_ets,
    "sarimax": _fc_sarimax,
    "supervised": _fc_supervised,
}


def forecast_code(method: str, date_col: str, value_col: str, filename: str,
                  grain: str, agg: str, seasonal_period: int, periods: int,
                  n: int) -> str:
    parts = [_HEADER, _load_block(filename, date_col)]
    if grain == "raw":
        parts.append(_raw_block(date_col, value_col))
    else:
        parts.append(_aggregate_block(date_col, value_col, grain, agg))
    parts.append(_FORECAST.get(method, _fc_linear)(periods, seasonal_period))
    return "".join(parts)


def correlation_code(columns: list[str], filename: str) -> str:
    cols_lit = "[" + ", ".join(repr(c) for c in columns) + "]"
    return (
        _HEADER +
        "import polars as pl\n"
        "import numpy as np\n"
        "from scipy import stats as scipy_stats\n\n"
        f"df = {_read_call(filename)}\n"
        f"cols = {cols_lit}\n"
        "matrix = []\n"
        "for c1 in cols:\n"
        "    row = []\n"
        "    for c2 in cols:\n"
        "        if c1 == c2:\n"
        "            row.append(1.0); continue\n"
        "        pair = df.select([c1, c2]).drop_nulls()   # pairwise-complete\n"
        "        if pair.height < 3:\n"
        "            row.append(None); continue\n"
        "        a = pair[c1].to_numpy(); b = pair[c2].to_numpy()\n"
        "        if a.std() == 0 or b.std() == 0:          # chặn NaN từ pearsonr\n"
        "            row.append(None); continue\n"
        "        r, _ = scipy_stats.pearsonr(a, b)\n"
        "        row.append(round(float(r), 4) if np.isfinite(r) else None)\n"
        "    matrix.append(row)\n"
        "print('columns =', cols)\n"
        "for r in matrix:\n"
        "    print(r)\n"
    )


# Khối helper so sánh kỳ — copy NGUYÊN VĂN từ analytics/timegrain.py (lines 95-189)
# để code sinh ra chạy độc lập và khớp 100% phép tính của app.
_TS_COMPARE_HELPERS = '''
import math
from datetime import date

def _delta_pct(cur, prior):
    if cur is None or prior is None or prior == 0:
        return None
    d = (cur - prior) / prior * 100
    return round(d, 2) if math.isfinite(d) else None

def _period_key(d, grain):
    if grain == "year":
        return date(d.year, 1, 1)
    if grain == "quarter":
        return date(d.year, (d.month - 1) // 3 * 3 + 1, 1)
    if grain == "month":
        return date(d.year, d.month, 1)
    if grain == "day":
        return d
    iso = d.isocalendar()
    return ("W", iso[0], iso[1])

def _prior_year_key(d, grain):
    if grain == "year":
        return date(d.year - 1, 1, 1)
    if grain == "quarter":
        return date(d.year - 1, (d.month - 1) // 3 * 3 + 1, 1)
    if grain == "month":
        return date(d.year - 1, d.month, 1)
    if grain == "day":
        try:
            return date(d.year - 1, d.month, d.day)
        except ValueError:
            return date(d.year - 1, d.month, 28)
    iso = d.isocalendar()
    return ("W", iso[0] - 1, iso[1])

def _yoy(period_starts, values, grain):
    index = {_period_key(d, grain): v for d, v in zip(period_starts, values)}
    yoy_vals, deltas = [], []
    for d, v in zip(period_starts, values):
        prior = index.get(_prior_year_key(d, grain))
        yoy_vals.append(prior); deltas.append(_delta_pct(v, prior))
    return {"values": yoy_vals, "delta_pct": deltas}

def _pop(values):
    vals, deltas = [], []
    for i, v in enumerate(values):
        prior = values[i - 1] if i > 0 else None
        vals.append(prior); deltas.append(_delta_pct(v, prior))
    return {"values": vals, "delta_pct": deltas}

def _rolling(values, window):
    out = []
    for i in range(len(values)):
        chunk = [x for x in values[max(0, i - window + 1):i + 1] if x is not None]
        out.append(round(sum(chunk) / len(chunk), 4) if chunk else None)
    return out

def _reset_key(d, reset):
    if reset == "month":
        return (d.year, d.month)
    if reset == "quarter":
        return (d.year, (d.month - 1) // 3)
    return d.year

def _cumulative(period_starts, values, reset):
    out, run, cur_key = [], 0.0, None
    for d, v in zip(period_starts, values):
        key = _reset_key(d, reset)
        if key != cur_key:
            cur_key, run = key, 0.0
        if v is not None:
            run += v
        out.append(round(run, 4))
    return out

def _index100(values):
    base = next((v for v in values if v not in (None, 0)), None)
    if base is None:
        return [None] * len(values)
    return [round(v / base * 100, 2) if v is not None else None for v in values]

def _share(values):
    total = sum(v for v in values if v is not None)
    if not total:
        return [None] * len(values)
    return [round(v / total * 100, 2) if v is not None else None for v in values]
'''

_TS_CALL = {
    "pop":        lambda g, w, r: "print('PoP delta% =', _pop(values)['delta_pct'])\n",
    "yoy":        lambda g, w, r: f"print('YoY delta% =', _yoy(period_starts, values, {g!r})['delta_pct'])\n",
    "rolling":    lambda g, w, r: f"print('Rolling mean =', _rolling(values, {w}))\n",
    "cumulative": lambda g, w, r: f"print('Cumulative =', _cumulative(period_starts, values, {r!r}))\n",
    "index100":   lambda g, w, r: "print('Index100 =', _index100(values))\n",
    "share":      lambda g, w, r: "print('Share% =', _share(values))\n",
}


def timeseries_code(date_col: str, value_col: str, filename: str, grain: str,
                    agg: str, comparisons: list[str], rolling_window: int,
                    cumulative_reset: str) -> str:
    parts = [
        _HEADER,
        _load_block(filename, date_col),
        _aggregate_block(date_col, value_col, grain, agg, keep_nulls=True),
        "print('labels =', labels)\n"
        "print('values =', values)\n",
    ]
    requested = [c for c in ("pop", "yoy", "rolling", "cumulative", "index100", "share")
                 if c in comparisons]
    if requested:
        parts.append(_TS_COMPARE_HELPERS)
        parts.append("\n")
        for c in requested:
            parts.append(_TS_CALL[c](grain, rolling_window, cumulative_reset))
    return "".join(parts)


def _stats_head(filename: str) -> str:
    return (
        _HEADER +
        "import polars as pl\n"
        "import numpy as np\n"
        "from scipy import stats as scipy_stats\n\n"
        f"df = {_read_call(filename)}\n"
    )


def stats_code(test: str, col_a: str, col_b: str | None, filename: str) -> str:
    head = _stats_head(filename)
    a_line = f"a = df[{col_a!r}].drop_nulls().cast(pl.Float64).to_numpy()\n"

    if test == "describe":
        return head + a_line + (
            "print('count =', len(a), 'mean =', float(a.mean()), 'std =', float(a.std()))\n"
            "print('min =', float(a.min()), 'max =', float(a.max()))\n"
            f"print('q25 =', float(df[{col_a!r}].quantile(0.25)))\n"
            f"print('q50 =', float(df[{col_a!r}].quantile(0.50)))\n"
            f"print('q75 =', float(df[{col_a!r}].quantile(0.75)))\n"
        )
    if test == "bootstrap":
        return head + a_line + (
            "rng = np.random.default_rng(42)\n"
            "sample = a if len(a) <= 10_000 else rng.choice(a, 10_000, replace=False)\n"
            "boot_means = rng.choice(sample, size=(1000, len(sample)), replace=True).mean(axis=1)\n"
            "print('mean =', round(float(a.mean()), 4))\n"
            "print('ci_lower_95 =', round(float(np.percentile(boot_means, 2.5)), 4))\n"
            "print('ci_upper_95 =', round(float(np.percentile(boot_means, 97.5)), 4))\n"
        )
    if test == "distribution":
        return head + a_line + (
            "counts, edges = np.histogram(a, bins=20)\n"
            "for i in range(len(counts)):\n"
            "    print(round(float(edges[i]), 4), '..', round(float(edges[i + 1]), 4), '->', int(counts[i]))\n"
        )
    if test == "correlation":
        return head + a_line + (
            f"b = df[{col_b!r}].drop_nulls().to_numpy()\n"
            "r, p = scipy_stats.pearsonr(a[:len(b)], b[:len(a)])\n"
            "print('r =', round(float(r), 4), 'p_value =', round(float(p), 6))\n"
        )
    if test == "ttest":
        return head + a_line + (
            f"b = df[{col_b!r}].drop_nulls().to_numpy()\n"
            "t, p = scipy_stats.ttest_ind(a, b)\n"
            "print('t_stat =', round(float(t), 4), 'p_value =', round(float(p), 6))\n"
        )
    if test == "mannwhitney":
        return head + a_line + (
            f"b = df[{col_b!r}].drop_nulls().to_numpy()\n"
            "u, p = scipy_stats.mannwhitneyu(a, b, alternative='two-sided')\n"
            "print('u_statistic =', round(float(u), 4), 'p_value =', round(float(p), 6))\n"
        )
    if test == "anova":
        return head + (
            f"group_vals = df[{col_b!r}].unique().drop_nulls().to_list()\n"
            f"groups = [df.filter(pl.col({col_b!r}) == v)[{col_a!r}].drop_nulls().to_numpy() for v in group_vals]\n"
            "groups = [g for g in groups if len(g) >= 2]\n"
            "f_stat, p = scipy_stats.f_oneway(*groups)\n"
            "print('f_statistic =', round(float(f_stat), 4), 'p_value =', round(float(p), 6), 'n_groups =', len(groups))\n"
        )
    if test == "chi2":
        return head + (
            f"vals_a = sorted(df[{col_a!r}].unique().drop_nulls().to_list())\n"
            f"vals_b = sorted(df[{col_b!r}].unique().drop_nulls().to_list())\n"
            f"table = [[df.filter((pl.col({col_a!r}) == va) & (pl.col({col_b!r}) == vb)).height for vb in vals_b] for va in vals_a]\n"
            "chi2, p, dof, _ = scipy_stats.chi2_contingency(np.array(table))\n"
            "print('chi2 =', round(float(chi2), 4), 'p_value =', round(float(p), 6), 'dof =', int(dof))\n"
        )
    if test == "zscore":
        return head + a_line + (
            "z = (a - a.mean()) / (a.std() + 1e-9)\n"
            "counts, edges = np.histogram(z, bins=30)\n"
            "print('mean =', round(float(a.mean()), 4), 'std =', round(float(a.std()), 4), 'n =', len(a))\n"
            "order = np.argsort(-np.abs(z))[:10]\n"
            "for i in order:\n"
            "    print('idx', int(i), 'value', round(float(a[i]), 4), 'z', round(float(z[i]), 4))\n"
        )
    if test == "boxplot":
        return head + a_line + (
            "q1 = float(np.percentile(a, 25)); med = float(np.percentile(a, 50)); q3 = float(np.percentile(a, 75))\n"
            "iqr = q3 - q1\n"
            "lower_fence = q1 - 1.5 * iqr; upper_fence = q3 + 1.5 * iqr\n"
            "outliers = [float(v) for v in a if v < lower_fence or v > upper_fence]\n"
            "print('q1 =', round(q1, 4), 'median =', round(med, 4), 'q3 =', round(q3, 4), 'iqr =', round(iqr, 4))\n"
            "print('fences =', round(lower_fence, 4), round(upper_fence, 4), 'n_outliers =', len(outliers))\n"
        )
    return head + a_line + "print('mean =', float(a.mean()))\n"


# Biểu thức chỉ số kỳ (period index) — khớp routers/ml.py:795-816.
_COHORT_PERIOD_NUM = {
    "week": "(pl.col('_date').dt.year() * 100 + pl.col('_date').dt.week())",
    "day": "pl.col('_date').dt.epoch('d').cast(pl.Int64)",
    "quarter": "(pl.col('_date').dt.year() * 4 + (pl.col('_date').dt.month() - 1) // 3).cast(pl.Int64)",
    "year": "pl.col('_date').dt.year().cast(pl.Int64)",
    "month": "(pl.col('_date').dt.year() * 100 + pl.col('_date').dt.month())",
}


def cohort_code(period: str, date_col: str, user_col: str, filename: str,
                offset_col: str | None = None, metric_col: str | None = None,
                filter_col: str | None = None, filter_val: str | None = None) -> str:
    head = _HEADER + "import polars as pl\n\n" + f"df = {_read_call(filename)}\n"
    if filter_col and filter_val:
        head += f"df = df.filter(pl.col({filter_col!r}).cast(pl.Utf8) == {filter_val!r})\n"

    if offset_col:
        value_expr = (f"pl.col({metric_col!r}).sum()" if metric_col
                      else f"pl.col({user_col!r}).n_unique()")
        return head + (
            "\n# Chế độ pre-aggregated (đã có cột offset sẵn)\n"
            "df = df.with_columns([\n"
            f"    pl.col({date_col!r}).cast(pl.Utf8).alias('_cohort_label'),\n"
            f"    pl.col({offset_col!r}).cast(pl.Int64).alias('_offset'),\n"
            "])\n"
            "agg = (\n"
            "    df.group_by(['_cohort_label', '_offset'])\n"
            f"    .agg(({value_expr}).alias('value'))\n"
            "    .sort(['_cohort_label', '_offset'])\n"
            ")\n"
            "# Bảng cohort bằng pivot (hàng = cohort, cột = offset)\n"
            "table = agg.pivot(values='value', index='_cohort_label', on='_offset').sort('_cohort_label')\n"
            "print(table)\n"
        )

    period_num = _COHORT_PERIOD_NUM.get(period, _COHORT_PERIOD_NUM["month"])
    return head + (
        "\n# Chế độ transactional (mặc định)\n"
        "df = df.with_columns(\n"
        f"    pl.col({date_col!r}).cast(pl.Utf8).str.to_datetime(strict=False).alias('_date')\n"
        ").drop_nulls('_date')\n"
        f"# Chỉ số kỳ (period index) theo '{period}'\n"
        f"df = df.with_columns(({period_num}).alias('_period_num'))\n"
        "# Kỳ đầu tiên của mỗi user = cohort\n"
        f"cohort_map = df.group_by({user_col!r}).agg(pl.col('_period_num').min().alias('_cohort_num'))\n"
        f"df = df.join(cohort_map, on={user_col!r}, how='left')\n"
        "df = df.with_columns((pl.col('_period_num') - pl.col('_cohort_num')).alias('_offset'))\n"
        "# Số user duy nhất theo (cohort, offset)\n"
        "agg = (\n"
        "    df.group_by(['_cohort_num', '_offset'])\n"
        f"    .agg(pl.col({user_col!r}).n_unique().alias('users'))\n"
        "    .sort(['_cohort_num', '_offset'])\n"
        ")\n"
        "# Bảng cohort bằng pivot, rồi đổi sang % retention so với offset 0\n"
        "table = agg.pivot(values='users', index='_cohort_num', on='_offset').sort('_cohort_num')\n"
        "sizes = dict(zip(\n"
        "    agg.filter(pl.col('_offset') == 0)['_cohort_num'].to_list(),\n"
        "    agg.filter(pl.col('_offset') == 0)['users'].to_list(),\n"
        "))\n"
        "print(table)\n"
        "print('cohort_sizes =', sizes)\n"
    )


def describe_code(filename: str) -> str:
    """Snippet tái hiện bảng thống kê mô tả (min/max/mean/median/range/std) cho mỗi
    cột số — khớp endpoint /describe. Không f-string & không '{' trong code sinh ra."""
    return (
        _HEADER +
        "import polars as pl\n\n"
        f"df = {_read_call(filename)}\n"
        "rows = []\n"
        "for col in df.columns:\n"
        "    s = df[col]\n"
        "    if not s.dtype.is_numeric():\n"
        "        continue\n"
        "    arr = s.drop_nulls().cast(pl.Float64)\n"
        "    if len(arr) == 0:\n"
        "        continue\n"
        "    mn = float(arr.min()); mx = float(arr.max())\n"
        "    rows.append(dict(\n"
        "        col=col, min=mn, max=mx, mean=float(arr.mean()),\n"
        "        median=float(arr.median()), range=mx - mn, std=float(arr.std()),\n"
        "    ))\n"
        "print(pl.DataFrame(rows))\n"
    )


_DRILL_FMT = {"year": "%Y", "month": "%Y-%m", "day": "%Y-%m-%d"}


def drilldown_code(date_col: str, value_col: str, filename: str, grain: str,
                   agg: str, year: int | None = None, month: int | None = None) -> str:
    """Snippet khoan sâu thời gian (year/month/day, lọc year/month tuỳ chọn) — khớp
    endpoint /drilldown. Không f-string & không '{' trong code sinh ra."""
    method = _AGG_METHOD.get(agg, "sum")
    fmt = _DRILL_FMT.get(grain, "%Y")
    parts = [
        _HEADER,
        "import polars as pl\n\n",
        f"df = {_read_call(filename)}\n",
        "df = df.with_columns(\n"
        f"    pl.col({date_col!r}).cast(pl.Utf8).str.to_datetime(strict=False).alias('_d')\n"
        ").drop_nulls('_d')\n",
    ]
    if year is not None:
        parts.append(f"df = df.filter(pl.col('_d').dt.year() == {int(year)})\n")
    if month is not None:
        parts.append(f"df = df.filter(pl.col('_d').dt.month() == {int(month)})\n")
    parts.append(
        f"df = df.with_columns(pl.col('_d').dt.strftime({fmt!r}).alias('_period'))\n"
        "grouped = (\n"
        "    df.group_by('_period')\n"
        f"    .agg(pl.col({value_col!r}).{method}().alias('_value'))\n"
        "    .sort('_period')\n"
        ")\n"
        "print('labels =', grouped['_period'].to_list())\n"
        "print('values =', grouped['_value'].to_list())\n"
    )
    return "".join(parts)


def merge_code(
    filenames: list[str],
    selected: list[str],
    alias_map: dict[str, str],
    *,
    field_groups: dict[str, list[str]],
    semantic_types: dict[str, str],
    dedup_key: str | None,
    required_fields: list[str],
    coalesce: bool,
    drop_invalid_key: bool,
    trim: bool,
) -> str:
    """Snippet tái hiện pipeline "Combine file" TỪ ĐẦU ĐẾN CUỐI — khớp 100%
    analytics.merge.align_and_merge.

    Gọi thẳng engine thật (thay vì chép tay ~140 dòng dễ lệch) nên kết quả luôn
    đúng bằng app; chỉ cần chạy trong thư mục repo (có sẵn package `analytics`).
    Mọi tham số được resolve sẵn từ wizard và in ra dạng literal qua repr() ⇒
    KHÔNG có '{' '}' trong f-string của generator (đúng nguyên tắc module).
    """
    reads = "".join("    " + _read_call(fn) + ",  # " + fn + "\n" for fn in filenames)
    fg_lit = {k: list(v) for k, v in (field_groups or {}).items()}
    return (
        _HEADER +
        "# Combine file: union nhiều file lệch schema -> làm sạch theo loại ngữ nghĩa\n"
        "# -> validate khoá -> gộp trùng (coalesce) -> đo chất lượng -> xuất CSV/XLSX.\n"
        "# Đặt các file gốc cạnh script; chạy trong repo để import được `analytics`.\n\n"
        "import polars as pl\n"
        "from analytics.merge import align_and_merge\n\n"
        "# 1) Đọc từng file gốc theo đúng thứ tự đã nạp ở bước Tải file\n"
        "frames = [\n" + reads + "]\n"
        "filenames = " + repr(list(filenames)) + "\n\n"
        "# 2) Tham số đã chọn trong wizard (Gộp & loại / Làm sạch)\n"
        "selected = " + repr(list(selected)) + "\n"
        "alias_map = " + repr(dict(alias_map or {})) + "  # tên cột gốc -> tên chuẩn\n"
        "field_groups = " + repr(fg_lit) + "  # cột chuẩn -> các cột thành viên cần gộp\n"
        "semantic_types = " + repr(dict(semantic_types or {})) + "  # cột -> loại (date/number/email/phone/...)\n"
        "dedup_key = " + repr(dedup_key) + "  # khoá khử trùng (None nếu bỏ qua)\n"
        "required_fields = " + repr(list(required_fields)) + "  # cột bắt buộc để tính 'đủ thông tin'\n\n"
        "# 3) Chạy đúng engine app dùng. Bên trong, theo thứ tự:\n"
        "#    rename/align -> select (thiếu cột thì thêm null) -> pl.concat(diagonal_relaxed)\n"
        "#    -> trim + rỗng->null -> normalize_value theo semantic_type\n"
        "#    -> is_valid(dedup_key) tách 'rejected' -> coalesce gộp trùng (giữ giá trị\n"
        "#    non-null đầu tiên) hoặc unique -> đếm completeness theo required_fields.\n"
        "clean, rejected, summary = align_and_merge(\n"
        "    frames, selected, alias_map,\n"
        "    filenames=filenames,\n"
        "    field_groups=field_groups,\n"
        "    semantic_types=semantic_types,\n"
        "    dedup_key=dedup_key,\n"
        "    required_fields=required_fields,\n"
        "    coalesce=" + repr(bool(coalesce)) + ",\n"
        "    drop_invalid_key=" + repr(bool(drop_invalid_key)) + ",\n"
        "    trim=" + repr(bool(trim)) + ",\n"
        ")\n\n"
        "# 4) Báo cáo chất lượng (khớp các chỉ số hiển thị trong app)\n"
        "print('Tong thu thap   :', summary.total_raw)\n"
        "print('Hop le dinh dang:', summary.valid_format)\n"
        "print('Null / sai      :', summary.null_or_wrong)\n"
        "print('Distinct        :', summary.distinct)\n"
        "print('Trung loai(sach):', summary.dup_removed_clean)\n"
        "print('Du thong tin    :', summary.complete)\n"
        "print('Ty le dien      :', summary.per_field_fill_rate)\n"
        "print('Dong gop / file :', summary.per_file_contribution)\n\n"
        "# 5) Xuất kết quả sạch ra CSV và Excel (+ bản bị loại nếu có)\n"
        "clean.write_csv('combined_clean.csv')\n"
        "clean.write_excel('combined_clean.xlsx')\n"
        "if rejected.height:\n"
        "    rejected.write_csv('combined_rejected.csv')\n"
        "print('Da ghi', clean.height, 'dong sach -> combined_clean.csv / .xlsx')\n"
    )
