# ⬡ SQL → Obsidian

> Paste câu SQL → app phân tích business intent → optimize → lưu thành note `.md` trong Obsidian vault.

## Dùng để làm gì?

Khi bạn viết SQL để trả lời một câu hỏi business, bạn muốn:
- Biết câu SQL đó **đang hỏi gì** (không phải syntax mà là ý nghĩa)
- Có bản **optimize** chạy nhanh hơn nếu có thể
- **Lưu lại** có thể tìm kiếm sau này trong Obsidian

## Cách dùng

```
1. Paste câu SQL vào text box
2. Nhấn Analyze → app gửi lên Claude AI để phân tích
3. Xem kết quả: business intent, optimization suggestions, tags
4. Điều chỉnh title / tags nếu cần
5. Nhấn Save → file .md được ghi vào D:\ai_brain\SQL Queries\
```

## Output file .md chứa gì?

- Title và business question
- Câu SQL gốc
- Câu SQL đã optimize (nếu có cải thiện)
- Tags để tìm kiếm sau
- Tên tables được dùng
- Ngày lưu

## Lưu ý

- Cần `ANTHROPIC_API_KEY` trong `.env` để phân tích bằng AI
- Nếu không có API key → fallback sang Ollama local
- File được lưu tại `D:\ai_brain\SQL Queries\` — cần path này tồn tại
