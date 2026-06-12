import duckdb


def run(con: duckdb.DuckDBPyConnection, shape_sql: str) -> int:
    """(Re)build the `data` table from user SQL over `raw`. Returns row count."""
    con.execute("DROP TABLE IF EXISTS data")
    sql = shape_sql.strip() or "SELECT * FROM raw"
    con.execute(f"CREATE TABLE data AS {sql}")
    return con.execute("SELECT count(*) FROM data").fetchone()[0]
