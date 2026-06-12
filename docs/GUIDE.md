# Task Tracker — Hướng dẫn sử dụng

## Khởi động lại sau khi tắt máy

Double-click vào file **`run.bat`** — xong.

Nó tự động:
- Mở scheduler chạy nền (cửa sổ thu nhỏ, gửi Discord lúc **09:00** và **13:30**)
- Mở menu chính để nhập task, chỉnh deadline, xem danh sách

---

## Tự động chạy khi bật máy (không cần mở tay)

Chạy một lần, không cần làm lại:

1. Nhấn `Win + R` → gõ `taskschd.msc` → Enter
2. Cột phải → **Create Basic Task**
3. Điền:
   - Name: `Task Tracker`
   - Trigger: **When the computer starts**
   - Action: **Start a program**
   - Program: dán đường dẫn đầy đủ:
     ```
     D:\My_Brain_AI\Project\task-tracker\run.bat
     ```
4. Finish → Done

---

## Chuyển sang máy khác

### Bước 1 — Copy thư mục

Copy toàn bộ thư mục `task-tracker` sang máy mới. Có thể bỏ folder `.venv` để nhẹ hơn.

### Bước 2 — Cài Python

Tải Python 3.11+ tại [python.org](https://python.org). Tick **Add to PATH** khi cài.

### Bước 3 — Tạo lại venv và cài thư viện

Mở PowerShell trong thư mục `task-tracker`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Bước 4 — Cập nhật đường dẫn vault Obsidian

Mở file `modules\obsidian_client.py`, sửa dòng:

```python
VAULT_PATH = Path(r"D:\Second_Brain\Second_Brain")
```

Thành đường dẫn vault trên máy mới, ví dụ:

```python
VAULT_PATH = Path(r"C:\Users\TenUser\Documents\Second_Brain")
```

### Bước 5 — Kiểm tra file .env

Mở file `.env`, đảm bảo các giá trị sau còn đúng:

```
DISCORD_WEBHOOK_URL=...   # giữ nguyên, webhook không đổi theo máy
OLLAMA_BASE_URL=http://localhost:11434   # cần cài Ollama trên máy mới
OLLAMA_MODEL=llama3
```

Nếu máy mới chưa có Ollama: tải tại [ollama.com](https://ollama.com) → sau khi cài chạy `ollama pull llama3`.

### Bước 6 — Chạy

```powershell
python main.py       # terminal 1
python scheduler.py  # terminal 2
```

---

## Các lệnh thường dùng

| Việc cần làm | Lệnh |
|---|---|
| Nhập task mới | `python main.py` → chọn ➕ |
| Chỉnh deadline | `python main.py` → chọn ✏️ |
| Xem danh sách task | `python main.py` → chọn 📋 |
| Test gửi Discord ngay | `python main.py` → chọn 🔔 |
| Chạy nhắc nhở hằng ngày | `python scheduler.py` |

---

## Cấu trúc thư mục

```
task-tracker/
├── .env                  ← Discord webhook, Obsidian key, Ollama URL
├── .env.example          ← Template tham khảo
├── .vscode/settings.json ← VS Code tự nhận .venv
├── requirements.txt      ← Danh sách thư viện Python
├── run.bat               ← Double-click: mở scheduler nền + menu chính cùng lúc
├── main.py               ← Menu chính
├── add_task.py           ← CLI nhập task mới
├── scheduler.py          ← Nhắc nhở 09:00 & 13:30 hằng ngày
├── modules/
│   ├── deadline.py       ← Tính deadline theo category (high/medium/low/ad-hoc)
│   ├── task_manager.py   ← Lưu/đọc/sửa tasks.json
│   ← ← ← ← ←  ← ←
│   ├── ollama_client.py  ← Gọi Ollama sinh checklist AI
│   ├── obsidian_client.py← Đọc vault Obsidian từ filesystem
│   └── discord_notifier.py ← Gửi embed Discord
└── data/
    └── tasks.json        ← Toàn bộ task (active + archived)
```

---

## Vault Obsidian

Đường dẫn hiện tại: `D:\ai_brain`

Mọi file `.md` thêm vào vault sẽ tự động được đọc khi tạo task mới — không cần config lại.

---

## SQL → Obsidian Note

**Tab:** 🤖 AI Tools → cuộn xuống cuối

### Cách dùng

1. Paste SQL query vào text area
2. Click **🔍 Phân tích** → AI sinh business description, title, tags, tables
3. Xem và chỉnh preview note trong expander
4. Click **💾 Lưu vào Obsidian** → file được lưu tại `D:\ai_brain\SQL Queries\`

### SQL Optimizer

Dùng nút **⚡ Optimize SQL** (độc lập với phân tích) để nhận gợi ý tối ưu query cùng outcome. Kết quả chỉ hiển thị trên UI, không lưu tự động.

### Định dạng file

File lưu dạng `YYYY-MM-DD_slug-title.md` với YAML frontmatter đầy đủ:
`title`, `date`, `tags`, `tables`, `filters`, `keywords`, `description`

Các field `tags` và `keywords` tự động tạo connections trong Obsidian Graph (tương thích Dataview plugin).

### Đổi đường dẫn vault

Mở `modules/sql_analyzer.py`, sửa dòng:

```python
VAULT_PATH = Path(r"D:\ai_brain")
```
