# AUTOMATION FEATURE — SESSION HANDOFF (2026-06-04)

> **Cách dùng:** Paste toàn bộ file này vào MESSAGE ĐẦU TIÊN của session mới.
> Yêu cầu Claude: *"Tiếp tục skill `superpowers:brainstorming` từ **Phần 2 thiết kế**.
> KHÔNG hỏi lại 36 câu (đã chốt bên dưới). KHÔNG viết code cho tới khi spec được mình duyệt."*

---

## 0. TÓM TẮT 1 DÒNG
Đang thiết kế (chưa code) tính năng **"Automation"** cho app **Leonie**: kéo dữ liệu **REST API** → lưu JSON thô → định hình bằng **SQL (DuckDB)** → xuất file (**.duckdb / parquet / csv / xlsx**, streaming 3–10M dòng) → **thông báo Discord + Email**. Đã brainstorm 36 câu, chốt MVP, chọn **Approach A**. Mới trình **Phần 1/3** thiết kế, **chưa duyệt**.

---

## 1. ĐÃ LÀM ✅
- **Box Plot ML Studio**: hoàn chỉnh, verified trực quan, đã commit (nhánh hiện tại). 136/136 backend test pass. *(Chưa merge vào main.)*
- **Chẩn đoán bug "Query failed"** (ảnh Churn.xlsx 726k dòng): nguyên nhân `backend/routers/ml.py` hàm `run_query` (~dòng 347-367) gọi `_load_df()` → `pl.read_excel()` **re-parse toàn bộ Excel mỗi lần query** → timeout. Cách fix: convert file sang `.duckdb`/parquet **một lần lúc upload**, query thẳng store đó.
- **Brainstorming Automation**: hỏi **36 câu / 9 đợt** → chốt toàn bộ requirements (mục 4).
- **Chốt kiến trúc = Approach A** (pipeline khai báo + executor streaming server-side).
- **Trình Phần 1/3 thiết kế** (kiến trúc + backend skeleton + data model). User dừng tại đây, **chưa duyệt Phần 1**.
- **Khám phá codebase**: đã xác minh các file/pattern chính (mục 6).

## 2. CHƯA LÀM ❌
- **Duyệt Phần 1** thiết kế (đang chờ).
- **Phần 2 & 3 thiết kế** (chưa trình — xem mục 5B).
- **Viết spec** → `docs/superpowers/specs/2026-06-04-automation-design.md` (+ self-review + user review).
- **Viết implementation plan** (skill `superpowers:writing-plans`).
- **Code** — CHƯA động một dòng nào (HARD-GATE: chỉ code sau khi spec được duyệt).
- **Merge nhánh box-plot** vào main.
- **Fix bug "Query failed"** — sẽ là **spec riêng nhỏ**, dùng lại module `.duckdb` của Automation.
- **2 feature ML Studio tồn** (từ MEMORY.md): Anomaly History Log + Action Plan linking.

---

## 3. KIẾN TRÚC ĐÃ CHỌN: Approach A
**Pipeline khai báo + executor streaming phía server.** Job = một **config JSON**. Backend có executor stream: `httpx` kéo từng trang → nạp dần vào **DuckDB store** (không nhồi RAM) → áp **SQL người dùng** trong DuckDB → xuất bằng `COPY TO` → gửi webhook. **Show Code** sinh script Python tương đương **từ cùng config** (chỉ để xem). Connector là interface `Source.fetch_pages()` → REST hôm nay, cắm **T-SQL** sau không đụng export/notify.

**Đã loại:** (B) code-first chạy script sinh ra → mâu thuẫn "read-only/an toàn"; (C) duckdb-wasm ở browser → CORS + chết RAM với 3–10M dòng + lộ secret.

---

## 4. REQUIREMENTS ĐÃ CHỐT (36 câu — KHÔNG HỎI LẠI)

| Mảng | Quyết định v1 |
|---|---|
| **Trigger** | Nút **Run thủ công** (CHƯA scheduler) |
| **Nguồn** | **REST API (JSON)** duy nhất; kiến trúc chừa chỗ cắm **T-SQL** kế tiếp (rồi MySQL/SOQL) |
| **Khai báo** | **Form + lưu thành job**, **CRUD đầy đủ**; UI đặt dưới nhóm **Data** |
| **Auth** | API key/header, Basic, Bearer; **secret để trong `.env`**, job chỉ trỏ `${TÊN_BIẾN}` |
| **Phân trang** | `?page=n` (số trang), tự lặp đến khi rỗng |
| **Fetch** | Giữ **JSON thô** (nested), lưu nguyên |
| **Định hình** | Ô **SQL DuckDB** (người dùng viết) → ra "outcome" |
| **Python** | **Hệ thống tự sinh, READ-ONLY** (không chạy code tuỳ ý). Show Code = tab Python + tab SQL |
| **Preview** | **Nút Preview riêng** (N dòng đầu), tách khỏi Run |
| **Xuất** | `.duckdb` / parquet / csv / xlsx; **streaming** (3–10M dòng); **Excel chỉ cho kết quả nhỏ** (guard ~1M) |
| **Đích & tên** | **Đường dẫn tuỳ chỉnh** người dùng nhập; tên `job + timestamp` |
| **.duckdb** | 1 bảng tên cố định **`data`**; **cho phép append** tích luỹ ("query → có data → add vào") |
| **Thông báo** | Cuối pipeline (file→xử lý→outcome→webhook). **Discord** (đọc `DISCORD_WEBHOOK_URL` từ `.env`) + **Email** (SMTP). Nội dung: trạng thái + số dòng + thời gian + lỗi chi tiết. Email: **nhỏ thì đính kèm, to thì gửi link** |
| **Lịch sử** | Chỉ **trạng thái lần chạy gần nhất** mỗi job (nhúng vào hàng job) |
| **Lỗi** | Ghi **atomic** (temp→rename, lỗi thì xoá temp); **retry chỉ 429/5xx** + backoff (KHÔNG retry 4xx); **timeout mỗi request** (vd 30s); **0 dòng → không xuất, chỉ cảnh báo** |
| **ƯU TIÊN #1** | **CHỊU TẢI FILE LỚN (streaming-first)** — quyết định mọi đánh đổi kiến trúc |

**Quy mô thật:** 3M–10M dòng/lần kéo (có khi hơn). `.duckdb` là **kho tích luỹ trung tâm**, không phải bug-fix phụ.

---

## 5. THIẾT KẾ

### 5A. PHẦN 1 (ĐÃ TRÌNH — cần duyệt lại đầu session mới)

**Cấu trúc backend** (package nhỏ, mỗi file 1 việc):
```
backend/automation/
  models.py     # Pydantic: JobConfig, RestSource, Pagination, ExportSpec, NotifySpec, RunResult
  store.py      # CRUD automation_jobs trên SQLite + cập nhật trạng thái lần chạy gần nhất
  sources/
    base.py     # Protocol Source.fetch_pages() -> Iterator[list[dict]]   ← seam cắm T-SQL
    rest.py     # RestSource: httpx + phân trang ?page=n + resolve ${BIẾN} từ os.environ
  ingest.py     # stream từng trang JSON thô → bảng DuckDB (không nhồi RAM)
  shape.py      # chạy SQL người dùng trên DuckDB store → 'outcome'
  export.py     # ghi .duckdb/parquet/csv/xlsx, atomic (temp→rename), streaming, guard xlsx
  notify.py     # Discord (.env webhook) + Email (SMTP); format trạng thái/số dòng/thời gian/lỗi
  codegen.py    # render script Python read-only + SQL từ JobConfig
  runner.py     # điều phối fetch→ingest→shape→export→notify; có chế độ preview
backend/routers/automation.py   # router mỏng APIRouter(prefix="/automation"), gọi runner+store
backend/tests/test_automation.py
```
Đăng ký: `app.include_router(automation_router, prefix="/api")` trong `backend/main.py`.

**Bảng SQLite `automation_jobs`** (thêm `_migrate_v6(conn)` vào `backend/database.py`):
`id` TEXT PK `lower(hex(randomblob(8)))` · `name` TEXT · `config` TEXT(JSON) · `last_status` TEXT(ok/error/warning/null) · `last_run_at` TEXT · `last_rows` INTEGER · `last_error` TEXT · `created`/`updated` TEXT `datetime('now')`. → chỉ giữ trạng thái lần gần nhất, không cần bảng history.

**Connector seam:** `RestSource` implement `Source.fetch_pages()`; mai `TSqlSource` (pyodbc, server-side cursor) implement cùng interface, ingest/shape/export/notify không đổi.
**Secret:** `${VAR}` trong header/auth → resolve từ `os.environ` lúc chạy (main.py đã nạp `.env`). Config trong DB không chứa secret thật.

### 5B. PHẦN 2 & 3 (CẦN TRÌNH & DUYỆT Ở SESSION MỚI)

**Phần 2 — Runtime chi tiết** (trình rồi xin duyệt):
- **Endpoints** của `routers/automation.py`: CRUD `/automation/jobs`, `POST /automation/jobs/{id}/preview` (N dòng), `POST /automation/jobs/{id}/run`, `GET /automation/jobs/{id}/code` (Show Code).
- **ingest.py**: cách nạp JSON thô từng trang vào DuckDB (vd `read_json_auto`/insert per-batch) sao cho không ngốn RAM ở mức 10M dòng.
- **shape.py**: chạy SQL người dùng trên store; xử lý khi SQL trống (= xuất thô).
- **export.py**: atomic temp→rename; `.duckdb` (table `data`, overwrite vs append toggle); parquet/csv qua DuckDB `COPY TO`; **xlsx guard** (chặn nếu > ~1M dòng); streaming.
- **notify.py**: Discord đọc `DISCORD_WEBHOOK_URL` từ env (giống `_send_webhook` ở discord_notify.py); Email SMTP — **cần chốt nguồn cấu hình SMTP** (đề xuất: `.env` SMTP_HOST/PORT/USER/PASS/FROM/TO); rule đính kèm theo ngưỡng size.
- **codegen.py**: template sinh script Python read-only (httpx + phân trang + duckdb + export + webhook) từ JobConfig; test so khớp logic với executor.

**Phần 3 — Frontend + cross-cutting** (trình rồi xin duyệt):
- **Page** `frontend/src/pages/data/Automation.tsx` (danh sách job + CRUD + Run + Preview + Show Code).
- **Components** `frontend/src/components/automation/*` (JobForm, JobList, RunPanel, …); **tái dùng** `components/ml/CodePanel.tsx` cho Show Code.
- **API** `frontend/src/api/automation.ts` (pattern `client.post`).
- **Types** thêm vào `frontend/src/types.ts`.
- **Nav**: thêm item vào mảng `NAV` nhóm `id:'data'` ở `Sidebar.tsx` → `{path:'/data/automation', label:'Automation', iconName:'<icon mới>', color:'#60a5fa'}` + import icon (vd `Workflow`/`Zap`) vào `ICON_MAP`. Route trong `frontend/src/App.tsx`.
- **Error handling** (atomic/retry/timeout/0-dòng), **testing strategy**, **security** (secret, no-exec), **OUT-OF-SCOPE/YAGNI** (scheduler, T-SQL/MySQL/SOQL, multi-source join, user-Python, browser orchestration, history dài).

---

## 6. CODEBASE FACTS (đường dẫn & pattern đã xác minh)

**Stack:** FastAPI + Polars + DuckDB + NumPy (backend) · React 18 + TS + Tailwind + Vite (frontend, port **5177**, proxy `/api`→`localhost:8000`).

**Backend:**
- `backend/main.py`: nạp `.env` qua `dotenv_values` vào `os.environ` (dòng 5-8); `app.include_router(x, prefix="/api")` (dòng 49-60); `lifespan` gọi `create_tables()`.
- `backend/database.py`: SQLite `data/leonie.db`; `get_connection()` (Row factory, WAL, FK on); `create_tables()` + `_migrate_v2.._v5`; `UPLOADS_DIR = data/uploads`. → thêm `_migrate_v6` cho `automation_jobs`.
- Router pattern: `APIRouter(prefix="/x", tags=["x"])`, dùng `get_connection()`. JSON-trong-cột-TEXT đã có tiền lệ (`performance_settings.streak_rule`).
- Webhook mẫu: `backend/routers/discord_notify.py` → `_send_webhook(url, message)` POST `{content: message}` (urllib, timeout 10). *(Hiện webhook lưu ở DB; Automation đọc từ `.env` theo yêu cầu user.)*
- Bug perf: `backend/routers/ml.py` `run_query` ~dòng 347-367 (`_load_df` re-parse xlsx mỗi query).

**Deps ĐÃ cài:** `duckdb`, `polars`, `openpyxl`, `pyarrow` (parquet), `fastexcel`, `httpx`.
**Deps CHƯA cài (chỉ cần khi mở rộng, KHÔNG cho v1):** scheduler (apscheduler), `pyodbc`/mysql/`simple-salesforce`, `sqlglot`.

**Frontend:**
- Nav: `frontend/src/components/layout/Sidebar.tsx` → mảng `NAV` (hardcode). Nhóm `id:'data'` (label `'SQL SANDBOX'`, color `#60a5fa`) gồm `/data/sql`, `/data/snippets`, `/data/fabric`. `ICON_MAP` ở đầu file.
- Routes: `frontend/src/App.tsx`. Pages: `frontend/src/pages/data/`. API: `frontend/src/api/` (vd `api/ml.ts` dùng `client.post`). Types: `frontend/src/types.ts`. Show Code tái dùng: `frontend/src/components/ml/CodePanel.tsx`.

**Run / test:**
- Backend: `uvicorn` cổng 8000. Frontend: `npm run dev` cổng 5177.
- Test backend: `backend\.venv\Scripts\python.exe -m pytest tests/ -v` (chạy trong `backend/`). Baseline 136/136 pass.
- ⚠️ **Chạy frontend trong worktree:** `node_modules` được tạo bằng **NTFS junction** trỏ về repo chính (`cmd /c mklink /J "<worktree>\frontend\node_modules" "<mainrepo>\frontend\node_modules"`) — symlink cần admin, junction thì không.

---

## 7. RÀNG BUỘC — KHÔNG ĐỘNG VÀO ⚠️
Các file uncommitted có sẵn (KHÔNG sửa, KHÔNG commit kèm):
`.claude/settings.local.json` · `backend/routers/{action_plan,fabric_views,snippets,sql_sandbox}.py` · `backend/tests/test_sql_sandbox.py` · `frontend/src/api/sql.ts` · `frontend/src/components/sql/` · `frontend/src/data/` · `frontend/src/pages/data/SqlSandbox.tsx` · `data/vina_brew/` · `scripts/generate_vina_brew.py`.
**`.env` chứa secret thật** (ANTHROPIC_API_KEY, OBSIDIAN_API_KEY, DISCORD_WEBHOOK_URL, Ollama…) — KHÔNG commit/expose. Chỉ commit đúng file của từng task.

---

## 8. BƯỚC TIẾP THEO NGAY (session mới)
1. Invoke `superpowers:brainstorming` (tiếp tục, không hỏi lại 36 câu).
2. **Trình Phần 2** (runtime) → xin duyệt → **Phần 3** (frontend + cross-cutting) → xin duyệt.
3. **Viết spec** `docs/superpowers/specs/2026-06-04-automation-design.md` → self-review → user review → commit.
4. Chuyển `superpowers:writing-plans` → plan `docs/superpowers/plans/2026-06-04-automation.md`.
5. Implement theo TDD, commit nhỏ. (HARD-GATE: chỉ code sau khi spec duyệt.)

**Điểm còn mở cần hỏi user ở Phần 2:** nguồn cấu hình **SMTP** cho Email (đề xuất `.env`); ngưỡng size đính kèm email; chốt `.duckdb` overwrite-vs-append mặc định.
