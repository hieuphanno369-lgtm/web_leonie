# Dictionary Tab — Design Spec
**Date:** 2026-05-10
**Project:** Chooper (Task Tracker)
**Status:** Approved — ready for implementation planning

---

## 1. Mục tiêu

Thêm tab **◈ DICTIONARY** vào app, đặt ngay trước tab **⊛ CONFIG**.

Tab này là "bản đồ" của toàn bộ web — phục vụ cả người mới join lẫn người đã dùng muốn tra cứu nhanh. Nhấn mạnh đặc biệt vào **Data Studio** vì đây là core của app.

---

## 2. Approach đã chọn

**Approach B — Index JSON + Markdown Content:**
- `docs/dictionary/index.json` chứa metadata (id, title, category, tags, parent)
- `docs/dictionary/content/vn/{id}.md` chứa nội dung tiếng Việt
- `docs/dictionary/content/en/{id}.md` chứa nội dung tiếng Anh (Phase 2)
- App load index → build search/filter → render `.md` được chọn

---

## 3. File Structure

```
docs/dictionary/
├── index.json
└── content/
    ├── vn/
    │   ├── 00_welcome.md
    │   ├── 01_data_studio.md
    │   ├── 01a_data_explorer.md
    │   ├── 01b_sql_obsidian.md
    │   ├── 01c_ml_studio.md         ← file chi tiết nhất
    │   ├── 01d_snippets.md
    │   ├── 02_tasks.md
    │   ├── 03_performance.md
    │   ├── 04_email.md
    │   ├── 05_focus.md
    │   ├── 06_pipeline.md
    │   ├── 07_notebook.md
    │   ├── 08_config.md
    │   ├── 90_glossary.md
    │   └── 91_shortcuts.md
    └── en/
        └── (cùng cấu trúc — thêm ở Phase 2)

modules/dictionary.py               ← render function mới
```

---

## 4. index.json Schema

```json
{
  "sections": [
    {
      "id": "00_welcome",
      "title": "◈ Welcome",
      "parent": null,
      "category": "core",
      "tags": ["overview", "map", "start"],
      "pinned": true
    },
    {
      "id": "01_data_studio",
      "title": "◈ Data Studio",
      "parent": null,
      "category": "core",
      "tags": ["data", "studio", "analysis", "root"],
      "pinned": true
    },
    {
      "id": "01a_data_explorer",
      "title": "· Data Explorer",
      "parent": "01_data_studio",
      "category": "core",
      "tags": ["csv", "excel", "parquet", "upload", "eda"],
      "pinned": false
    },
    {
      "id": "01b_sql_obsidian",
      "title": "· SQL → Obsidian",
      "parent": "01_data_studio",
      "category": "core",
      "tags": ["sql", "obsidian", "note", "analyze"],
      "pinned": false
    },
    {
      "id": "01c_ml_studio",
      "title": "· ⚗ ML Studio",
      "parent": "01_data_studio",
      "category": "ml",
      "tags": ["ml", "forecast", "cluster", "xgboost", "sarimax", "prophet", "kmeans", "random forest", "pipeline"],
      "pinned": true
    },
    {
      "id": "01d_snippets",
      "title": "· Snippets",
      "parent": "01_data_studio",
      "category": "core",
      "tags": ["sql", "snippet", "reuse"],
      "pinned": false
    },
    {
      "id": "02_tasks",
      "title": "⬡ Tasks",
      "parent": null,
      "category": "tools",
      "tags": ["task", "priority", "deadline", "checklist"],
      "pinned": false
    },
    {
      "id": "03_performance",
      "title": "◎ Performance",
      "parent": null,
      "category": "tools",
      "tags": ["analytics", "chart", "burndown", "tag"],
      "pinned": false
    },
    {
      "id": "04_email",
      "title": "◉ Email",
      "parent": null,
      "category": "tools",
      "tags": ["email", "outlook", "digest", "classify", "reply"],
      "pinned": false
    },
    {
      "id": "05_focus",
      "title": "⏱ Focus",
      "parent": null,
      "category": "tools",
      "tags": ["focus", "pomodoro", "timer", "deep work"],
      "pinned": false
    },
    {
      "id": "06_pipeline",
      "title": "◉ Pipeline",
      "parent": null,
      "category": "tools",
      "tags": ["pipeline", "scheduler", "discord", "monitor"],
      "pinned": false
    },
    {
      "id": "07_notebook",
      "title": "⬡ Notebook",
      "parent": null,
      "category": "tools",
      "tags": ["notebook", "python", "jupyter", "meeting notes"],
      "pinned": false
    },
    {
      "id": "08_config",
      "title": "⊛ Config",
      "parent": null,
      "category": "tools",
      "tags": ["config", "env", "settings", "api key"],
      "pinned": false
    },
    {
      "id": "90_glossary",
      "title": "📚 Glossary",
      "parent": null,
      "category": "ml",
      "tags": ["mape", "rmse", "silhouette", "ci", "confidence interval", "overfitting", "feature importance"],
      "pinned": false
    },
    {
      "id": "91_shortcuts",
      "title": "⌨ Shortcuts & Tips",
      "parent": null,
      "category": "tips",
      "tags": ["shortcut", "tip", "keyboard", "trick"],
      "pinned": false
    }
  ]
}
```

---

## 5. UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 [Search trong Dictionary...]               [VN] [EN]        │
│  Filter: [Tất cả] [Core] [ML] [Tools] [Tips]                    │
├──────────────────┬──────────────────────────────────────────────┤
│  NAV (22%)       │  CONTENT (78%)                               │
│                  │                                              │
│  ◈ Welcome       │  ## ⚗ ML Studio                             │
│  ▼ ◈ Data Studio │                                              │
│    · Explorer    │  > Dùng để làm gì?                          │
│    · SQL→Obsidian│  > Pipeline 8 bước                          │
│    · ML Studio ● │  > Các thuật toán                           │
│    · Snippets    │    └ XGBoost                                 │
│  ◆ Tasks         │    └ SARIMAX                                 │
│  ◎ Performance   │    └ Prophet                                 │
│  ◉ Email         │    └ KMeans                                  │
│  ⏱ Focus         │    └ Random Forest                          │
│  ◉ Pipeline      │                                              │
│  ⬡ Notebook      │  [bảng so sánh thuật toán]                  │
│  ⊛ Config        │  [ASCII pipeline flow]                      │
│  ────────────    │  [screenshot từng bước]                     │
│  📚 Glossary      │                                              │
│  ⌨ Shortcuts     │                                              │
└──────────────────┴──────────────────────────────────────────────┘
```

**Mặc định khi mở tab:**
- Load section `00_welcome`
- Data Studio node tự động expanded
- Filter = "Tất cả"

---

## 6. Session State

```python
st.session_state["lang"]              # "vn" | "en" — dùng chung cho Phase 2
st.session_state["dict_section"]      # id section đang xem, default "00_welcome"
st.session_state["dict_expanded"]     # dict {section_id: bool}, default {"01_data_studio": True}
st.session_state["dict_search"]       # string search hiện tại
st.session_state["dict_filter"]       # category filter hiện tại, default None
```

---

## 7. modules/dictionary.py — Interface

```python
def render_dictionary_tab() -> None:
    """Entry point từ app.py — render toàn bộ Dictionary tab."""

def _render_toolbar() -> tuple[str, str]:
    """Search bar + VN/EN toggle. Return (search_query, lang)."""

def _render_filter_chips(search_query: str) -> str:
    """Filter chips [Tất cả|Core|ML|Tools|Tips]. Return active_category."""

def _load_index() -> list[dict]:
    """Đọc docs/dictionary/index.json. Cache với st.cache_data."""

def _filter_sections(index: list, query: str, category: str) -> list[dict]:
    """Filter sections theo search query AND category. Return filtered list."""

def _render_nav(sections: list, expanded: dict) -> str:
    """Render nav tree bên trái. Return selected section_id."""

def _render_content(section_id: str, lang: str) -> None:
    """Load và render docs/dictionary/content/{lang}/{section_id}.md."""
```

---

## 8. Search & Filter Logic

**Search:** so sánh query với `title` + `tags` trong index.json (không đọc file .md).
**Filter:** so sánh `category` field.
**Kết hợp:** AND — cả hai điều kiện phải match.
**Kết quả 0:** hiển thị `"Không tìm thấy — thử: ml, forecast, task, email..."`

```python
def _filter_sections(index, query, category):
    results = []
    for s in index:
        match_search = (
            not query or
            query.lower() in s["title"].lower() or
            any(query.lower() in tag for tag in s["tags"])
        )
        match_category = (
            not category or
            s["category"] == category or
            s["id"] in CATEGORIES.get(category, [])
        )
        if match_search and match_category:
            results.append(s)
    return results
```

---

## 9. Nội dung từng .md file

### 00_welcome.md
- Bảng "Tôi muốn... → Vào đây" (8 dòng, 1 dòng/tab)
- Callout: "◈ Data Studio là trung tâm phân tích"
- Quick links tới các section hay dùng

### 01_data_studio.md
- Mô tả vai trò tổng quan
- Bảng 4 sub-view: tên · dùng khi nào · output là gì

### 01c_ml_studio.md *(file dài nhất)*
Cấu trúc:
1. **ML Studio là gì?** — giải thích như cho trẻ con, dùng analogy
2. **Pipeline 8 bước** — ASCII flow + bảng (bước | tên | bạn làm gì | app làm gì)
3. **Các thuật toán** — mỗi thuật toán có:
   - Analogy dễ hiểu (2-3 câu)
   - Dùng khi nào
   - Input cần gì
   - Output là gì
4. **Bảng chọn thuật toán** — "Câu hỏi của bạn → Dùng cái này"
5. **Link → Glossary** cho các chỉ số đánh giá

Thuật toán cần cover: XGBoost · Random Forest · SARIMAX · Prophet · KMeans

### 90_glossary.md
Bảng: Thuật ngữ | Nghĩa đơn giản
Cover: MAPE · RMSE · Silhouette Score · CI · Overfitting · Feature Importance

### 91_shortcuts.md
- Tips hay dùng theo từng tab (bullet points)
- Bảng phím tắt Streamlit

---

## 10. VN/EN Toggle — Phân kỳ

**Phase 1 (build cùng Dictionary):**
- Toggle button trong Dictionary tab, góc phải toolbar
- Chỉ affect nội dung `.md` của Dictionary
- State: `st.session_state["lang"]`
- Folder `en/` tạo sẵn, content để trống — không crash khi toggle (fallback về `vn/`)

**Phase 2 (feature riêng, sau này):**
- Move toggle lên top bar toàn app (ngang global search)
- Externalize UI strings vào `i18n/vn.json` + `i18n/en.json`
- Bind `session_state["lang"]` vào toàn bộ labels

---

## 11. app.py Changes

```python
# Thêm tab DICTIONARY trước CONFIG
(tab_data, tab_tasks, tab_perf, tab_email, tab_focus,
 tab_pipeline, tab_nb, tab_dict, tab_settings) = st.tabs([
    "◈ DATA STUDIO",
    "⬡ TASKS",
    "◎ PERFORMANCE",
    "◉ EMAIL",
    "⏱ FOCUS",
    "◉ PIPELINE",
    "⬡ NOTEBOOK",
    "◈ DICTIONARY",    # ← mới
    "⊛ CONFIG",
])

with tab_dict:
    from modules.dictionary import render_dictionary_tab
    render_dictionary_tab()
```

---

## 12. Out of Scope (không làm trong sprint này)

- VN/EN toggle cho toàn bộ app (Phase 2)
- Edit `.md` trực tiếp trong UI
- Version history / changelog tab
- Auto-generate Dictionary content từ code docstrings

---

## 13. Definition of Done

- [ ] `docs/dictionary/index.json` tạo xong với 15 sections
- [ ] Tất cả `.md` files trong `docs/dictionary/content/vn/` có nội dung
- [ ] `modules/dictionary.py` render đúng layout 2 cột
- [ ] Search real-time hoạt động (filter theo title + tags)
- [ ] Filter chips hoạt động (AND với search)
- [ ] Nav tree: Data Studio expanded mặc định, click section load đúng content
- [ ] VN/EN toggle: button hiển thị, fallback về vn/ nếu en/ chưa có
- [ ] Tab DICTIONARY xuất hiện đúng vị trí trong app (trước CONFIG)
- [ ] Không có lỗi khi section `.md` chưa tồn tại (graceful fallback)
