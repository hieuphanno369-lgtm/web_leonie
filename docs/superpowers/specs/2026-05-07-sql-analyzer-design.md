# SQL Analyzer & Optimizer — Design Spec
Date: 2026-05-07

## Overview

Add a **SQL → Obsidian Note** section to the existing AI Tools tab in the Streamlit app. When a user pastes a SQL query, two independent AI features are available:

1. **Business Analyzer** — AI reads the query, generates a business-level description ("what question does this query answer?"), extracts metadata (tables, filters, tags, keywords), and saves a structured YAML-frontmatter markdown note to the Obsidian vault.
2. **SQL Optimizer** — AI reads the same query and suggests an optimized version with the same outcome, explaining each improvement in bullet points.

---

## Architecture

### New file: `modules/sql_analyzer.py`

Single responsibility: AI calls + file writing for SQL notes. Contains:

- `analyze_query(sql: str) -> dict` — calls AI, returns `{title, description, tables, filters, tags, keywords}`
- `optimize_query(sql: str) -> dict` — calls AI, returns `{explanation: list[str], optimized_sql: str}`
- `save_note(analysis: dict, sql: str) -> Path` — writes `.md` to vault, returns saved path
- `_slugify(text: str) -> str` — converts title to filename slug

Uses `_call_ai()` from `modules/ai_client.py` (existing, Claude → Ollama fallback).

### Modified file: `app.py`

Add `render_sql_analyzer_section()` function, called at the bottom of `render_ai_tab()` after a `st.divider()`.

### Vault output

- **Folder:** `D:\ai_brain\SQL Queries\` — auto-created on first save
- **Filename:** `YYYY-MM-DD_slug-from-title.md`

---

## YAML + Note Format

```markdown
---
title: Doanh thu theo sản phẩm tháng này
date: 2026-05-07
tags: [sql, revenue, product, monthly]
tables: [orders, products]
filters: [month = current, status = active]
keywords: [doanh_thu, san_pham, thang]
description: "Query này trả lời câu hỏi: Doanh thu của từng sản phẩm trong tháng hiện tại là bao nhiêu?"
---

## Business Question

Doanh thu của từng sản phẩm trong tháng hiện tại là bao nhiêu?

## SQL Query

```sql
SELECT ...
```

## Notes

_Tạo tự động bởi Task Tracker SQL Analyzer — 2026-05-07_
```

Obsidian Graph connections come from `tags` and `keywords` in frontmatter — compatible with Dataview plugin. `tables` field groups notes that share the same database tables.

---

## UI Layout (in AI Tools tab)

```
st.divider()
st.subheader("🔍 SQL → Obsidian Note")
st.caption("Paste SQL query — AI phân tích business intent và gợi ý tối ưu.")

[text_area: SQL Query — key="sql_input"]

[col1: button "🔍 Phân tích"]    [col2: button "⚡ Optimize SQL"]

--- if st.session_state.sql_analysis ---
[expander "📄 Preview note" expanded=True]
  text_input: Title (editable)
  text_input: Tags (editable, comma-separated)
  text_input: Tables (editable)
  text_area: Business Description (editable)
  st.code: YAML + body preview (read-only)
  button "💾 Lưu vào Obsidian" → st.success with saved path

--- if st.session_state.sql_optimization ---
[expander "⚡ SQL được tối ưu" expanded=True]
  bullet list: improvement explanations
  st.code: optimized SQL (sql syntax highlight)
```

---

## Session State

| Key | Type | Purpose |
|-----|------|---------|
| `sql_analysis` | `dict \| None` | Result from analyze_query |
| `sql_optimization` | `dict \| None` | Result from optimize_query |

Both reset to `None` when user clears/changes the SQL input.

---

## AI Prompts

### Analyzer prompt
```
Phân tích SQL query sau và trả về JSON với các field:
- title: tên ngắn gọn mô tả mục đích query (tiếng Việt, max 60 ký tự)
- description: câu hỏi business mà query này trả lời (1 câu, tiếng Việt)
- tables: danh sách tên bảng được dùng (array)
- filters: danh sách điều kiện WHERE chính (array, dạng "column = value")
- tags: 3-5 từ khóa ngắn liên quan (array, tiếng Anh lowercase)
- keywords: 3-5 từ khóa tiếng Việt để link Obsidian graph (array)

Chỉ trả về JSON, không giải thích thêm.

SQL:
{sql}
```

### Optimizer prompt
```
Tối ưu SQL query sau. Giữ nguyên kết quả output (same columns, same rows).
Trả về JSON với:
- improvements: danh sách các điểm cải tiến (array of strings, tiếng Việt, mỗi item 1 câu)
- optimized_sql: câu query đã tối ưu (string)

Chỉ trả về JSON.

SQL:
{sql}
```

---

## Error Handling

- AI returns invalid JSON → show `st.error("AI trả về kết quả không hợp lệ, thử lại.")`, keep input
- Vault folder write fails → show `st.error("Không thể lưu file: {error}")`, do not clear state
- Empty SQL input → show `st.warning("Vui lòng nhập SQL query.")`, do not call AI

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `modules/sql_analyzer.py` | Create new |
| `app.py` | Add `render_sql_analyzer_section()` + session state init + call in `render_ai_tab()` |
| `GUIDE.md` | Update with SQL Analyzer section |
| `CLAUDE.md` | Update with new module description |

---

## Out of Scope

- Saving the optimizer result to Obsidian (user copies manually)
- SQL syntax validation before sending to AI
- Support for multiple queries at once
- Edit history / versioning of saved notes
