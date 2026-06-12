# ML Studio Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bốn cải tiến ML Studio do người dùng yêu cầu — (1) bộ chia đơn vị trục Y (`auto/K/M/B/%`) cho biểu đồ Chuỗi thời gian + Forecast; (2) đồng bộ icon line-style (lucide) thay emoji; (3a) Heatmap màu phân kỳ đẹp + chữ luôn đọc được, (3b) Forecast khi dữ liệu không phù hợp hiện thẻ vàng "giải thích + gợi ý" thay vì lỗi đỏ; (4) Show Code đầy đủ, trung thực cho cả 5 surface (Forecast, Stats, Cohort, Chuỗi thời gian, Heatmap).

**Architecture:** Backend tự sinh chuỗi `code` (Show Code) trong package thuần Python `backend/analytics/codegen.py` rồi trả kèm mỗi response — frontend không còn tự ghép chuỗi (vốn thiếu bước tiền xử lý và đang lỗi). Cổng "phù hợp dữ liệu" cho Forecast nằm ở `backend/analytics/forecast_check.py`, trả HTTP 200 `{suitable:false, reasons, recommended_method}` thay vì raise — giống cohort `check_suitability` có sẵn. Frontend thêm module dùng chung `numFormat.ts` (định dạng trục Y), bật toggle đơn vị cho 2 biểu đồ, đổi emoji → lucide, sửa màu/độ tương phản heatmap, và đọc `result.code` cho mọi Show Code.

**Tech Stack:** Backend — FastAPI, **Polars** (đọc/parse/gộp), NumPy, statsmodels (SARIMAX, ETS), scikit-learn (Ridge), scipy.stats; test bằng `pytest` trên package thuần `analytics/`. Frontend — React 19, TypeScript ~5.7, recharts, **lucide-react**; cổng kiểm thử = `npm run build` (`tsc -b && vite build`).

---

## Nguyên tắc thiết kế (đọc trước khi code)

1. **Backend sinh `code`, không phải frontend.** Mọi generator nằm trong `analytics/codegen.py` (thuần Python, không phụ thuộc FastAPI/DB ⇒ unit-test được). Router chỉ gọi và nhét vào response.
2. **Code SINH RA không dùng f-string** — chỉ `print('nhãn =', giá_trị)` (tham số ngăn bằng dấu phẩy). Đây chính là lớp lỗi đã làm hỏng Show Code cũ (`MlForecastView.tsx:116` có `print(f"Period {{i}}: {{v:.4f}}")` double-brace). Không f-string ⇒ không có `{`/`}` cần escape.
3. **Code SINH RA dùng list song song** (`forecast` / `lower` / `upper`) thay vì list-of-dict ⇒ không có dấu ngoặc nhọn ⇒ generator nội suy `{periods}`/`{seasonal}` bằng f-string an toàn.
4. **Trung thực với router.** Mỗi generator tái hiện ĐÚNG thuật toán đang chạy (đối chiếu `routers/ml.py` + `analytics/timegrain.py`). Mỗi chuỗi sinh ra phải `compile()` được và chứa từ khóa thuật toán tương ứng (assert trong test).
5. **Tiếng Việt cho mọi văn bản người dùng thấy** (comment trong code sinh ra, thẻ cảnh báo, label). Định danh/identifier giữ tiếng Anh.
6. **Ràng buộc frontend:** `tsconfig.app.json` bật `noUnusedLocals` + `noUnusedParameters`. ⇒ Mỗi import icon lucide PHẢI nằm cùng task lần đầu dùng nó; không import trước rồi mới dùng ở task sau (build sẽ fail).

---

## File Structure

**Tạo mới (backend):**
- `backend/analytics/forecast_check.py` — cổng phù hợp dữ liệu Forecast (Point 3b). Một hàm `check_forecast_suitability`.
- `backend/analytics/codegen.py` — sinh code Show Code cho 5 surface (Point 4). `forecast_code`, `correlation_code`, `timeseries_code`, `stats_code`, `cohort_code` + helpers nội bộ.
- `backend/tests/test_forecast_check.py`, `backend/tests/test_codegen.py`.

**Sửa (backend):**
- `backend/routers/ml.py` — gọi 2 module mới, nhét `code` vào 5 response, thay guard `n<2` của `/forecast` bằng cổng suitability.
- `backend/tests/test_ml.py` — đổi `test_forecast_sarimax_insufficient_data_error` từ kỳ vọng 400 → 200 + `suitable:false`.

**Tạo mới (frontend):**
- `frontend/src/components/ml/numFormat.ts` — `YScale`, `autoScale`, `fmtY`, `fmtFull` (tách từ `MlChartView`, thêm `export`).

**Sửa (frontend):**
- `frontend/src/types.ts`, `frontend/src/api/ml.ts` — thêm field `code?`/suitability vào type.
- `frontend/src/components/ml/MlForecastView.tsx` — toggle đơn vị + thẻ vàng + lucide + Show Code từ `result.code`.
- `frontend/src/components/ml/MlChartView.tsx` — toggle đơn vị cho Chuỗi thời gian + lucide + Show Code (chuỗi thời gian & heatmap).
- `frontend/src/components/ml/CorrelationHeatmap.tsx` — màu phân kỳ + chữ tương phản + ô co giãn.
- `frontend/src/components/ml/MlStatsView.tsx` — lucide + Show Code từ `result.code`.
- `frontend/src/components/ml/MlCohortView.tsx` — Show Code từ `result.code`.

**Lệnh kiểm thử:** Backend `cd backend ; uv run pytest -q`. Frontend `cd frontend ; npm run build`.

---

## Task 1: Cổng phù hợp dữ liệu Forecast (`forecast_check.py`)

**Files:**
- Create: `backend/analytics/forecast_check.py`
- Test: `backend/tests/test_forecast_check.py`

Bối cảnh: chỉ SARIMAX (`len(train) < 2*s`, xem `routers/ml.py:1609`) và supervised (`n < lags+2`, xem `:1661`) thực sự raise HTTPException(400) khiến người dùng tưởng thuật toán hỏng. ETS tự fallback non-seasonal, linear/moving_average chạy với `n>=2`. Cổng này chỉ chặn đúng các trường hợp thật sự không chạy được — chặn thừa sẽ báo "không phù hợp" sai.

- [ ] **Step 1: Viết test thất bại**

```python
# backend/tests/test_forecast_check.py
from analytics.forecast_check import check_forecast_suitability


def test_sarimax_insufficient_blocks_and_recommends_ets():
    r = check_forecast_suitability("sarimax", n=10, seasonal_period=12)
    assert r["suitable"] is False
    assert any("24" in reason for reason in r["reasons"])   # 2 * 12
    assert r["recommended_method"] == "ets"


def test_sarimax_enough_points_is_suitable():
    r = check_forecast_suitability("sarimax", n=24, seasonal_period=12)
    assert r["suitable"] is True
    assert r["reasons"] == []
    assert r["recommended_method"] is None


def test_supervised_too_few_points_blocks():
    r = check_forecast_suitability("supervised", n=3, seasonal_period=12)
    assert r["suitable"] is False
    assert r["recommended_method"] == "ets"


def test_linear_two_points_is_suitable():
    assert check_forecast_suitability("linear", n=2, seasonal_period=12)["suitable"] is True


def test_below_two_points_always_blocks_no_recommendation():
    r = check_forecast_suitability("linear", n=1, seasonal_period=12)
    assert r["suitable"] is False
    assert r["recommended_method"] is None


def test_recommended_never_equals_failing_method():
    r = check_forecast_suitability("sarimax", n=6, seasonal_period=12)
    assert r["recommended_method"] != "sarimax"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend ; uv run pytest tests/test_forecast_check.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'analytics.forecast_check'`.

- [ ] **Step 3: Hiện thực tối thiểu**

```python
# backend/analytics/forecast_check.py
"""Kiểm tra mức độ phù hợp của dữ liệu với thuật toán forecast.

Thuần Python, không phụ thuộc FastAPI/DB — unit-test bằng pytest. Trả về cấu trúc
giống analytics.cohort_check.check_suitability để router xử lý nhất quán: khi không
phù hợp, /forecast trả HTTP 200 kèm {suitable: False, ...} thay vì raise lỗi đỏ
khiến người dùng tưởng thuật toán hỏng.

Chỉ chặn đúng các trường hợp router thật sự raise:
  • SARIMAX: cần >= 2 * seasonal_period điểm (routers/ml.py:1609).
  • supervised: cần >= 4 điểm để tạo đặc trưng trễ (routers/ml.py:1661).
  • mọi method: cần >= 2 điểm.
"""
from __future__ import annotations

# Thứ tự ưu tiên gợi ý: ETS (tổng quát tốt) → moving_average → linear.
# Không bao giờ trùng method đang lỗi (sarimax/supervised).
_RECOMMEND_ORDER = [("ets", 2), ("moving_average", 2), ("linear", 2)]


def _recommend_method(n: int) -> str | None:
    for name, floor in _RECOMMEND_ORDER:
        if n >= floor:
            return name
    return None


def check_forecast_suitability(method: str, n: int, seasonal_period: int) -> dict:
    reasons: list[str] = []
    if n < 2:
        reasons.append(f"Cần tối thiểu 2 điểm dữ liệu để dự báo, nhưng chỉ có {n} điểm.")
    elif method == "sarimax":
        need = 2 * seasonal_period
        if n < need:
            reasons.append(
                f"SARIMAX cần tối thiểu {need} điểm (2 chu kỳ mùa vụ × "
                f"{seasonal_period}), nhưng dữ liệu chỉ có {n} điểm."
            )
    elif method == "supervised":
        if n < 4:
            reasons.append(
                f"Phương pháp 'supervised' cần tối thiểu 4 điểm để tạo đặc trưng "
                f"trễ (lag), nhưng dữ liệu chỉ có {n} điểm."
            )
    suitable = not reasons
    return {
        "suitable": suitable,
        "reasons": reasons,
        "recommended_method": None if suitable else _recommend_method(n),
    }
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend ; uv run pytest tests/test_forecast_check.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/forecast_check.py backend/tests/test_forecast_check.py
git commit -m "feat(ml): forecast data-suitability gate (friendly card, no false error)"
```

---

## Task 2: `codegen.py` — helpers chung + `forecast_code`

**Files:**
- Create: `backend/analytics/codegen.py`
- Test: `backend/tests/test_codegen.py`

- [ ] **Step 1: Viết test thất bại**

```python
# backend/tests/test_codegen.py
from analytics.codegen import forecast_code


def _compiles(code: str):
    compile(code, "<generated>", "exec")   # raise SyntaxError nếu code hỏng


def test_forecast_sarimax_code_faithful_and_compiles():
    code = forecast_code(
        method="sarimax", date_col="Order Date", value_col="Sales",
        filename="orders.csv", grain="month", agg="sum",
        seasonal_period=12, periods=6, n=48,
    )
    _compiles(code)
    assert "SARIMAX" in code
    assert "get_forecast" in code
    assert "dt.truncate" in code            # khối gộp thời gian
    assert "f\"" not in code and "f'" not in code   # KHÔNG f-string trong code sinh ra


def test_forecast_linear_uses_linregress():
    code = forecast_code("linear", "d", "v", "x.csv", "week", "sum", 52, 4, 30)
    _compiles(code)
    assert "linregress" in code


def test_forecast_moving_average_uses_mean():
    code = forecast_code("moving_average", "d", "v", "x.csv", "day", "sum", 7, 4, 30)
    _compiles(code)
    assert "mean" in code


def test_forecast_ets_uses_exponential_smoothing():
    code = forecast_code("ets", "d", "v", "x.csv", "month", "sum", 12, 4, 30)
    _compiles(code)
    assert "ExponentialSmoothing" in code


def test_forecast_supervised_uses_ridge():
    code = forecast_code("supervised", "d", "v", "x.csv", "month", "sum", 12, 4, 30)
    _compiles(code)
    assert "Ridge" in code


def test_forecast_raw_grain_reads_rows_not_aggregate():
    code = forecast_code("linear", "d", "v", "x.csv", "raw", "sum", 12, 4, 30)
    _compiles(code)
    assert "dt.truncate" not in code        # raw không gộp
    assert "to_numpy()" in code


def test_forecast_xlsx_uses_read_excel():
    code = forecast_code("linear", "d", "v", "báo cáo.xlsx", "month", "sum", 12, 4, 30)
    _compiles(code)
    assert "read_excel" in code
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend ; uv run pytest tests/test_codegen.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'analytics.codegen'`.

- [ ] **Step 3: Hiện thực — tạo `codegen.py` với header + helpers chung + forecast**

```python
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
        "mean_pred = fcast.predicted_mean\n"
        "ci_df = fcast.conf_int(alpha=0.05)\n"
        f"forecast = [round(float(mean_pred.iloc[i]), 4) for i in range({periods})]\n"
        f"lower = [round(float(ci_df.iloc[i, 0]), 4) for i in range({periods})]\n"
        f"upper = [round(float(ci_df.iloc[i, 1]), 4) for i in range({periods})]\n"
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend ; uv run pytest tests/test_codegen.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/codegen.py backend/tests/test_codegen.py
git commit -m "feat(ml): codegen — faithful forecast pipeline (no f-string brace bug)"
```

---

## Task 3: `correlation_code`

**Files:**
- Modify: `backend/analytics/codegen.py`
- Test: `backend/tests/test_codegen.py`

- [ ] **Step 1: Thêm test thất bại** (vào cuối `test_codegen.py`)

```python
from analytics.codegen import correlation_code


def test_correlation_code_faithful():
    code = correlation_code(["Doanh thu", "Chi phí", "Lợi nhuận"], "kpi.xlsx")
    _compiles(code)
    assert "pearsonr" in code
    assert "read_excel" in code
    assert "pair.height < 3" in code        # guard trung thực với router
    assert "f\"" not in code and "f'" not in code
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend ; uv run pytest tests/test_codegen.py::test_correlation_code_faithful -q`
Expected: FAIL — `ImportError: cannot import name 'correlation_code'`.

- [ ] **Step 3: Hiện thực** — thêm vào `codegen.py` (sau `forecast_code`)

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend ; uv run pytest tests/test_codegen.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/codegen.py backend/tests/test_codegen.py
git commit -m "feat(ml): codegen — correlation pipeline (pearsonr, faithful guards)"
```

---

## Task 4: `timeseries_code`

**Files:**
- Modify: `backend/analytics/codegen.py`
- Test: `backend/tests/test_codegen.py`

Bối cảnh: code phải tái hiện `aggregate_series` (truncate→group_by→agg) VÀ các phép so sánh trong `analytics/timegrain.py`. Để chạy độc lập + tuyệt đối trung thực, ta nhúng nguyên văn khối helper so sánh từ `timegrain.py` rồi chỉ gọi phép user đã chọn.

- [ ] **Step 1: Thêm test thất bại**

```python
from analytics.codegen import timeseries_code


def test_timeseries_code_aggregates_and_compiles():
    code = timeseries_code("Ngày", "Doanh thu", "ban_hang.csv", "month", "sum",
                           comparisons=[], rolling_window=7, cumulative_reset="year")
    _compiles(code)
    assert "dt.truncate" in code
    assert "group_by" in code
    assert "f\"" not in code and "f'" not in code


def test_timeseries_code_emits_only_requested_comparisons():
    code = timeseries_code("Ngày", "Doanh thu", "ban_hang.csv", "month", "sum",
                           comparisons=["pop", "yoy", "rolling"],
                           rolling_window=3, cumulative_reset="year")
    _compiles(code)
    assert "_pop(values)" in code
    assert "_yoy(period_starts, values, 'month')" in code
    assert "_rolling(values, 3)" in code
    # Chỉ kiểm tra phép GỌI không được phát — không dùng "_cumulative(" / "_share("
    # vì khối helper LUÔN định nghĩa `def _cumulative(...)`/`def _share(...)`.
    # Nhãn 'Cumulative ='/'Share% =' chỉ xuất hiện ở chỗ gọi (print), nên dùng nó.
    assert "Cumulative =" not in code        # không yêu cầu cumulative
    assert "Share% =" not in code
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend ; uv run pytest tests/test_codegen.py -k timeseries -q`
Expected: FAIL — `ImportError: cannot import name 'timeseries_code'`.

- [ ] **Step 3: Hiện thực** — thêm vào `codegen.py`

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend ; uv run pytest tests/test_codegen.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/codegen.py backend/tests/test_codegen.py
git commit -m "feat(ml): codegen — timeseries pipeline (aggregate + faithful comparisons)"
```

---

## Task 5: `stats_code` (10 phép kiểm định)

**Files:**
- Modify: `backend/analytics/codegen.py`
- Test: `backend/tests/test_codegen.py`

Ghi chú phạm vi: spec gốc đặt tên `describe_code` (số ít), nhưng surface Stats gọi `/ml/stats` với 10 `test`. Ta hiện thực `stats_code` là superset điều phối cả 10 — đây là làm rõ có chủ đích để Show Code đầy đủ. Mỗi nhánh tái hiện đúng `routers/ml.py:1034-1220`.

- [ ] **Step 1: Thêm test thất bại**

```python
import pytest
from analytics.codegen import stats_code

_STATS_KEYWORD = {
    "describe": "mean", "bootstrap": "np.random", "distribution": "histogram",
    "correlation": "pearsonr", "ttest": "ttest_ind", "mannwhitney": "mannwhitneyu",
    "anova": "f_oneway", "chi2": "chi2_contingency", "zscore": "std",
    "boxplot": "percentile",
}


@pytest.mark.parametrize("test,kw", list(_STATS_KEYWORD.items()))
def test_stats_code_each_test_faithful(test, kw):
    code = stats_code(test, "Giá trị", "Nhóm", "data.csv")
    _compiles(code)
    assert kw in code
    assert "f\"" not in code and "f'" not in code
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend ; uv run pytest tests/test_codegen.py -k stats -q`
Expected: FAIL — `ImportError: cannot import name 'stats_code'`.

- [ ] **Step 3: Hiện thực** — thêm vào `codegen.py`

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend ; uv run pytest tests/test_codegen.py -k stats -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/codegen.py backend/tests/test_codegen.py
git commit -m "feat(ml): codegen — stats pipeline (all 10 tests, faithful)"
```

---

## Task 6: `cohort_code`

**Files:**
- Modify: `backend/analytics/codegen.py`
- Test: `backend/tests/test_codegen.py`

Tái hiện cả 2 nhánh của `run_cohort` (`routers/ml.py:695-892`): transactional (mặc định, `n_unique`) và pre-aggregated (có `offset_col`). Bảng cohort biểu diễn bằng `pivot` (tương đương vòng lặp Python của router, rõ hơn).

- [ ] **Step 1: Thêm test thất bại**

```python
from analytics.codegen import cohort_code


def test_cohort_transactional_uses_n_unique_and_pivot():
    code = cohort_code("month", "Ngày mua", "Khách hàng", "don_hang.csv")
    _compiles(code)
    assert "n_unique" in code
    assert "pivot" in code
    assert "f\"" not in code and "f'" not in code


def test_cohort_period_index_changes_with_period():
    assert "dt.week" in cohort_code("week", "d", "u", "x.csv")
    assert "dt.epoch" in cohort_code("day", "d", "u", "x.csv")
    assert "// 3" in cohort_code("quarter", "d", "u", "x.csv")


def test_cohort_preaggregated_branch_compiles():
    code = cohort_code("month", "Cohort", "User", "x.csv",
                       offset_col="period_idx", metric_col="Revenue")
    _compiles(code)
    assert "_cohort_label" in code
    assert "pivot" in code
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend ; uv run pytest tests/test_codegen.py -k cohort -q`
Expected: FAIL — `ImportError: cannot import name 'cohort_code'`.

- [ ] **Step 3: Hiện thực** — thêm vào `codegen.py`

```python
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
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend ; uv run pytest tests/test_codegen.py -q`
Expected: PASS (toàn bộ test_codegen.py).

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/codegen.py backend/tests/test_codegen.py
git commit -m "feat(ml): codegen — cohort pipeline (both modes, n_unique + pivot)"
```

---

## Task 7: Nối codegen + forecast_check vào router `ml.py`

**Files:**
- Modify: `backend/routers/ml.py` (imports; `run_forecast`, `get_correlation`, `run_timeseries`, `run_stats`, `run_cohort`)
- Modify: `backend/tests/test_ml.py` (sửa test sarimax)

Lưu ý quan trọng (`/forecast`): các call site dùng `row["filename"]`. Trong `run_forecast`/`get_correlation`/... `row` lấy từ `_get_file_row(conn, ...)` rồi `conn.close()`; `row` là `sqlite3.Row` đã fetch nên vẫn dùng được sau khi đóng kết nối. Kiểm tra `row` có khóa `filename` — bảng `uploaded_files` có cột `filename` (đã dùng ở các handler khác).

- [ ] **Step 1: Thêm import** (sau dòng import analytics hiện có, gần `routers/ml.py:19-20`)

```python
from analytics.forecast_check import check_forecast_suitability
from analytics.codegen import (
    forecast_code, timeseries_code, correlation_code, stats_code, cohort_code,
)
```

- [ ] **Step 2: `/forecast` — thay guard `n<2` bằng cổng suitability + nhét `code`**

Tại `routers/ml.py:1557-1559`, thay:

```python
    n = len(values)
    if n < 2:
        raise HTTPException(400, "Need at least 2 data points")
```

bằng:

```python
    n = len(values)
    s_check = _seasonal(body, step_grain)
    fc_code = forecast_code(body.method, body.date_col, body.value_col,
                            row["filename"], eff_grain, body.agg, s_check,
                            body.periods, n)
    suit = check_forecast_suitability(body.method, n, s_check)
    if not suit["suitable"]:
        return {**suit, "method": body.method, "code": fc_code, "grain": step_grain}
```

Rồi thêm `"code": fc_code,` vào CẢ 5 return dict của method (moving_average `:1598`, sarimax `:1646`, supervised `:1684`, ets `:1731`, linear `:1757`). Ví dụ với linear (`:1757-1763`):

```python
    return {
        "method": "linear",
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "forecast": forecast,
        "history": _history,
        "code": fc_code,
    }
```

(Làm tương tự cho 4 dict còn lại — chỉ thêm đúng dòng `"code": fc_code,`.) Các guard `len(train) < 2*s` (`:1609`) và `SARIMAX failed to converge` (`:1630`) GIỮ NGUYÊN — chỉ chạy tới khi đã `suitable`.

- [ ] **Step 3: `/correlation`, `/timeseries`, `/stats`, `/cohort` — nhét `code`**

`get_correlation` (`:485`), thay `return {"columns": cols, "matrix": matrix, "excluded_columns": excluded}` bằng:

```python
    return {
        "columns": cols, "matrix": matrix, "excluded_columns": excluded,
        "code": correlation_code(cols, row["filename"]),
    }
```

`run_timeseries` (`:610-623`), thêm vào return:

```python
        "code": timeseries_code(body.date_col, body.value_col, row["filename"],
                                grain, body.agg, body.comparisons,
                                body.rolling_window, body.cumulative_reset),
```

`run_stats` (`:1029-1033`): ngay sau khối `try/except` dựng `a`, tính `code` một lần rồi thêm `"code": code,` vào CẢ 10 return:

```python
    code = stats_code(body.test, body.col_a, body.col_b, row["filename"])
```

(Thêm `"code": code,` vào: describe `:1035`, bootstrap `:1050`, distribution `:1061`, correlation `:1073`, ttest `:1079`, mannwhitney `:1087`, anova `:1105`, chi2 `:1125`, zscore `:1147`, boxplot `:1215`.)

`run_cohort`: pre-agg return (`:771-778`) thêm:

```python
            "code": cohort_code(body.period, body.date_col, body.user_col,
                                row["filename"], offset_col=body.offset_col,
                                metric_col=body.metric_col,
                                filter_col=body.filter_col, filter_val=body.filter_val),
```

transactional return (`:885-892`) thêm:

```python
        "code": cohort_code(body.period, body.date_col, body.user_col,
                            row["filename"], filter_col=body.filter_col,
                            filter_val=body.filter_val),
```

Return `suit` khi không phù hợp (`:787-788`) GIỮ NGUYÊN (không có `code` — đó là cổng suitability của cohort, không phải Show Code).

- [ ] **Step 4: Sửa test sarimax trong `test_ml.py`**

Tìm `test_forecast_sarimax_insufficient_data_error` (`backend/tests/test_ml.py:155-174`). Hiện nó kỳ vọng `resp.status_code == 400`. Thay phần assert bằng (n=10 điểm tháng, seasonal=12 ⇒ cần 24):

```python
    assert resp.status_code == 200
    body = resp.json()
    assert body["suitable"] is False
    assert any("24" in r for r in body["reasons"])
    assert body["recommended_method"] == "ets"
    assert "code" in body and "SARIMAX" in body["code"]
```

(Giữ nguyên phần setup/upload + payload sarimax phía trên; nếu hàm tên chứa `_error`, có thể đổi thành `_returns_unsuitable` cho rõ — tùy chọn.)

- [ ] **Step 5: Chạy toàn bộ test backend**

Run: `cd backend ; uv run pytest -q`
Expected: PASS toàn bộ (bao gồm test_forecast_check, test_codegen, test_ml đã sửa).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(ml): wire codegen + forecast suitability into 5 ML endpoints"
```

---

## Task 8: Frontend — module dùng chung `numFormat.ts`

**Files:**
- Create: `frontend/src/components/ml/numFormat.ts`

Tách logic định dạng trục Y (hiện đang nội bộ trong `MlChartView.tsx:26,49-66`) thành module dùng chung để cả 3 chỗ (heatmap-suggester có sẵn, time-series mới, forecast mới) dùng chung 1 nguồn.

- [ ] **Step 1: Tạo file**

```typescript
// frontend/src/components/ml/numFormat.ts
// Định dạng số trục Y dùng chung cho mọi biểu đồ ML Studio.
export type YScale = 'auto' | 'K' | 'M' | 'B' | '%'

export function autoScale(maxAbs: number): YScale {
  if (maxAbs >= 1e9) return 'B'
  if (maxAbs >= 1e6) return 'M'
  if (maxAbs >= 1e3) return 'K'
  return 'auto'
}

export function fmtY(v: number, scale: YScale, maxAbs: number): string {
  const s = scale === 'auto' ? autoScale(maxAbs) : scale
  if (scale === '%') return `${v.toFixed(1)}%`
  if (s === 'B') return `${(v / 1e9).toFixed(2)}B`
  if (s === 'M') return `${(v / 1e6).toFixed(2)}M`
  if (s === 'K') return `${(v / 1e3).toFixed(1)}K`
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}

export function fmtFull(v: number): string {
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}
```

- [ ] **Step 2: Build (cổng kiểm thử frontend)**

Run: `cd frontend ; npm run build`
Expected: build thành công (module mới chưa được import nên không ảnh hưởng; xác nhận không có lỗi cú pháp).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/numFormat.ts
git commit -m "feat(ml): shared numFormat module (Y-axis unit scaling)"
```

---

## Task 9: Frontend — mở rộng type cho `code` + suitability

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/ml.ts`

- [ ] **Step 1: `types.ts` — bổ sung field**

`ForecastResult` (`:184-197`) thêm các field tùy chọn (trước dấu `}` đóng interface):

```typescript
  code?: string
  suitable?: boolean
  reasons?: string[]
  recommended_method?: string | null
  grain?: string
```

`CorrelationMatrix` (`:220-224`) thêm:

```typescript
  code?: string
```

`TimeseriesResult` (`:226-241`) thêm:

```typescript
  code?: string
```

`StatsResult` (`:166-168`) hiện là `{ [key: string]: number | string }`. Đổi để chứa được `code`:

```typescript
export interface StatsResult {
  [key: string]: number | string | undefined
  code?: string
}
```

- [ ] **Step 2: `api/ml.ts` — `CohortResult` thêm `code`**

Trong interface `CohortResult` (`:87-99`), thêm:

```typescript
  code?: string
```

- [ ] **Step 3: Build**

Run: `cd frontend ; npm run build`
Expected: build thành công.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/ml.ts
git commit -m "feat(ml): add code/suitability fields to ML result types"
```

---

## Task 10: Forecast view — toggle đơn vị + thẻ vàng + lucide + Show Code

**Files:**
- Modify: `frontend/src/components/ml/MlForecastView.tsx`

Gói trọn Point 1 (forecast), 3b (thẻ vàng), 2 (icon) và 4 (Show Code) cho surface Forecast trong một task để thỏa `noUnusedLocals` (mọi icon import đều được dùng ngay).

- [ ] **Step 1: Import + bỏ code thừa**

Dòng `:2` import lucide `{ TrendingUp, Download, BarChart2, Sparkles, Code2 }` → thêm `Star, Check, X, AlertTriangle`:

```typescript
import { TrendingUp, Download, BarChart2, Sparkles, Code2, Star, Check, X, AlertTriangle } from 'lucide-react'
```

Thêm import định dạng (gần các import nội bộ khác):

```typescript
import { type YScale, fmtY, fmtFull } from './numFormat'
```

XÓA hàm `formatNum` cục bộ (`:13-21`) và hàm `generateForecastCode` (`:107-124`, chứa bug double-brace `:116`).

- [ ] **Step 2: State + maxAbs cho thang đo**

Gần khai báo state (quanh `:143`) thêm:

```typescript
const [fcScale, setFcScale] = useState<YScale>('auto')
```

Tính `fcMaxAbs` từ dữ liệu biểu đồ (lịch sử + forecast) — đặt cạnh nơi dựng dữ liệu chart, ví dụ:

```typescript
const fcMaxAbs = useMemo(() => {
  if (!result) return 0
  const hist = (result.history ?? []).map(h => Math.abs(h.value))
  const fc = (result.forecast ?? []).map(p => Math.abs(p.value))
  return Math.max(0, ...hist, ...fc)
}, [result])
```

(Nếu file chưa import `useMemo`/`useState`, bổ sung vào dòng import React tương ứng.)

- [ ] **Step 3: Lọc field nội bộ khỏi bảng "thông số khác"**

Tại danh sách loại trừ extraFields (`:223`), thêm các khóa mới:

```typescript
const HIDDEN = ['method', 'slope', 'intercept', 'forecast', 'history',
                'code', 'suitable', 'reasons', 'recommended_method', 'grain']
```

(Dùng đúng tên biến đang có; chỉ bổ sung 5 phần tử cuối.)

- [ ] **Step 4: Thẻ vàng khi không phù hợp + chỉ vẽ chart khi phù hợp**

Khối render chart bắt đầu `{result && (` (`:315`) → đổi điều kiện:

```tsx
{result && result.suitable !== false && (
```

Ngay TRƯỚC khối đó, thêm thẻ cảnh báo amber:

```tsx
{result && result.suitable === false && (
  <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 space-y-3">
    <div className="flex items-center gap-2 text-amber-300 font-medium">
      <AlertTriangle size={16} />
      Dữ liệu chưa phù hợp với phương pháp này
    </div>
    <ul className="list-disc list-inside text-sm text-amber-100/90 space-y-1">
      {(result.reasons ?? []).map((r, i) => <li key={i}>{r}</li>)}
    </ul>
    {result.recommended_method && (
      <button
        onClick={() => handleUseRecommended(result.recommended_method!)}
        className="inline-flex items-center gap-1.5 rounded-md bg-amber-500/20 hover:bg-amber-500/30 px-3 py-1.5 text-sm text-amber-100 transition-colors"
      >
        <Sparkles size={14} />
        Dùng {result.recommended_method} thay thế
      </button>
    )}
    {result.code && <CodePanel code={result.code} filename="forecast_pipeline.py" />}
  </div>
)}
```

Thêm handler chạy lại forecast với method được gợi ý (đặt cạnh hàm chạy forecast hiện có; tái dùng đúng tên hàm/biến đang gọi `runForecast`):

```typescript
function handleUseRecommended(nm: string) {
  setMethod(nm)            // dùng đúng setter state method hiện có của component
  void runForecastWith(nm) // gọi cùng luồng submit; truyền method override
}
```

Nếu luồng hiện tại không tách được method override, hiện thực tối thiểu: `setMethod(nm)` rồi gọi lại chính hàm submit (đọc method từ state) trong `useEffect`/sau setState. Mục tiêu: bấm nút → chạy lại bằng method gợi ý, KHÔNG tự đổi khi chưa bấm.

- [ ] **Step 5: Trục Y + tooltip + toggle đơn vị cho chart forecast**

YAxis (`:322`) `tickFormatter={formatNum}` → `tickFormatter={(v) => fmtY(v, fcScale, fcMaxAbs)}`.
Tooltip (`:329`) formatter → `fmtY` (giá trị) hoặc `fmtFull` cho nhãn chi tiết.
Thêm cụm nút toggle (đặt trên/cạnh chart), 5 đơn vị:

```tsx
<div className="flex gap-1">
  {(['auto', 'K', 'M', 'B', '%'] as YScale[]).map(s => (
    <button
      key={s}
      onClick={() => setFcScale(s)}
      className={`px-2 py-0.5 text-xs rounded transition-colors ${
        fcScale === s ? 'bg-blue-500/30 text-blue-200' : 'text-gray-400 hover:text-gray-200'
      }`}
    >{s}</button>
  ))}
</div>
```

- [ ] **Step 6: Đổi emoji còn lại sang lucide + Show Code từ `result.code`**

- Bảng so sánh ⭐ (`:474`) → `<Star size={12} />`.
- Trạng thái ✓ (`:488`) → `<Check size={14} className="text-green-400" />`; ✗ (`:489`) → `<span title={r.error}><X size={14} className="text-red-400" /></span>`.
- Caption ⭐ (`:497`) → viết lại bỏ emoji, ví dụ: `Phương pháp tốt nhất được đánh dấu sao.`
- RMSE/giá trị số (`:481`) → bọc bằng `fmtFull(...)`.
- CodePanel (`:433`) `code={generateForecastCode(...)}` → `code={result?.code ?? ''}`.

- [ ] **Step 7: Build**

Run: `cd frontend ; npm run build`
Expected: build thành công, không còn `formatNum`/`generateForecastCode` (tránh lỗi `noUnusedLocals`).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(ml): forecast Y-unit toggle + amber suitability card + lucide + backend code"
```

---

## Task 11: Chart view — toggle đơn vị Chuỗi thời gian + lucide + Show Code

**Files:**
- Modify: `frontend/src/components/ml/MlChartView.tsx`

- [ ] **Step 1: Import + dọn formatter cục bộ**

Dòng `:1` thêm `type ElementType` vào import React. Dòng `:2` lucide `{ ArrowUpDown, Grid2x2, Users, TrendingUp }` → thêm `Link2, BarChart3, ScatterChart, ArrowUp, ArrowDown, AlertTriangle, Code2`. Thêm:

```typescript
import { type YScale, fmtY, fmtFull } from './numFormat'
import CodePanel from './CodePanel'
```

XÓA `type YScale` cục bộ (`:26`) và các formatter cục bộ (`:49-66`) — giờ dùng từ `numFormat`. `makeDot` (`:125-139`) dùng `fmtY` đã import (`:137`) — không đổi logic.

- [ ] **Step 2: Recipe icon → lucide (Point 2)**

Interface recipe thêm `Icon: ElementType`. Bỏ emoji 📈(`:305`) 🔗(`:312`) 📊(`:319`) ⚬(`:326`); gán `Icon` tương ứng (`TrendingUp`, `Link2`, `BarChart3`, `ScatterChart`), render:

```tsx
<Icon size={11} /> {title}
```

- [ ] **Step 3: Toggle đơn vị + maxAbs cho Chuỗi thời gian (Point 1)**

Thêm state:

```typescript
const [tsScale, setTsScale] = useState<YScale>('auto')
```

Tính `tsMaxAbs` từ `tsResult.series.values`:

```typescript
const tsMaxAbs = useMemo(
  () => Math.max(0, ...(tsResult?.series.values ?? []).map(v => Math.abs(v ?? 0))),
  [tsResult],
)
```

YAxis Chuỗi thời gian (`:803`) `tickFormatter={(v) => fmtY(v, tsScale, tsMaxAbs)}`; Tooltip (`:804`) formatter dùng `fmtY`/`fmtFull`. Thêm cụm toggle 5 đơn vị (sao chép mẫu ở Step 5 Task 10, đổi `fcScale/setFcScale` → `tsScale/setTsScale`, `fcMaxAbs` → `tsMaxAbs`).

- [ ] **Step 4: Emoji footer/treemap → lucide**

Treemap ⚠ (`:438`) → `<AlertTriangle size={12} />`; footer ▲ (`:548`) → `<ArrowUp size={12} />`; ▼ (`:549`) → `<ArrowDown size={12} />`.

- [ ] **Step 5: Show Code cho Chuỗi thời gian + Heatmap (Point 4)**

Sau biểu đồ Chuỗi thời gian thêm:

```tsx
{tsResult?.code && <CodePanel code={tsResult.code} filename="timeseries_pipeline.py" />}
```

Sau `<CorrelationHeatmap data={corrData} />` (`:722`) thêm (quyết định: render Show Code của heatmap ở đây để giữ component heatmap thuần SVG):

```tsx
{corrData?.code && <CodePanel code={corrData.code} filename="correlation_pipeline.py" />}
```

- [ ] **Step 6: Build**

Run: `cd frontend ; npm run build`
Expected: build thành công (mọi icon mới đều được dùng).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ml/MlChartView.tsx
git commit -m "feat(ml): timeseries Y-unit toggle + lucide recipes + Show Code (ts & heatmap)"
```

---

## Task 12: Heatmap — màu phân kỳ + chữ tương phản + ô co giãn (Point 3a)

**Files:**
- Modify: `frontend/src/components/ml/CorrelationHeatmap.tsx`

- [ ] **Step 1: Màu phân kỳ + hàm chọn màu chữ theo độ sáng**

Thay `corrToColor` (`:13-22`) bằng thang phân kỳ đỏ↔xám↔xanh (độ bão hòa phi tuyến `t = |r|^0.7` để ô tương quan yếu vẫn phân biệt được):

```typescript
function corrToColor(r: number | null): string {
  if (r === null || Number.isNaN(r)) return '#1f2937'   // ô rỗng
  const t = Math.pow(Math.min(Math.abs(r), 1), 0.7)
  const gray = [55, 65, 81]
  const target = r >= 0 ? [37, 99, 235] : [220, 38, 38]  // xanh dương / đỏ
  const mix = gray.map((g, i) => Math.round(g + (target[i] - g) * t))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}

// Chọn màu chữ tương phản theo độ sáng nền (sửa bug chữ bị mất ở r thấp).
function textColor(bg: string): string {
  const m = bg.match(/rgb\((\d+), (\d+), (\d+)\)/)
  if (!m) return '#ffffff'
  const [r, g, b] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return lum > 0.6 ? '#0b0f14' : '#ffffff'
}
```

- [ ] **Step 2: Dùng `textColor` thay ngưỡng `|val|>0.3` (bug `:91`)**

Thay dòng `txtFill = ... Math.abs(val) > 0.3 ? '#ffffff' : '#9ca3af'` bằng:

```typescript
const cellBg = corrToColor(val)
const txtFill = textColor(cellBg)
```

(và dùng `cellBg` cho nền ô để màu nền & màu chữ luôn nhất quán).

- [ ] **Step 3: Ô co giãn theo bề rộng (56–96px) bằng ResizeObserver**

Trong component, đo bề rộng container và suy ra kích thước ô:

```typescript
const wrapRef = useRef<HTMLDivElement>(null)
const [cell, setCell] = useState(72)
useEffect(() => {
  const el = wrapRef.current
  if (!el) return
  const ro = new ResizeObserver(([e]) => {
    const n = data.columns.length || 1
    const avail = e.contentRect.width - 120     // chừa cột nhãn
    setCell(Math.max(56, Math.min(96, Math.floor(avail / n))))
  })
  ro.observe(el)
  return () => ro.disconnect()
}, [data.columns.length])
```

Bọc SVG bằng `<div ref={wrapRef}>` và dùng `cell` cho width/height/x/y của ô + cỡ chữ (`fontSize={Math.max(10, cell * 0.18)}`). (Bổ sung `useRef`, `useEffect`, `useState` vào import React nếu thiếu.)

- [ ] **Step 4: Build**

Run: `cd frontend ; npm run build`
Expected: build thành công.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ml/CorrelationHeatmap.tsx
git commit -m "feat(ml): heatmap diverging colors + luminance text + responsive cells"
```

---

## Task 13: Stats view — lucide + Show Code từ `result.code` (Point 2 + 4)

**Files:**
- Modify: `frontend/src/components/ml/MlStatsView.tsx`

- [ ] **Step 1: Import lucide + bỏ generator cũ**

Dòng `:2` thêm `Hash, Lightbulb, Target` vào import lucide. XÓA `generateCode` (`:69-109`).

- [ ] **Step 2: Lọc `code` khỏi render generic**

Render generic (`:280`) `Object.entries(result).map(...)` → thêm `.filter(([k]) => k !== 'code')` trước `.map`.

- [ ] **Step 3: Show Code từ backend**

CodePanel (`:317`) `code={generateCode(...)}` → `code={String(result.code ?? '')}`.

- [ ] **Step 4: Emoji thẻ AI → lucide**

🔢 (`:346`) → `<Hash size={14} />`; 💡 (`:358`) → `<Lightbulb size={14} />`; 🎯 (`:370`) → `<Target size={14} />`.

- [ ] **Step 5: Build**

Run: `cd frontend ; npm run build`
Expected: build thành công (không còn `generateCode`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ml/MlStatsView.tsx
git commit -m "feat(ml): stats lucide icons + Show Code from backend pipeline"
```

---

## Task 14: Cohort view — Show Code từ `result.code` (Point 4)

**Files:**
- Modify: `frontend/src/components/ml/MlCohortView.tsx`

- [ ] **Step 1: Bỏ generator cũ + đọc `result.code`**

XÓA `generateCohortCode` (`:10-73`). CodePanel (`:374`) `code={generateCohortCode(...)}` → `code={result?.code ?? ''}`. (CodePanel đã import sẵn `:8`. Thẻ vàng suitability của cohort `:272-282` đã có sẵn — không đụng.)

- [ ] **Step 2: Build**

Run: `cd frontend ; npm run build`
Expected: build thành công (không còn `generateCohortCode`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ml/MlCohortView.tsx
git commit -m "feat(ml): cohort Show Code from backend pipeline"
```

---

## Task 15: Kiểm thử tổng hợp toàn diện

**Files:** (không sửa — chỉ chạy cổng)

- [ ] **Step 1: Backend — toàn bộ test**

Run: `cd backend ; uv run pytest -q`
Expected: PASS toàn bộ (forecast_check, codegen, ml).

- [ ] **Step 2: Frontend — build production**

Run: `cd frontend ; npm run build`
Expected: `tsc -b` không lỗi type/unused, `vite build` tạo `frontend/dist` thành công.

- [ ] **Step 3: Rà emoji còn sót (tùy chọn)**

Run: `cd frontend ; git grep -nP "[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]" src/components/ml/` (hoặc dùng công cụ Grep). Kỳ vọng: chỉ còn các glyph ngoài phạm vi spec (ví dụ `⇄`/`✕` trong cohort mode-toggle/clear — KHÔNG nằm trong yêu cầu này). Nếu lộ emoji trong surface kết quả → xử lý trước khi đóng.

- [ ] **Step 4: Commit cuối (nếu có thay đổi rà soát)**

```bash
git add -A
git commit -m "chore(ml): final verification — backend tests + frontend build green"
```

---

## Self-Review (đã thực hiện khi soạn plan)

**1. Spec coverage** — đối chiếu 4 điểm yêu cầu:
- Point 1 (toggle đơn vị Chuỗi thời gian + Forecast): Task 8 (module), Task 10 Step 2/5 (forecast), Task 11 Step 3 (time-series). ✓
- Point 2 (icon lucide): Task 10 Step 1/6, Task 11 Step 2/4, Task 13 Step 1/4. ✓ (phạm vi emoji = bộ liệt kê trong spec + glyph kết quả lệch rõ; `⇄`/`✕` cohort ghi chú ngoài phạm vi ở Task 15 Step 3.)
- Point 3a (heatmap màu + chữ + co giãn): Task 12. ✓
- Point 3b (thẻ vàng forecast, không fail giả): Task 1 (cổng) + Task 7 Step 2 (router) + Task 10 Step 4 (thẻ vàng). ✓
- Point 4 (Show Code đầy đủ 5 surface): Task 2-6 (generator) + Task 7 (nối router) + Task 10/11/13/14 (đọc `result.code`). ✓
- "dịch tiếng Việt hết": mọi văn bản người dùng thấy + comment code sinh ra bằng tiếng Việt. ✓

**2. Placeholder scan** — không có "TBD/TODO"; mọi step có code đầy đủ. Hai chỗ phụ thuộc luồng component hiện hữu (`handleUseRecommended` ở Task 10 Step 4 dùng đúng setter/`runForecast` của component; toggle UI ở Task 11 Step 3 sao chép mẫu Task 10) được mô tả với mục tiêu rõ ràng + code mẫu hoàn chỉnh, executor đọc file để khớp tên biến.

**3. Type consistency** — `code?: string` đồng nhất trên `ForecastResult`/`CorrelationMatrix`/`TimeseriesResult`/`StatsResult`/`CohortResult` (Task 9). `YScale`/`fmtY`/`fmtFull`/`autoScale` định nghĩa một lần ở `numFormat.ts` (Task 8) và import ở Task 10/11. Tên generator (`forecast_code`/`correlation_code`/`timeseries_code`/`stats_code`/`cohort_code`) khớp giữa Task 2-6, import Task 7, và chữ ký call-site Task 7. `check_forecast_suitability(method, n, seasonal_period)` khớp Task 1 ↔ Task 7 Step 2.

**Quyết định thiết kế đáng chú ý (khác nhẹ so với spec, có chủ đích):**
- `forecast_check` chỉ chặn SARIMAX (`n<2s`) + supervised (`n<4`) + chung (`n<2`) — đúng các trường hợp router thật sự raise; chặn rộng hơn sẽ báo "không phù hợp" sai, đi ngược Point 3b.
- Khối gộp thời gian dùng `dt.truncate` + `group_by` (khớp `aggregate_series`), KHÔNG phải `group_by_dynamic`; timeseries nhúng nguyên văn helper so sánh từ `timegrain.py` để tuyệt đối trung thực.
- `stats_code` là superset 10 test (spec đặt tên số ít `describe_code`).
- Code sinh ra tránh f-string + dùng list song song → diệt tận gốc lớp bug double-brace của Show Code cũ.
