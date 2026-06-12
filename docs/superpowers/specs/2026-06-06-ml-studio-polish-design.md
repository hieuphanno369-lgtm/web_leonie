# ML Studio Polish — Thiết kế (Design)

**Ngày:** 2026-06-06
**Phạm vi:** 4 cải tiến cho ML Studio (frontend React + backend FastAPI), không thêm dependency mới.

## Mục tiêu (Goal)

Làm ML Studio "đọc được số" và "đáng tin" hơn:

1. **Bộ chuyển đơn vị** (`auto/K/M/B/%`) cho biểu đồ **Chuỗi thời gian** và **Forecast** — số kiểu `230124589356` hiện không đọc nổi.
2. **Đồng bộ icon** — thay emoji (📈 🔗 📊 ⚬ ⭐ ⚠) bằng icon **lucide** dạng nét, khớp với tab/tiêu đề mục.
3. **Correlation Heatmap** đẹp & rõ hơn (màu, tương phản chữ, tận dụng không gian) + **Forecast** không còn báo "failed" đỏ gây hiểu nhầm thuật toán lỗi: khi dữ liệu không phù hợp thì cảnh báo thân thiện + gợi ý phương pháp chạy được.
4. **Show Code đầy đủ** — hiển thị toàn bộ pipeline từ lúc nạp dataset đến outcome (parse ngày → gộp grain/agg → xử lý null → model → output), trung thực với những gì backend thật sự chạy.

## Vấn đề hiện tại (đã xác minh trong code)

| # | Vị trí | Vấn đề |
|---|--------|--------|
| 1 | `MlChartView.tsx:803` | Panel "Chuỗi thời gian" dùng `<YAxis tick={axisStyle} />` trần — không formatter, không toggle. Toggle `auto/K/M/B/%` chỉ có ở biểu đồ chính (lines 410–417). |
| 2 | `MlChartView.tsx:305,312,318,325` · `MlForecastView.tsx:474` | Nút "Gợi ý biểu đồ" dùng emoji (📈🔗📊⚬); bảng so sánh model dùng ⭐; vài banner dùng ⚠. Trong khi tab/tiêu đề mục dùng lucide nét → lệch phong cách. |
| 3a | `CorrelationHeatmap.tsx` | Ô cố định 64px; thang `gray→blue/red` bị đục; `txtFill` = gray `#9ca3af` khi `|r|≤0.3` → số mờ trên nền xanh (0.23/0.05/0.11 gần như mất). Footprint nhỏ dù còn nhiều chiều ngang. |
| 3b | `ml.py:1606` · `MlForecastView.tsx:189` | `/forecast` đơn lẻ `raise HTTPException`/`SARIMAX failed to converge` khi không đủ điểm cho seasonal → frontend hiện chữ đỏ "Forecast failed". Trong khi `/forecast/compare` (`ml.py:896`) chạy trên grain mịn hơn nên SARIMAX **thành công** (⭐ 68.5%) → trông như thuật toán lúc được lúc lỗi. |
| 4 | `MlForecastView.tsx:107` · `MlStatsView.tsx:69` · `MlCohortView.tsx:10` | 3 generator code là **chuỗi hardcode ở frontend**, không phản ánh tiền xử lý thật (parse ngày đa định dạng, gộp grain/agg, xử lý null, anomaly). |

---

## Quyết định kiến trúc chính

### QĐ-1: Sinh code ở **backend**, trả về field `code` (cho Điểm 4)

Lý do frontend hiện không show được tiền xử lý: nó **không hề thấy** logic backend. Thay vì nhân bản pipeline ở frontend (sẽ lệch dần — đúng lỗi đang gặp), mỗi endpoint ML sẽ tự ghép một **script Python sạch, có chú thích, chạy được**, phản ánh đúng các bước **logic** nó chạy, và trả về trong response dưới field `code: str`. `CodePanel` ở frontend chỉ render nguyên văn.

- Script phản ánh **logic**, KHÔNG phản ánh hạ tầng (parquet cache, DB lookup) — sẽ có 1 comment nói rõ điều này để trung thực.
- Xóa 3 generator-chuỗi cũ ở frontend (`generateForecastCode`, `generateCode`, `generateCohortCode`).
- Code được build bằng một helper thuần Python mới `backend/analytics/codegen.py` (dễ unit-test, không phụ thuộc FastAPI).

### QĐ-2: Tách formatter số ra file dùng chung (cho Điểm 1)

`autoScale` / `fmtY` / `fmtFull` đang nằm cục bộ trong `MlChartView`. Tách ra `frontend/src/components/ml/numFormat.ts` để cả `MlChartView` (time-series) và `MlForecastView` (forecast) cùng dùng, đảm bảo cách format đồng nhất.

### QĐ-3: Suitability check cho forecast theo cơ chế giống cohort (cho Điểm 3b)

`/forecast` trả về **HTTP 200** với `{ suitable: false, reasons: [...], recommended_method }` khi phương pháp không chạy được trên dữ liệu — giống pattern `cohort` đang có (frontend đã quen kiểm tra `result.suitable === false`). Logic kiểm tra đặt trong helper thuần `backend/analytics/forecast_check.py` (unit-test riêng). Lỗi đỏ chỉ dành cho exception bất ngờ thật.

---

## Cấu trúc file

| File | New/Modify | Trách nhiệm |
|------|-----------|-------------|
| `backend/analytics/codegen.py` | Create | Hàm thuần build script Python cho từng phân tích: `forecast_code`, `timeseries_code`, `correlation_code`, `describe_code`, `cohort_code`. |
| `backend/analytics/forecast_check.py` | Create | `check_forecast_suitability(method, n, seasonal_period, ...) -> {suitable, reasons, recommended_method}`. |
| `backend/tests/test_codegen.py` | Create | Unit test: code sinh ra chứa đúng các bước (parse/aggregate/model) & là Python hợp lệ (`compile()`). |
| `backend/tests/test_forecast_check.py` | Create | Unit test rule suitability + recommended_method. |
| `backend/tests/test_ml.py` | Modify | Endpoint trả `code`; forecast trả `suitable:false` khi thiếu điểm (không 400). |
| `backend/routers/ml.py` | Modify | `/forecast`, `/forecast/compare`, `/timeseries`, `/correlation`, `/describe`, `/cohort`: gọi suitability + đính kèm `code`. |
| `frontend/src/components/ml/numFormat.ts` | Create | `YScale`, `autoScale`, `fmtY`, `fmtFull` dùng chung. |
| `frontend/src/components/ml/MlChartView.tsx` | Modify | Toggle đơn vị cho panel Chuỗi thời gian; emoji→lucide ở recipe & footer; import formatter chung; Show Code cho time-series. |
| `frontend/src/components/ml/MlForecastView.tsx` | Modify | Toggle đơn vị cho forecast chart; thẻ amber "chưa phù hợp" + nút recommend; bỏ `generateForecastCode`, render `result.code`; ⭐→`Star`. |
| `frontend/src/components/ml/CorrelationHeatmap.tsx` | Modify | Màu diverging mới, chữ theo luminance, ô co giãn, nhãn đầy đủ hơn, panel Show Code. |
| `frontend/src/components/ml/MlStatsView.tsx` | Modify | Bỏ `generateCode`, render `result.code`. |
| `frontend/src/components/ml/MlCohortView.tsx` | Modify | Bỏ `generateCohortCode`, render `result.code`. |
| `frontend/src/types.ts` | Modify | Thêm `code?: string` vào các result type; thêm `suitable/reasons/recommended_method` vào `ForecastResult`. |
| `frontend/src/api/ml.ts` | Modify | Truyền/đọc field mới (`code`, suitability). |

---

## Thiết kế chi tiết

### A — Bộ chuyển đơn vị (Điểm 1)

- `numFormat.ts` export: `type YScale = 'auto'|'K'|'M'|'B'|'%'`, `autoScale(maxAbs)`, `fmtY(v, scale, maxAbs)`, `fmtFull(v)` (chuyển nguyên từ `MlChartView`, giữ nguyên ngữ nghĩa — `%` chỉ hậu tố `.toFixed(1)%`, không tính lại).
- **Chuỗi thời gian** (`MlChartView`): thêm state `tsScale: YScale='auto'`, hàng nút `auto·K·M·B·%` (style giống main chart). `maxAbs` = max trị tuyệt đối trên **mọi** chuỗi đang vẽ (value + các comparison đang bật). Áp vào: `<YAxis tickFormatter>`, `<Tooltip formatter>`, nhãn các đường.
- **Forecast** (`MlForecastView`): thêm state `fcScale: YScale='auto'`, cùng hàng nút; thay `formatNum` ở `<YAxis>`/`<Tooltip>` bằng `fmtY(..., fcScale, maxAbs)` với `maxAbs` tính trên history+forecast+CI. Mặc định `auto` ⇒ hành vi cũ.

### B — Emoji → lucide (Điểm 2)

Icon lucide **đơn sắc** (không tô brand — theo lựa chọn của user):

| Hiện tại | Thay bằng |
|----------|-----------|
| 📈 (recipe time-series) | `TrendingUp` |
| 🔗 (recipe correlation) | `Link2` |
| 📊 (recipe bar) | `BarChart3` |
| ⚬ (recipe scatter) | `ScatterChart` |
| ⭐ (best model) | `Star` (accent `text-analytics`) |
| ▲ / ▼ (footer max/min) | `ArrowUp` / `ArrowDown` (giữ màu green/red) |
| ⚠ (banner cảnh báo) | `AlertTriangle` |

Recipe đổi từ `{ title: string }` sang `{ Icon: ElementType; title: string }`; nút render `<Icon size={11}/> {title}`.

### C — Correlation Heatmap (Điểm 3a)

- **Màu:** thang phân kỳ (diverging) `đỏ ↔ xám trung tính ↔ xanh`, bão hòa theo `|r|`. Thay `corrToColor` bằng nội suy 3 chốt có saturation thật để 0.05 vs 0.23 phân biệt rõ.
- **Tương phản chữ:** `textColor(bg)` tính luminance tương đối của màu ô → trả `#0b0f14` (nền sáng) hoặc `#ffffff` (nền tối). Bỏ ngưỡng cứng `|val|>0.3`.
- **Không gian:** `CELL` co giãn theo bề rộng container (đo bằng `ResizeObserver` hoặc `clientWidth` của wrapper), `min 56` – `max 96`px; tăng font số (11–13px theo cell); nhãn cột bớt cắt (tăng `trunc` max hoặc hiện đủ khi cell đủ rộng).
- Giữ SVG (chỉ restyle). Thêm panel **Show Code** (từ Điểm 4) dưới heatmap.

### D — Forecast suitability (Điểm 3b)

**Backend** `backend/analytics/forecast_check.py` — ngưỡng điểm tối thiểu (sau khi đã gộp theo grain):

| method | yêu cầu | ghi chú |
|--------|---------|---------|
| `linear` | `n ≥ 2` | hầu như luôn phù hợp |
| `moving_average` | `n ≥ 6` | |
| `ets` | `n ≥ 4` | chạy non-seasonal nếu `n < 2·s` (chỉ cảnh báo nhẹ, vẫn `suitable:true`) |
| `sarimax` | `n ≥ 2·s` | **case chính** gây fail |
| `supervised` | `n ≥ 20` | |

- Khi **không** đạt: trả `{ suitable: false, reasons: ["SARIMAX cần ≥ 2×seasonal = 24 điểm, hiện có 16 (grain=month)."], recommended_method }`.
- `recommended_method` = method ưu tiên cao nhất mà dữ liệu đáp ứng, theo thứ tự `ets → moving_average → linear` (bỏ qua điều kiện seasonal của ets). Đảm bảo recommend là method **chắc chắn chạy được**.
- `/forecast` gọi check **trước** khi fit; nếu `suitable:false` trả 200 ngay (kèm `code` mô tả pipeline tới bước check). Bọc `model.fit` trong try/except: lỗi thật → 400 với thông điệp rõ (vẫn là lỗi đỏ).

**Frontend** `MlForecastView`:
- Nếu `result.suitable === false`: render thẻ **amber** (mẫu giống cohort `MlChartView.tsx:599`): tiêu đề "Dữ liệu chưa phù hợp cho {method}", list `reasons`, và nút **"Dùng {recommended_method}"** → set method + tự Run lại.
- `error` đỏ chỉ giữ cho exception thật (`catch`).

### E — Show Code đầy đủ (Điểm 4) — cả 5 surface

`backend/analytics/codegen.py` build script cho từng loại; endpoint đính `code` vào response. Mỗi script gồm header comment + các bước đánh số. Ví dụ **forecast** (grain=month, agg=sum, sarimax):

```python
# Pipeline tái hiện đúng logic ML Studio đã chạy (bỏ qua lớp cache parquet).
import polars as pl
import numpy as np

# 1) Nạp dataset
df = pl.read_excel("Revenue_2024_to_Current.xlsx")   # hoặc pl.read_csv(...)

# 2) Parse cột ngày (thử nhiều định dạng: YYYY-MM-DD, YYYY-MM, MM-YYYY, DD-MM-YYYY)
df = df.with_columns(
    pl.col("day_month_year").str.to_date(strict=False).alias("_d")
).drop_nulls(subset=["_d"]).sort("_d")

# 3) Gộp theo grain=month, agg=sum
g = (df.group_by(pl.col("_d").dt.truncate("1mo").alias("period"))
        .agg(pl.col("total_amount_daily").sum().alias("value"))
        .sort("period"))
values = g["value"].to_numpy(); n = len(values)

# 4) SARIMAX (cần n >= 2*seasonal_period)
from statsmodels.tsa.statespace.sarimax import SARIMAX
fit = SARIMAX(values, order=(1,1,1), seasonal_order=(1,1,1,12),
              enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)

# 5) Dự báo 3 kỳ + 95% CI
fc = fit.get_forecast(steps=3)
print(fc.predicted_mean); print(fc.conf_int())
print("AIC:", fit.aic)
```

Các surface khác (timeseries / correlation / describe / cohort) theo cùng khuôn: load → parse/clean → phép tính lõi → output. Code phản ánh tham số **thật** của lần chạy (cột, grain, agg, method, seasonal).

---

## Kiểm thử (Testing)

- **Backend (`uv run pytest -q`):** `test_forecast_check.py` (rule + recommended), `test_codegen.py` (mỗi script `compile()` được + chứa keyword bước bắt buộc), cập nhật `test_ml.py` (forecast thiếu điểm → `suitable:false` chứ không 400; mọi endpoint có `code`).
- **Frontend (`npm run build` = `tsc -b && vite build`):** gate type-check/build + smoke tay (toggle đơn vị đổi trục; emoji biến mất; heatmap chữ rõ; SARIMAX thiếu điểm hiện thẻ amber + nút recommend; Show Code hiện pipeline đầy đủ).

## Ràng buộc giao hàng (Delivery)

- **Làm trong MAIN tree:** `D:\assitant_tools\tools_performance\08_Projects\leonie`, nhánh **master** — dev server (Vite :5177, uvicorn :8000) đọc file ở đó; sửa trong worktree không tới được app đang chạy.
- **Commit local vào master. KHÔNG `git push`** (history master chứa secret thật; chỉ orphan `backup-clean` mới được push — ngoài phạm vi).
- Mỗi commit kèm trailer co-author bắt buộc.

## Ngoài phạm vi (Out of scope)

- Không đổi thuật toán forecast (chỉ thêm lớp suitability + UX).
- Heatmap vẫn SVG (không chuyển canvas/thư viện).
- Thẻ suitability hiện **khi bấm Run** (không phải gate real-time trước Run).
- Không thêm dependency mới.
