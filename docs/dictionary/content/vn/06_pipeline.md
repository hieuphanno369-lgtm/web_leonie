# ◉ Pipeline Monitor

> Xem trạng thái scheduler, trigger Discord notifications thủ công, kiểm tra sức khỏe hệ thống.

## Scheduler jobs

| Job                  | Giờ chạy   | Làm gì                                      |
|----------------------|------------|---------------------------------------------|
| Morning reminder     | 09:00      | Gửi danh sách task hôm nay lên Discord      |
| Afternoon reminder   | 13:30      | Nhắc task chưa done + task overdue          |

## Tính năng trong tab

- **Manual trigger**: bấm nút để gửi Discord notification ngay lập tức (không chờ schedule)
- **Health check**: xem Discord webhook có hoạt động không
- **Job status**: xem lần cuối job chạy lúc mấy giờ, có lỗi không

## Lưu ý

- Scheduler chạy bằng `scheduler.py` — cần file này đang chạy trong background
- Cần `DISCORD_WEBHOOK_URL` trong `.env`
- Nếu Discord webhook lỗi → check URL trong `.env` trước
