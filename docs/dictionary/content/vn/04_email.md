# ◉ Email

> Đọc email Outlook, AI phân loại theo priority, tóm tắt, gợi ý reply.

## Pipeline Email

```
Outlook → Đọc email → Phân loại priority → Tóm tắt → Gợi ý reply → Gửi digest Discord
```

## Các bước

| Bước            | App làm gì                                               |
|-----------------|----------------------------------------------------------|
| Đọc Outlook     | Dùng win32com để đọc inbox (cần Outlook desktop)        |
| Phân loại       | Rule-based + AI → gán priority: Urgent / Normal / FYI   |
| Tóm tắt         | Claude AI tóm tắt nội dung chính 2-3 câu                |
| Gợi ý reply     | 3 phương án reply từ ngắn đến dài                       |
| Digest Discord  | Tổng hợp email quan trọng → gửi vào Discord channel    |

## Lưu ý

- Cần **Outlook desktop** đang mở và đăng nhập
- Cần `ANTHROPIC_API_KEY` cho AI tóm tắt/reply
- Email đã xử lý được lưu vào `data/email_history.json` tránh duplicate
- Style học từ email cũ của bạn để gợi ý reply đúng giọng văn
