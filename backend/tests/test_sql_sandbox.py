import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_tables_empty(client):
    """GET /api/sql/tables returns a list (may be empty or contain pre-seeded rows)."""
    resp = client.get("/api/sql/tables")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_seed_vina_brew(client):
    """POST /api/sql/seed-vina-brew seeds or skips existing VINA BREW tables."""
    resp = client.post("/api/sql/seed-vina-brew")
    assert resp.status_code == 200
    d = resp.json()
    assert "seeded" in d
    assert "total" in d
    assert isinstance(d["seeded"], list)
    assert d["total"] == len(d["seeded"])


def test_list_tables_after_seed(client):
    """After seeding, GET /api/sql/tables returns the 6 VINA BREW tables."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.get("/api/sql/tables")
    assert resp.status_code == 200
    tables = resp.json()
    names = {t["table_name"] for t in tables}
    expected = {"dim_date", "dim_product", "dim_channel", "dim_store", "fact_sales", "fact_transactions"}
    assert expected.issubset(names), f"Missing tables: {expected - names}"
    # VINA BREW tables must be labeled correctly
    for t in tables:
        if t["table_name"] in expected:
            assert t["source"] == "vina_brew"


def test_list_tables_schema_info(client):
    """Each table in the list has file_id, rows, cols, columns with name+dtype."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.get("/api/sql/tables")
    tables = resp.json()
    assert len(tables) > 0
    first = tables[0]
    assert "file_id" in first
    assert first["rows"] > 0
    assert first["cols"] > 0
    assert len(first["columns"]) > 0
    col0 = first["columns"][0]
    assert "name" in col0
    assert "dtype" in col0


def test_query_select_all(client):
    """POST /api/sql/query runs a basic SELECT and returns columns + rows."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/query", json={"sql": "SELECT * FROM dim_channel ORDER BY channel_id"})
    assert resp.status_code == 200
    d = resp.json()
    assert d["columns"] == ["channel_id", "channel_name", "channel_type", "commission_rate"]
    assert len(d["rows"]) == 8
    assert d["duration_ms"] >= 0


def test_query_aggregation(client):
    """Aggregation query returns computed columns."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/query", json={
        "sql": "SELECT brand, COUNT(*) AS n FROM dim_product GROUP BY brand ORDER BY brand"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["columns"] == ["brand", "n"]
    assert len(d["rows"]) > 0


def test_query_join(client):
    """Multi-table JOIN returns combined columns."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/query", json={
        "sql": (
            "SELECT p.brand, SUM(s.gross_amount) AS gsv "
            "FROM fact_sales s "
            "JOIN dim_product p ON s.product_id = p.product_id "
            "GROUP BY p.brand ORDER BY gsv DESC LIMIT 3"
        )
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["columns"] == ["brand", "gsv"]
    assert len(d["rows"]) == 3


def test_query_syntax_error(client):
    """Malformed SQL returns 400 with error detail."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/query", json={"sql": "SELECT FROM WHERE"})
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_query_unknown_table(client):
    """Querying a nonexistent table returns 400."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/query", json={"sql": "SELECT * FROM nonexistent_table_xyz"})
    assert resp.status_code == 400


def test_query_empty_sql(client):
    """Empty SQL returns 400."""
    resp = client.post("/api/sql/query", json={"sql": "   "})
    assert resp.status_code == 400


def test_exercise_check_pass(client):
    """Exercise check passes when user SQL returns correct column names."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/exercises/check", json={
        "exercise_id": "ex-01",
        "sql": "SELECT product_name, brand, category FROM dim_product ORDER BY brand",
        "expected_columns": ["product_name", "brand", "category"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["passed"] is True
    assert d["actual_columns"] == ["product_name", "brand", "category"]
    assert d["error"] is None


def test_exercise_check_fail_wrong_columns(client):
    """Exercise check fails when column names don't match."""
    client.post("/api/sql/seed-vina-brew")
    resp = client.post("/api/sql/exercises/check", json={
        "exercise_id": "ex-01",
        "sql": "SELECT product_name, brand FROM dim_product",  # missing 'category'
        "expected_columns": ["product_name", "brand", "category"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["passed"] is False
    assert "category" not in d["actual_columns"]


def test_exercise_check_sql_error(client):
    """Exercise check with invalid SQL returns passed=False and error message."""
    resp = client.post("/api/sql/exercises/check", json={
        "exercise_id": "ex-01",
        "sql": "SELECT * FROM does_not_exist",
        "expected_columns": ["product_name"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["passed"] is False
    assert d["error"] is not None


def test_delete_vina_brew_table_blocked(client):
    """Attempting to delete a VINA BREW table returns 400."""
    client.post("/api/sql/seed-vina-brew")
    tables = client.get("/api/sql/tables").json()
    vb = next((t for t in tables if t["source"] == "vina_brew"), None)
    assert vb is not None
    resp = client.delete(f"/api/sql/dataset/{vb['file_id']}")
    assert resp.status_code == 400


def test_delete_nonexistent_dataset(client):
    """Deleting a dataset that doesn't exist returns 404."""
    resp = client.delete("/api/sql/dataset/no-such-id-99999")
    assert resp.status_code == 404


# ── table-name cleanup helpers (unit) ─────────────────────────────────────────

from routers.sql_sandbox import _clean_identifier, _assign_table_names


def test_clean_identifier_basic():
    assert _clean_identifier("Q1 Sales (2024)") == "q1_sales_2024"
    assert _clean_identifier("dim_date") == "dim_date"
    assert _clean_identifier("  weird---name!! ") == "weird_name"


def test_clean_identifier_leading_digit_and_empty():
    assert _clean_identifier("2024 report") == "t_2024_report"
    assert _clean_identifier("") == "table"
    assert _clean_identifier("!!!") == "table"


def test_assign_table_names_dedup():
    files = [
        {"file_id": "a", "filename": "Q1 Sales.csv"},
        {"file_id": "b", "filename": "q1-sales.csv"},   # collides with 'a' after cleaning
        {"file_id": "c", "filename": "dim_date.csv"},
    ]
    m = _assign_table_names(files)
    assert m["a"] == "q1_sales"
    assert m["b"] == "q1_sales_2"
    assert m["c"] == "dim_date"
