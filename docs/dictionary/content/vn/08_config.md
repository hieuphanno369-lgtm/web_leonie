# ⊛ Config

> Xem biến môi trường đang được load từ file `.env`. Chỉ xem — không edit tại đây.

## Các biến quan trọng

| Biến                  | Dùng cho                                      |
|-----------------------|-----------------------------------------------|
| `ANTHROPIC_API_KEY`   | Tất cả tính năng AI (ML insight, email, SQL)  |
| `OLLAMA_BASE_URL`     | Fallback khi không có Claude API              |
| `DISCORD_WEBHOOK_URL` | Gửi reminder và digest lên Discord            |
| `OBSIDIAN_VAULT_PATH` | Đường dẫn Obsidian vault để lưu SQL notes     |

## Cách thay đổi config

```
1. Mở file .env ở root project
2. Sửa giá trị cần thay đổi
3. Restart app: Ctrl+C → streamlit run app.py
```

## Lưu ý bảo mật

- Không commit file `.env` lên git (đã có trong `.gitignore`)
- API key bị lộ → revoke ngay tại console.anthropic.com
- Xem `.env.example` để biết format cần điền
