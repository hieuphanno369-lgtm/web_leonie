# SP2 Remaining Features — Design Spec
**Date:** 2026-05-18
**Status:** Approved
**Sprint:** SP2 (completion)

---

## Overview

Ba tính năng SP2 còn placeholder: EDA Tracker, WIP Builder, Discord Notify. Mỗi tính năng độc lập, build lần lượt trong cùng một sprint.

---

## Feature 1: EDA Tracker

### Purpose
Track các analysis request (EDA) từ stakeholder — status, requester, dataset, deadline.

### Data Model

Bảng mới `eda_requests` trong `backend/database.py`:

```sql
eda_requests (
  id        TEXT PK  -- hex random 8 bytes
  title     TEXT NOT NULL
  requester TEXT NOT NULL
  dataset   TEXT NOT NULL
  priority  TEXT     -- 'low' | 'medium' | 'high'
  status    TEXT     -- 'todo' | 'in_progress' | 'done'
  due_date  TEXT     -- ISO date string, nullable
  notes     TEXT     -- nullable
  created   TEXT
  updated   TEXT
)
```

### API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/eda` | List all (filter by `status`) |
| POST | `/eda` | Create new request |
| GET | `/eda/{id}` | Get single |
| PATCH | `/eda/{id}` | Partial update |
| DELETE | `/eda/{id}` | Delete |

### Frontend Components

**`pages/work/EDATracker.tsx`** — root page, state: `requests[]`, `selectedId`, `mode` (`view|create|edit`)

**`components/eda/EDAList.tsx`** — filter tabs (All/Todo/In Progress/Done) + search + scrollable list (340px fixed)

**`components/eda/EDAItem.tsx`** — row: title, requester, priority badge, due date

**`components/eda/EDADetail.tsx`** — chips (status, priority, due date) + requester + dataset + notes + Edit/Delete (2-click confirm)

**`components/eda/EDAForm.tsx`** — fields: title (required), requester (required), dataset (required), priority, status, due_date, notes

**`api/eda.ts`** — `fetchEDA(status?)`, `createEDA(body)`, `updateEDA(id, body)`, `deleteEDA(id)`

### Layout
List + Detail Panel — giống Task Manager (340px trái + flex-1 phải). Không dùng modal.

---

## Feature 2: WIP Builder

### Purpose
Track tiến độ từng task đang làm dở (work-in-progress), gắn với Task Manager task, có daily log.

### Data Model

Hai bảng mới trong `backend/database.py`:

```sql
wip_items (
  id        TEXT PK
  task_id   TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE
  progress  INTEGER NOT NULL DEFAULT 0  -- 0-100
  created   TEXT
  updated   TEXT
)

wip_logs (
  id        TEXT PK
  wip_id    TEXT NOT NULL REFERENCES wip_items(id) ON DELETE CASCADE
  date      TEXT NOT NULL  -- ISO date string (YYYY-MM-DD)
  note      TEXT NOT NULL
  created   TEXT
)
```

### API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/wip` | List all WIP items (join task title) |
| POST | `/wip` | Create (body: task_id, progress) |
| GET | `/wip/{id}` | Get WIP + logs |
| PATCH | `/wip/{id}` | Update progress |
| DELETE | `/wip/{id}` | Delete WIP + cascade logs |
| GET | `/wip/{id}/logs` | List logs (newest first) |
| POST | `/wip/{id}/logs` | Add log entry (body: date, note) |
| DELETE | `/wip/{wip_id}/logs/{log_id}` | Delete log entry |

GET `/wip` response includes `task_title` (joined from `tasks`).

### Frontend Components

**`pages/work/WipBuilder.tsx`** — root page, state: `wips[]`, `selectedId`, `mode` (`view|create`)

**`components/wip/WIPList.tsx`** — list trái 340px; mỗi item: task title + progress bar màu động:
- < 70%: màu `data` (#60a5fa / xanh dương)
- 70–99%: màu `warning` (#fbbf24 / vàng)
- 100%: màu `work` (#34d399 / xanh lá)

**`components/wip/WIPItem.tsx`** — row: task title + mini progress bar + % number

**`components/wip/WIPDetail.tsx`** — panel phải:
- Header: task title + link sang Task Manager (highlight task tương ứng)
- Progress slider (0–100) + số %; PATCH ngay khi thả slider (`onMouseUp`)
- Nút "+ Add Log" mở inline text input (date tự điền hôm nay, note free text) → POST log
- Timeline log entries: mới nhất trên đầu, mỗi entry có date + note + nút xoá

**`components/wip/WIPForm.tsx`** — tạo WIP mới: dropdown chọn task (fetch từ `/tasks`) + progress slider initial (default 0)

**`api/wip.ts`** — `fetchWIPs()`, `createWIP(body)`, `updateWIPProgress(id, progress)`, `deleteWIP(id)`, `fetchLogs(wip_id)`, `addLog(wip_id, body)`, `deleteLog(wip_id, log_id)`

### Interactions

| Action | Behaviour |
|--------|-----------|
| Click WIP row | Show detail panel phải |
| Move slider | Update % live; PATCH on `onMouseUp` |
| "+ Add Log" | Inline input xuất hiện dưới timeline; Enter hoặc nút Save → POST |
| Delete log | Nút nhỏ bên cạnh entry, xoá ngay (không confirm) |
| "+ New WIP" | Panel phải → WIPForm |
| Task bị xoá | WIP tự xoá theo CASCADE — không cần handle orphan |

---

## Feature 3: Discord Notify

### Purpose
Gửi webhook notification lên Discord — manual (soạn tự do) và auto (trigger theo event từ Task Manager).

### Data Model

Một bảng mới trong `backend/database.py`:

```sql
discord_settings (
  id            INTEGER PK DEFAULT 1  -- singleton row
  webhook_url   TEXT
  rule_overdue  INTEGER DEFAULT 1     -- 0|1 boolean
  rule_done     INTEGER DEFAULT 0
  rule_summary  INTEGER DEFAULT 0
  last_checked  TEXT                  -- ISO datetime, tránh spam
)
```

### API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/discord/settings` | Lấy settings (tạo row mặc định nếu chưa có) |
| POST | `/discord/settings` | Upsert webhook URL + rules |
| POST | `/discord/send` | Gửi message thủ công (body: `{message: str}`) |
| POST | `/discord/check` | Kiểm tra auto rules → gửi nếu trigger |

**Logic `/discord/check`:**
1. Lấy settings; nếu không có `webhook_url` → trả lỗi 400
2. Nếu `rule_overdue=1`: query `tasks WHERE due_date < today AND status != 'done'` → gửi 1 message tổng hợp danh sách
3. Nếu `rule_done=1`: query `tasks WHERE status = 'done' AND updated >= last_checked` → gửi notify từng task Done mới
4. Update `last_checked = datetime('now')`
5. Trả về `{sent: N}` — số message đã gửi

### Frontend — `pages/work/DiscordNotify.tsx`

3 tabs:

**Tab Manual:**
- Textarea soạn message (placeholder: "Nhập nội dung notification...")
- Dropdown chọn tag prefix: `✅ Done` / `⚠️ Alert` / `📊 Report` / `(none)`
- Nút "Send to Discord" → POST `/discord/send`; show "Sent!" inline hoặc error

**Tab Auto Rules:**
- Toggle switch cho 3 rules: "Task overdue", "Status → Done", "Daily summary"
- Mỗi toggle PATCH `/discord/settings` ngay
- Khi vào tab này → auto gọi POST `/discord/check` nếu webhook đã set
- Show timestamp `Last checked: HH:mm DD/MM`

**Tab Settings:**
- Input webhook URL + nút Save
- Nút "Test" → gửi message `"🔔 Leonie webhook test — OK"` qua `/discord/send`
- Warning nếu chưa set webhook khi dùng tab khác

### Error Handling
- Webhook call fail (Discord trả lỗi) → backend trả 502 với message gốc từ Discord
- Chưa set webhook → 400 "Webhook URL not configured"
- Frontend hiển thị error inline (không dùng toast)

---

## Files to Create / Modify

```
backend/
  database.py           ← MODIFY: thêm 4 bảng mới (eda_requests, wip_items, wip_logs, discord_settings)
  routers/
    eda.py              ← NEW: EDA CRUD endpoints
    wip.py              ← NEW: WIP + logs endpoints
    discord_notify.py   ← NEW: send + check + settings
  main.py               ← MODIFY: include 3 routers mới
  tests/
    test_eda.py         ← NEW
    test_wip.py         ← NEW
    test_discord.py     ← NEW

frontend/src/
  api/
    eda.ts              ← NEW
    wip.ts              ← NEW
    discord.ts          ← NEW
  components/
    eda/
      EDAList.tsx       ← NEW
      EDAItem.tsx       ← NEW
      EDADetail.tsx     ← NEW
      EDAForm.tsx       ← NEW
    wip/
      WIPList.tsx       ← NEW
      WIPItem.tsx       ← NEW
      WIPDetail.tsx     ← NEW
      WIPForm.tsx       ← NEW
  pages/work/
    EDATracker.tsx      ← REPLACE placeholder
    WipBuilder.tsx      ← REPLACE placeholder
    DiscordNotify.tsx   ← REPLACE placeholder
```

---

## Out of Scope

- EDA Tracker: attachment upload, multi-assignee
- WIP Builder: sub-steps / checklist bên trong WIP, progress history chart
- Discord Notify: multi-channel, scheduled daily summary (cần cron backend), read Discord messages
