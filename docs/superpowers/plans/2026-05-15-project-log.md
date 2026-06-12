# Project Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 📂 Project Log feature to the NOTEBOOK tab — a per-project daily work journal with AI-generated SOP and reusable template on completion.

**Architecture:** New `modules/project_log.py` handles all data logic (CRUD, entries, file copy, AI generate). App.py adds a third radio option to the NOTEBOOK tab plus a banner for active projects. Data persists in `data/project_logs.json` following the same pattern as `meeting_notes.json`. Files attach to `D:\claude-workspace\07_Outputs\On-going\<project_title>\`.

**Tech Stack:** Python 3.11, Streamlit 1.57, pytest, `modules/ai_client.py` (`call_ai()`), `pathlib.Path`, `json`, `uuid`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `modules/project_log.py` | All data logic: CRUD, entries, file copy, AI generate |
| Create | `tests/test_project_log.py` | Unit tests for project_log.py |
| Modify | `app.py:1766` | Add "📂 Project Log" radio option |
| Modify | `app.py:1764` | Update subtitle to include "project log" |
| Modify | `app.py:1867` | Add banner + Project Log UI block after Meeting Notes |
| Create | `D:\claude-workspace\07_Outputs\On-going\` | File attachment storage (created by code) |

---

## Task 1: CRUD layer — load / add / update / delete

**Files:**
- Create: `modules/project_log.py`
- Create: `tests/test_project_log.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_project_log.py`:

```python
import json
import pytest
from pathlib import Path


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_data_path(tmp_path, monkeypatch):
    """Redirect DATA_PATH to a temp file so tests don't touch real data."""
    import modules.project_log as pl
    monkeypatch.setattr(pl, "DATA_PATH", tmp_path / "project_logs.json")
    monkeypatch.setattr(pl, "OUTPUTS_ONGOING", tmp_path / "On-going")
    monkeypatch.setattr(pl, "OUTPUTS_ROOT", tmp_path / "07_Outputs")


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_load_projects_returns_empty_when_no_file():
    from modules.project_log import load_projects
    result = load_projects()
    assert result == []


def test_add_project_creates_file_and_returns_dict():
    from modules.project_log import add_project, load_projects
    p = add_project(
        title="Test Project",
        type_="one-time",
        goal="Test goal",
        start_date="2026-01-01",
        end_date="2026-01-31",
    )
    assert p["title"] == "Test Project"
    assert p["type"] == "one-time"
    assert p["status"] == "active"
    assert p["progress"] == 0
    assert p["entries"] == []
    assert len(p["id"]) == 8
    assert load_projects() == [p]


def test_add_project_recurring_stores_pattern():
    from modules.project_log import add_project
    p = add_project(
        title="Monthly Report",
        type_="recurring",
        goal="Monthly summary",
        start_date="2026-01-01",
        recur_pattern="monthly",
    )
    assert p["recur_pattern"] == "monthly"
    assert p["end_date"] is None


def test_update_project_modifies_fields():
    from modules.project_log import add_project, update_project
    p = add_project("Proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
    updated = update_project(p["id"], status="paused", progress=50)
    assert updated["status"] == "paused"
    assert updated["progress"] == 50


def test_update_project_raises_on_missing_id():
    from modules.project_log import update_project
    with pytest.raises(ValueError, match="not found"):
        update_project("nonexistent", status="done")


def test_delete_project_removes_record():
    from modules.project_log import add_project, delete_project, load_projects
    p = add_project("Del me", "one-time", "Goal", "2026-01-01", "2026-01-31")
    delete_project(p["id"])
    assert load_projects() == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd D:\claude-workspace\08_Projects\task-tracker
.venv\Scripts\python.exe -m pytest tests/test_project_log.py -v
```

Expected: ImportError or ModuleNotFoundError (module doesn't exist yet).

- [ ] **Step 3: Create `modules/project_log.py` with CRUD layer**

```python
"""modules/project_log.py — Project Log data layer."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_PATH      = Path("data/project_logs.json")
OUTPUTS_ONGOING = Path(r"D:\claude-workspace\07_Outputs\On-going")
OUTPUTS_ROOT    = Path(r"D:\claude-workspace\07_Outputs")


# ── private helpers ───────────────────────────────────────────────────────────

def _save(projects: list[dict]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(projects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

def load_projects() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def add_project(
    title: str,
    type_: str,
    goal: str,
    start_date: str,
    end_date: str | None = None,
    recur_pattern: str | None = None,
) -> dict:
    projects = load_projects()
    project: dict = {
        "id":            uuid.uuid4().hex[:8],
        "title":         title,
        "type":          type_,          # "one-time" | "recurring"
        "recur_pattern": recur_pattern,  # "weekly" | "monthly" | "quarterly" | None
        "status":        "active",       # "active" | "paused" | "done"
        "goal":          goal,
        "start_date":    start_date,
        "end_date":      end_date,
        "progress":      0,
        "milestones":    [],
        "entries":       [],
        "sop_path":      None,
        "template_path": None,
        "created_at":    datetime.now().isoformat(),
        "done_at":       None,
    }
    projects.append(project)
    _save(projects)
    return project


def update_project(project_id: str, **fields) -> dict:
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            p.update(fields)
            _save(projects)
            return p
    raise ValueError(f"Project {project_id!r} not found")


def delete_project(project_id: str) -> None:
    _save([p for p in load_projects() if p["id"] != project_id])
```

- [ ] **Step 4: Run tests — expect all CRUD tests to pass**

```
.venv\Scripts\python.exe -m pytest tests/test_project_log.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```
git add modules/project_log.py tests/test_project_log.py
git commit -m "feat: add project_log CRUD layer"
```

---

## Task 2: Entries + file attachment

**Files:**
- Modify: `modules/project_log.py`
- Modify: `tests/test_project_log.py`

- [ ] **Step 1: Add failing tests for entries and file attachment**

Append to `tests/test_project_log.py`:

```python
# ── Entries ───────────────────────────────────────────────────────────────────

def test_add_entry_appends_to_project():
    from modules.project_log import add_project, add_entry, load_projects
    p = add_project("E-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
    entry = add_entry(p["id"], "daily", "Finished brief")
    projects = load_projects()
    assert projects[0]["entries"] == [entry]
    assert entry["type"] == "daily"
    assert entry["content"] == "Finished brief"
    assert entry["files"] == []


def test_add_entry_decision_type():
    from modules.project_log import add_project, add_entry
    p = add_project("D-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
    entry = add_entry(p["id"], "decision", "Switched agency", files=[{"name": "brief.pdf", "url": "https://example.com"}])
    assert entry["type"] == "decision"
    assert entry["files"][0]["name"] == "brief.pdf"


def test_add_entry_raises_on_missing_project():
    from modules.project_log import add_entry
    with pytest.raises(ValueError, match="not found"):
        add_entry("bad_id", "daily", "content")


# ── Progress ──────────────────────────────────────────────────────────────────

def test_update_progress_sets_pct_and_milestones():
    from modules.project_log import add_project, update_progress, load_projects
    p = add_project("P-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
    milestones = [{"label": "Brief done", "done": True, "date": "2026-01-03"}]
    update_progress(p["id"], 60, milestones)
    saved = load_projects()[0]
    assert saved["progress"] == 60
    assert saved["milestones"] == milestones


# ── File attachment ───────────────────────────────────────────────────────────

def test_save_attachment_copies_file(tmp_path):
    from modules.project_log import add_project, save_attachment
    p = add_project("FA-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")

    # Simulate Streamlit UploadedFile with .name and .getbuffer()
    class FakeUpload:
        name = "doc.pdf"
        def getbuffer(self):
            return b"PDF content"

    dest_path = save_attachment(p["id"], FakeUpload())
    assert Path(dest_path).exists()
    assert Path(dest_path).read_bytes() == b"PDF content"
    assert "FA_proj" in dest_path or "FA-proj" in dest_path
```

- [ ] **Step 2: Run tests to confirm they fail**

```
.venv\Scripts\python.exe -m pytest tests/test_project_log.py -v
```

Expected: 5 new tests FAIL with AttributeError (functions not defined yet).

- [ ] **Step 3: Add `add_entry`, `update_progress`, `save_attachment` to `modules/project_log.py`**

Append to the bottom of `modules/project_log.py`:

```python
# ── Entries ───────────────────────────────────────────────────────────────────

def add_entry(
    project_id: str,
    entry_type: str,
    content: str,
    files: list[dict] | None = None,
) -> dict:
    """entry_type: 'daily' | 'decision'"""
    entry: dict = {
        "entry_id": uuid.uuid4().hex[:8],
        "date":     datetime.now().strftime("%Y-%m-%d"),
        "type":     entry_type,
        "content":  content,
        "files":    files or [],
    }
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            p["entries"].append(entry)
            _save(projects)
            return entry
    raise ValueError(f"Project {project_id!r} not found")


# ── Progress ──────────────────────────────────────────────────────────────────

def update_progress(project_id: str, pct: int, milestones: list[dict]) -> None:
    """pct: 0–100. milestones: [{"label": str, "done": bool, "date": str}]"""
    update_project(project_id, progress=pct, milestones=milestones)


# ── File attachment ───────────────────────────────────────────────────────────

def _safe_name(title: str) -> str:
    return title.replace(" ", "_").replace("/", "_").replace("\\", "_")


def save_attachment(project_id: str, uploaded_file) -> str:
    """Copy Streamlit UploadedFile to OUTPUTS_ONGOING/<project_title>/. Returns dest path str."""
    projects = load_projects()
    title = next((p["title"] for p in projects if p["id"] == project_id), project_id)
    dest_dir = OUTPUTS_ONGOING / _safe_name(title)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / uploaded_file.name
    dest.write_bytes(uploaded_file.getbuffer())
    return str(dest)
```

- [ ] **Step 4: Run tests — all 11 tests should pass**

```
.venv\Scripts\python.exe -m pytest tests/test_project_log.py -v
```

Expected: 11 tests PASS.

- [ ] **Step 5: Commit**

```
git add modules/project_log.py tests/test_project_log.py
git commit -m "feat: add project_log entries, progress, file attachment"
```

---

## Task 3: AI generate — SOP + template + Done flow

**Files:**
- Modify: `modules/project_log.py`
- Modify: `tests/test_project_log.py`

- [ ] **Step 1: Add failing tests for generate + save + clone**

Append to `tests/test_project_log.py`:

```python
# ── AI Generate ───────────────────────────────────────────────────────────────

def test_generate_sop_calls_ai_and_splits_output():
    from unittest.mock import patch
    from modules.project_log import add_project, add_entry, generate_sop_and_template

    p = add_project("AI-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
    add_entry(p["id"], "daily", "Did stuff")
    add_entry(p["id"], "decision", "Chose option A")

    fake_response = "PHẦN 1 — SOP\nStep 1: do this\nPHẦN 2\nTEMPLATE\n[PLACEHOLDER]"
    with patch("modules.project_log.call_ai", return_value=fake_response):
        from modules.project_log import load_projects
        project = load_projects()[0]
        sop, template = generate_sop_and_template(project)

    assert "PHẦN 1" in sop or "SOP" in sop
    assert "PHẦN 2" in template or "TEMPLATE" in template


def test_save_outputs_writes_files_and_updates_project():
    from unittest.mock import patch
    from modules.project_log import add_project, save_outputs, load_projects

    p = add_project("Save-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
    with patch("modules.project_log.call_ai", return_value="PHẦN 1 sop\nPHẦN 2\ntemplate"):
        sop_path, tmpl_path = save_outputs(p["id"], "# SOP content", "# Template content")

    assert Path(sop_path).exists()
    assert Path(tmpl_path).exists()
    assert "SOP content" in Path(sop_path).read_text(encoding="utf-8")
    saved = load_projects()[0]
    assert saved["status"] == "done"
    assert saved["sop_path"] == sop_path
    assert saved["template_path"] == tmpl_path
    assert saved["done_at"] is not None


def test_clone_for_next_cycle_creates_new_active_project():
    from modules.project_log import add_project, clone_for_next_cycle, load_projects

    p = add_project("Recurring", "recurring", "Goal", "2026-01-01", recur_pattern="monthly")
    clone = clone_for_next_cycle(p)

    projects = load_projects()
    assert len(projects) == 2
    assert clone["title"] == "Recurring"
    assert clone["status"] == "active"
    assert clone["entries"] == []
    assert clone["recur_pattern"] == "monthly"
    assert clone["id"] != p["id"]
```

- [ ] **Step 2: Run tests to confirm they fail**

```
.venv\Scripts\python.exe -m pytest tests/test_project_log.py -v -k "generate or save_outputs or clone"
```

Expected: 3 new tests FAIL.

- [ ] **Step 3: Add generate / save_outputs / clone to `modules/project_log.py`**

Append to the bottom of `modules/project_log.py`:

```python
# ── AI Generate ───────────────────────────────────────────────────────────────

def _build_prompt(project: dict) -> str:
    def fmt_entries(type_: str) -> str:
        lines = [
            f"[{e['date']}] {e['content']}"
            for e in project["entries"] if e["type"] == type_
        ]
        return "\n".join(lines) if lines else "(không có)"

    file_lines = [
        f"- {f.get('name', '')}: {f.get('path', f.get('url', ''))}"
        for e in project["entries"]
        for f in e.get("files", [])
    ]
    file_list = "\n".join(file_lines) if file_lines else "(không có)"

    return (
        f'Bạn là một DA senior tại VitaDairy. Dưới đây là toàn bộ log của project "{project["title"]}".\n'
        f'Mục tiêu ban đầu: {project["goal"]}\n'
        f'Thời gian: {project["start_date"]} → {project.get("done_at") or "nay"}\n\n'
        f'=== DAILY LOG ===\n{fmt_entries("daily")}\n\n'
        f'=== DECISION LOG ===\n{fmt_entries("decision")}\n\n'
        f'=== FILE ĐÍNH KÈM ===\n{file_list}\n\n'
        'Hãy tạo ra 2 phần rõ ràng:\n\n'
        '**PHẦN 1 — SOP (Standard Operating Procedure)**\n'
        'Viết quy trình từng bước theo trình tự thời gian thực tế.\n'
        'Mỗi bước: Tên bước | Mô tả | Người/team thực hiện | Output cụ thể.\n'
        'Kèm "Bài học kinh nghiệm" ở cuối.\n\n'
        '**PHẦN 2 — TEMPLATE (Khung trống để dùng lại)**\n'
        'Giữ đúng cấu trúc của SOP nhưng:\n'
        '- Thay số liệu cụ thể bằng [PLACEHOLDER]\n'
        '- Thay tên người/brand bằng [TÊN NGƯỜI THỰC HIỆN] / [TÊN BRAND]\n'
        '- Thay ngày bằng [DD/MM] hoặc [TUẦN N]\n'
        'Mục tiêu: ai cũng có thể điền vào và chạy lại project tương tự.'
    )


def generate_sop_and_template(project: dict) -> tuple[str, str]:
    """Call AI to generate SOP + template markdown. Returns (sop_md, template_md)."""
    from modules.ai_client import call_ai  # import here to allow easy mocking in tests
    raw = call_ai(_build_prompt(project), max_tokens=2000)
    if "PHẦN 2" in raw:
        idx = raw.index("PHẦN 2")
        sop      = raw[:idx].strip()
        template = raw[idx:].strip()
    else:
        sop = template = raw
    return sop, template


def save_outputs(project_id: str, sop_md: str, template_md: str) -> tuple[str, str]:
    """Write SOP + template to OUTPUTS_ROOT. Update project status to done. Returns (sop_path, tmpl_path)."""
    projects = load_projects()
    project  = next((p for p in projects if p["id"] == project_id), None)
    if project is None:
        raise ValueError(f"Project {project_id!r} not found")

    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
    date_str   = datetime.now().strftime("%Y-%m-%d")
    safe_title = _safe_name(project["title"])
    sop_path   = OUTPUTS_ROOT / f"{safe_title}_SOP_{date_str}.md"
    tmpl_path  = OUTPUTS_ROOT / f"{safe_title}_TEMPLATE_{date_str}.md"

    sop_path.write_text(sop_md, encoding="utf-8")
    tmpl_path.write_text(template_md, encoding="utf-8")

    now = datetime.now().isoformat()
    update_project(project_id,
        status="done",
        sop_path=str(sop_path),
        template_path=str(tmpl_path),
        done_at=now,
    )
    return str(sop_path), str(tmpl_path)


def clone_for_next_cycle(project: dict) -> dict:
    """Create a fresh active project from a recurring project (entries cleared)."""
    return add_project(
        title=project["title"],
        type_=project["type"],
        goal=project["goal"],
        start_date=datetime.now().strftime("%Y-%m-%d"),
        end_date=None,
        recur_pattern=project.get("recur_pattern"),
    )
```

- [ ] **Step 4: Run all tests**

```
.venv\Scripts\python.exe -m pytest tests/test_project_log.py -v
```

Expected: 17 tests PASS.

- [ ] **Step 5: Commit**

```
git add modules/project_log.py tests/test_project_log.py
git commit -m "feat: add project_log AI generate, save_outputs, clone"
```

---

## Task 4: App.py — Radio option + banner

**Files:**
- Modify: `app.py` (lines 1764, 1766, ~1867)

> No automated tests for Streamlit UI — verify visually after `streamlit run app.py`.

- [ ] **Step 1: Add "📂 Project Log" to the radio and update subtitle**

In `app.py` at line 1764–1767, replace:

```python
    section_header("⬡", "PYTHON NOTEBOOK", color="#f7cc00", anim="float",
                   subtitle="jupyterlab · meeting notes · DA / DS / DE stack")
    nb_view = st.radio("", ["▶ JupyterLab", "📋 Meeting Notes"],
                       horizontal=True, key="nb_view", label_visibility="collapsed")
```

With:

```python
    section_header("⬡", "PYTHON NOTEBOOK", color="#f7cc00", anim="float",
                   subtitle="jupyterlab · meeting notes · project log · DA / DS / DE stack")
    nb_view = st.radio("", ["▶ JupyterLab", "📋 Meeting Notes", "📂 Project Log"],
                       horizontal=True, key="nb_view", label_visibility="collapsed")
```

- [ ] **Step 2: Add active-project banner block**

Insert this block immediately after the radio (after line 1767, before `if nb_view == "▶ JupyterLab":`):

```python
    # ── Active project banner ──────────────────────────────────────────────────
    from modules.project_log import load_projects
    _active_projects = [p for p in load_projects() if p["status"] == "active"]
    if _active_projects:
        # Show the most recently updated (last in list, append-only)
        _ap = sorted(
            _active_projects,
            key=lambda p: max(
                (e["date"] for e in p["entries"]), default=p["start_date"]
            ),
        )[-1]
        _pct   = _ap["progress"]
        _bar   = "█" * (_pct // 10) + "░" * (10 - _pct // 10)
        _n_entries = len(_ap["entries"])
        _n_files   = sum(len(e.get("files", [])) for e in _ap["entries"])
        _last_date = max(
            (e["date"] for e in _ap["entries"]), default=_ap["start_date"]
        )
        st.markdown(
            f'<div style="background:#0d1f12;border:1px solid #30d158;border-radius:6px;'
            f'padding:10px 16px;margin-bottom:10px;display:flex;align-items:center;gap:16px;">'
            f'<span style="color:#f7cc00;font-size:11px;font-family:\'JetBrains Mono\',monospace;">'
            f'🟡 ĐANG ACTIVE</span>'
            f'<span style="color:#e6edf3;font-size:12px;font-weight:600;">{_ap["title"]}</span>'
            f'<span style="color:#30d158;font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
            f'{_bar} {_pct}%</span>'
            f'<span style="color:#3d5a6b;font-size:11px;">'
            f'Cập nhật: {_last_date} · {_n_entries} entries · {_n_files} files</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("→ Mở Project Log", key="banner_open_pl"):
            st.session_state["nb_view"] = "📂 Project Log"
            st.rerun()
```

- [ ] **Step 3: Quick visual smoke test**

```
cd D:\claude-workspace\08_Projects\task-tracker
.venv\Scripts\Activate.ps1
streamlit run app.py
```

Open `http://localhost:8501` → NOTEBOOK tab → confirm radio now has 3 options. No banner yet (no data). Click "📂 Project Log" → should show blank (no UI yet, that's fine).

- [ ] **Step 4: Commit**

```
git add app.py
git commit -m "feat: add Project Log radio option and active-project banner"
```

---

## Task 5: App.py — Project Log UI: create form + project list

**Files:**
- Modify: `app.py` (~line 1968, after Meeting Notes block ends)

- [ ] **Step 1: Add the Project Log rendering block**

Find the line after the Meeting Notes block ends (the `if nb_view == "📋 Meeting Notes":` block closes around line 1968). Add immediately after:

```python
    # ── Project Log ───────────────────────────────────────────────────────────
    if nb_view == "📂 Project Log":
        from modules.project_log import (
            load_projects, add_project, update_project, delete_project,
            add_entry, update_progress, save_attachment,
            generate_sop_and_template, save_outputs, clone_for_next_cycle,
        )

        pl_projects = load_projects()
        n_active = sum(1 for p in pl_projects if p["status"] == "active")
        n_done   = sum(1 for p in pl_projects if p["status"] == "done")

        st.markdown(
            f'<div style="color:#3d5a6b;font-size:10px;font-family:\'JetBrains Mono\','
            f'monospace;letter-spacing:.08em;padding:2px 0 8px 0">'
            f'Đang active: {n_active}  |  Done: {n_done}</div>',
            unsafe_allow_html=True,
        )

        # ── Create new project form ────────────────────────────────────────────
        with st.expander("➕ TẠO PROJECT MỚI", expanded=not pl_projects):
            pl_title = st.text_input("Tên project *", key="pl_title",
                                     placeholder="VD: Campaign Tết 2026")
            pl_type  = st.radio("Loại", ["one-time", "recurring"],
                                horizontal=True, key="pl_type",
                                format_func=lambda x: "📌 One-time" if x == "one-time" else "🔄 Recurring")

            if st.session_state.get("pl_type") == "recurring":
                pl_recur = st.selectbox("Chu kỳ", ["weekly", "monthly", "quarterly"], key="pl_recur")
            else:
                pl_recur = None

            pl_goal  = st.text_area("Mục tiêu", key="pl_goal", height=60,
                                    placeholder="VD: Tăng GMV ColosBaby 20% trong T01")
            pl_col_s, pl_col_e = st.columns(2)
            pl_start = pl_col_s.date_input("Ngày bắt đầu", key="pl_start")
            if st.session_state.get("pl_type") == "one-time":
                pl_end = pl_col_e.date_input("Ngày kết thúc", key="pl_end")
            else:
                pl_end = None

            # Milestones
            st.markdown(
                '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.1em;'
                'font-family:\'JetBrains Mono\',monospace;padding:4px 0">── MILESTONES ──</div>',
                unsafe_allow_html=True,
            )
            if "pl_milestones" not in st.session_state:
                st.session_state["pl_milestones"] = [{"label": "", "date": ""}]
            for mi, ms in enumerate(st.session_state["pl_milestones"]):
                ms_col_l, ms_col_d, ms_col_x = st.columns([3, 1.5, 0.3])
                ms["label"] = ms_col_l.text_input("Milestone", value=ms["label"],
                                                   key=f"pl_ms_l_{mi}", label_visibility="collapsed",
                                                   placeholder=f"Milestone {mi+1}")
                ms["date"]  = ms_col_d.text_input("Ngày", value=ms["date"],
                                                   key=f"pl_ms_d_{mi}", label_visibility="collapsed",
                                                   placeholder="YYYY-MM-DD")
                if ms_col_x.button("✕", key=f"pl_ms_x_{mi}"):
                    st.session_state["pl_milestones"].pop(mi)
                    st.rerun()
            if st.button("＋ Thêm milestone", key="pl_ms_add"):
                st.session_state["pl_milestones"].append({"label": "", "date": ""})
                st.rerun()

            if st.button("💾 TẠO PROJECT", key="pl_create"):
                if not pl_title.strip():
                    st.error("Tên project không được để trống.")
                elif pl_end and pl_end < pl_start and st.session_state.get("pl_type") == "one-time":
                    st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                else:
                    milestones_init = [
                        {"label": m["label"], "done": False, "date": m["date"]}
                        for m in st.session_state.get("pl_milestones", [])
                        if m["label"].strip()
                    ]
                    new_p = add_project(
                        title=pl_title.strip(),
                        type_=st.session_state.get("pl_type", "one-time"),
                        goal=pl_goal.strip(),
                        start_date=str(pl_start),
                        end_date=str(pl_end) if pl_end else None,
                        recur_pattern=pl_recur,
                    )
                    if milestones_init:
                        update_project(new_p["id"], milestones=milestones_init)
                    st.session_state.pop("pl_milestones", None)
                    st.success(f"✅ Đã tạo project: {pl_title}")
                    st.rerun()

        # ── Project list ───────────────────────────────────────────────────────
        pl_projects = load_projects()
        if not pl_projects:
            st.markdown(
                '<div style="color:#3d5a6b;font-size:11px;text-align:center;padding:24px 0">'
                'Chưa có project nào. Tạo project đầu tiên ở trên.</div>',
                unsafe_allow_html=True,
            )
```

- [ ] **Step 2: Add project card rendering (append inside the `if nb_view == "📂 Project Log":` block)**

```python
        for proj in reversed(pl_projects):  # newest first
            status_icon = {"active": "🟡", "paused": "⏸", "done": "✅"}.get(proj["status"], "")
            recur_label = f" 🔄 {proj.get('recur_pattern','')}" if proj["type"] == "recurring" else ""
            pct  = proj["progress"]
            bar  = "█" * (pct // 10) + "░" * (10 - pct // 10)
            with st.expander(
                f"{status_icon} {proj['title']}{recur_label}  {bar} {pct}%",
                expanded=(proj["status"] == "active"),
            ):
                # ── Milestone progress ─────────────────────────────────────────
                if proj["milestones"]:
                    ms_cols = st.columns(len(proj["milestones"]))
                    for mi, ms in enumerate(proj["milestones"]):
                        with ms_cols[mi]:
                            icon = "✅" if ms["done"] else "⬜"
                            st.markdown(
                                f'<div style="font-size:10px;color:#8b949e;">'
                                f'{icon} {ms["label"]}<br>'
                                f'<span style="color:#3d5a6b">{ms.get("date","")}</span></div>',
                                unsafe_allow_html=True,
                            )

                # ── Progress slider ────────────────────────────────────────────
                new_pct = st.slider("Tiến độ %", 0, 100, pct,
                                    key=f"pl_pct_{proj['id']}")
                if new_pct != pct:
                    update_progress(proj["id"], new_pct, proj["milestones"])
                    st.rerun()

                # ── Entry log ─────────────────────────────────────────────────
                for entry in reversed(proj["entries"]):
                    e_icon = "📝" if entry["type"] == "daily" else "⚖️"
                    fnames = ", ".join(f.get("name","") for f in entry.get("files",[]))
                    st.markdown(
                        f'<div style="font-size:11px;color:#8b949e;padding:2px 0">'
                        f'{e_icon} <span style="color:#3d5a6b">{entry["date"]}</span> '
                        f'<span style="color:#e6edf3">{entry["content"]}</span>'
                        + (f' <span style="color:#3d5a6b">📎 {fnames}</span>' if fnames else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )
```

- [ ] **Step 3: Smoke test — create a project**

Restart streamlit, go to NOTEBOOK → 📂 Project Log, create a project. Confirm it appears in the list with progress slider and milestones.

- [ ] **Step 4: Commit**

```
git add app.py
git commit -m "feat: Project Log create form and project list UI"
```

---

## Task 6: App.py — Entry forms + file upload

**Files:**
- Modify: `app.py` (inside project card expander, after entry log)

- [ ] **Step 1: Add entry + file forms inside each project card**

Append inside the `for proj in reversed(pl_projects):` block, after the entry log section and before the closing of the expander:

```python
                # ── Add entry form ─────────────────────────────────────────────
                if proj["status"] == "active":
                    with st.expander("➕ Ghi hôm nay / Decision", expanded=False):
                        ae_type = st.radio(
                            "Loại", ["daily", "decision"],
                            horizontal=True, key=f"pl_ae_type_{proj['id']}",
                            format_func=lambda x: "📝 Daily log" if x == "daily" else "⚖️ Decision",
                        )
                        ae_content = st.text_area(
                            "Nội dung *", key=f"pl_ae_content_{proj['id']}", height=80,
                        )
                        # File: upload or URL
                        ae_files: list[dict] = []
                        ae_uploaded = st.file_uploader(
                            "📎 Upload file (tuỳ chọn)", key=f"pl_ae_upload_{proj['id']}",
                        )
                        ae_url  = st.text_input("🔗 Hoặc paste URL", key=f"pl_ae_url_{proj['id']}",
                                                placeholder="https://drive.google.com/...")
                        ae_name = st.text_input("Tên hiển thị (nếu paste URL)",
                                                key=f"pl_ae_name_{proj['id']}",
                                                placeholder="VD: Brief v1")

                        if st.button("💾 Lưu entry", key=f"pl_ae_save_{proj['id']}"):
                            if not ae_content.strip():
                                st.error("Nội dung không được để trống.")
                            else:
                                if ae_uploaded:
                                    dest = save_attachment(proj["id"], ae_uploaded)
                                    ae_files.append({"name": ae_uploaded.name, "path": dest})
                                if ae_url.strip():
                                    ae_files.append({
                                        "name": ae_name.strip() or ae_url.strip(),
                                        "url": ae_url.strip(),
                                    })
                                add_entry(proj["id"], ae_type, ae_content.strip(), ae_files)
                                st.success("✅ Đã lưu entry.")
                                st.rerun()
```

- [ ] **Step 2: Smoke test — add a daily entry**

Restart streamlit → open an active project → click "➕ Ghi hôm nay / Decision" → type content → save. Confirm entry appears in the list.

- [ ] **Step 3: Commit**

```
git add app.py
git commit -m "feat: Project Log entry form with file upload and URL"
```

---

## Task 7: App.py — Mark as Done + AI generate flow

**Files:**
- Modify: `app.py` (inside project card expander, below entry form)

- [ ] **Step 1: Add action buttons + Done flow inside each project card**

Append inside the `for proj in reversed(pl_projects):` block, after the entry form section:

```python
                # ── Action buttons ─────────────────────────────────────────────
                if proj["status"] == "active":
                    btn_col_done, btn_col_pause, btn_col_del = st.columns([2, 1.5, 0.5])

                    with btn_col_pause:
                        if st.button("⏸ Pause", key=f"pl_pause_{proj['id']}"):
                            update_project(proj["id"], status="paused")
                            st.rerun()

                    with btn_col_del:
                        if st.button("🗑", key=f"pl_del_{proj['id']}"):
                            delete_project(proj["id"])
                            st.rerun()

                    with btn_col_done:
                        if st.button("⚑ Mark as Done", key=f"pl_done_{proj['id']}",
                                     type="primary", use_container_width=True):
                            st.session_state[f"pl_confirming_done_{proj['id']}"] = True

                    if st.session_state.get(f"pl_confirming_done_{proj['id']}"):
                        st.warning(
                            f"Done project **{proj['title']}**? "
                            "AI sẽ đọc toàn bộ log và tạo SOP + Template."
                        )
                        conf_col_yes, conf_col_no = st.columns(2)
                        with conf_col_no:
                            if st.button("↩ Quay lại", key=f"pl_done_cancel_{proj['id']}"):
                                st.session_state.pop(f"pl_confirming_done_{proj['id']}", None)
                                st.rerun()
                        with conf_col_yes:
                            if st.button("✅ Xác nhận Done + Generate",
                                         key=f"pl_done_confirm_{proj['id']}",
                                         type="primary", use_container_width=True):
                                with st.spinner("🤖 AI đang đọc log và tạo SOP..."):
                                    try:
                                        _sop, _tmpl = generate_sop_and_template(proj)
                                    except Exception as _e:
                                        st.error(f"⚠ AI lỗi: {_e}. Thử lại?")
                                        st.stop()
                                st.session_state[f"pl_sop_{proj['id']}"]  = _sop
                                st.session_state[f"pl_tmpl_{proj['id']}"] = _tmpl
                                st.session_state.pop(f"pl_confirming_done_{proj['id']}", None)
                                st.rerun()

                    # Preview + save
                    if st.session_state.get(f"pl_sop_{proj['id']}"):
                        _sop  = st.session_state[f"pl_sop_{proj['id']}"]
                        _tmpl = st.session_state[f"pl_tmpl_{proj['id']}"]
                        with st.expander("📄 SOP Preview", expanded=True):
                            st.markdown(_sop[:800] + ("..." if len(_sop) > 800 else ""))
                        with st.expander("📋 Template Preview"):
                            st.markdown(_tmpl[:800] + ("..." if len(_tmpl) > 800 else ""))

                        save_col, back_col = st.columns(2)
                        with back_col:
                            if st.button("↩ Chưa done, quay lại",
                                         key=f"pl_save_cancel_{proj['id']}"):
                                st.session_state.pop(f"pl_sop_{proj['id']}", None)
                                st.session_state.pop(f"pl_tmpl_{proj['id']}", None)
                                st.rerun()
                        with save_col:
                            if st.button("💾 Lưu vào 07_Outputs/",
                                         key=f"pl_save_confirm_{proj['id']}",
                                         type="primary", use_container_width=True):
                                _sop_path, _tmpl_path = save_outputs(
                                    proj["id"], _sop, _tmpl
                                )
                                # If recurring → clone for next cycle
                                if proj["type"] == "recurring":
                                    clone_for_next_cycle(proj)
                                st.session_state.pop(f"pl_sop_{proj['id']}", None)
                                st.session_state.pop(f"pl_tmpl_{proj['id']}", None)
                                st.success(
                                    f"✅ Đã lưu!\n\n"
                                    f"📄 SOP: `{_sop_path}`\n\n"
                                    f"📋 Template: `{_tmpl_path}`"
                                )
                                st.rerun()

                elif proj["status"] == "paused":
                    btn_resume_col, btn_del_col = st.columns([3, 0.5])
                    with btn_resume_col:
                        if st.button("▶ Resume", key=f"pl_resume_{proj['id']}"):
                            update_project(proj["id"], status="active")
                            st.rerun()
                    with btn_del_col:
                        if st.button("🗑", key=f"pl_del_p_{proj['id']}"):
                            delete_project(proj["id"])
                            st.rerun()

                elif proj["status"] == "done":
                    sop_path  = proj.get("sop_path")
                    tmpl_path = proj.get("template_path")
                    if sop_path:
                        st.markdown(
                            f'<div style="font-size:11px;color:#3d5a6b">📄 SOP: <code>{sop_path}</code></div>',
                            unsafe_allow_html=True,
                        )
                    if tmpl_path:
                        st.markdown(
                            f'<div style="font-size:11px;color:#3d5a6b">📋 Template: <code>{tmpl_path}</code></div>',
                            unsafe_allow_html=True,
                        )
                    if st.button("🗑 Xoá", key=f"pl_del_d_{proj['id']}"):
                        delete_project(proj["id"])
                        st.rerun()
```

- [ ] **Step 2: Full end-to-end smoke test**

```
streamlit run app.py
```

Checklist:
1. NOTEBOOK tab → 3 radio options visible ✓
2. Create a project → appears in list ✓
3. Add a daily entry → shows in log ✓
4. Add a decision entry → shows in log ✓
5. Move progress slider → updates ✓
6. Banner shows on other tabs if project active ✓
7. Mark as Done → AI spinner → SOP preview → save → files written to 07_Outputs\ ✓
8. Recurring project: after Done → new project appears automatically ✓
9. Pause → Resume works ✓
10. Delete works ✓

- [ ] **Step 3: Run full test suite**

```
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

Expected: all existing tests + 17 new project_log tests PASS.

- [ ] **Step 4: Create `07_Outputs\On-going\` folder**

```python
# Run once in python to create the folder
from pathlib import Path
Path(r"D:\claude-workspace\07_Outputs\On-going").mkdir(parents=True, exist_ok=True)
print("Created.")
```

Or from PowerShell:
```
New-Item -ItemType Directory -Force -Path "D:\claude-workspace\07_Outputs\On-going"
```

- [ ] **Step 5: Final commit**

```
git add app.py
git commit -m "feat: Project Log Mark as Done, AI generate, pause/resume UI"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Two project types (one-time / recurring) — Task 1, 5
- ✅ Daily log + decision log — Task 2, 6
- ✅ File attachment (local upload + URL) — Task 2, 6
- ✅ Progress % + milestones — Task 2, 5
- ✅ Banner with active project — Task 4
- ✅ AI generate SOP + template on Done — Task 3, 7
- ✅ Save to 07_Outputs\ — Task 3, 7
- ✅ Recurring: clone on Done — Task 3, 7
- ✅ Pause / resume — Task 7
- ✅ Error handling: AI fails → error shown, project stays active — Task 7
- ✅ Error handling: missing JSON → auto-create — Task 1 (`_save` creates parent)
- ✅ Error handling: end_date < start_date — Task 5
- ✅ File > 10MB not explicitly blocked (Streamlit default 200MB) — acceptable, out of scope for now

**Placeholder scan:** None found.

**Type consistency:**
- `add_project(type_=...)` uses `type_` (underscore to avoid shadowing builtin) — consistent across all call sites in Task 5, 7
- `generate_sop_and_template(project: dict)` takes full project dict — Task 3 defines it, Task 7 calls it with `proj` (same dict from `load_projects()`) ✓
- `save_outputs(project_id, sop_md, template_md)` — Task 3 defines, Task 7 calls ✓
- `clone_for_next_cycle(project)` — Task 3 defines, Task 7 calls ✓
- `OUTPUTS_ONGOING` / `OUTPUTS_ROOT` monkeypatched in tests, used in `save_attachment` and `save_outputs` ✓
