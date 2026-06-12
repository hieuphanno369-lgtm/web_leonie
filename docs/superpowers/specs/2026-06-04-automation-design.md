# Automation — Design Spec

> **Date:** 2026-06-04 · **Status:** Approved design (pre-plan) · **Project:** Leonie task-tracker
> **Next step:** `superpowers:writing-plans` → implementation plan.

---

## 1. Goal

Một mục **"Automation"** mới trong app Leonie cho phép người dùng: **kéo dữ liệu từ REST API → lưu JSON thô → định hình bằng SQL (DuckDB) → xuất file (`.duckdb` / parquet / csv / xlsx) → gửi thông báo (Discord + Email)**. Toàn bộ chạy bằng **executor streaming phía server**, chịu được dữ liệu **3–10M dòng**. Người dùng khai báo job qua form, lưu lại, chạy thủ công, xem trước (Preview), và xem **code Python sinh tự động (read-only)**.

## 2. Background & Problem

- ML Studio hiện đọc file lớn (vd Churn.xlsx 726k dòng) bằng cách re-parse mỗi query → **"Query failed"**. Bài học: phải dùng **store cột (DuckDB/parquet) + streaming**, không nạp hết vào RAM.
- Người dùng cần một luồng lặp đi lặp lại: *query API → có data → tích luỹ vào kho `.duckdb` → xuất file → báo webhook*, với dữ liệu lớn dần (3M, có khi 10M dòng).
- **Ưu tiên #1 = chịu tải file lớn.** Mọi đánh đổi kiến trúc nghiêng về streaming-first, columnar.

## 3. Scope

### 3.1 In-scope (v1)
- Nguồn **REST API trả JSON** (GET + query params + phân trang `?page=n`).
- Auth: none / API key (header) / Basic / Bearer — **secret đọc từ `.env`** qua tham chiếu `${VAR}`.
- Giữ **JSON thô (nested)**; định hình bằng **SQL DuckDB do người dùng viết**.
- Xuất **`.duckdb` / parquet / csv / xlsx**, streaming; `.duckdb` có chế độ **overwrite | append** vào 1 bảng cố định `data`.
- **Preview** (N dòng) tách khỏi **Run**.
- **Show Code**: Python read-only + SQL (chỉ để xem, không chạy).
- Thông báo cuối pipeline: **Discord** (`DISCORD_WEBHOOK_URL` từ `.env`) + **Email** (SMTP từ `.env`); báo cả thành công lẫn thất bại.
- Quản lý job: **CRUD đầy đủ**; lưu **trạng thái lần chạy gần nhất** mỗi job.
- Trigger: **nút Run thủ công** (chạy nền + UI poll).

### 3.2 Out-of-scope (YAGNI — v1 KHÔNG làm)
Scheduler/cron · nguồn T-SQL/MySQL/SOQL (chỉ chừa interface seam) · join nhiều nguồn · chạy Python do user viết · orchestration ở browser (duckdb-wasm) · history dài hơn lần gần nhất · multi-user/auth · request body POST/GraphQL · **dedup khi append** (append = nối thêm thuần) · incremental/delta sync.

## 4. Locked Requirements (chốt từ 36 câu phỏng vấn)

| Mảng | Quyết định v1 |
|---|---|
| Trigger | Nút **Run thủ công** (chưa scheduler) |
| Nguồn | **REST API (JSON)**; kiến trúc chừa seam cắm **T-SQL** kế tiếp |
| Khai báo | **Form + lưu thành job**, CRUD đầy đủ; UI dưới nhóm **Data** |
| Auth | API key/header, Basic, Bearer; **secret trong `.env`**, job chỉ trỏ `${VAR}` |
| Phân trang | `?page=n`, tự lặp tới khi trang rỗng |
| Fetch | Giữ **JSON thô** (nested) |
| Định hình | Ô **SQL DuckDB** (user viết) → "outcome" |
| Python | **Hệ thống tự sinh, read-only** (không chạy code tuỳ ý) |
| Preview | **Nút Preview riêng** (N dòng), tách khỏi Run |
| Xuất | `.duckdb`/parquet/csv/xlsx; **streaming** (3–10M dòng); **Excel chỉ cho kết quả nhỏ** (guard ~1M) |
| Đích & tên | **Đường dẫn tuỳ chỉnh** user nhập; tên `job + timestamp` |
| .duckdb | 1 bảng cố định **`data`**; **overwrite hoặc append** |
| Thông báo | Cuối pipeline; **Discord (.env webhook)** + **Email (SMTP)**; nội dung: status + số dòng + thời gian + đường dẫn + lỗi; báo cả success & failure |
| Lịch sử | Chỉ **trạng thái lần chạy gần nhất** mỗi job |
| Lỗi | Atomic write (temp→rename); retry **chỉ 429/5xx** + backoff (không retry 4xx); **timeout mỗi request**; 0 dòng → không xuất, chỉ cảnh báo |
| Ưu tiên #1 | **Chịu tải file lớn → streaming-first, columnar** |

## 5. Architecture — Approach A

**Pipeline khai báo + executor streaming phía server.** Một job = một **JobConfig (JSON)**. Backend có executor stream: kéo từng trang qua `httpx` → nạp dần vào **DuckDB store** (không nhồi RAM) → áp **SQL người dùng** trong DuckDB → xuất bằng DuckDB `COPY` → gửi webhook/email. **Show Code** render script Python tương đương **từ cùng JobConfig** (chỉ hiển thị).

**Connector là interface** `Source.fetch_pages()`: hôm nay `RestSource`, mai cắm `TSqlSource` mà không đụng ingest/shape/export/notify.

**Vì sao chọn A:** ưu tiên #1 là tải file lớn → executor streaming server-side là con đường an toàn RAM duy nhất.
**Đã loại:** (B) code-first chạy script user sinh ra → mâu thuẫn yêu cầu "read-only/không chạy code tuỳ ý"; (C) duckdb-wasm ở browser → CORS + chết RAM với 10M dòng + lộ secret ra client.

## 6. Backend Design

### 6.1 Package structure
```
backend/automation/
  __init__.py
  models.py          # Pydantic: JobConfig, RestSource, RestAuth, Pagination, ExportSpec, NotifySpec, EmailSpec, RunResult, AutomationJob
  store.py           # CRUD automation_jobs trên SQLite + cập nhật last-run
  sources/
    __init__.py
    base.py          # Protocol Source: fetch_pages(limit_pages=None) -> Iterator[list[dict]]   ← seam T-SQL
    rest.py          # RestSource: httpx.Client + phân trang + resolve ${VAR} + retry/timeout
  ingest.py          # stream từng page → bảng staging raw(rec JSON) trong DuckDB
  shape.py           # chạy SQL người dùng trên raw → bảng data
  export.py          # ghi 4 format, atomic temp→rename, streaming, guard xlsx, append .duckdb
  notify.py          # Discord (.env webhook) + Email (SMTP từ .env)
  codegen.py         # render script Python read-only + SQL từ JobConfig
  runner.py          # điều phối fetch→ingest→shape→export→notify; preview mode; chạy nền
backend/routers/automation.py    # APIRouter(prefix="/automation"); đăng ký trong main.py
backend/tests/test_automation.py
```
Đăng ký trong `backend/main.py`: `from routers.automation import router as automation_router` rồi `app.include_router(automation_router, prefix="/api")`.

### 6.2 Data model (Pydantic — `models.py`)
```python
from typing import Literal
from pydantic import BaseModel

class RestAuth(BaseModel):
    type: Literal["none", "api_key", "basic", "bearer"] = "none"
    header_name: str | None = None     # api_key: tên header (vd "X-API-Key")
    value_ref: str | None = None       # api_key/bearer: tên biến ${VAR}, vd "API_KEY"
    user_ref: str | None = None        # basic: tên biến user
    pass_ref: str | None = None        # basic: tên biến pass

class Pagination(BaseModel):
    param: str = "page"                # tên query param phân trang
    start: int = 1                     # trang bắt đầu

class RestSource(BaseModel):
    url: str                           # có thể chứa ${VAR}
    method: Literal["GET"] = "GET"
    headers: dict[str, str] = {}       # value có thể chứa ${VAR}
    params: dict[str, str] = {}        # query param tĩnh
    auth: RestAuth = RestAuth()
    records_path: str = ""             # đường dẫn tới mảng record, vd "data.items"; "" = response chính là mảng
    pagination: Pagination | None = None
    timeout_seconds: int = 30
    max_retries: int = 3

class ExportSpec(BaseModel):
    formats: list[Literal["duckdb", "parquet", "csv", "xlsx"]] = []
    dest_dir: str                      # thư mục đích do user nhập
    duckdb_mode: Literal["overwrite", "append"] = "overwrite"
    xlsx_row_guard: int = 1_000_000

class EmailSpec(BaseModel):
    enabled: bool = False
    recipients: list[str] = []
    attach_max_bytes: int = 10_485_760 # 10MB: nhỏ hơn đính kèm, lớn hơn ghi đường dẫn

class NotifySpec(BaseModel):
    discord_enabled: bool = False
    email: EmailSpec = EmailSpec()

class JobConfig(BaseModel):
    name: str
    source: RestSource
    shape_sql: str = ""                # SQL DuckDB trên `raw`; "" = passthrough (SELECT * FROM raw)
    export: ExportSpec
    notify: NotifySpec = NotifySpec()

class RunResult(BaseModel):
    status: Literal["ok", "warning", "error", "running"]
    rows: int = 0
    duration_seconds: float = 0.0
    output_files: list[str] = []
    error: str | None = None

class AutomationJob(BaseModel):
    id: str
    config: JobConfig
    last_status: str | None = None
    last_run_at: str | None = None
    last_rows: int | None = None
    last_error: str | None = None
    created: str
    updated: str
```

### 6.3 DB schema — `_migrate_v6(conn)` trong `backend/database.py`
Thêm gọi `_migrate_v6(conn)` vào cuối `create_tables()` (sau `_migrate_v5`):
```sql
CREATE TABLE IF NOT EXISTS automation_jobs (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name        TEXT NOT NULL,
    config      TEXT NOT NULL,           -- JSON của JobConfig
    last_status TEXT,                    -- ok | warning | error | running | NULL
    last_run_at TEXT,
    last_rows   INTEGER,
    last_error  TEXT,
    created     TEXT NOT NULL DEFAULT (datetime('now')),
    updated     TEXT NOT NULL DEFAULT (datetime('now'))
);
```
Idempotent: `CREATE TABLE IF NOT EXISTS` (cùng pattern các migration hiện có). `config` lưu JSON string của `JobConfig` (tiền lệ: `performance_settings.streak_rule`).

### 6.4 Runtime flow (1 lần Run)
```
runner.run(job):
  t0 = now
  set last_status='running' trong DB (đồng thời là khoá chống chạy trùng)
  with tạo working dir tạm  data/automation_tmp/<job_id>_<ts>/  và working DuckDB:
    1) fetch  : for page in source.fetch_pages():        # rest.py — Iterator[list[dict]]
    2) ingest :     ingest.append_page(con, page)        # mỗi page → INSERT vào raw(rec JSON)
    3) shape  : ingest xong → shape.run(con, shape_sql)  # tạo bảng `data` từ `raw`
    4) rows = SELECT count(*) FROM data
       nếu rows == 0: status='warning', bỏ qua export
       else: export.write(con, data, export_spec) → output_files  # streaming, atomic
    5) notify.send(job, RunResult)                       # Discord + Email
  cập nhật automation_jobs: last_status/last_run_at/last_rows/last_error
  dọn working dir tạm
```
Mọi exception trong các bước → `status='error'`, `last_error=str(e)`, vẫn gọi `notify` (failure), vẫn dọn temp.

**Preview mode** (`runner.preview(job, n_rows)`): chỉ `fetch_pages(limit_pages=1)` → ingest → shape → `SELECT * FROM data LIMIT n` → trả `list[dict]`. **KHÔNG export, KHÔNG notify, KHÔNG đụng DB job.**

### 6.5 Module behavior

**`sources/base.py`** — interface seam:
```python
from typing import Protocol, Iterator
class Source(Protocol):
    def fetch_pages(self, limit_pages: int | None = None) -> Iterator[list[dict]]: ...
```

**`sources/rest.py`** — `RestSource`:
- `httpx.Client` đồng bộ (runner chạy trong thread nền nên không cần async).
- Resolve `${VAR}` trong url/headers/auth từ `os.environ` lúc chạy (vd `_resolve("${API_KEY}")` → `os.environ["API_KEY"]`; thiếu biến → raise lỗi rõ ràng "Missing env var API_KEY").
- Auth: `api_key` → set header `header_name = <value_ref>`; `bearer` → `Authorization: Bearer <value_ref>`; `basic` → `httpx` BasicAuth(user_ref, pass_ref).
- Phân trang: nếu có `pagination`, lặp `param=start, start+1, …`, mỗi vòng GET, trích mảng theo `records_path`; **dừng khi mảng rỗng**. Không có `pagination` → gọi 1 lần.
- Trích `records_path`: tách theo dấu chấm, đi sâu vào JSON (vd `data.items`); `""` → response chính là mảng.
- `timeout_seconds` mỗi request. Retry **chỉ khi 429 hoặc 5xx**, backoff luỹ thừa (0.5·2^k), tối đa `max_retries`; **4xx → raise ngay** (không retry).
- `limit_pages` để Preview chỉ lấy 1 trang.

**`ingest.py`**:
- `ensure_raw(con)`: `CREATE TABLE IF NOT EXISTS raw (rec JSON)`.
- `append_page(con, page: list[dict])`: ghi batch ra file tạm NDJSON rồi `INSERT INTO raw SELECT json FROM read_json('<tmp>', records='false')` (mỗi record = 1 giá trị JSON, giữ nguyên nested). Xoá file tạm. → stream theo page, RAM thấp.

**`shape.py`**:
- `run(con, shape_sql)`: nếu `shape_sql` rỗng → `CREATE TABLE data AS SELECT * FROM raw`. Ngược lại → `CREATE TABLE data AS <shape_sql>` (SQL user tham chiếu `raw`, dùng toán tử JSON DuckDB như `rec->>'$.field'`). Lỗi SQL → raise (UI/preview hiển thị).

**`export.py`** — mỗi format ghi atomic (ghi `<final>.tmp` → `os.replace`; lỗi xoá tmp). Tên file `<job_name>_<YYYYMMDD_HHMMSS>.<ext>` trong `dest_dir`:
- `parquet`/`csv`: `COPY (SELECT * FROM data) TO '<tmp>' (FORMAT parquet)` / `(FORMAT csv, HEADER)` — DuckDB streaming.
- `xlsx`: **guard** — nếu `rows > xlsx_row_guard` → bỏ qua format này, thêm cảnh báo (không fail cả job); ngược lại (đã nhỏ) nạp `data` vào bộ nhớ và ghi bằng **openpyxl** (đã cài sẵn).
- `duckdb`:
  - `overwrite`: tạo `<tmp>.duckdb`, `CREATE TABLE data AS SELECT * FROM <working>.data`, `os.replace` đè đích.
  - `append`: nếu đích chưa có → tạo mới + bảng `data`; nếu có → `ATTACH '<dest>.duckdb'; INSERT INTO dest.data SELECT * FROM data` trong **transaction** (begin → commit / rollback). (Append không atomic-rename được; an toàn dựa vào transaction DuckDB.)
- Trả `list[str]` đường dẫn file đã ghi + danh sách cảnh báo (vd xlsx bị skip).

**`notify.py`**:
- `_discord(message)`: đọc `os.getenv("DISCORD_WEBHOOK_URL")`; POST `{"content": message}` (urllib, timeout 10 — cùng pattern `routers/discord_notify._send_webhook`). Thiếu env → bỏ qua + ghi cảnh báo.
- `_email(subject, body, attachments)`: SMTP từ `.env` (`SMTP_HOST/PORT/USER/PASS/FROM`), gửi tới `recipients`. File `< attach_max_bytes` → đính kèm; lớn hơn → ghi đường dẫn trong body. Dùng `smtplib` + `email.message.EmailMessage`.
- `send(job, result)`: dựng nội dung = `status + rows + duration + output_files/đường dẫn + error`; gọi Discord (nếu bật) + Email (nếu bật). Gọi cho **cả success & failure**.

**`codegen.py`**:
- `python_script(config) -> str`: render script đứng độc lập (httpx fetch + phân trang + auth qua `os.environ[...]` + duckdb ingest + `shape_sql` + `COPY` export + webhook). **`${VAR}` render thành `os.environ["VAR"]`, KHÔNG nhúng secret thật.** Chỉ để hiển thị.
- `shape_sql_text(config) -> str`: trả `shape_sql` (hoặc `SELECT * FROM raw`).

**`store.py`** — `list_jobs() / get_job(id) / create_job(config) / update_job(id, config) / delete_job(id) / set_run_status(id, result)`; map row ↔ `AutomationJob` (parse `config` JSON).

**`runner.py`** — `run(job)` (đồng bộ, gọi trong thread nền), `preview(job, n)`; chạy nền: `routers` spawn `threading.Thread(target=run, ...)` daemon. Chống chạy trùng: từ chối `/run` nếu `last_status == 'running'`.

### 6.6 API endpoints — `routers/automation.py` (prefix `/api/automation`)
| Method · Path | Body / Trả về |
|---|---|
| `GET /jobs` | → `list[AutomationJob]` (kèm last-run) |
| `POST /jobs` | `JobConfig` → `AutomationJob` |
| `GET /jobs/{id}` | → `AutomationJob` |
| `PUT /jobs/{id}` | `JobConfig` → `AutomationJob` |
| `DELETE /jobs/{id}` | → `{ok: true}` |
| `POST /jobs/{id}/preview` | `{n_rows?: int=100}` → `{columns, rows}` (đồng bộ; không export/notify) |
| `POST /jobs/{id}/run` | → `{status: "running"}` (spawn thread nền); 409 nếu đang chạy |
| `GET /jobs/{id}/code` | → `{python: str, sql: str}` (read-only) |

UI theo dõi tiến độ bằng cách **poll `GET /jobs/{id}`** đến khi `last_status != "running"`.

## 7. Frontend Design

**Page** `frontend/src/pages/data/Automation.tsx` — 2 cột: trái **JobList** (badge status + thời gian + số dòng + nút New), phải **JobForm** + nút **Preview / Run / Show Code / Save / Delete**.

**Components** `frontend/src/components/automation/`:
| File | Việc |
|---|---|
| `JobList.tsx` | Danh sách job + badge `ok/error/warning/running` |
| `JobForm.tsx` | Config: name · RestSource (url, method, headers, auth + `${VAR}`, `records_path`, pagination param) · ô SQL shaping · ExportSpec (chọn format, `dest_dir`, radio `overwrite|append`) · NotifySpec (toggle Discord, toggle Email + recipients) |
| `PreviewPanel.tsx` | Bảng N dòng preview |
| `RunStatus.tsx` | Hiện trạng thái + **poll `GET /jobs/{id}` mỗi ~2s** tới khi khác `running` |
| *(reuse)* `components/ml/CodePanel.tsx` | Show Code: tab Python + tab SQL (read-only) |

**API** `frontend/src/api/automation.ts`: `listJobs, getJob, createJob, updateJob, deleteJob, previewJob, runJob, getJobCode` (pattern axios `client`).
**Types** thêm vào `frontend/src/types.ts`: `AutomationJob, JobConfig, RestSource, RestAuth, Pagination, ExportSpec, EmailSpec, NotifySpec, RunResult, PreviewResult`.
**Nav** `frontend/src/components/layout/Sidebar.tsx`: thêm vào nhóm `id:'data'` → `{ path:'/data/automation', label:'Automation', iconName:'Workflow', color:'#60a5fa' }`; import `Workflow` từ `lucide-react` và thêm vào `ICON_MAP`.
**Route** `frontend/src/App.tsx`: thêm `<Route path="/data/automation" element={<Automation/>} />`.

## 8. Error Handling
- **Fetch**: retry **chỉ 429/5xx** (backoff luỹ thừa, tối đa `max_retries`); **4xx fail ngay**; **timeout mỗi request** (`timeout_seconds`).
- **Export atomic**: `<final>.tmp` → `os.replace`; lỗi → xoá `.tmp`. `.duckdb append` → transaction DuckDB (commit/rollback).
- **0 dòng** → bỏ export, `status='warning'`, notify warning.
- **Lỗi giữa chừng** → cả run `status='error'`, dọn working temp, set `last_error`, notify failure.
- **Preview lỗi** → trả lỗi inline (HTTP 400 + message), không notify, không đụng DB job.
- **Env var thiếu** (`${VAR}` không có trong `os.environ`) → lỗi rõ ràng "Missing env var X".
- Mọi exception gói thành `last_error` (string) → UI hiển thị.

## 9. Security
- **Secret chỉ trong `.env`**; `JobConfig` lưu **tên `${VAR}`**, không lưu giá trị thật. Resolve lúc chạy qua `os.environ`. **Không log secret**. Show Code render `os.environ["VAR"]`, không lộ giá trị.
- **Không chạy code tuỳ ý**: user chỉ nhập **config khai báo + SQL** (chạy trong DuckDB). Python sinh ra **chỉ hiển thị, không `exec`**.
- **`dest_dir`** do user nhập (app local 1 user): kiểm tra thư mục cha tồn tại/ghi được trước khi xuất.
- `.env` không commit (đã trong `.gitignore`). `DISCORD_WEBHOOK_URL` + `SMTP_*` đọc qua `os.getenv`.

## 10. Testing Strategy — `backend/tests/test_automation.py` (pytest, hermetic)
- **rest**: mock httpx → phân trang lặp & dừng khi rỗng; retry 5xx; **không** retry 4xx; resolve `${VAR}`; timeout; `records_path` lồng.
- **ingest**: nạp page mẫu → DuckDB temp → đếm dòng `raw` đúng; nested giữ nguyên.
- **shape**: SQL mẫu → đúng bảng `data`; `shape_sql` rỗng → passthrough.
- **export**: mỗi format ra file & `.tmp` đã biến mất; guard xlsx skip khi vượt ngưỡng (test với ngưỡng nhỏ); `.duckdb` append cộng dồn dòng; 0 dòng → không tạo file.
- **notify**: mock webhook + SMTP → đúng format nội dung (success + failure); thiếu env → cảnh báo, không crash.
- **codegen**: script chứa lời gọi mong đợi + `compile()` hợp lệ cú pháp; không lộ secret (chỉ `os.environ[...]`).
- **runner**: end-to-end (mock source) → set status/rows/last_error; preview trả rows mà không export/notify.
- **store**: CRUD + `_migrate_v6` tạo bảng đúng (idempotent chạy 2 lần).

Bảo đảm hermetic: temp dir, DuckDB temp, mock network/SMTP.

## 11. Decisions Resolved (5 điểm chốt ở Phần 2)
1. **Run lâu** → chạy **nền** (`threading.Thread` daemon); `/run` trả `{status:"running"}`; UI **poll** `GET /jobs/{id}`. Chống chạy trùng qua `last_status='running'`.
2. **JSON lồng** → field **`records_path`** (vd `data.items`) trỏ tới mảng; record giữ nguyên nested.
3. **`.duckdb`** → radio mỗi job **`overwrite | append`**, mặc định **overwrite**.
4. **SMTP** → đọc từ **`.env`** (`SMTP_HOST/PORT/USER/PASS/FROM`), đồng bộ Discord.
5. **Email đính kèm** → `< 10MB` đính kèm, lớn hơn → ghi đường dẫn file.

## 12. Related (spec riêng, KHÔNG trong plan này)
- **ML Studio "Query failed"**: chuyển file lớn sang `.duckdb`/parquet **một lần lúc upload**, query thẳng store — dùng lại `ingest.py`/DuckDB của Automation. Sẽ là spec + plan riêng.
