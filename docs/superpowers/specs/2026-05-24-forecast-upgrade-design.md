# Forecast Section Upgrade — Design Spec
**Date:** 2026-05-24  
**Approach:** B (Fix + ETS + Historical chart + Format số + AI giải thích + CSV + Model comparison + Anomaly)  
**Target directory:** `D:\assitant_tools\tools_performance\08_Projects\leonie`

---

## Context

ML Studio có tab Forecast với 4 methods: Linear, Moving Average, SARIMAX, Supervised ML.  
SARIMAX đang fail, số hiển thị không format (897436771169.6013), chart chỉ show forecast không có historical.  
Cần nâng cấp toàn diện theo yêu cầu người dùng data analyst làm việc với dữ liệu monthly/weekly/quarterly.

---

## Root Causes

1. **SARIMAX fail**: `df.sort(body.date_col)` sort theo string, không parse ngày đúng. Hàm `_try_parse_dates` có sẵn ở cohort nhưng không dùng ở forecast. Ngoài ra SARIMAX (1,1,1)×(1,1,1,s) với dữ liệu ít cần error message rõ hơn.
2. **Số không format**: Frontend không có `formatNum()`, raw float 897436771169 gây khó đọc.
3. **Chart thiếu historical**: Chỉ show forecast points, không thấy xu hướng quá khứ.

---

## Architecture

```
MlForecastView.tsx
  ├── Controls: Method | Date col | Value col | Periods | [Seasonal period]
  ├── Method hint card (đã có)
  ├── [NEW] "So sánh Model" button → CompareTable
  ├── Chart: Historical (solid) ──|── Forecast (dashed) + CI + Anomaly dots
  ├── Metric cards: AIC / R² / LAGS USED — formatted numbers
  ├── [NEW] "Giải thích AI" button → AI explanation panel
  └── Export: CSV | Python
```

---

## Backend Changes (`backend/routers/ml.py`)

### 1. Fix SARIMAX — Date parsing
Replace `df.sort(body.date_col)` with:
```python
try:
    parsed_dates = _try_parse_dates(df[body.date_col])
    df = df.with_columns(parsed_dates.alias("_date_parsed"))
    df_sorted = df.sort("_date_parsed")
except ValueError as e:
    raise HTTPException(400, f"Không thể parse cột ngày: {e}")
```

### 2. Fix SARIMAX — Validation
Before fitting, check:
```python
if len(train) < 2 * s:
    raise HTTPException(400,
        f"SARIMAX cần tối thiểu {2 * s} điểm với seasonal_period={s}. "
        f"Dữ liệu hiện tại: {len(train)} điểm. "
        f"Giảm seasonal_period xuống {len(train) // 2} hoặc dùng Linear/ETS.")
```

### 3. Return historical data
Tất cả methods trả thêm field `history`:
```python
hist_n = min(n, 60)
history = [
    {"date": str(df_sorted[body.date_col][-hist_n + i]),
     "value": round(float(values[-hist_n + i]), 4),
     "is_anomaly": bool(z_scores[-hist_n + i] > 2.5),
     "z_score": round(float(z_scores[-hist_n + i]), 2)}
    for i in range(hist_n)
]
```

### 4. Anomaly detection (integrated into run_forecast)
```python
q1, q3 = np.percentile(values, 25), np.percentile(values, 75)
iqr = q3 - q1
lower_fence, upper_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
z_scores = np.abs((values - values.mean()) / (values.std() + 1e-9))
is_anomaly = (values < lower_fence) | (values > upper_fence) | (z_scores > 2.5)
```

### 5. Add ETS model (Holt-Winters)
```python
if body.method == 'ets':
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    s = body.seasonal_period
    use_seasonal = len(values) >= 2 * s
    model = ExponentialSmoothing(
        train,
        trend='add',
        seasonal='add' if use_seasonal else None,
        seasonal_periods=s if use_seasonal else None,
    ).fit(optimized=True, disp=False)
    fcast_vals = model.forecast(body.periods)
    resid_std = float(np.std(model.resid))
    # ... build forecast list + return aic, alpha, beta, gamma
```

### 6. New endpoint: `POST /ml/forecast/compare`
```python
class ForecastCompareIn(BaseModel):
    file_id: str
    date_col: str
    value_col: str
    periods: int = 7
    seasonal_period: int = 12
    methods: list[str]  # ["linear", "moving_average", "ets", "sarimax", "supervised"]
```

Logic:
- Split data 80/20 (train/test)
- Fit each method on train, predict len(test) steps
- Compute MAPE = mean(|actual-pred|/|actual|) * 100
- Compute RMSE = sqrt(mean((actual-pred)^2))
- Return ranked list + best method (lowest MAPE)

Response:
```json
{
  "results": [
    {"method": "ets", "label": "ETS", "mape": 3.2, "rmse": 9876.5, "aic": -45.2, "status": "ok"},
    {"method": "linear", "label": "Linear Trend", "mape": 5.1, "rmse": 12345.6, "aic": null, "status": "ok"},
    {"method": "sarimax", "label": "SARIMAX", "mape": null, "rmse": null, "aic": null, "status": "error", "error": "..."}
  ],
  "best": "ets"
}
```

### 7. New endpoint: `POST /ml/forecast/interpret`
```python
class ForecastInterpretIn(BaseModel):
    method: str
    date_col: str
    value_col: str
    periods: int
    result: dict
    filename: str
```

Prompt to AI (Claude Haiku → Ollama fallback):
```
Bạn là Senior Data Analyst người Việt 10 năm kinh nghiệm.
Dataset: {filename}, Cột ngày: {date_col}, Cột giá trị: {value_col}
Method: {method}, Dự báo {periods} kỳ tới.
Kết quả: slope={slope}, {extra_metrics}
Forecast gần nhất: {last_3_values}

Phân tích theo JSON:
{"summary": "...", "trend": "...", "actions": "..."}
```

---

## Frontend Changes

### `frontend/src/types.ts`

```typescript
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
  history?: HistoryPoint[]     // NEW
  aic?: number
  r2?: number
  lags_used?: number
  trained_on?: number
  alpha?: number   // ETS params
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
```

### `frontend/src/api/ml.ts`

Add 2 functions:
```typescript
export async function compareForecast(
  file_id: string, date_col: string, value_col: string,
  periods: number, seasonal_period: number, methods: string[]
): Promise<ForecastCompareResult>

export async function interpretForecast(body: {
  method: string, date_col: string, value_col: string,
  periods: number, result: object, filename: string
}): Promise<{ summary: string; trend: string; actions: string }>
```

Update `runForecast` signature to include `method` and `seasonal_period` (already done in main dir).

### `frontend/src/components/ml/MlForecastView.tsx`

#### formatNum utility
```typescript
function formatNum(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 1e12) return (v / 1e12).toFixed(1) + 'T'
  if (abs >= 1e9)  return (v / 1e9).toFixed(1)  + 'B'
  if (abs >= 1e6)  return (v / 1e6).toFixed(1)  + 'M'
  if (abs >= 1e3)  return (v / 1e3).toFixed(1)  + 'K'
  return v.toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}
```

#### Add ETS to METHODS array
```typescript
{
  value: 'ets',
  label: 'ETS (Holt-Winters)',
  group: 'Statistical (Seasonal)',
  what: 'Exponential Smoothing — tự động học weight cho level, trend, seasonality.',
  when: 'Dữ liệu có trend + seasonality rõ. Nhanh hơn SARIMAX, ít tham số hơn.',
  requires: 'Tối thiểu 2× seasonal_period. statsmodels đã có sẵn.',
  output: 'AIC, alpha (level), beta (trend), gamma (seasonal).',
  needsSeasonal: true,
}
```

#### Combined chart (history + forecast)
```typescript
// Merge history + forecast into chartData
const histData = result.history?.map(h => ({
  date: h.date.slice(5),
  hist: h.value,
  isAnomaly: h.is_anomaly,
  zScore: h.z_score,
})) ?? []

const fcastData = result.forecast.map(f => ({
  date: f.date.slice(5),
  value: f.value,
  lower: f.lower,
  upper: f.upper,
  range: [f.lower, f.upper] as [number, number],
}))

const chartData = [...histData, ...fcastData] // merged with separator marker
```

Chart elements:
- `<Line dataKey="hist">` — solid, color #60a5fa
- `<Line dataKey="value">` — dashed (strokeDasharray="5 3"), same color
- `<Area dataKey="range">` — CI area, fillOpacity 0.12
- `<ReferenceLine x={lastHistDate}>` — vertical dashed separator
- Custom dot render for anomaly points (red dot, larger)

#### YAxis with formatNum
```tsx
<YAxis
  tick={{ fill: '#6b7280', fontSize: 10 }}
  tickFormatter={formatNum}
  width={65}  // wider for formatted labels
/>
```

#### Tooltip with formatNum
```tsx
<Tooltip
  formatter={(value) => formatNum(Number(value))}
  contentStyle={{ background: '#161b22', ... }}
/>
```

#### Model comparison panel
State: `comparing: boolean`, `compareResult: ForecastCompareResult | null`

UI: Button "So sánh Model" → loading → bảng:
```
| Model          | MAPE   | RMSE    | AIC   | Status |
|----------------|--------|---------|-------|--------|
| ⭐ ETS         | 3.2%   | 9.8M   | -45.2 | ✓     |
| Linear Trend   | 5.1%   | 12.3M  | —    | ✓     |
| SARIMAX        | —      | —       | —    | ✗ err |
```
Best model highlighted với border analytics color.

#### AI explanation panel
State: `aiLoading: boolean`, `aiResult: {summary, trend, actions} | null`

Button "Giải thích AI" xuất hiện sau khi có forecast result.
Loading spinner → 3 sections:
- **Tóm tắt**: paragraph
- **Xu hướng**: paragraph  
- **Đề xuất hành động**: paragraph

#### Export CSV
```typescript
function downloadCsv(result: ForecastResult) {
  const rows = [
    ['date', 'value', 'lower_95', 'upper_95'],
    ...result.forecast.map(f => [f.date, f.value, f.lower, f.upper])
  ]
  const csv = rows.map(r => r.join(',')).join('\n')
  // download as forecast.csv
}
```

---

## File Change Summary

| File | Change |
|------|--------|
| `backend/routers/ml.py` | Fix date parsing, add ETS, add history+anomaly to response, 2 new endpoints |
| `frontend/src/types.ts` | Add `HistoryPoint`, update `ForecastResult`, add `ForecastCompareResult` |
| `frontend/src/api/ml.ts` | Add `compareForecast`, `interpretForecast` |
| `frontend/src/components/ml/MlForecastView.tsx` | formatNum, ETS method, combined chart, comparison, AI explain, CSV export |

No new npm packages needed. No new Python deps needed (statsmodels already in pyproject.toml).

---

## Non-goals

- Prophet (separate task, needs new dep)
- LSTM/Deep Learning
- Ensemble model
- Excel export (CSV đủ)
- Real-time data refresh
