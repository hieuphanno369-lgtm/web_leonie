"""Smoke tests for the parallel cohort comparison endpoint."""
import io
import sys
import pathlib
import pytest

# Add backend to sys.path so we can import main, database, etc.
_BACKEND = str(pathlib.Path(__file__).parent.parent / "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import database  # noqa: E402
from fastapi.testclient import TestClient
from main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Isolate each test with a fresh SQLite DB."""
    db_path = str(tmp_path / "test.db")
    database.create_tables(db_path)
    orig_defaults = database.get_connection.__defaults__
    database.get_connection.__defaults__ = (db_path,)
    yield db_path
    database.get_connection.__defaults__ = orig_defaults


@pytest.fixture
def client():
    return TestClient(app)


def _make_cohort_csv() -> bytes:
    """60 rows: 30 for 2026-01 and 30 for 2026-02.
    Each month has 15 North + 15 South rows.
    """
    lines = ["cohort_month,user_id,region"]
    for month in ("2026-01", "2026-02"):
        for i in range(1, 16):
            lines.append(f"{month},u{i},North")
        for i in range(16, 31):
            lines.append(f"{month},u{i},South")
    return "\n".join(lines).encode()


COHORT_CSV = _make_cohort_csv()


def _upload(client: TestClient) -> str:
    resp = client.post(
        "/api/ml/upload",
        files={"file": ("cohort_compare.csv", io.BytesIO(COHORT_CSV), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["file_id"]


def test_cohort_north(client):
    """filter_col=region, filter_val=North → 200 with cohorts and matrix keys."""
    file_id = _upload(client)
    resp = client.post("/api/ml/cohort", json={
        "file_id": file_id,
        "date_col": "cohort_month",
        "user_col": "user_id",
        "period": "month",
        "filter_col": "region",
        "filter_val": "North",
    })
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert "cohorts" in d
    assert "matrix" in d
    assert len(d["cohorts"]) > 0


def test_cohort_south(client):
    """filter_col=region, filter_val=South → 200."""
    file_id = _upload(client)
    resp = client.post("/api/ml/cohort", json={
        "file_id": file_id,
        "date_col": "cohort_month",
        "user_col": "user_id",
        "period": "month",
        "filter_col": "region",
        "filter_val": "South",
    })
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert "cohorts" in d
    assert len(d["cohorts"]) > 0


def test_cohort_no_filter(client):
    """No filter → 200 and all_users_row is not None."""
    file_id = _upload(client)
    resp = client.post("/api/ml/cohort", json={
        "file_id": file_id,
        "date_col": "cohort_month",
        "user_col": "user_id",
        "period": "month",
    })
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert "cohorts" in d
    assert "all_users_row" in d
    assert d["all_users_row"] is not None


def test_cohort_invalid_filter_returns_400(client):
    """filter_val=NonExistentRegion → 400."""
    file_id = _upload(client)
    resp = client.post("/api/ml/cohort", json={
        "file_id": file_id,
        "date_col": "cohort_month",
        "user_col": "user_id",
        "period": "month",
        "filter_col": "region",
        "filter_val": "NonExistentRegion",
    })
    assert resp.status_code == 400, resp.text
