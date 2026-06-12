# Project Log — Design Spec
**Date:** 2026-05-15  
**Author:** Leonie (VitaDairy DA)  
**Status:** Approved by user  

---

## Overview

Add a **📂 Project Log** feature to the NOTEBOOK tab in the Task Tracker Streamlit app. This gives the user a structured daily work journal per project, with AI-generated SOP and reusable template when a project is marked done.

**Goal:** Replace ad-hoc note-taking with a persistent, structured log that produces a shareable framework teammates can follow.

---

## Scope

- Solo user (no multi-user, no auth)
- Supports 2 project types: one-time (deadline-bound) and recurring (periodic)
- Files stored locally at `D:\claude-workspace\07_Outputs\On-going\<project_title>\`
- AI uses existing `modules/ai_client.py` (`call_ai()`)
- Output (SOP + template) saved to `07_Outputs\`
- No changes to existing modules (`meeting_notes.py`, `ai_client.py`, `discord_notifier.py`)

---

## Data Model

**File:** `data/project_logs.json` (auto-created on first save, same pattern as `meeting_notes.json`)

```json
[
  {
    "id": "abc12345",
    "title": "Campaign Tết 2026",
    "type": "one-time",
    "recur_pattern": null,
    "status": "active",
    "goal": "Tăng GMV ColosBaby 20% trong T01",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "progress": 45,
    "milestones": [
      {"label": "Brief approved", "done": true,  "date": "2026-01-03"},
      {"label": "Assets ready",   "done": false, "date": "2026-01-10"}
    ],
    "entries": [
      {
        "entry_id": "e001",
        "date": "2026-01-05",
        "type": "daily",
        "content": "Hoàn thành brief với agency",
        "files": [
          {"name": "brief_v1.pdf", "path": "07_Outputs/On-going/Campaign_Tet/brief_v1.pdf"},
          {"name": "Ref deck",     "url": "https://drive.google.com/..."}
        ]
      }
    ],
    "sop_path": null,
    "template_path": null,
    "created_at": "2026-01-01T08:00:00",
    "done_at": null
  }
]
```

**Field rules:**
- `type`: `"one-time"` | `"recurring"`
- `recur_pattern`: `null` | `"weekly"` | `"monthly"` | `"quarterly"` (only for recurring)
- `status`: `"active"` | `"done"` | `"paused"`
- `entries[].type`: `"daily"` | `"decision"`
- `entries[].files[].path`: local file path (relative to workspace root)
- `entries[].files[].url`: external URL (Google Drive, SharePoint, etc.) — mutually exclusive with `path`
- `sop_path` / `template_path`: filled by AI generate step; relative to `07_Outputs\`

---

## File & Folder Structure

```
task-tracker/
  modules/
    project_log.py          # NEW
  data/
    project_logs.json       # NEW (auto-created)
  docs/superpowers/specs/
    2026-05-15-project-log-design.md  # this file

D:\claude-workspace\
  07_Outputs\
    On-going\               # NEW folder
      <project_title>\      # one subfolder per project (spaces → underscores)
        <uploaded_files>
    <done project SOP/template files live at 07_Outputs\ root level>
```

---

## Module: `modules/project_log.py`

### Function groups

**CRUD**
```python
load_projects() -> list[dict]
add_project(title, type_, goal, start_date, end_date, recur_pattern) -> dict
update_project(project_id, **fields) -> dict
delete_project(project_id) -> None
```

**Entries**
```python
add_entry(project_id, entry_type, content, files: list[dict]) -> dict
# entry_type: "daily" | "decision"
# files: [{"name": str, "path": str} | {"name": str, "url": str}]
```

**Progress**
```python
update_progress(project_id, pct: int, milestones: list[dict]) -> None
```

**File handling**
```python
save_attachment(project_id, uploaded_file) -> str
# Copies file to 07_Outputs\On-going\<project_title>\
# Returns relative path string
```

**AI Generate (called on Mark as Done)**
```python
generate_sop_and_template(project: dict) -> tuple[str, str]
# Returns (sop_markdown, template_markdown)
# Internally calls ai_client.call_ai()

save_outputs(project_id, sop_md, template_md) -> tuple[str, str]
# Saves both files to 07_Outputs\
# Returns (sop_path, template_path)
# Updates project record: sop_path, template_path, status="done", done_at=now
```

**Recurring helper**
```python
clone_for_next_cycle(project: dict) -> dict
# Creates new project record: same title/goal/milestones, entries=[], status="active"
# Called automatically after save_outputs() if type == "recurring"
```

### AI prompt template (inside `generate_sop_and_template`)

```
Bạn là một DA senior tại VitaDairy. Dưới đây là toàn bộ log của project "{title}".
Mục tiêu ban đầu: {goal}
Thời gian: {start_date} → {done_at}

=== DAILY LOG ===
{entries_daily}

=== DECISION LOG ===
{entries_decision}

=== FILE ĐÍNH KÈM ===
{file_list}

Hãy tạo ra 2 phần:

**PHẦN 1 — SOP (Standard Operating Procedure)**
Viết quy trình từng bước theo trình tự thời gian thực tế.
Mỗi bước: Tên bước | Mô tả | Người/team thực hiện | Output cụ thể.
Kèm "Bài học kinh nghiệm" ở cuối.

**PHẦN 2 — TEMPLATE (Khung trống để dùng lại)**
Giữ đúng cấu trúc của SOP nhưng:
- Thay số liệu cụ thể bằng [PLACEHOLDER]
- Thay tên người/brand bằng [TÊN NGƯỜI THỰC HIỆN] / [TÊN BRAND]
- Thay ngày bằng [DD/MM] hoặc [TUẦN N]
Mục tiêu: ai cũng có thể điền vào và chạy lại project tương tự.
```

---

## UI Design

### Banner (hiện đầu NOTEBOOK tab khi có project active)

```
┌───────────────────────────────────────────────────────┐
│ 🟡 ĐANG ACTIVE: Campaign Tết 2026  ████░░░░ 45%       │
│ Cập nhật cuối: 05/01 · 3 entries · 2 files  [→ Mở]   │
└───────────────────────────────────────────────────────┘
```

- Shows only if ≥1 project with `status == "active"`
- If multiple active: show the most recently updated
- "→ Mở" button switches radio to "📂 Project Log"

### Project Log tab layout

```
[ + Tạo project mới ]   Đang active: 2  |  Done: 1
──────────────────────────────────────────────────────
▼ Campaign Tết 2026  [🟡 active]  ████░░ 45%  → 31/01
  Milestone: ✅ Brief approved  ⬜ Assets ready (10/01)
  ─ [ + Ghi hôm nay ]  [ + Decision ]  [ 📎 Thêm file ]
  ─ 05/01 DAILY   "Hoàn thành brief với agency"
  ─ 04/01 DECISION "Chọn agency X thay Y vì ngân sách"
  [ ⚑ Mark as Done ]  [ ⏸ Pause ]  [ 🗑 Xóa ]

▼ Báo cáo tháng  [🔄 recurring: monthly]  ...
──────────────────────────────────────────────────────
```

### Form: Tạo project mới (expandable)

```
Tên project*:     [______________________________]
Loại:             ● One-time  ○ Recurring
Chu kỳ (nếu R):  [ weekly / monthly / quarterly ]
Mục tiêu:        [text area]
Ngày bắt đầu:    [date picker]
Ngày kết thúc:   [date picker]  (hidden if recurring)
Milestones:      [+ Thêm milestone] rows: label + date
[ 💾 Tạo project ]
```

### Form: Ghi entry (inline expandable per project)

```
Type:     ● Daily log  ○ Decision log
Nội dung: [text area — required]
File:     [📁 Upload file]  hoặc  [🔗 Paste URL _____]
          (tên hiển thị) [___________]
[ 💾 Lưu entry ]
```

### Mark as Done flow

```
1. User clicks [ ⚑ Mark as Done ]
2. Confirm dialog: "Done project này? AI sẽ tự tạo SOP + Template."
3. Spinner: "🤖 AI đang đọc log và tạo SOP..."
4. Show preview:
   ├─ Expander: "📄 SOP Preview" (first 500 chars + "...")
   └─ Expander: "📋 Template Preview" (first 500 chars + "...")
5. [ 💾 Lưu vào 07_Outputs/ ]   [ ↩ Quay lại ]
6. On save:
   - Write SOP to: 07_Outputs\<title>_SOP_<YYYY-MM-DD>.md
   - Write template to: 07_Outputs\<title>_TEMPLATE_<YYYY-MM-DD>.md
   - Update project: status="done", sop_path, template_path, done_at
   - If recurring: clone_for_next_cycle() → new active project created
   - Show success: "✅ Đã lưu. [Mở SOP] [Mở Template]"
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `data/project_logs.json` missing | Auto-create on first `add_project()` |
| `07_Outputs\On-going\` missing | Auto-create on first `save_attachment()` |
| AI call fails | Show error in spinner area: "⚠ AI lỗi: {e}. Thử lại?" — project stays active |
| File upload > 10MB | Warn user, suggest paste URL instead |
| `end_date` < `start_date` | Validation error on form submit |
| Delete project with files | Delete record only; leave files on disk (safe) |

---

## Out of Scope (này không làm)

- Multi-user / sharing live in the app
- Discord notification for project reminders (banner in-app is enough for now)
- Obsidian integration for SOP output
- In-app file viewer/editor
- Search across project logs
