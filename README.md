# Leonie — Work Hub

Personal "Work Hub": **React (Vite) frontend + FastAPI backend**. Single-user
desktop-style web app cho tasks, analytics, ML/forecast, SQL và automation.

---

## Cài trên máy mới (clone & run)

### 1. Cài sẵn (prerequisites)

| Công cụ | Ghi chú |
|---------|---------|
| **Git** | để clone |
| **Python ≥ 3.13** | backend (uv có thể tự cài Python nếu thiếu) |
| **uv** | quản lý môi trường Python — https://docs.astral.sh/uv/ |
| **Node.js ≥ 18 + npm** | frontend |
| **Microsoft Edge** | `run.py` tự mở Edge (không bắt buộc — mở browser khác cũng được) |

### 2. Các bước

```powershell
# a) Clone
git clone <URL-repo> leonie
cd leonie

# b) Tạo file .env từ mẫu rồi điền key thật
copy .env.example .env        # (macOS/Linux: cp .env.example .env)
#   -> mở .env, điền ANTHROPIC_API_KEY, DISCORD_WEBHOOK_URL, ... (xem .env.example)

# c) Cài dependency frontend (backend tự cài qua `uv run` ở bước sau)
cd frontend
npm install
cd ..

# d) Chạy cả 2 server + tự mở Edge
python run.py
```

`run.py` khởi động Vite (**:5177**) + uvicorn (**:8000**) và mở app trong Edge.
Lần chạy đầu, `uv run` sẽ tự tạo `.venv` và cài backend dependencies từ `uv.lock`
(có thể mất 1–2 phút). Nhấn **Ctrl+C** để tắt cả hai.

> ⚠️ **Không commit file `.env`** (đã nằm trong `.gitignore`). Chỉ commit `.env.example`
> với giá trị placeholder.

---

## Chạy thủ công (tùy chọn)

```powershell
# Backend (FastAPI) — http://localhost:8000  (API docs: /docs)
cd backend ; uv run uvicorn main:app --reload --port 8000

# Frontend (dev, hot-reload) — http://localhost:5177
cd frontend ; npm run dev

# Frontend (production build → backend phục vụ tại :8000)
cd frontend ; npm run build
```

## Test

```powershell
cd backend ; uv run pytest -q
```

---

## Cấu trúc

- **`frontend/`** — React 19 · Vite 6 · TypeScript · TailwindCSS · Zustand · recharts · CodeMirror
- **`backend/`** — FastAPI (uvicorn :8000), deps quản lý bằng **uv**; DuckDB cho ML/SQL, SQLite cho state
- **`_legacy/`** — app Streamlit cũ (chỉ tham khảo, KHÔNG chạy)
- **`run.py`** — launcher khởi động cả frontend + backend

Chi tiết kiến trúc & module map: xem [`CLAUDE.md`](CLAUDE.md).
Hướng dẫn sử dụng cho người dùng cuối: xem [`docs/GUIDE.md`](docs/GUIDE.md).
