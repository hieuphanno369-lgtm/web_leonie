import sqlite3
import os
import pathlib

_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "data", "leonie.db")

UPLOADS_DIR = pathlib.Path(__file__).parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str = _DEFAULT_DB) -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to Row."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables(db_path: str = _DEFAULT_DB) -> None:
    """Create all application tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title     TEXT NOT NULL,
            status    TEXT NOT NULL DEFAULT 'todo'
                          CHECK(status IN ('todo', 'in_progress', 'done')),
            priority  TEXT NOT NULL DEFAULT 'medium'
                          CHECK(priority IN ('low', 'medium', 'high')),
            due_date  TEXT,
            recurring TEXT CHECK(recurring IN (NULL, 'daily', 'weekly')),
            notes     TEXT,
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS snippets (
            id       TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            filename TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'ad_hoc',
            sql      TEXT NOT NULL,
            source   TEXT NOT NULL DEFAULT 'user'
                         CHECK(source IN ('file', 'user')),
            created  TEXT NOT NULL DEFAULT (datetime('now')),
            updated  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kpi_entries (
            id      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            metric  TEXT NOT NULL,
            value   REAL NOT NULL,
            date    TEXT NOT NULL,
            note    TEXT,
            created TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS uploaded_datasets (
            file_id  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            rows     INTEGER,
            cols     INTEGER,
            uploaded TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS eda_requests (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title     TEXT NOT NULL,
            requester TEXT NOT NULL,
            dataset   TEXT NOT NULL,
            priority  TEXT NOT NULL DEFAULT 'medium'
                          CHECK(priority IN ('low', 'medium', 'high')),
            status    TEXT NOT NULL DEFAULT 'todo'
                          CHECK(status IN ('todo', 'in_progress', 'done')),
            due_date  TEXT,
            notes     TEXT,
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wip_items (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            task_id   TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            progress  INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wip_logs (
            id      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            wip_id  TEXT NOT NULL REFERENCES wip_items(id) ON DELETE CASCADE,
            date    TEXT NOT NULL,
            note    TEXT NOT NULL,
            created TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS discord_settings (
            id           INTEGER PRIMARY KEY DEFAULT 1,
            webhook_url  TEXT,
            rule_overdue INTEGER NOT NULL DEFAULT 1,
            rule_done    INTEGER NOT NULL DEFAULT 0,
            rule_summary INTEGER NOT NULL DEFAULT 0,
            last_checked TEXT
        );
    """)
    conn.commit()
    _migrate_v2(conn)
    _migrate_v3(conn)
    _migrate_v4(conn)
    _migrate_v5(conn)
    _migrate_v6(conn)
    conn.close()


def _migrate_v2(conn) -> None:
    """Safe idempotent migrations for v2 schema additions."""
    existing = {r[1] for r in conn.execute("PRAGMA table_info(kpi_entries)").fetchall()}
    if "category" not in existing:
        conn.execute(
            "ALTER TABLE kpi_entries ADD COLUMN "
            "category TEXT NOT NULL DEFAULT 'da_output'"
        )
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS performance_settings (
            id          INTEGER PRIMARY KEY DEFAULT 1,
            streak_rule TEXT NOT NULL DEFAULT
                '{"conditions":[{"type":"tasks_done","op":"gte","value":2}],"logic":"OR"}'
        );

        CREATE TABLE IF NOT EXISTS uploaded_files (
            file_id   TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            filename  TEXT NOT NULL,
            filepath  TEXT NOT NULL,
            rows      INTEGER,
            cols      INTEGER,
            uploaded  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def _migrate_v3(conn) -> None:
    """Add quick_notes table."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS quick_notes (
            id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title     TEXT,
            content   TEXT NOT NULL,
            date      TEXT NOT NULL,
            category  TEXT,
            task_id   TEXT REFERENCES tasks(id) ON DELETE SET NULL,
            eda_id    TEXT REFERENCES eda_requests(id) ON DELETE SET NULL,
            created   TEXT NOT NULL DEFAULT (datetime('now')),
            updated   TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def _migrate_v4(conn) -> None:
    """Add action_plans table."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS action_plans (
            id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            title        TEXT NOT NULL,
            category     TEXT NOT NULL DEFAULT 'other'
                             CHECK(category IN ('rfm','cohort','statistical','etl','dashboard','other')),
            status       TEXT NOT NULL DEFAULT 'draft'
                             CHECK(status IN ('draft','proposed','approved','in_progress','done')),
            priority     TEXT NOT NULL DEFAULT 'medium'
                             CHECK(priority IN ('low','medium','high')),
            problem      TEXT,
            pic_main     TEXT,
            pic_support  TEXT,
            due_date     TEXT,
            manager_notes TEXT,
            approval     TEXT NOT NULL DEFAULT 'pending'
                             CHECK(approval IN ('pending','approved','rejected')),
            ai_timeline  TEXT,
            ai_checklist TEXT,
            ai_input     TEXT,
            ai_output    TEXT,
            ai_value     TEXT,
            ai_impact    TEXT,
            ai_refs      TEXT,
            ai_suggestions TEXT,
            created      TEXT NOT NULL DEFAULT (datetime('now')),
            updated      TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def _migrate_v5(conn) -> None:
    """Merge EDA Tracker into Tasks: add type/requester/dataset columns + migrate data."""
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}

    if "type" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN type TEXT NOT NULL DEFAULT 'task'")
    if "requester" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN requester TEXT")
    if "dataset" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN dataset TEXT")

    # Migrate eda_requests rows into tasks (only if table exists and has rows)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "eda_requests" in tables:
        eda_rows = conn.execute("SELECT * FROM eda_requests").fetchall()
        for r in eda_rows:
            r = dict(r)
            # Check not already migrated (by matching id)
            exists = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (r["id"],)).fetchone()
            if not exists:
                conn.execute(
                    """INSERT INTO tasks
                       (id, title, status, priority, due_date, notes, type, requester, dataset, created, updated)
                       VALUES (?, ?, ?, ?, ?, ?, 'eda', ?, ?, ?, ?)""",
                    (r["id"], r["title"], r["status"], r["priority"],
                     r.get("due_date"), r.get("notes"),
                     r["requester"], r["dataset"],
                     r["created"], r["updated"]),
                )

    conn.commit()


def _migrate_v6(conn) -> None:
    """Add automation_jobs table (Automation feature)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS automation_jobs (
            id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            name        TEXT NOT NULL,
            config      TEXT NOT NULL,
            last_status TEXT,
            last_run_at TEXT,
            last_rows   INTEGER,
            last_error  TEXT,
            created     TEXT NOT NULL DEFAULT (datetime('now')),
            updated     TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
