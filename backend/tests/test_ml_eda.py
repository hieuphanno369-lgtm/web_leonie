import polars as pl
from analytics.eda import infer_role, profile_columns


def test_infer_role_basic():
    df = pl.DataFrame({
        "id": [1, 2, 3, 4],
        "amount": [10.0, 20.0, 30.0, 40.0],
        "city": ["A", "B", "A", "C"],
        "active": [True, False, True, False],
        "order_date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
    })
    roles = {c["name"]: c["role"] for c in profile_columns(df)}
    assert roles["id"] == "id"
    assert roles["amount"] == "metric"
    assert roles["city"] == "dimension"
    assert roles["active"] == "flag"
    assert roles["order_date"] == "date"


def test_profile_columns_null_pct_and_constant():
    df = pl.DataFrame({"k": [1, None, 3, None], "const": ["x", "x", "x", "x"]})
    prof = {c["name"]: c for c in profile_columns(df)}
    assert prof["k"]["null_pct"] == 50.0
    assert prof["const"]["is_constant"] is True
    assert prof["const"]["cardinality"] == 1


from analytics.eda import correlation_matrix


def test_correlation_matrix_perfect_positive():
    df = pl.DataFrame({"a": [1.0, 2, 3, 4], "b": [2.0, 4, 6, 8], "c": [4.0, 3, 2, 1]})
    cm = correlation_matrix(df)
    i = cm["columns"].index("a"); j = cm["columns"].index("b"); k = cm["columns"].index("c")
    assert round(cm["matrix"][i][j], 3) == 1.0
    assert round(cm["matrix"][i][k], 3) == -1.0
    assert cm["matrix"][i][i] == 1.0


def test_correlation_matrix_excludes_constant_and_allnull():
    df = pl.DataFrame({"a": [1.0, 2, 3], "const": [5.0, 5, 5], "x": [None, None, None]})
    cm = correlation_matrix(df)
    assert "a" in cm["columns"]
    assert "const" not in cm["columns"]
    excluded = {e["name"] for e in cm["excluded_columns"]}
    assert "const" in excluded


from analytics.eda import numeric_distributions


def test_numeric_distributions_bins_and_stats():
    df = pl.DataFrame({"v": [float(i) for i in range(100)], "label": ["x"] * 100})
    dists = numeric_distributions(df, ["v"], log_transform="off")
    assert len(dists) == 1
    d = dists[0]
    assert d["column"] == "v"
    assert sum(b["count"] for b in d["bins"]) == 100
    assert d["min"] == 0.0 and d["max"] == 99.0
    assert abs(d["mean"] - 49.5) < 1e-6
    assert d["log_applied"] is False


def test_numeric_distributions_auto_log_on_skew():
    # Heavy right skew, all positive -> auto log.
    vals = [1.0] * 90 + [1000.0] * 10
    df = pl.DataFrame({"v": vals})
    dists = numeric_distributions(df, ["v"], log_transform="auto")
    assert dists[0]["skew"] > 1.0
    assert dists[0]["log_applied"] is True


from analytics.eda import segment_breakdown


def test_segment_breakdown_table_and_scatter():
    df = pl.DataFrame({
        "city": ["A", "A", "B", "B", "C"],
        "rev":  [10.0, 20, 30, 40, 50],
        "qty":  [1.0, 2, 3, 4, 5],
    })
    bd = segment_breakdown(df, "city", ["rev", "qty"], top_n=2, sample_n=100)
    # top_n=2 by row count -> A and B (2 each) before C (1).
    seg_names = {r["segment"] for r in bd["table"]}
    assert seg_names == {"A", "B"}
    a = next(r for r in bd["table"] if r["segment"] == "A")
    assert a["count"] == 2
    assert a["rev_sum"] == 30.0
    # scatter uses first two metrics.
    assert bd["scatter"]["x_col"] == "rev"
    assert bd["scatter"]["y_col"] == "qty"
    assert len(bd["scatter"]["points"]) == 5


def test_segment_breakdown_no_metrics():
    df = pl.DataFrame({"city": ["A", "B"]})
    bd = segment_breakdown(df, "city", [], top_n=10, sample_n=100)
    assert bd["scatter"]["points"] == []
    assert len(bd["table"]) == 2


from analytics.eda import derive_rule_insights


def test_derive_rule_insights_shape_and_content():
    profile = [
        {"name": "rev", "role": "metric", "null_pct": 0.0, "is_constant": False, "cardinality": 50},
        {"name": "note", "role": "dimension", "null_pct": 80.0, "is_constant": False, "cardinality": 5},
    ]
    corr = {"columns": ["rev", "qty"], "matrix": [[1.0, 0.95], [0.95, 1.0]], "excluded_columns": []}
    dists = [{"column": "rev", "skew": 3.2, "log_applied": True, "mean": 10, "median": 2,
              "std": 5, "min": 0, "max": 100, "bins": []}]
    segs = {"table": [{"segment": "A", "count": 80}, {"segment": "B", "count": 20}],
            "scatter": {"x_col": None, "y_col": None, "points": []}}
    ins = derive_rule_insights(profile, corr, dists, segs, total_rows=100, max_insights=5)
    assert 1 <= len(ins) <= 5
    for it in ins:
        assert set(it.keys()) >= {"finding", "so_what", "action", "severity"}
    blob = " ".join(i["finding"] for i in ins)
    assert "note" in blob          # high-null column flagged
    assert "rev" in blob           # skew or correlation flagged


def test_derive_rule_insights_never_empty():
    profile = [{"name": "x", "role": "dimension", "null_pct": 0.0, "is_constant": False, "cardinality": 3}]
    corr = {"columns": [], "matrix": [], "excluded_columns": []}
    ins = derive_rule_insights(profile, corr, [], {"table": [], "scatter": {}}, total_rows=10)
    assert len(ins) >= 1


import io
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


EDA_CSV = (
    b"city,rev,qty,note\n"
    b"A,10,1,x\nA,20,2,\nB,30,3,y\nB,40,4,\nC,50,5,z\n"
)


def test_eda_report_structure(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("e.csv", io.BytesIO(EDA_CSV), "text/csv")},
    ).json()
    resp = client.post(f"/api/ml/{up['file_id']}/eda", json={"segment_col": "city"})
    assert resp.status_code == 200
    d = resp.json()
    for key in ("meta", "profile", "correlation", "distributions",
                "segments", "insights", "insights_source"):
        assert key in d
    assert d["meta"]["rows"] == 5
    assert len(d["profile"]) == 4
    # No API key + no Ollama in CI -> rule-based fallback, never empty.
    assert d["insights_source"] in ("ai", "rule")
    assert len(d["insights"]) >= 1
    assert {"finding", "so_what", "action"} <= set(d["insights"][0].keys())


def test_eda_unknown_file(client):
    assert client.post("/api/ml/bad-id/eda", json={}).status_code == 404
