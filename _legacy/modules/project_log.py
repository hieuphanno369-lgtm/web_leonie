"""modules/project_log.py — Project Log data layer."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

# Imported at module level so tests can patch "modules.project_log.call_ai"
try:
    from modules.ai_client import call_ai
except ImportError:  # pragma: no cover — ai_client not available in some envs
    call_ai = None  # type: ignore[assignment]

DATA_PATH       = Path(__file__).parent.parent / "data" / "project_logs.json"
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
    """Strip all Windows-illegal path characters (<>:"/\\|?*)."""
    return re.sub(r'[<>:"/\\|?*\s]', "_", title)


def save_attachment(project_id: str, uploaded_file) -> str:
    """Copy Streamlit UploadedFile to OUTPUTS_ONGOING/<project_title>/. Returns dest path str."""
    projects = load_projects()
    title = next((p["title"] for p in projects if p["id"] == project_id), project_id)
    dest_dir = OUTPUTS_ONGOING / _safe_name(title)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / uploaded_file.name
    dest.write_bytes(uploaded_file.getbuffer())
    return str(dest)


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
    if call_ai is None:
        raise RuntimeError(
            "AI client không khả dụng — kiểm tra cấu hình ANTHROPIC_API_KEY hoặc Ollama"
        )
    raw = call_ai(_build_prompt(project), max_tokens=4000)
    match = re.search(r'\*\*PHẦN 2', raw)
    if match:
        sop      = raw[:match.start()].strip()
        template = raw[match.start():].strip()
    elif "PHẦN 2" in raw:
        idx      = raw.index("PHẦN 2")
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
