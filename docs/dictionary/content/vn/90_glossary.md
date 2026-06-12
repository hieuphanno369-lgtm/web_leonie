# 📚 Glossary — Thuật ngữ hay gặp

> Giải thích ngắn gọn, không dài dòng. Nếu thấy thuật ngữ lạ trong ML Studio → tìm ở đây.

## Chỉ số đánh giá model

| Thuật ngữ              | Nghĩa đơn giản                                                                 | Tốt khi nào          |
|------------------------|--------------------------------------------------------------------------------|----------------------|
| **MAPE**               | Dự đoán sai bao nhiêu % so với thực tế (Mean Absolute Percentage Error)       | Càng thấp càng tốt   |
| **RMSE**               | Sai số trung bình tính bằng đơn vị gốc (Root Mean Squared Error)              | Càng thấp càng tốt   |
| **R²**                 | Model giải thích được bao nhiêu % sự biến động của data (0→1)                 | Càng gần 1 càng tốt  |
| **Accuracy**           | Tỉ lệ dự đoán đúng trên tổng số dự đoán (cho bài toán phân loại)             | Càng cao càng tốt    |
| **F1 Score**           | Cân bằng giữa Precision và Recall — dùng khi data imbalanced                  | Càng gần 1 càng tốt  |
| **Silhouette Score**   | Các cụm KMeans có tách biệt rõ không? (-1→1)                                  | Càng gần 1 càng tốt  |
| **AIC / BIC**          | Điểm đánh giá SARIMAX — model nào fit tốt hơn với ít tham số hơn             | Càng thấp càng tốt   |

## Khái niệm ML

| Thuật ngữ              | Nghĩa đơn giản                                                                  |
|------------------------|---------------------------------------------------------------------------------|
| **Overfitting**        | Model học thuộc data cũ nhưng đoán sai data mới — như học vẹt                  |
| **Feature Importance** | Cột nào ảnh hưởng nhiều nhất đến kết quả dự đoán                               |
| **Confidence Interval**| Vùng dự báo — thực tế sẽ rơi vào đây với xác suất ~95%                        |
| **Seasonality**        | Chu kỳ lặp lại theo mùa/tháng/tuần — VD: tháng 12 luôn cao hơn               |
| **Exogenous variable** | Biến ngoài đưa vào để giúp dự báo tốt hơn — VD: ngày khuyến mãi              |
| **Imputation**         | Tự động điền giá trị cho ô null thay vì xóa cả hàng                           |
| **Cross-validation**   | Kiểm tra model bằng cách chia data ra nhiều phần, test từng phần               |

## Định dạng dữ liệu

| Thuật ngữ    | Nghĩa                                                              |
|--------------|--------------------------------------------------------------------|
| **CSV**      | File text, các giá trị cách nhau bằng dấu phẩy                    |
| **Parquet**  | File nhị phân nén — load nhanh hơn CSV nhiều khi data lớn         |
| **Long format** | Mỗi hàng là 1 observation (ngày × sản phẩm) — ML Studio cần vậy |
| **Wide format** | Mỗi sản phẩm là 1 cột — cần pivot trước khi dùng               |
