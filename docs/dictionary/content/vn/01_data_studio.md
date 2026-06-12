# ◈ Data Studio

> Phòng phân tích dữ liệu của bạn. 4 công cụ trong 1 chỗ — từ khám phá đến dự đoán.

## 4 Sub-view

| Sub-view        | Dùng khi nào                                     | Output                          |
|-----------------|--------------------------------------------------|---------------------------------|
| Data Explorer   | Upload file → cần hiểu ngay cấu trúc dữ liệu    | Stats, missing%, correlation    |
| SQL → Obsidian  | Có câu SQL → muốn phân tích + lưu thành note    | File .md trong Obsidian vault   |
| ⚗ ML Studio    | Có data → muốn dự đoán hoặc phân nhóm            | Model + chart + AI insight      |
| Snippets        | Có câu SQL hay dùng lại → muốn lưu trữ          | Thư viện SQL cá nhân            |

## Flow điển hình

```
1. Upload CSV/Excel/Parquet vào Data Explorer
   → Kiểm tra cột, missing values, phân phối

2. Nếu cần viết SQL để lọc/aggregate:
   → Sang SQL → Obsidian → paste SQL → analyze → lưu note

3. Khi đã hiểu data:
   → Sang ML Studio → upload file đã clean → chạy pipeline 8 bước

4. Lưu câu SQL hay dùng:
   → Sang Snippets → thêm snippet → gán tag
```

## Lưu ý

- Data Explorer và ML Studio **không kết nối trực tiếp** — bạn cần export/save file rồi upload lại
- SQL → Obsidian ghi file `.md` vào `D:\ai_brain\SQL Queries\` — cần Obsidian vault được mount
- ML Studio lưu session tại `data/ml_sessions/` — có thể tiếp tục từ bước bất kỳ
