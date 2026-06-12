# Forecast Section Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the ML Studio Forecast tab with fixed SARIMAX, new ETS model, historical+forecast combined chart, number formatting, AI explanation, model comparison, CSV export, and anomaly detection.

**Architecture:** Backend adds ETS model + 2 new endpoints (`/ml/forecast/compare`, `/ml/forecast/interpret`) + fixes date parsing + returns historical data with anomaly flags. Frontend adds `formatNum` utility, merges historical/forecast on one chart, adds Compare and AI Explain panels.

**Tech Stack:** Python/FastAPI, statsmodels (already installed), scikit-learn (already installed), React/TypeScript, Recharts

**Working directory:** `D:\assitant_tools\tools_performance\08_Projects\leonie`  
**Run backend tests:** `cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py -v`  
**Run frontend dev:** `cd frontend && npm run dev`

---

## File Map

| File | Change |
|------|--------|
| `backend/routers/ml.py` | Fix date parsing, add ETS, history+anomaly in response, 2 new endpoints |
| `backend/tests/test_ml.py` | Add tests for new methods + endpoints |
| `frontend/src/types.ts` | Add `HistoryPoint`, `ForecastCompareResult`, update `ForecastResult` |
| `frontend/src/api/ml.ts` | Add `compareForecast`, `interpretForecast` |
| `frontend/src/components/ml/MlForecastView.tsx` | formatNum, ETS, combined chart, compare, AI explain, CSV |

---

## Task 1: Fix SARIMAX — Proper Date Parsing in run_forecast

**Files:**
- Modify: `backend/routers/ml.py` (the `run_forecast` function)
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_ml.py`:

```python
# Fixture with non-ISO date format (MM-YYYY)
TS_MMYYYY = (
    b"month_year,revenue\n"
    b"01-2024,100\n02-2024,120\n03-2024,110\n04-2024,130\n05-2024,140\n"
    b"06-2024,135\n07-2024,150\n08-2024,160\n09-2024,155\n10-2024,170\n"
    b"11-2024,180\n12-2024,175\n01-2025,190\n02-2025,200\n03-2025,195\n"
)

def test_forecast_non_iso_dates(client):
    """SARIMAX / any method must work when date column uses MM-YYYY format."""
    upload = client.post(
        "/ml/upload",
        files={"file": ("mmyyyy.csv", io.BytesIO(TS_MMYYYY), "text/csv")},
    ).json()
    resp = client.post("/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "month_year",
        "value_col": "revenue",
        "periods": 3,
        "method": "linear",
        "seasonal_period": 12,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["forecast"]) == 3
    # Verify values are monotonically reasonable (linear on ascending data)
    assert d["forecast"][0]["value"] > 0


def test_forecast_sarimax_insufficient_data_error(client):
    """SARIMAX with data < 2×seasonal_period must return 400 with helpful message."""
    # 10 rows, seasonal_period=12 → needs ≥24 → must fail with clear message
    short_ts = b"date,val\n"
    for i in range(10):
        short_ts += f"2024-0{i+1 if i < 9 else 9}-01,{100 + i * 10}\n".encode()
    upload = client.post(
        "/ml/upload",
        files={"file": ("short.csv", io.BytesIO(short_ts), "text/csv")},
    ).json()
    resp = client.post("/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date",
        "value_col": "val",
        "periods": 3,
        "method": "sarimax",
        "seasonal_period": 12,
    })
    assert resp.status_code == 400
    assert "24" in resp.json()["detail"] or "seasonal" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_non_iso_dates tests/test_ml.py::test_forecast_sarimax_insufficient_data_error -v
```
Expected: both FAIL (likely 422 or wrong behavior for non-ISO dates, no proper error for insufficient data).

- [ ] **Step 3: Fix run_forecast — replace df.sort with date-aware sort**

In `backend/routers/ml.py`, find `run_forecast` and replace the sorting + date extraction block:

```python
# OLD (lines ~682-695):
#   df_sorted = df.sort(body.date_col)
#   values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
#   n = len(values)
#   if n < 2:
#       raise HTTPException(400, "Need at least 2 data points")
#   try:
#       last_date = date.fromisoformat(str(df_sorted[body.date_col][-1]))
#   except Exception:
#       last_date = date.today()

# NEW:
    try:
        parsed_dates = _try_parse_dates(df[body.date_col])
        df = df.with_columns(parsed_dates.alias("_date_parsed"))
    except ValueError as e:
        raise HTTPException(400, f"Không thể parse cột ngày '{body.date_col}': {e}")

    df_sorted = df.sort("_date_parsed")
    values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
    dates_raw = df_sorted[body.date_col].cast(pl.Utf8).to_list()
    n = len(values)
    if n < 2:
        raise HTTPException(400, "Need at least 2 data points")

    try:
        last_date = df_sorted["_date_parsed"][-1]
        # Polars Date → Python date
        if hasattr(last_date, "item"):
            last_date = last_date.item()
        if not isinstance(last_date, date):
            last_date = date.today()
    except Exception:
        last_date = date.today()
```

Also add validation at the top of the SARIMAX branch (find `if body.method == 'sarimax':` and add before the try/except):

```python
    if body.method == 'sarimax':
        s = body.seasonal_period
        train = values[-500:] if n > 500 else values
        if len(train) < 2 * s:
            raise HTTPException(
                400,
                f"SARIMAX cần tối thiểu {2 * s} điểm dữ liệu với seasonal_period={s}. "
                f"Dữ liệu hiện tại: {len(train)} điểm. "
                f"Giải pháp: giảm Seasonal period xuống ≤ {len(train) // 2}, "
                f"hoặc dùng ETS / Linear thay thế."
            )
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX as _SARIMAX
        # ... rest of existing sarimax code
```

- [ ] **Step 4: Run tests to verify fix**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_non_iso_dates tests/test_ml.py::test_forecast_sarimax_insufficient_data_error -v
```
Expected: both PASS.

- [ ] **Step 5: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "fix(forecast): use _try_parse_dates for date sorting + SARIMAX validation"
```

---

## Task 2: Add History + Anomaly to Forecast Response

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_ml.py`:

```python
TS_20 = b"date,val\n"
for _i in range(20):
    TS_20 += f"2024-{_i+1:02d}-01,{100 + _i * 5}\n".encode()

def test_forecast_returns_history(client):
    """run_forecast must include 'history' list in response."""
    upload = client.post(
        "/ml/upload",
        files={"file": ("ts20.csv", io.BytesIO(TS_20), "text/csv")},
    ).json()
    resp = client.post("/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 3, "method": "linear", "seasonal_period": 12,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "history" in d
    assert len(d["history"]) > 0
    h0 = d["history"][0]
    assert "date" in h0
    assert "value" in h0
    assert "is_anomaly" in h0
    assert "z_score" in h0
```

- [ ] **Step 2: Run test to confirm failure**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_returns_history -v
```
Expected: FAIL — `"history" not in d`.

- [ ] **Step 3: Add anomaly helper + history builder before method branches**

In `backend/routers/ml.py`, in `run_forecast` after computing `n` and before the method routing (`if body.method == 'moving_average':`), add:

```python
    # ── Anomaly detection (IQR + z-score on full history) ──────────────────
    q1, q3 = float(np.percentile(values, 25)), float(np.percentile(values, 75))
    iqr = q3 - q1
    fence_lo = q1 - 1.5 * iqr
    fence_hi = q3 + 1.5 * iqr
    z_scores_arr = np.abs((values - values.mean()) / (values.std() + 1e-9))
    is_anomaly_arr = (values < fence_lo) | (values > fence_hi) | (z_scores_arr > 2.5)

    hist_n = min(n, 60)
    _history = [
        {
            "date":       dates_raw[n - hist_n + i],
            "value":      round(float(values[n - hist_n + i]), 4),
            "is_anomaly": bool(is_anomaly_arr[n - hist_n + i]),
            "z_score":    round(float(z_scores_arr[n - hist_n + i]), 2),
        }
        for i in range(hist_n)
    ]
```

Then in each method's return statement, add `"history": _history`. For example the linear return becomes:

```python
    return {
        "method": "linear",
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "forecast": forecast,
        "history": _history,
    }
```

Do the same for `moving_average`, `sarimax`, and `supervised` returns.

- [ ] **Step 4: Run test to verify**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_returns_history -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(forecast): add history + anomaly detection to forecast response"
```

---

## Task 3: Add ETS (Holt-Winters) Model

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write failing test**

```python
TS_24 = b"date,val\n"
for _i in range(24):
    TS_24 += f"202{3 + _i // 12}-{_i % 12 + 1:02d}-01,{100 + _i * 3 + (_i % 12) * 2}\n".encode()

def test_forecast_ets(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("ets24.csv", io.BytesIO(TS_24), "text/csv")},
    ).json()
    resp = client.post("/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 6, "method": "ets", "seasonal_period": 12,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["method"].startswith("ETS")
    assert len(d["forecast"]) == 6
    assert "aic" in d
    assert "history" in d
```

- [ ] **Step 2: Run test to confirm failure**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_ets -v
```
Expected: FAIL — `"method" field won't start with "ETS"`.

- [ ] **Step 3: Add ETS branch in run_forecast**

In `backend/routers/ml.py`, add this branch before the `# Default: linear regression` fallback (i.e., between `supervised` and `linear` blocks):

```python
    if body.method == 'ets':
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing as _ETS
        except ImportError:
            raise HTTPException(500, "statsmodels not installed — run `uv sync`")

        s = body.seasonal_period
        train = values[-500:] if n > 500 else values
        use_seasonal = len(train) >= 2 * s

        try:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore")
                ets_model = _ETS(
                    train,
                    trend='add',
                    damped_trend=True,
                    seasonal='add' if use_seasonal else None,
                    seasonal_periods=s if use_seasonal else None,
                ).fit(optimized=True, disp=False)
        except Exception as e:
            raise HTTPException(400, f"ETS failed to fit: {e}")

        fcast_vals = ets_model.forecast(body.periods)
        resid_std = float(np.std(ets_model.resid))
        ci = resid_std * 1.96

        ets_forecast = []
        for i, pred in enumerate(fcast_vals):
            ets_forecast.append({
                "date":  (last_date + timedelta(days=i + 1)).isoformat(),
                "value": round(float(pred), 4),
                "lower": round(float(pred - ci), 4),
                "upper": round(float(pred + ci), 4),
            })

        params = ets_model.params
        return {
            "method":       f"ETS(add,damp,{'add' if use_seasonal else 'none'})",
            "slope":        0.0,
            "intercept":    round(float(params.get("smoothing_level", 0.0)), 4),
            "aic":          round(float(ets_model.aic), 2) if hasattr(ets_model, 'aic') else None,
            "alpha":        round(float(params.get("smoothing_level", 0.0)), 4),
            "beta":         round(float(params.get("smoothing_trend", 0.0)), 4),
            "gamma":        round(float(params.get("smoothing_seasonal", 0.0)), 4) if use_seasonal else None,
            "trained_on":   int(len(train)),
            "forecast":     ets_forecast,
            "history":      _history,
        }
```

- [ ] **Step 4: Run test to verify**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_ets -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(forecast): add ETS (Holt-Winters) model with damped trend + AIC"
```

---

## Task 4: Add /ml/forecast/compare Endpoint

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write failing test**

```python
def test_forecast_compare(client):
    upload = client.post(
        "/ml/upload",
        files={"file": ("cmp.csv", io.BytesIO(TS_24), "text/csv")},
    ).json()
    resp = client.post("/ml/forecast/compare", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 3,
        "seasonal_period": 12,
        "methods": ["linear", "moving_average", "ets"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "results" in d
    assert "best" in d
    assert len(d["results"]) == 3
    r0 = d["results"][0]
    assert "method" in r0
    assert "mape" in r0
    assert "rmse" in r0
    assert "status" in r0
    # best is one of the requested methods
    assert d["best"] in ["linear", "moving_average", "ets"]
```

- [ ] **Step 2: Run test to confirm failure**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_compare -v
```
Expected: FAIL — 404 or 422 (endpoint doesn't exist).

- [ ] **Step 3: Add Pydantic model + endpoint**

In `backend/routers/ml.py`, add after the `ForecastIn` class definition:

```python
class ForecastCompareIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7
    seasonal_period: int = 12
    methods: list[str]
```

Then add the endpoint function (after `run_forecast`, before `run_stats`):

```python
@router.post("/forecast/compare")
def compare_forecast(body: ForecastCompareIn):
    conn = get_connection()
    row = _get_file_row(conn, body.file_id)
    conn.close()
    df = _load_df(row["filepath"])

    for col in (body.date_col, body.value_col):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        parsed_dates = _try_parse_dates(df[body.date_col])
        df = df.with_columns(parsed_dates.alias("_date_parsed"))
    except ValueError as e:
        raise HTTPException(400, f"Cannot parse date column: {e}")

    df_sorted = df.sort("_date_parsed")
    values = df_sorted[body.value_col].drop_nulls().cast(pl.Float64).to_numpy()
    n = len(values)
    if n < 6:
        raise HTTPException(400, "Need at least 6 data points for comparison")

    split = max(int(n * 0.8), n - 6)
    train_vals, test_vals = values[:split], values[split:]
    n_test = len(test_vals)
    s = body.seasonal_period

    METHOD_LABELS = {
        "linear": "Linear Trend",
        "moving_average": "Moving Average",
        "ets": "ETS (Holt-Winters)",
        "sarimax": "SARIMAX",
        "supervised": "Supervised ML",
    }

    results = []
    for method in body.methods:
        label = METHOD_LABELS.get(method, method)
        try:
            preds = _predict_for_compare(train_vals, n_test, method, s)
            mape = float(np.mean(np.abs((test_vals - preds) / (np.abs(test_vals) + 1e-9)))) * 100
            rmse = float(np.sqrt(np.mean((test_vals - preds) ** 2)))
            results.append({
                "method": method, "label": label,
                "mape": round(mape, 2), "rmse": round(rmse, 4),
                "aic": None, "status": "ok",
            })
        except Exception as e:
            results.append({
                "method": method, "label": label,
                "mape": None, "rmse": None,
                "aic": None, "status": "error", "error": str(e)[:200],
            })

    ok_results = [r for r in results if r["status"] == "ok" and r["mape"] is not None]
    best = min(ok_results, key=lambda r: r["mape"])["method"] if ok_results else (body.methods[0] if body.methods else "linear")
    return {"results": results, "best": best}
```

Then add the helper function `_predict_for_compare` before `run_forecast`:

```python
def _predict_for_compare(train: np.ndarray, n_steps: int, method: str, s: int) -> np.ndarray:
    """Fit method on train, forecast n_steps, return predictions array."""
    n = len(train)

    if method == "linear":
        x = np.arange(n)
        slope, intercept, *_ = scipy_stats.linregress(x, train)
        return np.array([intercept + slope * (n + i) for i in range(n_steps)])

    if method == "moving_average":
        window = max(3, min(7, n // 3))
        ma = np.array([train[max(0, i - window + 1):i + 1].mean() for i in range(n)])
        look_back = min(window, n - 1)
        slope_ma = (ma[-1] - ma[-look_back - 1]) / look_back if look_back > 0 else 0.0
        return np.array([ma[-1] + slope_ma * (i + 1) for i in range(n_steps)])

    if method == "ets":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing as _ETS
        use_seasonal = n >= 2 * s
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = _ETS(
                train,
                trend='add', damped_trend=True,
                seasonal='add' if use_seasonal else None,
                seasonal_periods=s if use_seasonal else None,
            ).fit(optimized=True, disp=False)
        return np.array(fit.forecast(n_steps))

    if method == "sarimax":
        if n < 2 * s:
            raise ValueError(f"SARIMAX cần ≥ {2*s} điểm, có {n}")
        from statsmodels.tsa.statespace.sarimax import SARIMAX as _SARIMAX
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = _SARIMAX(
                train, order=(1, 1, 1), seasonal_order=(1, 1, 1, s),
                enforce_stationarity=False, enforce_invertibility=False,
            ).fit(disp=False, maxiter=100)
        return np.array(fit.forecast(n_steps))

    if method == "supervised":
        from sklearn.linear_model import Ridge
        lags = min(5, n // 4)
        if n < lags + 2:
            raise ValueError(f"Supervised cần ≥ {lags + 2} điểm")
        X = np.array([train[i - lags:i] for i in range(lags, n)])
        y = train[lags:]
        model = Ridge(alpha=1.0).fit(X, y)
        history = list(train[-lags:])
        preds = []
        for _ in range(n_steps):
            p = float(model.predict(np.array(history[-lags:]).reshape(1, -1))[0])
            preds.append(p)
            history.append(p)
        return np.array(preds)

    raise ValueError(f"Unknown method: {method}")
```

- [ ] **Step 4: Run test to verify**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_compare -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(forecast): add /forecast/compare endpoint with MAPE/RMSE cross-validation"
```

---

## Task 5: Add /ml/forecast/interpret Endpoint

**Files:**
- Modify: `backend/routers/ml.py`
- Test: `backend/tests/test_ml.py`

- [ ] **Step 1: Write failing test**

```python
def test_forecast_interpret_structure(client, monkeypatch):
    """interpret endpoint returns summary/trend/actions (mocked AI)."""
    import backend.routers.ml as ml_module

    def mock_ai(prompt, max_tokens=1024):
        return '{"summary": "Doanh thu tăng đều.", "trend": "Xu hướng tăng nhẹ.", "actions": "Giữ nguyên chiến lược."}'

    monkeypatch.setattr(ml_module, "_call_ai_ml", mock_ai)

    resp = client.post("/ml/forecast/interpret", json={
        "method": "linear",
        "date_col": "date",
        "value_col": "revenue",
        "periods": 7,
        "result": {"slope": 1.5, "intercept": 100.0, "forecast": [{"date": "2026-01-01", "value": 150.0, "lower": 140.0, "upper": 160.0}]},
        "filename": "test.csv",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "summary" in d
    assert "trend" in d
    assert "actions" in d
```

- [ ] **Step 2: Run test to confirm failure**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_interpret_structure -v
```
Expected: FAIL — endpoint doesn't exist.

- [ ] **Step 3: Add Pydantic model + endpoint**

In `backend/routers/ml.py`, add after `ForecastCompareIn`:

```python
class ForecastInterpretIn(BaseModel):
    method: str
    date_col: str
    value_col: str
    periods: int
    result: dict
    filename: str
```

Add the endpoint after `compare_forecast`:

```python
@router.post("/forecast/interpret")
def interpret_forecast(body: ForecastInterpretIn):
    # Build a readable summary of the result
    fcast = body.result.get("forecast", [])
    last_vals = fcast[-3:] if len(fcast) >= 3 else fcast
    last_summary = ", ".join(
        f"{f['date']}: {f['value']:,.0f}" for f in last_vals
    )

    extras = {k: v for k, v in body.result.items()
              if k not in ("forecast", "history", "method", "slope", "intercept")
              and not isinstance(v, list)}
    extras_str = "\n".join(f"  {k}: {v}" for k, v in extras.items())

    first_val = fcast[0]["value"] if fcast else None
    last_val  = fcast[-1]["value"] if fcast else None
    trend_pct = ""
    if first_val and last_val and first_val != 0:
        pct = (last_val - first_val) / abs(first_val) * 100
        trend_pct = f"Từ kỳ 1 đến kỳ {len(fcast)}: {'tăng' if pct > 0 else 'giảm'} {abs(pct):.1f}%."

    prompt = (
        f"Bạn là Senior Data Analyst người Việt với 10 năm kinh nghiệm.\n"
        f"Dataset: {body.filename}\n"
        f"Cột ngày: {body.date_col}, Cột giá trị: {body.value_col}\n"
        f"Phương pháp dự báo: {body.method}, Dự báo {body.periods} kỳ tới.\n"
        f"{extras_str}\n"
        f"Các giá trị dự báo cuối: {last_summary}\n"
        f"{trend_pct}\n\n"
        "Phân tích kết quả dự báo này theo 3 phần, trả về JSON:\n"
        "{\n"
        '  "summary": "Tóm tắt xu hướng dự báo bằng 1-2 câu dễ hiểu",\n'
        '  "trend": "Giải thích xu hướng + mức độ tin cậy của model này",\n'
        '  "actions": "2-3 đề xuất hành động cụ thể dựa trên kết quả"\n'
        "}\n"
        "Viết bằng tiếng Việt, ngắn gọn, thực tế. Chỉ JSON, không giải thích thêm."
    )

    try:
        raw = _call_ai_ml(prompt, max_tokens=800)
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        import json as _json
        result = _json.loads(raw.strip())
        return result
    except Exception as e:
        raise HTTPException(500, f"AI interpret failed: {e}")
```

- [ ] **Step 4: Run test to verify**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py::test_forecast_interpret_structure -v
```
Expected: PASS.

- [ ] **Step 5: Run full backend test suite**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```
git add backend/routers/ml.py backend/tests/test_ml.py
git commit -m "feat(forecast): add /forecast/interpret AI explanation endpoint"
```

---

## Task 6: Update Frontend Types

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Update ForecastResult and add new types**

In `frontend/src/types.ts`, replace the `ForecastPoint` and `ForecastResult` interfaces with:

```typescript
export interface ForecastPoint {
  date: string
  value: number
  lower: number
  upper: number
}

export interface HistoryPoint {
  date: string
  value: number
  is_anomaly: boolean
  z_score: number
}

export interface ForecastResult {
  method: string
  slope: number
  intercept: number
  forecast: ForecastPoint[]
  history?: HistoryPoint[]
  aic?: number
  r2?: number
  lags_used?: number
  trained_on?: number
  alpha?: number
  beta?: number
  gamma?: number
}

export interface ForecastCompareRow {
  method: string
  label: string
  mape: number | null
  rmse: number | null
  aic: number | null
  status: 'ok' | 'error'
  error?: string
}

export interface ForecastCompareResult {
  results: ForecastCompareRow[]
  best: string
}

export interface ForecastInterpretResult {
  summary: string
  trend: string
  actions: string
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors related to types.ts changes.

- [ ] **Step 3: Commit**

```
git add frontend/src/types.ts
git commit -m "feat(types): add HistoryPoint, ForecastCompareResult, ForecastInterpretResult"
```

---

## Task 7: Update API Client

**Files:**
- Modify: `frontend/src/api/ml.ts`

- [ ] **Step 1: Add two new API functions**

In `frontend/src/api/ml.ts`, update `runForecast` signature (add `method` and `seasonal_period` if not already there) and add two new functions at the end:

```typescript
import type {
  DatasetInfo, QueryResult, StatsResult, ForecastResult,
  ForecastCompareResult, ForecastInterpretResult,
} from '../types'

// Update existing runForecast (already has method + seasonal_period in main dir — verify it matches):
export async function runForecast(
  file_id: string,
  date_col: string,
  value_col: string,
  periods: number,
  method = 'linear',
  seasonal_period = 12,
): Promise<ForecastResult> {
  const { data } = await client.post<ForecastResult>('/ml/forecast', {
    file_id, date_col, value_col, periods, method, seasonal_period,
  })
  return data
}

export async function compareForecast(
  file_id: string,
  date_col: string,
  value_col: string,
  periods: number,
  seasonal_period: number,
  methods: string[],
): Promise<ForecastCompareResult> {
  const { data } = await client.post<ForecastCompareResult>('/ml/forecast/compare', {
    file_id, date_col, value_col, periods, seasonal_period, methods,
  })
  return data
}

export async function interpretForecast(body: {
  method: string
  date_col: string
  value_col: string
  periods: number
  result: object
  filename: string
}): Promise<ForecastInterpretResult> {
  const { data } = await client.post<ForecastInterpretResult>('/ml/forecast/interpret', body)
  return data
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```
git add frontend/src/api/ml.ts
git commit -m "feat(api): add compareForecast + interpretForecast API functions"
```

---

## Task 8: Number Formatter + ETS Method in Frontend

**Files:**
- Modify: `frontend/src/components/ml/MlForecastView.tsx`

- [ ] **Step 1: Add formatNum helper and ETS method entry**

At the top of `MlForecastView.tsx` (before the `METHODS` array), add:

```typescript
function formatNum(v: number): string {
  if (v === null || v === undefined || isNaN(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e12) return (v / 1e12).toFixed(1) + 'T'
  if (abs >= 1e9)  return (v / 1e9).toFixed(1)  + 'B'
  if (abs >= 1e6)  return (v / 1e6).toFixed(1)  + 'M'
  if (abs >= 1e3)  return (v / 1e3).toFixed(1)  + 'K'
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}
```

Update the `ForecastMethod` type:

```typescript
type ForecastMethod = 'linear' | 'moving_average' | 'ets' | 'sarimax' | 'supervised'
```

Add ETS entry to `METHODS` array (after `moving_average`, before `sarimax`):

```typescript
  {
    value: 'ets',
    label: 'ETS (Holt-Winters)',
    group: 'Statistical (Seasonal)',
    what: 'Exponential Smoothing — tự động học trọng số cho level, trend, và seasonality theo thời gian.',
    when: 'Dữ liệu có trend + seasonality rõ. Nhanh hơn SARIMAX, ít over-fit hơn. Tốt với monthly/quarterly.',
    requires: 'Tối thiểu 2× seasonal_period điểm. statsmodels có sẵn, không cần cài thêm.',
    output: 'AIC (thấp = tốt hơn), alpha (level), beta (trend), gamma (seasonal).',
    needsSeasonal: true,
  },
```

- [ ] **Step 2: Apply formatNum to metric cards and chart tooltip**

In the `extraFields` rendering block (the metric cards), replace the raw number display:

```tsx
// BEFORE:
<p className="text-sm font-semibold text-white">{typeof v === 'number' ? v : String(v)}</p>

// AFTER:
<p className="text-sm font-semibold text-white">
  {typeof v === 'number' ? formatNum(v) : String(v)}
</p>
```

In the `<Tooltip>` component, add `formatter`:

```tsx
<Tooltip
  formatter={(value: number) => [formatNum(value), '']}
  labelFormatter={(label) => `${label}`}
  contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }}
/>
```

In `<YAxis>`, update:

```tsx
<YAxis
  tick={{ fill: '#6b7280', fontSize: 10 }}
  tickFormatter={formatNum}
  width={65}
/>
```

- [ ] **Step 3: Check TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(forecast-ui): add formatNum, ETS method, fix number display in chart + cards"
```

---

## Task 9: Combined Historical + Forecast Chart with Anomaly Dots

**Files:**
- Modify: `frontend/src/components/ml/MlForecastView.tsx`

- [ ] **Step 1: Add ReferenceLine import and build combined chart data**

Update the Recharts imports at the top of `MlForecastView.tsx`:

```typescript
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
```

Replace the `chartData` computation (currently just forecast) with combined data:

```typescript
  // Build combined chart data: history (hist field) + forecast (value field)
  const histPoints = result?.history?.map(h => ({
    date:      h.date.slice(5),
    hist:      h.value,
    isAnomaly: h.is_anomaly,
    zScore:    h.z_score,
    value:     undefined as number | undefined,
    lower:     undefined as number | undefined,
    upper:     undefined as number | undefined,
    range:     undefined as [number, number] | undefined,
  })) ?? []

  const fcastPoints = result?.forecast.map(f => ({
    date:      f.date.slice(5),
    hist:      undefined as number | undefined,
    isAnomaly: false,
    zScore:    0,
    value:     f.value,
    lower:     f.lower,
    upper:     f.upper,
    range:     [f.lower, f.upper] as [number, number],
  })) ?? []

  const chartData = [...histPoints, ...fcastPoints]
  const separatorDate = histPoints.length > 0 ? histPoints[histPoints.length - 1].date : undefined
```

- [ ] **Step 2: Update chart JSX to show both lines + anomaly dots + separator**

Replace the chart content inside `<ComposedChart>`:

```tsx
<ComposedChart data={chartData}>
  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
  <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} />
  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={formatNum} width={65} />
  <Tooltip
    formatter={(value: number, name: string) => {
      const labels: Record<string, string> = {
        hist: 'Lịch sử', value: 'Dự báo',
        lower: 'CI thấp', upper: 'CI cao',
      }
      return [formatNum(value), labels[name] ?? name]
    }}
    contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }}
  />
  {/* 95% CI area — forecast only */}
  <Area
    type="monotone" dataKey="range"
    fill="#60a5fa" fillOpacity={0.12} stroke="none"
  />
  {/* Historical line */}
  <Line
    type="monotone" dataKey="hist"
    stroke="#60a5fa" strokeWidth={2}
    dot={(props) => {
      const { cx, cy, payload } = props as { cx: number; cy: number; payload: { isAnomaly: boolean } }
      if (payload.isAnomaly) {
        return <circle key={`a-${cx}`} cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#ef4444" strokeWidth={1} />
      }
      return <circle key={`h-${cx}`} cx={cx} cy={cy} r={2} fill="#60a5fa" />
    }}
    connectNulls={false}
  />
  {/* Forecast line — dashed */}
  <Line
    type="monotone" dataKey="value"
    stroke="#60a5fa" strokeWidth={2}
    strokeDasharray="5 3"
    dot={{ r: 3, fill: '#60a5fa' }}
    connectNulls={false}
  />
  {/* Vertical separator */}
  {separatorDate && (
    <ReferenceLine
      x={separatorDate}
      stroke="rgba(255,255,255,0.2)"
      strokeDasharray="4 2"
      label={{ value: 'Dự báo →', position: 'top', fill: '#6b7280', fontSize: 9 }}
    />
  )}
</ComposedChart>
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(forecast-ui): combined historical+forecast chart with anomaly dots + separator"
```

---

## Task 10: Model Comparison Panel

**Files:**
- Modify: `frontend/src/components/ml/MlForecastView.tsx`

- [ ] **Step 1: Add compare state + import**

In `MlForecastView.tsx`, add new imports:

```typescript
import { TrendingUp, Download, BarChart2, Sparkles } from 'lucide-react'
import { compareForecast, interpretForecast } from '../../api/ml'
import type { ForecastCompareResult, ForecastInterpretResult } from '../../types'
```

Add new state variables after the existing ones:

```typescript
  const [comparing,     setComparing]     = useState(false)
  const [compareResult, setCompareResult] = useState<ForecastCompareResult | null>(null)
  const [compareError,  setCompareError]  = useState('')
```

Add handler:

```typescript
  async function handleCompare() {
    setComparing(true); setCompareError(''); setCompareResult(null)
    const methods = ['linear', 'moving_average', 'ets', 'sarimax', 'supervised']
    try {
      setCompareResult(await compareForecast(
        dataset.file_id, dateCol, valueCol, periods, seasonalPeriod, methods
      ))
    } catch (e: unknown) {
      setCompareError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Compare failed')
    } finally { setComparing(false) }
  }
```

- [ ] **Step 2: Add compare button and result table to JSX**

After the Export buttons row, add:

```tsx
      {/* Model comparison */}
      <div className="flex gap-2 items-center">
        <button
          onClick={handleCompare} disabled={comparing}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
        >
          <BarChart2 size={12} /> {comparing ? 'Đang so sánh...' : 'So sánh Model'}
        </button>
      </div>

      {compareError && <p className="text-danger text-xs">{compareError}</p>}

      {compareResult && (
        <div className="bg-secondary border border-white/5 rounded-lg overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left px-3 py-2 text-gray-600 font-normal">Model</th>
                <th className="text-right px-3 py-2 text-gray-600 font-normal">MAPE</th>
                <th className="text-right px-3 py-2 text-gray-600 font-normal">RMSE</th>
                <th className="text-right px-3 py-2 text-gray-600 font-normal">AIC</th>
                <th className="text-center px-3 py-2 text-gray-600 font-normal">Status</th>
              </tr>
            </thead>
            <tbody>
              {compareResult.results.map((r) => (
                <tr
                  key={r.method}
                  className={`border-b border-white/5 last:border-0 transition-colors ${
                    r.method === compareResult.best
                      ? 'bg-analytics/10 border-l-2 border-l-analytics'
                      : 'hover:bg-white/2'
                  }`}
                >
                  <td className="px-3 py-2 text-white">
                    {r.method === compareResult.best && <span className="mr-1">⭐</span>}
                    {r.label}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {r.mape != null ? `${r.mape.toFixed(1)}%` : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {r.rmse != null ? formatNum(r.rmse) : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {r.aic != null ? r.aic.toFixed(1) : '—'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {r.status === 'ok'
                      ? <span className="text-green-500">✓</span>
                      : <span className="text-danger" title={r.error}>✗</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-3 py-1.5 text-[10px] text-gray-600">
            Cross-validation 80/20 · thấp hơn = tốt hơn · ⭐ model tốt nhất theo MAPE
          </p>
        </div>
      )}
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(forecast-ui): model comparison panel with MAPE/RMSE table"
```

---

## Task 11: AI Explanation Panel

**Files:**
- Modify: `frontend/src/components/ml/MlForecastView.tsx`

- [ ] **Step 1: Add AI state**

Add state variables:

```typescript
  const [aiLoading, setAiLoading] = useState(false)
  const [aiResult,  setAiResult]  = useState<ForecastInterpretResult | null>(null)
  const [aiError,   setAiError]   = useState('')
```

Add handler:

```typescript
  async function handleAiExplain() {
    if (!result) return
    setAiLoading(true); setAiError(''); setAiResult(null)
    try {
      setAiResult(await interpretForecast({
        method: result.method,
        date_col: dateCol,
        value_col: valueCol,
        periods,
        result: result as unknown as object,
        filename: dataset.filename,
      }))
    } catch (e: unknown) {
      setAiError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'AI explain failed')
    } finally { setAiLoading(false) }
  }
```

- [ ] **Step 2: Add AI explanation UI after the chart section**

After the metric cards (`extraFields`) and before the Export row, add:

```tsx
      {/* AI Explanation */}
      {result && (
        <div>
          <button
            onClick={handleAiExplain}
            disabled={aiLoading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-white/10 text-gray-400 hover:text-white hover:border-white/20 transition-colors disabled:opacity-40"
          >
            <Sparkles size={12} />
            {aiLoading ? 'Đang phân tích...' : 'Giải thích AI'}
          </button>

          {aiError && <p className="text-danger text-xs mt-2">{aiError}</p>}

          {aiResult && (
            <div className="mt-3 bg-white/3 border border-white/5 rounded-lg p-4 flex flex-col gap-3 text-[11px]">
              <div>
                <p className="text-[10px] text-analytics uppercase tracking-wider mb-1">Tóm tắt</p>
                <p className="text-gray-300 leading-relaxed">{aiResult.summary}</p>
              </div>
              <div>
                <p className="text-[10px] text-analytics uppercase tracking-wider mb-1">Xu hướng</p>
                <p className="text-gray-300 leading-relaxed">{aiResult.trend}</p>
              </div>
              <div>
                <p className="text-[10px] text-analytics uppercase tracking-wider mb-1">Đề xuất</p>
                <p className="text-gray-300 leading-relaxed">{aiResult.actions}</p>
              </div>
            </div>
          )}
        </div>
      )}
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(forecast-ui): AI explanation panel (giải thích AI) for forecast results"
```

---

## Task 12: CSV Export

**Files:**
- Modify: `frontend/src/components/ml/MlForecastView.tsx`

- [ ] **Step 1: Add downloadCsv function**

Add this function before the component definition (alongside `downloadPy` and `formatNum`):

```typescript
function downloadCsv(result: ForecastResult, valueCol: string) {
  const rows: string[] = ['date,value,lower_95,upper_95']
  for (const f of result.forecast) {
    rows.push(`${f.date},${f.value},${f.lower},${f.upper}`)
  }
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `forecast_${valueCol}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: Add CSV button alongside Export Python**

In the existing footer row (where `Export Python` button is), add the CSV button:

```tsx
          <div className="flex items-center justify-between">
            <p className="text-gray-600 text-[10px]">
              {result.method} · shaded = 95% CI
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={() => downloadCsv(result, valueCol)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                <Download size={12} /> Export CSV
              </button>
              <button
                onClick={() => downloadPy(result, dateCol, valueCol, periods, seasonalPeriod, dataset.filename)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                <Download size={12} /> Export Python
              </button>
            </div>
          </div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Run full backend test suite one final time**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ml.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Final commit**

```
git add frontend/src/components/ml/MlForecastView.tsx
git commit -m "feat(forecast-ui): CSV export for forecast results"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Fix SARIMAX (Task 1 — date parsing + validation)
- [x] ETS model (Task 3 — backend + Task 8 frontend METHODS)
- [x] History + anomaly in response (Task 2)
- [x] Model comparison with MAPE/RMSE (Task 4 + Task 10)
- [x] AI explanation for forecast (Task 5 + Task 11)
- [x] Number formatting (Task 8 — formatNum)
- [x] Combined historical + forecast chart (Task 9)
- [x] CSV export (Task 12)
- [x] Type updates (Task 6)
- [x] API client (Task 7)

**Placeholder scan:** No TBD, TODO, or "similar to Task N" patterns. All code blocks complete.

**Type consistency:**
- `ForecastResult.history` is `HistoryPoint[]` — defined Task 6, used Task 9 ✓
- `ForecastCompareResult` defined Task 6, used Task 10 ✓
- `ForecastInterpretResult` defined Task 6, used Task 11 ✓
- `compareForecast` / `interpretForecast` defined Task 7, imported Task 10+11 ✓
- `formatNum` defined Task 8, used Task 9+10 ✓
- `downloadCsv` defined Task 12, used Task 12 ✓
- `_history` variable built Task 2, referenced in all method returns Task 2+3 ✓
- `_predict_for_compare` helper defined Task 4, called in Task 4 endpoint ✓
