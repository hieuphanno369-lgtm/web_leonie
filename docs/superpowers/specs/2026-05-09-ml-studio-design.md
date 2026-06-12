# ML STUDIO — Design Spec
**Date:** 2026-05-09  
**Feature:** Data Scientist role trong Data Studio  
**Approach:** Hybrid (Streamlit control panel + Jupyter notebook)  
**Status:** Approved, pending implementation

---

## 1. Tổng quan

Thêm pill **"⚗ ML STUDIO"** vào Data Studio sub-nav (ngang hàng DATA EXPLORER, SQL→OBSIDIAN). User upload dataset CSV/Excel, pipeline tự chạy qua 6 bước có confirm gate, sinh Jupyter notebook micro-cell dùng Polars, hiển thị kết quả Plotly ngay trong Streamlit.

**Không dùng pandas ở bất kỳ đâu.** Toàn bộ xử lý dữ liệu dùng Polars. Sklearn/XGBoost chỉ nhận numpy tại điểm train duy nhất (`df.to_numpy()`).

---

## 2. Kiến trúc & File Structure

### Vị trí UI
```
◈ DATA STUDIO
  pills: [ DATA EXPLORER ] [ SQL → OBSIDIAN ] [ ⚗ ML STUDIO ]
```

### Files mới
```
modules/
  ml_studio.py              ← render_ml_studio() + session history UI
  ml_pipeline/
    __init__.py
    header_detector.py      ← phát hiện merged rows, tìm header thật (~80 lines)
    eda.py                  ← EDA với Polars: schema, null, dupe, outlier (~120 lines)
    cleaner.py              ← dedupe, fill null, encode, outlier Polars (~100 lines)
    feature_selector.py     ← tính importance, trả về ranked list (~80 lines)
    trainer.py              ← train 4 loại model (~150 lines)
    notebook_gen.py         ← sinh .ipynb qua Jinja2 (~100 lines)
    result_plotter.py       ← Plotly charts cho Streamlit (~120 lines)
templates/
  ml_notebooks/
    regression.ipynb.j2
    classification.ipynb.j2
    clustering.ipynb.j2
    timeseries.ipynb.j2
data/
  ml_sessions/              ← tạo tự động khi user bấm Save
```

### Session state
```python
st.session_state["ml_pipeline"] = {
    "step":          3,           # bước hiện tại (0-7)
    "df_raw":        ...,         # Polars LazyFrame gốc
    "df_clean":      ...,         # sau clean
    "header_row":    2,           # header thật ở row nào
    "problem_type":  "regression",
    "features":      [...],
    "target":        "revenue",
    "model_results": {...},
    "notebook_path": "...",
}
```

### Tích hợp vào Data Studio
```python
ds_view = st.radio("", [
    "◈ DATA EXPLORER",
    "⬡ SQL → OBSIDIAN",
    "⚗ ML STUDIO",
], horizontal=True, key="ds_view", label_visibility="collapsed")

if ds_view == "⚗ ML STUDIO":
    from modules.ml_studio import render_ml_studio
    render_ml_studio()
```

---

## 3. Pipeline Flow

```
[Upload CSV/Excel]
      ↓
[Step 1: Header Detection]     → confirm gate ①
      ↓
[Step 2: EDA + Duplicate]      → confirm gate ②
      ↓
[Step 3: Clean & Transform]    → confirm gate ③
      ↓
[Step 4: Problem type + Feature selection] → confirm gate ④
      ↓
[Step 5: Train model]   (song song: sinh notebook .ipynb)
      ↓
[Step 6: Results: Plotly dashboard + download + mở JupyterLab]
      ↓
[💾 SAVE SESSION]  ← chỉ lưu khi user bấm
```

Mỗi confirm gate: hiển thị kết quả bước trước → user bấm **"▶ Tiếp tục"** mới chạy tiếp. Không bước nào tự chạy ngầm.

---

## 4. UI Flow Chi Tiết

### Step 0 — Upload
- `st.file_uploader` nhận CSV / Excel (.xlsx)
- Preview 5 rows đầu (raw, chưa xử lý)
- Tự động trigger Header Detector

### Step 1 — Header Detection (confirm gate ①)
Detect các trường hợp:
- 1-3 rows đầu là metadata/title bị merge → bỏ qua
- Header thật nằm ở row N
- Tên cột trùng hoặc rỗng → đặt tên `col_1`, `col_2`…

Hiển thị: raw rows → header đề xuất → preview sau fix → nút chỉnh tay nếu cần.

### Step 2 — EDA (confirm gate ②)
**Block A — Schema & Chất lượng:** dtype, null%, unique count  
**Block A.2 — Descriptive Statistics:**

| Chỉ số | Hiển thị |
|--------|----------|
| count | Số rows không null |
| null_count | Số giá trị thiếu |
| mean | Trung bình |
| median | Trung vị |
| std | Độ lệch chuẩn |
| min / max | Giá trị nhỏ nhất / lớn nhất |
| 25% (Q1) / 75% (Q3) | Tứ phân vị |
| skewness | Độ lệch phân phối |
| kurtosis | Độ nhọn phân phối |

Ghi chú tự động: cảnh báo nếu skew > 2, null > 5%, outlier cực đoan.

**Block B — Phân phối:** Plotly histogram (numeric), bar chart (categorical)  
**Block C — Duplicate:** đếm rows trùng  
**Block D — Outlier summary:** IQR method

Polars code:
```python
df.select(cs.numeric()).describe()
df.is_duplicated().sum()
df[col].skew(), df[col].kurtosis()
```

### Step 3 — Clean & Transform (confirm gate ③)
Hiển thị **kế hoạch** trước, user confirm mới chạy:
- Xóa duplicate rows
- Điền null: median theo nhóm (numeric), mode (categorical)
- Flag outlier (IQR × 3) thành cột `{col}_is_outlier`
- Encode categorical: ordinal nếu có thứ tự, label encode còn lại
- Tách date column → year, month, day_of_week, quarter

Sau chạy: hiển thị before/after stats tóm tắt.

### Step 4 — Problem Type + Feature Selection (confirm gate ④)
- Chọn bài toán: Regression / Classification / Clustering / Time Series
- Chọn target column (dropdown từ cột có sẵn)
- Nếu Time Series: chọn date column + forecast horizon (ngày)
- AI tính feature importance → hiển thị ranked list với score
- User tick/bỏ tick từng feature trước khi train

### Step 5 — Train
- Chạy model primary + baseline song song
- Sinh notebook `.ipynb` từ Jinja2 template
- Progress spinner trong Streamlit

### Step 6 — Results
- Metrics so sánh primary vs baseline
- Plotly charts (xem chi tiết Section 5)
- Top N recommendations (khách hàng, segment…)
- Nút: download CSV, mở JupyterLab, Save session

---

## 5. ML Models

| Problem | Primary | Baseline | Metrics |
|---------|---------|---------|---------|
| Regression | XGBoost Regressor | Linear Regression | RMSE, MAE, R² |
| Classification | XGBoost Classifier | Logistic Regression | Accuracy, F1, AUC-ROC |
| Clustering | K-Means (auto K) | DBSCAN optional | Silhouette, Inertia |
| Time Series | SARIMAX | Moving Average | RMSE, MAPE, AIC |

### Chi tiết theo bài toán

**Regression:** Train/test split 80/20 stratified theo thời gian nếu có date. Charts: actual vs predicted scatter, feature importance bar, residual histogram.

**Classification:** Detect class imbalance (ratio > 1:5) → áp dụng `scale_pos_weight`. Charts: confusion matrix heatmap, ROC curve, feature importance. Output: top N khách hàng nguy cơ cao kèm probability.

**Clustering:** Auto-select K=2..10 dùng KneeLocator (elbow curve). Charts: elbow curve, PCA 2D scatter, radar chart profile từng cluster. AI tự đặt tên cluster dựa trên đặc trưng nổi bật. Output: gợi ý hành động kinh doanh cho từng cluster.

**Time Series:** `pmdarima.auto_arima` tìm order (p,d,q)(P,D,Q,s). Auto-detect frequency (daily/weekly/monthly). Charts: historical + forecast line, confidence interval 95%, seasonal decomposition.

---

## 6. Notebook Micro-Cell Format

### Quy tắc
- Mỗi Markdown cell = tiêu đề section + 1-2 dòng giải thích ngắn
- Mỗi code cell = tối đa 15-20 dòng, chỉ làm **một việc**
- Toàn bộ code dùng Polars; `to_numpy()` chỉ tại điểm train
- Plotly `template="plotly_dark"` xuyên suốt (khớp theme CHOOPER)
- Cell cuối luôn export CSV + print đường dẫn

### Cấu trúc cells (ví dụ Regression)
```
Cell 01 [MD]   # Header: tên notebook, dataset, target, timestamp
Cell 02 [MD]   ## 1. Import thư viện
Cell 03 [PY]   import polars, xgboost, sklearn, plotly...
Cell 04 [MD]   ## 2. Load dữ liệu thô — giải thích header row
Cell 05 [PY]   pl.read_csv(skip_rows=N)
Cell 06 [MD]   ## 3. EDA — Schema & chất lượng
Cell 07 [PY]   df.null_count()
Cell 08 [PY]   df.is_duplicated().sum()
Cell 09 [PY]   df.select(cs.numeric()).describe()
Cell 10 [PY]   skewness & kurtosis loop
Cell 11 [PY]   px.histogram(revenue)
Cell 12 [MD]   ## 4. Làm sạch — liệt kê các bước áp dụng
Cell 13 [PY]   xóa duplicate
Cell 14 [PY]   fill null + flag outlier
Cell 15 [PY]   tách date columns
Cell 16 [MD]   ## 5. Feature Selection
Cell 17 [PY]   tính correlation / importance
Cell 18 [MD]   ## 6. Huấn luyện mô hình
Cell 19 [PY]   train/test split + XGBoost fit
Cell 20 [PY]   eval_metrics() primary vs baseline
Cell 21 [MD]   ## 7. Kết quả & Business Insights
Cell 22 [PY]   actual vs predicted scatter
Cell 23 [PY]   feature importance bar chart
Cell 24 [PY]   top N predictions
Cell 25 [PY]   export predictions.csv
```

---

## 7. Save Session & Lịch sử

### Folder structure khi save
```
data/ml_sessions/{timestamp}_{dataset_name}/
  ├── raw.csv             ← file gốc
  ├── cleaned.parquet     ← Polars parquet (nhanh hơn CSV)
  ├── predictions.csv     ← output dự đoán
  ├── model.pkl           ← trained model
  ├── notebook.ipynb      ← notebook đã generate
  └── report.json         ← metadata: metrics, config, timestamp
```

### report.json schema
```json
{
  "session_id":  "20260509_1654_sales_q1_2025",
  "dataset":     "sales_q1_2025.csv",
  "rows":        511600,
  "cols":        16,
  "problem":     "regression",
  "target":      "revenue",
  "features":    ["month", "region", "tenure"],
  "model":       "XGBoostRegressor",
  "metrics":     { "rmse": 1203440, "r2": 0.847, "mae": 820100 },
  "created_at":  "2026-05-09T16:54:00"
}
```

### Mở lại session cũ
Click **Mở** trong danh sách → load `report.json` + `cleaned.parquet` → hiển thị kết quả cũ, không cần train lại.

### Mở notebook trong JupyterLab
Dùng lại `_launch_jupyter()` sẵn có, redirect URL trỏ thẳng vào file:
```python
nb_url = f"{jupyter_base_url}/lab/tree/{notebook_path}"
```

---

## 8. Dependencies mới (pyproject.toml)

```toml
"scikit-learn>=1.4.0",
"xgboost>=2.0.0",
"statsmodels>=0.14.0",
"pmdarima>=2.0.0",
"kneed>=0.8.0",
"nbformat>=5.9.0",
"nbconvert>=7.0.0",
"jinja2>=3.1.0",
```

Polars, Plotly đã có sẵn.

---

## 9. Constraints & Non-goals

**Constraints:**
- Không dùng pandas ở bất kỳ đâu ngoài điểm bắt buộc của thư viện ngoài
- Dataset lớn (500k+ rows): dùng Polars LazyFrame, tránh `.collect()` sớm
- Jupyter phải đang chạy để mở notebook (dùng lại flow sidebar)
- Không auto-tạo task trong TASKS tab

**Non-goals (không làm trong scope này):**
- Deep learning / neural networks
- Real-time streaming data
- Multi-file join tự động
- Auto-deploy model lên API
