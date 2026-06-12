import sqlite3
import tempfile
import os
import pytest
from database import create_tables, get_connection


def test_create_tables_creates_all_four_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_tables(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    assert "tasks" in tables
    assert "snippets" in tables
    assert "kpi_entries" in tables
    assert "uploaded_datasets" in tables


def test_tasks_table_has_required_columns(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_tables(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()
    assert "id" in columns
    assert "title" in columns
    assert "status" in columns
    assert "priority" in columns
    assert "due_date" in columns
    assert "recurring" in columns
    assert "notes" in columns
    assert "created" in columns
    assert "updated" in columns


def test_create_tables_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_tables(db_path)
    create_tables(db_path)  # calling twice should not raise
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table'"
    )
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 13  # 12 prior + automation_jobs (v6)


def test_get_connection_returns_connection(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_tables(db_path)
    conn = get_connection(db_path)
    assert conn is not None
    cursor = conn.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
    conn.close()


@pytest.fixture
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_tables(db_path)
    return db_path


def test_eda_requests_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(eda_requests)").fetchall()]
    conn.close()
    assert "id" in cols
    assert "requester" in cols
    assert "dataset" in cols

def test_wip_tables_exist(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    wip_cols = [r[1] for r in conn.execute("PRAGMA table_info(wip_items)").fetchall()]
    log_cols = [r[1] for r in conn.execute("PRAGMA table_info(wip_logs)").fetchall()]
    conn.close()
    assert "task_id" in wip_cols
    assert "progress" in wip_cols
    assert "wip_id" in log_cols

def test_discord_settings_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(discord_settings)").fetchall()]
    conn.close()
    assert "webhook_url" in cols
    assert "rule_overdue" in cols

def test_quick_notes_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "quick_notes" in tables

def test_automation_jobs_table_exists(fresh_db):
    import sqlite3
    conn = sqlite3.connect(fresh_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(automation_jobs)").fetchall()}
    conn.close()
    assert {"id", "name", "config", "last_status", "last_run_at",
            "last_rows", "last_error", "created", "updated"} <= cols
