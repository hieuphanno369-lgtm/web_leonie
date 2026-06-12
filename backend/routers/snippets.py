from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/snippets", tags=["snippets"])


class SnippetIn(BaseModel):
    title: str
    category: str = "ad_hoc"
    sql: str
    tags: str = ""          # comma-separated


class SnippetOut(BaseModel):
    id: str
    title: str
    category: str
    sql: str
    tags: str
    created: str
    updated: str


def _migrate_snippets(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(snippets)").fetchall()}
    if "title" not in cols:
        conn.execute("ALTER TABLE snippets ADD COLUMN title TEXT NOT NULL DEFAULT ''")
    if "tags" not in cols:
        conn.execute("ALTER TABLE snippets ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
    conn.commit()


def _row(r) -> SnippetOut:
    return SnippetOut(
        id=r["id"],
        title=r["title"] or r["filename"],
        category=r["category"],
        sql=r["sql"],
        tags=r["tags"] if "tags" in r.keys() else "",
        created=r["created"],
        updated=r["updated"],
    )


@router.get("", response_model=list[SnippetOut])
def list_snippets(q: str = "", category: str = ""):
    conn = get_connection(); _migrate_snippets(conn)
    sql = "SELECT * FROM snippets WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (title LIKE ? OR filename LIKE ? OR sql LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY updated DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.post("", response_model=SnippetOut, status_code=201)
def create_snippet(body: SnippetIn):
    conn = get_connection(); _migrate_snippets(conn)
    conn.execute(
        "INSERT INTO snippets (filename, title, category, sql, source, tags) VALUES (?,?,?,?,?,?)",
        (body.title, body.title, body.category, body.sql, "user", body.tags),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM snippets WHERE rowid = last_insert_rowid()"
    ).fetchone()
    conn.close()
    return _row(row)


@router.put("/{snippet_id}", response_model=SnippetOut)
def update_snippet(snippet_id: str, body: SnippetIn):
    conn = get_connection(); _migrate_snippets(conn)
    r = conn.execute("SELECT id FROM snippets WHERE id=?", (snippet_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Snippet not found")
    conn.execute(
        "UPDATE snippets SET filename=?, title=?, category=?, sql=?, tags=?, updated=datetime('now') WHERE id=?",
        (body.title, body.title, body.category, body.sql, body.tags, snippet_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM snippets WHERE id=?", (snippet_id,)).fetchone()
    conn.close()
    return _row(row)


@router.delete("/{snippet_id}", status_code=204)
def delete_snippet(snippet_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM snippets WHERE id=?", (snippet_id,))
    conn.commit()
    conn.close()


@router.get("/categories")
def list_categories():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT category FROM snippets ORDER BY category"
    ).fetchall()
    conn.close()
    return [r["category"] for r in rows]
