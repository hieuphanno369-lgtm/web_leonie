# ML Studio — Analyst Upgrade · Thiết kế (Design)

**Ngày:** 2026-06-07
**Phạm vi:** 7 tính năng + tư vấn UX cho ML Studio (frontend React + backend FastAPI).
Không thêm dependency mới (PNG export dùng canvas thuần của trình duyệt).

## Mục tiêu (Goal)

Nâng ML Studio thành công cụ phân tích "từ tổng quan → chi tiết" cho Data Analyst:
khoan sâu theo thời gian, gợi ý biểu đồ đa góc nhìn, đọc tương quan dương/âm nhanh,
gom nhiều measure cạnh nhau, và bớt ma sát thao tác (Show Code, export, insight tự
động). Mọi thay đổi giao vào **main working tree** (app đang chạy tự nhận), **không push**.

## Người dùng chọn (đã chốt qua brainstorming)

| # | Tính năng | Phương án đã chốt |
|---|-----------|-------------------|
| 1 | Dataset Overview | Thêm Median + Range + **Show Code** — ngay tại rail Overview |
| 2 | Gợi ý biểu đồ ⟳ | **Xoay vòng template** (pool công thức, bấm n lần) |
| 3 | Xem thời gian | **Khoan sâu + breadcrumb** Năm→Tháng→Ngày |
| 4 | Bug Run | Fix nhảy trang panel "Chuỗi thời gian" |
| 5 | Tương quan | **Xếp hạng cặp +/−** (giữ heatmap) |
| 6 | Chart mới | **Clustered Columns** (nhiều measure) |
| 7 | Sidebar | Automation lên dưới ML Studio |
| 8 | Tư vấn | Làm hết — đóng gói theo phase |

---

## Quyết định kiến trúc

### QĐ-1 · Tái dùng `backend/analytics/codegen.py`
Code "Show Code" của #1 (describe) và #3 (drilldown) sinh ở **backend** qua helper thuần
`codegen.py` (đã có sẵn, dễ unit-test), trả trong response field `code: str`. Frontend chỉ
render bằng `CodePanel`. Đồng nhất với pattern đã có (timeseries/correlation/stats).

### QĐ-2 · Tách logic nặng ra component/helper riêng — không phình `MlChartView`
`MlChartView.tsx` đã ~830 dòng. Mọi phần mới sẽ là **file riêng**, MlChartView chỉ render:
- `MlDrilldownView.tsx` (mới) — panel khoan sâu thời gian (#3).
- `CorrelationRanked.tsx` (mới) — bảng xếp hạng cặp +/− (#5), tính client-side từ ma trận.
- `chartRecipes.ts` (mới, pure) — sinh pool gợi ý biểu đồ (#2), unit-test được.
- `insights.ts` (mới, pure) — sinh câu insight tiếng Việt (#8c), unit-test được.
- `chartExport.ts` (mới) — `copyRowsAsCsv` + `downloadSvgAsPng` (#8b), canvas thuần.

### QĐ-3 · Phân phase (vì #8 có 2 ý lớn)
- **Phase 1 (build ngay):** #1–#7 + #8b (export) + #8c (auto-insight). *(#8a Ctrl+Enter đã có
  sẵn trong `SqlEditor` → không làm.)*
- **Phase 2 (plan riêng kế tiếp):** Power BI value-format picker (currency/number/percent +
  tooltip). Lớn, đáng có spec riêng — đã treo trong memory.
- **Phase 3 (plan riêng kế tiếp):** Pin-to-dashboard (lưu cấu hình chart → trang dashboard cá
  nhân). Cần store bền + surface mới → spec riêng.

---

## Đặc tả từng mục (Phase 1)

### #1 · Dataset Overview: +Median +Range +Show Code
**Hiện trạng:** [`describe_dataset`](backend/routers/ml.py:495) trả mảng `[{col,dtype,nulls,min,max,mean,std}]`.
Rail [`MlDescribePanel`](frontend/src/components/ml/MlDescribePanel.tsx) hiện 6 cột (Column/Type/Nulls%/Min/Mean/Max), 280px — chật.

**Backend:**
- Thêm `median = arr.median()`, `range = max − min` cho mỗi cột số.
- Đổi response: `{ "rows": [...], "code": "<python>" }` (thêm `code` qua `codegen.describe_code(...)`).
- `code` = snippet polars sạch: `import polars as pl` → đọc file → `select([min,max,mean,median,std])` →
  thêm `range` → bảng, kèm comment "logic, không phản ánh cache hạ tầng".

**Frontend:**
- `DescribeRow` (+`median?`, `range?`) và `fetchDescribe` trả `{rows, code}` (api/ml.ts).
- Rail: bảng hiện đủ **Min · Max · Mean · Median · Range · Std** trong vùng `overflow-x-auto` sẵn có
  (cuộn ngang — đúng "chỗ đó luôn"). Nút **"⌗ Show Code"** ở chân panel bung `CodePanel` inline.
- **Không** thêm bản full-width ở Stats (tab Stats đã có test `Describe` per-column + code → tránh trùng).

**Acceptance:** rail hiện 6 chỉ số; Show Code mở ra code chạy được; `pytest` describe trả `rows`+`code`.

### #2 · Gợi ý biểu đồ ⟳ (xoay vòng template)
**Hiện trạng:** [`recipes`](frontend/src/components/ml/MlChartView.tsx:284) sinh ~4 gợi ý cố định, hiện hết một lượt.

**Thiết kế:**
- `chartRecipes.ts`: hàm thuần `buildRecipePool(profile, resultColumns)` → mảng recipe lớn (mỗi
  date×metric, dim×metric, **flag×metric** vd `has_campaign`, multi-measure clustered, tỉ trọng pie,
  scatter metric×metric, tương quan…). Mỗi recipe: `{title, Icon, kind, apply-params}`.
- MlChartView giữ `poolOffset` (useState). Hiện **một cửa sổ 4 recipe**; nút **"⟳ Góc nhìn khác"**
  tăng offset (xoay vòng `% pool.length`), nhãn *"bộ k/N"*. `apply()` map sang hành vi sẵn có
  (set X/Y/type, mở panel ts/corr/drilldown).

**Acceptance:** bấm ⟳ đổi sang bộ gợi ý khác; quay vòng khi hết; mỗi gợi ý apply đúng.

### #3 · Khoan sâu thời gian — Năm→Tháng→Ngày (breadcrumb)
**Backend — endpoint mới** `GET /api/ml/{file_id}/drilldown`:
- Params: `date_col`, `value_col`, `agg` (sum|mean|count|min|max|n_unique), `grain` (year|month|day),
  `year?` (int), `month?` (int).
- Logic (polars, dùng `_try_parse_dates` sẵn có): parse ngày → lọc theo `year`/`month` nếu có →
  group theo `grain` → trả `{ grain, labels[], values[], value_col, agg, code }`.
  - `grain=year` → nhãn `["2024","2025","2026"]`.
  - `grain=month, year=2024` → nhãn `["2024-01"…"2024-12"]`.
  - `grain=day, year=2024, month=7` → nhãn `["2024-07-01"…]`.
- `code` qua `codegen.drilldown_code(...)`.

**Frontend — `MlDrilldownView.tsx`** (panel trong tab Charts, đồng bộ Cohort/Correlation):
- Controls: Date field · Value · Agg. State: `level` (year/month/day), `year`, `month`.
- Biểu đồ **cột**; **click 1 cột** → khoan xuống cấp con (year→month→day) + nạp lại.
- **Breadcrumb** `Tất cả › 2024 › Th07`: click nấc để quay lên; mỗi nấc là **dropdown** đổi ngang
  (vd 2024→2025 cùng cấp) → "linh hoạt chọn timeframe".
- Reuse `fmtY`/`numFormat` + tooltip style. Có nút Show Code (`result.code`).

**Acceptance:** từ Năm click xuống Tháng rồi Ngày; breadcrumb quay lên & đổi ngang chạy đúng; endpoint có test.

### #4 · Fix nhảy trang khi Run "Chuỗi thời gian"
**Nguyên nhân:** panel ở cuối vùng `overflow-auto`; `setTsResult(null)` (MlChartView:263) làm khối cao
co lại → browser kẹp `scrollTop` về trên.
**Fix:**
1. Lúc loading giữ **skeleton đúng chiều cao** (không unmount khối cao → không co layout).
2. `ref` vào panel + `scrollIntoView({block:'nearest'})` sau khi có `tsResult`.
3. Áp cùng pattern cho panel Cohort/Correlation (cùng kiểu set-null → refetch) cho nhất quán.

**Acceptance:** bấm Run, vùng nhìn **không nhảy lên**; kết quả hiện tại chỗ.

### #5 · Tương quan: xếp hạng cặp +/−
**Frontend-only** (không đổi backend — tính từ `corrData.matrix`+`columns`):
- `CorrelationRanked.tsx`: lấy cặp tam giác trên (i<j, bỏ self & null), tách **DƯƠNG** (r>0, giảm dần)
  và **ÂM** (r<0, âm nhất trước). Mỗi cặp một hàng: `colA × colB …… r=+0.87` + thanh độ mạnh
  (`|r|`), màu xanh (+) / đỏ (−) theo `corrToColor` để đồng bộ heatmap. Hiện top ~8 mỗi phía.
- Render **dưới** heatmap trong panel Correlation sẵn có (MlChartView), heatmap **giữ nguyên**.

**Acceptance:** danh sách đúng dấu, đúng thứ tự độ mạnh; rỗng thì báo "không có cặp tương quan".

### #6 · Clustered Columns (nhiều measure)
**Frontend-only** trong MlChartView:
- Thêm chart type `clustered` vào `CHART_TYPES` (nhãn "Cột nhóm").
- Khi chọn: X = 1 cột; thay select Y đơn bằng **multi-select chip** các cột số trong `result.columns`
  (mặc định 2–3 cột số đầu). Render nhiều `<Bar>` chung XAxis (recharts tự nhóm cạnh nhau),
  `Legend` + màu `PIE_COLORS`, dùng lại `fmtY`/`yScale`. Cảnh báo nhẹ nếu chọn >6 series.

**Acceptance:** chọn 2–4 cột số → các cột vẽ cạnh nhau theo từng nhóm X, legend đúng tên cột.

### #7 · Chuyển Automation lên dưới ML Studio
**Frontend-only** [`Sidebar.tsx`](frontend/src/components/layout/Sidebar.tsx):
- Bỏ item `/data/automation` khỏi nhóm `data` (SQL SANDBOX).
- Thêm vào nhóm `analytics` (ANALYTICS) **ngay sau ML Studio**, đổi `color` amber `#fbbf24` cho đồng bộ.
- **Route giữ nguyên** `/data/automation` → không đụng `App.tsx`.

**Acceptance:** Automation hiện dưới ML Studio (mục ANALYTICS), điều hướng vẫn vào đúng trang.

### #8b · Export (Copy CSV / Download PNG)
- `chartExport.ts`: `copyRowsAsCsv(columns, rows)` (clipboard) + `downloadCsv(...)`; `downloadSvgAsPng(svgEl, filename)`
  (serialize SVG → `<canvas>` → `toDataURL('image/png')`, canvas thuần, **không thêm lib**).
- Gắn nút nhỏ "⧉ CSV" / "⬇ PNG" ở: bảng (`MlTableView`), biểu đồ chính (MlChartView), drilldown.
- PNG là **best-effort** (SVG inline, font hệ thống) — nếu lỗi thì hiện toast nhẹ, không vỡ app.

**Acceptance:** Copy CSV ra đúng cột/hàng; PNG tải về xem được.

### #8c · Insight tự động dưới chart
- `insights.ts`: hàm thuần `describeSeries(labels, values)` → 1–2 câu tiếng Việt: điểm cao/thấp nhất,
  xu hướng tổng (đầu↔cuối), số điểm bất thường (|z|>2). `formatTrend(...)`.
- Render dải insight mảnh dưới biểu đồ chính + chuỗi thời gian + drilldown.

**Acceptance:** câu insight khớp dữ liệu (đỉnh/đáy/xu hướng) cho ≥1 ví dụ test.

---

## Cấu trúc file

| File | New/Modify | Trách nhiệm |
|------|-----------|-------------|
| `backend/routers/ml.py` | Modify | describe +median/range/code; **endpoint `/drilldown`** |
| `backend/analytics/codegen.py` | Modify | `describe_code()`, `drilldown_code()` |
| `backend/tests/…` | Modify | test describe shape, drilldown grain |
| `frontend/src/api/ml.ts` | Modify | DescribeRow+2 field; `fetchDescribe`→{rows,code}; `fetchDrilldown` |
| `frontend/src/types.ts` | Modify | `DrilldownResult` |
| `frontend/src/components/ml/MlDescribePanel.tsx` | Modify | 6 chỉ số + Show Code (#1) |
| `frontend/src/components/ml/MlChartView.tsx` | Modify | ⟳ pool (#2), clustered (#6), render drilldown/ranked/export/insight |
| `frontend/src/components/ml/MlTableView.tsx` | Modify | nút Copy/Download CSV (#8b) |
| `frontend/src/components/layout/Sidebar.tsx` | Modify | dời Automation (#7) |
| `frontend/src/components/ml/MlDrilldownView.tsx` | **New** | khoan sâu thời gian (#3) |
| `frontend/src/components/ml/CorrelationRanked.tsx` | **New** | xếp hạng cặp +/− (#5) |
| `frontend/src/components/ml/chartRecipes.ts` | **New** | pool gợi ý (#2, pure) |
| `frontend/src/components/ml/insights.ts` | **New** | insight tự động (#8c, pure) |
| `frontend/src/components/ml/chartExport.ts` | **New** | CSV/PNG export (#8b) |

## Kiểm thử (Testing)
- **Backend:** `cd backend ; uv run pytest -q` — describe trả `{rows, code}` + có `median`/`range`;
  drilldown đúng nhãn theo grain (year/month/day) + filter year/month; pure helpers `chartRecipes`,
  `insights` test ở FE (vitest nếu có; nếu không, test logic qua hàm thuần).
- **Frontend:** `cd frontend ; npm run build` (tsc + vite) phải xanh.
- **Thủ công:** mở ML Studio với `Revenue_2024_to_Current.xlsx` → kiểm #1–#6; Sidebar #7.

## Ngoài phạm vi Phase 1 (sẽ có spec riêng)
- **Phase 2:** Power BI value-format picker (currency/number/percent/custom + format tooltip).
- **Phase 3:** Pin-to-dashboard (store bền + trang dashboard cá nhân).
- Không đụng `_legacy/`; không push; không xoay key (việc riêng).

## Rủi ro & giảm thiểu
- *MlChartView phình thêm:* giảm bằng QĐ-2 (tách 5 file mới, MlChartView chỉ orchestrate).
- *PNG export tainted/font:* để best-effort + fallback toast; CSV là đường chắc chắn.
- *Drilldown nhiều dạng ngày:* tái dùng `_try_parse_dates` đã chịu nhiều định dạng trong app.
- *Giao nhầm vào worktree:* nhớ deliver vào **main working tree** `D:\…\leonie` (app chạy ở đó).
