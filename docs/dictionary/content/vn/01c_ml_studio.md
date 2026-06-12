# ⚗ ML Studio

> Cho app tự phân tích dữ liệu của bạn — không cần biết code, không cần biết ML.

---

## ML Studio là gì?

Tưởng tượng bạn có một đống số liệu bán hàng từ 2 năm qua.

**ML Studio giống như một người bạn thông minh** — bạn đưa file cho nó, nó tự hỏi *"Dữ liệu này muốn trả lời câu hỏi gì nhỉ?"*, rồi chọn cách phân tích phù hợp và giải thích kết quả bằng tiếng người bình thường.

Bạn không cần biết SARIMAX là gì. Bạn chỉ cần biết: *"Tôi muốn dự đoán doanh số tháng tới."*

---

## Pipeline 8 bước

```
[1] Upload  →  [2] Detect Header  →  [3] EDA  →  [4] Clean
     ↓
[5] Feature Select  →  [6] AI Recommend  →  [7] Train  →  [8] Result + Insight
```

| Bước | Tên               | Bạn làm gì                      | App làm gì                                         |
|------|-------------------|---------------------------------|----------------------------------------------------|
| 1    | Upload            | Kéo file CSV/Excel vào          | Đọc file, detect encoding, load vào bộ nhớ         |
| 2    | Detect Header     | Xác nhận tên cột                | Tự đoán header row, hỏi lại nếu file phức tạp     |
| 3    | EDA               | Xem tổng quan data              | Thống kê, % missing, correlation, phân phối        |
| 4    | Clean             | Chọn cách xử lý giá trị null    | Drop hàng/cột, fill mean/median, hoặc impute       |
| 5    | Feature Select    | Xem cột nào quan trọng nhất     | Tính feature importance, gợi ý bỏ cột thừa        |
| 6    | AI Recommend      | Xác nhận bài toán + thuật toán  | Claude AI đề xuất thuật toán phù hợp + lý do      |
| 7    | Train             | Nhấn Train                      | Chạy model, tính metrics, lưu kết quả             |
| 8    | Result + Insight  | Đọc kết quả                     | Vẽ chart + viết nhận xét bằng ngôn ngữ tự nhiên   |

**Lưu ý quan trọng:** Bạn có thể quay lại bất kỳ bước nào mà không cần upload lại file. Session được lưu tại `data/ml_sessions/`.

---

## Các thuật toán hiện có

### XGBoost — Phân loại & Hồi quy

> **Analogy:** Hỏi ý kiến 500 người bạn khác nhau. Mỗi người nhìn dữ liệu theo một góc độ riêng, rồi cả nhóm bỏ phiếu ra đáp án. Người nào hay sai thì lần sau ít được hỏi hơn — nhờ vậy nhóm ngày càng thông minh hơn.

| | |
|-|-|
| **Dùng khi** | Dự đoán con số (doanh thu, tỉ lệ chuyển đổi) hoặc phân loại (có/không, nhóm A/B/C) |
| **Input cần** | Bảng dữ liệu có **cột mục tiêu** rõ ràng (cột bạn muốn dự đoán) |
| **Output** | Giá trị dự đoán + biểu đồ Feature Importance (cột nào ảnh hưởng nhất) |
| **Điểm mạnh** | Chính xác cao, xử lý tốt missing values, nhanh |
| **Điểm yếu** | Khó giải thích "tại sao" cho từng dự đoán cụ thể |

---

### Random Forest — Phân loại & Hồi quy

> **Analogy:** Giống XGBoost nhưng 500 người bạn đó học **hoàn toàn độc lập** — không ai biết người kia đang học gì. Kết quả đa dạng hơn, ít bị "học vẹt" hơn.

| | |
|-|-|
| **Dùng khi** | Tương tự XGBoost; đặc biệt tốt khi data nhỏ hoặc có nhiều outlier |
| **Input cần** | Bảng dữ liệu có cột mục tiêu |
| **Output** | Giá trị dự đoán + Feature Importance |
| **Khác XGBoost** | Ổn định hơn, ít overfit hơn, nhưng chậm hơn một chút |

---

### SARIMAX — Dự báo chuỗi thời gian

> **Analogy:** Bạn có doanh số 24 tháng. SARIMAX nhìn vào và học 3 thứ: (1) xu hướng tăng/giảm dài hạn, (2) chu kỳ lặp lại theo mùa (tháng 12 luôn cao hơn), (3) yếu tố bên ngoài bạn cung cấp như khuyến mãi hay ngày lễ. Rồi nó nói: *"Tháng sau bạn bán được khoảng X, sai số ±Y"*.

| | |
|-|-|
| **Dùng khi** | Data là chuỗi theo ngày/tuần/tháng **và** có seasonality rõ ràng |
| **Cần tối thiểu** | 24 điểm dữ liệu (24 tháng, hoặc 24 tuần...) |
| **Input cần** | Cột ngày + cột giá trị; optionally: cột exogenous (biến ngoài) |
| **Output** | Đường dự báo (màu cam) + vùng confidence interval (màu mờ xung quanh) |
| **Điểm mạnh** | Xử lý seasonality tốt, có thể tích hợp biến ngoài |
| **Điểm yếu** | Cần ít nhất 24 điểm; data có khoảng trống thì khó |

**Đọc biểu đồ SARIMAX:**
- **Đường xanh** = data thực tế đã có
- **Đường cam** = dự báo
- **Vùng mờ** = confidence interval — thực tế sẽ rơi vào đây với xác suất ~95%

---

### Prophet — Dự báo chuỗi thời gian

> **Analogy:** Giống SARIMAX nhưng dễ tính hơn nhiều — tự xử lý ngày lễ, không cần bạn chỉnh tham số phức tạp. Phù hợp khi data có khoảng trống hoặc những ngày bất thường.

| | |
|-|-|
| **Dùng khi** | Time series có holiday effects, data không đều, hoặc bạn muốn setup nhanh |
| **Input cần** | Cột ngày (tên `ds`) + cột giá trị (tên `y`) |
| **Output** | Đường dự báo + vùng uncertainty + decomposition (trend, seasonality, holidays) |
| **Khác SARIMAX** | Dễ dùng hơn, ít kiểm soát hơn; tốt cho forecast ngắn-trung hạn |

---

### KMeans — Phân cụm (Clustering)

> **Analogy:** Bạn có 1000 khách hàng và không biết nên chia họ thành mấy nhóm. KMeans tự thử nhiều cách chia khác nhau, chấm điểm mỗi cách, rồi báo cho bạn cách nào tự nhiên nhất — không cần bạn nói trước có bao nhiêu nhóm.

| | |
|-|-|
| **Dùng khi** | Muốn segment khách hàng, SKU, vùng địa lý — không có nhãn sẵn |
| **Input cần** | Bảng dữ liệu **không có cột mục tiêu** (unsupervised) |
| **Output** | Biểu đồ scatter màu các cụm + bảng đặc trưng của từng cluster |
| **Điểm mạnh** | Không cần dữ liệu đã được gán nhãn |
| **Điểm yếu** | Kết quả phụ thuộc vào việc chọn số cụm K |

---

## Khi nào dùng thuật toán nào?

| Câu hỏi của bạn                              | Thuật toán gợi ý          |
|----------------------------------------------|---------------------------|
| Tháng tới tôi bán được bao nhiêu?            | SARIMAX hoặc Prophet      |
| Khách hàng này có mua lại không?             | XGBoost hoặc Random Forest|
| Yếu tố nào ảnh hưởng nhất đến doanh thu?    | XGBoost (Feature Importance)|
| Tôi nên chia khách hàng thành mấy nhóm?     | KMeans                    |
| Data có khoảng trống, ngày lễ phức tạp?      | Prophet                   |
| Data nhỏ (<500 dòng), có outlier?            | Random Forest             |

---

## Đọc kết quả — Các chỉ số đánh giá

Xem giải thích chi tiết tại: **📚 Glossary**

| Chỉ số           | Thuật toán dùng          | Nghĩa ngắn gọn                        |
|------------------|--------------------------|---------------------------------------|
| MAPE             | SARIMAX, Prophet         | Sai bao nhiêu % so với thực tế        |
| RMSE             | XGBoost, RF, SARIMAX     | Sai số trung bình (đơn vị gốc)        |
| Silhouette Score | KMeans                   | Các cụm có tách biệt tốt không?       |
| R²               | XGBoost, RF              | Model giải thích được bao % variance  |
| Accuracy / F1    | XGBoost, RF (classification) | Dự đoán đúng bao nhiêu %          |
