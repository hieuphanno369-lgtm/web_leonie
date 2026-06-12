# ⌨ Shortcuts & Tips

> Các mẹo hay dùng để làm việc nhanh hơn trong Leonie.

## Tips theo tab

### ◈ ML Studio
- Có thể **quay lại bước bất kỳ** mà không cần upload lại — bấm nút bước ở progress bar
- Session được **lưu tự động** — tắt app đi rồi mở lại vẫn còn
- Nếu model chạy sai → thử step 4 (Clean) lại — data chất lượng > thuật toán xịn

### ⬡ Tasks
- Search bar hỗ trợ **filter theo tag**: gõ `#sf` để chỉ xem task Salesforce
- **Click trực tiếp** vào tên task để edit — không cần mở form riêng
- Task recurring: sau khi done → tự tạo task mới cho kỳ tiếp theo

### ⬡ SQL → Obsidian
- **Ctrl+Enter** trong text box SQL để trigger analyze nhanh
- Sau khi analyze, **title và tags** có thể sửa trước khi save
- File lưu vào `D:\ai_brain\SQL Queries\` → tự động index bởi Obsidian

### ⬢ Data Explorer
- **Kéo nhiều file** cùng lúc để so sánh cấu trúc
- Tab **CORRELATION** → giá trị > 0.9 giữa 2 cột = cân nhắc bỏ 1 cột trước khi ML
- Tab **MISSING** → cột > 30% null thường nên drop thay vì impute

### ◉ Email
- Email digest gửi Discord **ngay lập tức** nếu bấm Manual trigger trong Pipeline tab
- Nếu muốn **skip email** mà không gửi → nhấn Skip (lưu vào history, không nhắc lại)

## Phím tắt Streamlit (khi app đang mở)

| Phím          | Tác dụng                                       |
|---------------|------------------------------------------------|
| `R`           | Reload lại app (hard refresh)                  |
| `Ctrl + Enter`| Chạy lại widget hiện tại (text area, code box) |
| `Esc`         | Đóng dropdown / dialog đang mở                 |

## Khi app bị lỗi

```
1. Thử Ctrl+C → streamlit run app.py  (restart app)
2. Nếu lỗi import → .venv\Scripts\python.exe -m pip install -r requirements.txt
3. Nếu AI không respond → kiểm tra ANTHROPIC_API_KEY trong .env
4. Nếu Discord không gửi → kiểm tra DISCORD_WEBHOOK_URL trong .env
```
