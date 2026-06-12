# ⬢ Data Explorer

> Upload file → app tự động phân tích và cho bạn thấy mọi thứ cần biết trước khi làm gì tiếp theo.

## Dùng để làm gì?

Khi bạn có một file dữ liệu mới và chưa biết nó có gì bên trong — Data Explorer là điểm đầu tiên nên ghé.

## Các file được hỗ trợ

| Format  | Extension        |
|---------|------------------|
| CSV     | `.csv`           |
| Excel   | `.xlsx`, `.xls`  |
| Parquet | `.parquet`       |

## 5 tab tự động sau khi upload

| Tab         | Hiển thị gì                                              |
|-------------|----------------------------------------------------------|
| HEAD        | 5 dòng đầu tiên của data                                 |
| DTYPES      | Kiểu dữ liệu từng cột (int, float, string, datetime...)  |
| MISSING     | % missing của từng cột, bar chart trực quan             |
| STATS       | Min, max, mean, median, std của các cột số              |
| CORRELATION | Heatmap tương quan giữa các cột số                      |

## Tips

- Xem **MISSING** trước: cột nào > 30% missing thường nên drop trước khi đưa vào ML
- **CORRELATION** > 0.9 giữa 2 cột → chỉ cần giữ 1 cột (multicollinearity)
- Sau khi hiểu data → chuyển sang **ML Studio** để phân tích sâu hơn
