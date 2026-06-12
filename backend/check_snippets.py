import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leonie.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT category, COUNT(*) as cnt FROM snippets GROUP BY category ORDER BY category").fetchall()
total = conn.execute("SELECT COUNT(*) FROM snippets").fetchone()[0]
print(f"Total snippets: {total}")
for r in rows:
    print(f"  {r['category']}: {r['cnt']}")

conn.close()
