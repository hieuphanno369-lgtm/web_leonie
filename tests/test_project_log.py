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


def test_safe_name_handles_windows_illegal_chars():
    from modules.project_log import _safe_name
    assert _safe_name("ColosBaby: Q2 Report") == "ColosBaby__Q2_Report"
    assert _safe_name("file/path\\name") == "file_path_name"
    assert _safe_name("query?results<out>.txt") == "query_results_out_.txt"
    assert _safe_name("pipe|test*file") == "pipe_test_file"


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
    from modules.project_log import add_project, save_outputs, load_projects

    p = add_project("Save-proj", "one-time", "Goal", "2026-01-01", "2026-01-31")
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
