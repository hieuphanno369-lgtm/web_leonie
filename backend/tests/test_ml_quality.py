import io
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _upload(client, csv_bytes: bytes, name: str = "test.csv") -> str:
    resp = client.post(
        "/api/ml/upload",
        files={"file": (name, io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["file_id"]


def test_quality_clean_data(client):
    fid = _upload(client, b"name,value\nAlice,100\nBob,200\nCarol,150\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    assert resp.status_code == 200
    d = resp.json()
    assert d["issue_count"] == 0
    assert d["issues"] == []
    assert d["rows"] == 3
    assert d["cols"] == 2


def test_quality_null_detection(client):
    fid = _upload(client, b"name,value\nAlice,100\nBob,\nCarol,150\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    assert resp.status_code == 200
    null_issues = [i for i in resp.json()["issues"] if i["type"] == "null"]
    assert len(null_issues) == 1
    assert null_issues[0]["column"] == "value"
    assert "%" in null_issues[0]["detail"]


def test_quality_duplicate_detection(client):
    fid = _upload(client, b"name,value\nAlice,100\nAlice,100\nBob,200\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    dup_issues = [i for i in resp.json()["issues"] if i["type"] == "duplicate"]
    assert len(dup_issues) == 1
    assert dup_issues[0]["column"] is None
    assert "duplicate" in dup_issues[0]["detail"]


def test_quality_outlier_detection(client):
    # 1000 is a clear outlier vs 1,2,3,4,5 (z-score >> 3)
    fid = _upload(client, b"val\n1\n2\n3\n4\n5\n1000\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    outlier_issues = [i for i in resp.json()["issues"] if i["type"] == "outlier"]
    assert len(outlier_issues) == 1
    assert outlier_issues[0]["column"] == "val"
    assert "modified z > 3.5" in outlier_issues[0]["detail"]


def test_quality_constant_column(client):
    fid = _upload(client, b"name,region\nAlice,VN\nBob,VN\nCarol,VN\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    const_issues = [i for i in resp.json()["issues"] if i["type"] == "constant"]
    assert any(i["column"] == "region" for i in const_issues)


def test_quality_dtype_mismatch(client):
    # order_date column name contains "date" but values are strings
    fid = _upload(client, b"order_date,value\n2026-01-01,100\n2026-01-02,200\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    dtype_issues = [i for i in resp.json()["issues"] if i["type"] == "dtype"]
    assert any(i["column"] == "order_date" for i in dtype_issues)


def test_quality_file_not_found(client):
    resp = client.get("/api/ml/quality/nonexistent-file-id")
    assert resp.status_code == 404


def test_quality_zero_std_no_crash(client):
    # All same value → std = 0, must not raise ZeroDivisionError
    fid = _upload(client, b"val\n5\n5\n5\n5\n5\n")
    resp = client.get(f"/api/ml/quality/{fid}")
    assert resp.status_code == 200
