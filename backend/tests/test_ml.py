import io
import math
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


CSV_CONTENT = b"name,value,date\nAlice,100,2026-01-01\nBob,200,2026-01-02\nCarol,150,2026-01-03\n"


def test_upload_csv(client):
    resp = client.post(
        "/api/ml/upload",
        files={"file": ("test.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    )
    assert resp.status_code == 201
    d = resp.json()
    assert d["filename"] == "test.csv"
    assert d["rows"] == 3
    assert d["cols"] == 3
    assert len(d["columns"]) == 3
    assert d["file_id"]


def test_query_basic(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("q.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    resp = client.post("/api/ml/query", json={
        "file_id": upload["file_id"],
        "sql": "SELECT name, value FROM data ORDER BY value DESC",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["columns"] == ["name", "value"]
    assert d["rows"][0] == ["Bob", 200]
    assert "duration_ms" in d


def test_query_invalid_sql(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("e.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    resp = client.post("/api/ml/query", json={
        "file_id": upload["file_id"],
        "sql": "SELECT * FROM nonexistent_table",
    })
    assert resp.status_code == 400


def test_query_unknown_file(client):
    resp = client.post("/api/ml/query", json={"file_id": "bad-id", "sql": "SELECT 1"})
    assert resp.status_code == 404


def test_list_datasets(client):
    client.post("/api/ml/upload", files={"file": ("a.csv", io.BytesIO(CSV_CONTENT), "text/csv")})
    resp = client.get("/api/ml/datasets")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_delete_dataset(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("del.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    assert client.delete(f"/api/ml/{upload['file_id']}").status_code == 204
    datasets = client.get("/api/ml/datasets").json()
    ids = [d["file_id"] for d in datasets]
    assert upload["file_id"] not in ids


NUMERIC_CSV = b"a,b,date\n1,10,2026-01-01\n2,20,2026-01-02\n3,30,2026-01-03\n4,40,2026-01-04\n5,50,2026-01-05\n"


def test_stats_describe(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("num.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "describe", "col_a": "a"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "mean" in d
    assert d["mean"] == pytest.approx(3.0)


def test_stats_correlation(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("num2.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "correlation",
        "col_a": "a", "col_b": "b"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["r"] == pytest.approx(1.0, abs=0.01)
    assert d["p_value"] < 0.05


def test_forecast(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("ts.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "a", "periods": 3
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["forecast"]) == 3
    assert "date" in d["forecast"][0]
    assert "value" in d["forecast"][0]


TS_MMYYYY = (
    b"month_year,revenue\n"
    b"01-2024,100\n02-2024,120\n03-2024,110\n04-2024,130\n05-2024,140\n"
    b"06-2024,135\n07-2024,150\n08-2024,160\n09-2024,155\n10-2024,170\n"
    b"11-2024,180\n12-2024,175\n01-2025,190\n02-2025,200\n03-2025,195\n"
)

def test_forecast_non_iso_dates(client):
    """Any method must work when date column uses MM-YYYY format."""
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("mmyyyy.csv", io.BytesIO(TS_MMYYYY), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "month_year",
        "value_col": "revenue",
        "periods": 3,
        "method": "linear",
        "seasonal_period": 12,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["forecast"]) == 3
    assert d["forecast"][0]["value"] > 0


def test_forecast_sarimax_insufficient_data_returns_unsuitable(client):
    """SARIMAX with data < 2*seasonal_period returns 200 with a friendly unsuitable
    card (suitable=False + reasons + recommended_method) instead of a 400 error."""
    rows = b"date,val\n"
    for i in range(10):
        rows += f"2024-{i+1:02d}-01,{100 + i * 10}\n".encode()
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("short.csv", io.BytesIO(rows), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date",
        "value_col": "val",
        "periods": 3,
        "method": "sarimax",
        "seasonal_period": 12,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["suitable"] is False
    assert any("24" in r for r in body["reasons"])
    assert body["recommended_method"] == "ets"
    assert "code" in body and "SARIMAX" in body["code"]


TS_20 = b"date,val\n" + b"".join(
    f"2024-{i+1:02d}-01,{100 + i * 5}\n".encode() for i in range(20)
)

def test_forecast_returns_history(client):
    """run_forecast must include 'history' list in response."""
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("ts20.csv", io.BytesIO(TS_20), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 3, "method": "linear", "seasonal_period": 12,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "history" in d
    assert len(d["history"]) > 0
    h0 = d["history"][0]
    assert "date" in h0
    assert "value" in h0
    assert "is_anomaly" in h0
    assert "z_score" in h0


TS_24 = b"date,val\n" + b"".join(
    f"202{3 + i // 12}-{i % 12 + 1:02d}-01,{100 + i * 3 + (i % 12) * 2}\n".encode()
    for i in range(24)
)

def test_forecast_compare(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("cmp.csv", io.BytesIO(TS_24), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast/compare", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 3,
        "seasonal_period": 12,
        "methods": ["linear", "moving_average", "ets"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "results" in d
    assert "best" in d
    assert len(d["results"]) == 3
    r0 = d["results"][0]
    assert "method" in r0
    assert "mape" in r0
    assert "rmse" in r0
    assert "status" in r0
    assert d["best"] in ["linear", "moving_average", "ets"]


def test_forecast_ets(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("ets24.csv", io.BytesIO(TS_24), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 6, "method": "ets", "seasonal_period": 12,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["method"].startswith("ETS")
    assert len(d["forecast"]) == 6
    assert "aic" in d
    assert "history" in d
    assert len(d["history"]) > 0


# 48 monthly points (2021-01 .. 2024-12), clear trend + sine seasonality →
# SARIMAX converges with FINITE confidence intervals.
TS_48 = b"date,val\n" + b"".join(
    f"{2021 + i // 12}-{i % 12 + 1:02d}-01,{100 + 2.0 * i + 15 * math.sin(2 * math.pi * i / 12):.4f}\n".encode()
    for i in range(48)
)


def test_forecast_sarimax_suitable_returns_forecast(client):
    """SARIMAX on a long, clean seasonal series returns 200 with finite forecast
    points AND finite 95% CIs.

    Regression for the numpy-vs-pandas bug: get_forecast() returns numpy arrays
    (the model is fit on a numpy array, so there is no pandas index), but the
    extraction used `.iloc`, raising AttributeError → uncaught 500 → the UI
    showed 'Dự báo thất bại.' every single time SARIMAX reached this branch.
    The unsuitable-data path was tested; this success path was not.
    """
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("sarimax48.csv", io.BytesIO(TS_48), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 6, "method": "sarimax", "seasonal_period": 12,
    })
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d.get("suitable") is not False        # forecast path, not the amber gate
    assert d["method"].startswith("SARIMAX")
    assert len(d["forecast"]) == 6
    for pt in d["forecast"]:
        assert isinstance(pt["value"], (int, float))
        assert pt["lower"] is not None and pt["upper"] is not None
        assert pt["lower"] <= pt["value"] <= pt["upper"]
    assert "history" in d and len(d["history"]) > 0


def test_forecast_sarimax_short_series_returns_forecast_not_500(client):
    """A 'suitable' but marginal series (n == 2*seasonal_period) yields a valid
    point forecast with non-estimable CIs (covariance → NaN). NaN is not JSON-
    encodable, which previously produced a raw 500. The endpoint must instead
    return 200 with finite point values and null CI bounds — never crash."""
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("sarimax24.csv", io.BytesIO(TS_24), "text/csv")},
    ).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": upload["file_id"],
        "date_col": "date", "value_col": "val",
        "periods": 4, "method": "sarimax", "seasonal_period": 12,
    })
    assert resp.status_code == 200, resp.text
    d = resp.json()
    assert d.get("suitable") is not False
    assert d["method"].startswith("SARIMAX")
    assert len(d["forecast"]) == 4
    for pt in d["forecast"]:
        assert isinstance(pt["value"], (int, float))          # point forecast always finite
        assert pt["lower"] is None or isinstance(pt["lower"], (int, float))
        assert pt["upper"] is None or isinstance(pt["upper"], (int, float))


def test_forecast_interpret_structure(client, monkeypatch):
    """interpret endpoint returns summary/trend/actions (mocked AI)."""
    import routers.ml as ml_module

    def mock_ai(prompt, max_tokens=1024):
        return '{"summary": "Doanh thu tăng đều.", "trend": "Xu hướng tăng nhẹ.", "actions": "Giữ nguyên chiến lược."}'

    monkeypatch.setattr(ml_module, "_call_ai_ml", mock_ai)

    resp = client.post("/api/ml/forecast/interpret", json={
        "method": "linear",
        "date_col": "date",
        "value_col": "revenue",
        "periods": 7,
        "result": {
            "slope": 1.5,
            "intercept": 100.0,
            "forecast": [
                {"date": "2026-01-01", "value": 150.0, "lower": 140.0, "upper": 160.0}
            ]
        },
        "filename": "test.csv",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "summary" in d
    assert "trend" in d
    assert "actions" in d


OUTLIER_CSV = b"val,cat\n1,a\n2,b\n2,c\n2,d\n2,e\n2,f\n2,g\n2,h\n2,i\n50,j\n"
# val = [1,2,2,2,2,2,2,2,2,50]  mean=6.7  std≈14.44 (ddof=0)  z(50)≈3.0


def test_stats_zscore(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("ztest.csv", io.BytesIO(OUTLIER_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "zscore", "col_a": "val"
    })
    assert resp.status_code == 200
    d = resp.json()
    assert "mean" in d
    assert "std" in d
    assert d["n"] == 10
    assert "rows" in d
    assert isinstance(d["rows"], list)
    assert len(d["rows"]) == 10
    assert "histogram_bins" in d
    assert isinstance(d["histogram_bins"], list)
    assert sum(b["count"] for b in d["histogram_bins"]) == 10
    assert d["rows"][0]["value"] == pytest.approx(50.0)
    assert abs(d["rows"][0]["z_score"]) > 2.0
    for row in d["rows"]:
        assert "idx" in row
        assert "value" in row
        assert "z_score" in row
    for bin_ in d["histogram_bins"]:
        assert "x0" in bin_
        assert "x1" in bin_
        assert "count" in bin_


def test_zscore_csv(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("zcsv.csv", io.BytesIO(OUTLIER_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/zscore_csv", json={
        "file_id": upload["file_id"], "col_a": "val"
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.content.decode("utf-8")
    header = text.splitlines()[0]
    assert "z_score" in header
    assert "z_status" in header
    assert "outlier" in text   # val=50 has |z| ~3.0 -> labeled outlier
    assert "normal"  in text   # val=1,2 rows have small z -> labeled normal


def test_stats_zscore_unknown_col(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("zbad.csv", io.BytesIO(OUTLIER_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "zscore", "col_a": "nonexistent"
    })
    assert resp.status_code == 400


BOX_SINGLE_CSV = b"val\n1\n2\n3\n4\n5\n6\n7\n8\n9\n100\n"
# val = [1..9, 100]  Q1≈3.25, Q3≈7.75, IQR≈4.5, upper_fence≈14.5 → outlier: 100

BOX_GROUPED_CSV = b"""val,grp
1,A
2,A
3,A
4,A
5,A
6,A
7,A
10,B
20,B
30,B
40,B
50,B
100,C
200,C
300,C
"""
# A: 7 rows (Q1≈2.5, Q3≈5.5, IQR=3.0)
# B: 5 rows (Q1=20, Q3=40, IQR=20)
# C: 3 rows  — DROPPED (n < 4)

BOX_SMALL_IQR_CSV = b"val\n1\n2\n2\n2\n2\n2\n"
# IQR will be 0 → handler must not crash


def test_stats_boxplot_single(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxs.csv", io.BytesIO(BOX_SINGLE_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot", "col_a": "val",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["total_n"] == 10
    assert d["total_groups"] == 1
    assert d["truncated"] is False
    assert len(d["groups"]) == 1
    g = d["groups"][0]
    assert g["name"] == "val"
    assert g["n"] == 10
    assert g["min"] == pytest.approx(1.0)
    assert g["max"] == pytest.approx(100.0)
    assert g["median"] == pytest.approx(5.5)
    assert g["iqr"] > 0
    assert g["upper_fence"] < 100
    assert len(g["outliers"]) == 1
    assert g["outliers"][0]["value"] == pytest.approx(100.0)


def test_stats_boxplot_grouped(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxg.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 200
    d = resp.json()
    # C dropped (n=3 < 4)
    assert len(d["groups"]) == 2
    names = {g["name"] for g in d["groups"]}
    assert names == {"A", "B"}
    # Order is top-N by count desc — A (7) before B (5)
    assert d["groups"][0]["name"] == "A"
    assert d["groups"][1]["name"] == "B"
    assert d["total_groups"] == 3        # before dropping (3 unique values)
    assert d["truncated"] is False        # max_groups (10) ≥ total_groups (3)


def test_stats_boxplot_max_groups(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxm.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    # Cap at 1 — only top group (A, count=7) returned
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp", "max_groups": 1,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["groups"]) == 1
    assert d["groups"][0]["name"] == "A"
    assert d["truncated"] is True


def test_stats_boxplot_drops_tiny_groups(client):
    """When all groups are too small, return 400."""
    tiny = b"val,grp\n1,A\n2,A\n1,B\n2,B\n"
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxt.csv", io.BytesIO(tiny), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 400


def test_stats_boxplot_handles_zero_iqr(client):
    """Constant-ish column (IQR=0) must not crash."""
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxz.csv", io.BytesIO(BOX_SMALL_IQR_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot", "col_a": "val",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["groups"]) == 1
    assert d["groups"][0]["iqr"] == pytest.approx(0.0)


def test_boxplot_outliers_csv(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxoc.csv", io.BytesIO(BOX_SINGLE_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/boxplot_outliers_csv", json={
        "file_id": upload["file_id"], "col_a": "val",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.content.decode("utf-8")
    header = text.splitlines()[0]
    assert "row_idx" in header
    assert "group"   in header
    assert "value"   in header
    assert "distance_iqr" in header
    # The outlier row (val=100) must appear
    assert "100" in text


def test_boxplot_stats_csv(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxsc.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/boxplot_stats_csv", json={
        "file_id": upload["file_id"], "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.content.decode("utf-8")
    header = text.splitlines()[0]
    for col in ["group", "n", "min", "q1", "median", "q3", "max",
                "iqr", "lower_fence", "upper_fence", "outlier_count"]:
        assert col in header
    # A and B should appear (C dropped due to n<4)
    assert "A" in text
    assert "B" in text


def test_stats_boxplot_handles_nan(client):
    """NaN values must be stripped before percentile (not crash with HTTP 500)."""
    csv = b"val\n1\n2\n3\n4\n5\n6\n7\n8\n9\nnan\n"
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxnan.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot", "col_a": "val",
    })
    assert resp.status_code == 200
    d = resp.json()
    # NaN dropped — n should be 9, not 10
    assert d["groups"][0]["n"] == 9


def test_stats_boxplot_max_groups_validates(client):
    """max_groups out of bounds returns 422."""
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxv.csv", io.BytesIO(BOX_GROUPED_CSV), "text/csv")},
    ).json()
    # max_groups=0 → 422
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp", "max_groups": 0,
    })
    assert resp.status_code == 422
    # max_groups=101 → 422
    resp = client.post("/api/ml/stats", json={
        "file_id": upload["file_id"], "test": "boxplot",
        "col_a": "val", "col_b": "grp", "max_groups": 101,
    })
    assert resp.status_code == 422


def test_boxplot_outliers_csv_preserves_comma_in_group_name(client):
    """Group name containing a comma must round-trip through CSV without corruption."""
    csv_in = b'val,grp\n1,"a,b"\n2,"a,b"\n3,"a,b"\n4,"a,b"\n5,"a,b"\n100,"a,b"\n'
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("boxc.csv", io.BytesIO(csv_in), "text/csv")},
    ).json()
    resp = client.post("/api/ml/stats/boxplot_outliers_csv", json={
        "file_id": upload["file_id"], "col_a": "val", "col_b": "grp",
    })
    assert resp.status_code == 200
    # Parse with csv.reader to verify proper quoting
    import csv as csvmod
    rows = list(csvmod.reader(resp.content.decode("utf-8").splitlines()))
    assert rows[0] == ["row_idx", "group", "value", "distance_iqr"]
    # Find the outlier row — group cell must equal "a,b" (not "a;b")
    data_rows = rows[1:]
    assert any(r[1] == "a,b" for r in data_rows), f"Expected 'a,b' group name, got rows: {data_rows}"


# ── Parquet sidecar cache (large-file performance) ───────────────────────────
# Excel/CSV are re-parsed from scratch on every request (~3s for a 726k-row
# xlsx). _load_df now caches a parquet sidecar next to the source so subsequent
# loads read the parquet (~50ms). These tests pin that behaviour.

def _sidecar_paths(file_id: str, filename: str):
    """Return (source_path, parquet_sidecar_path) inside the real uploads dir."""
    import database
    src = database.UPLOADS_DIR / f"{file_id}_{filename}"
    return src, src.with_name(src.name + ".parquet")


def test_load_creates_parquet_sidecar(client):
    """Uploading (which loads the df) must build a '<file>.parquet' sidecar."""
    up = client.post(
        "/api/ml/upload",
        files={"file": ("cache_probe.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    src, sidecar = _sidecar_paths(up["file_id"], "cache_probe.csv")
    try:
        assert sidecar.exists(), "parquet sidecar should be created on upload/load"
        # Query still returns correct data (served from the cache)
        r = client.post("/api/ml/query", json={
            "file_id": up["file_id"],
            "sql": "SELECT name, value FROM data ORDER BY value DESC",
        }).json()
        assert r["rows"][0] == ["Bob", 200]
    finally:
        client.delete(f"/api/ml/{up['file_id']}")


def test_delete_removes_parquet_sidecar(client):
    """Deleting a dataset must also remove its parquet sidecar (no orphans)."""
    up = client.post(
        "/api/ml/upload",
        files={"file": ("cache_del.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    src, sidecar = _sidecar_paths(up["file_id"], "cache_del.csv")
    assert sidecar.exists()
    assert client.delete(f"/api/ml/{up['file_id']}").status_code == 204
    assert not sidecar.exists(), "sidecar must be removed with the dataset"
    assert not src.exists()


def test_stale_source_invalidates_cache(client):
    """A source modified after caching must trigger a rebuild (no stale data)."""
    import os, time
    up = client.post(
        "/api/ml/upload",
        files={"file": ("cache_stale.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    src, sidecar = _sidecar_paths(up["file_id"], "cache_stale.csv")
    try:
        assert sidecar.exists()
        # Overwrite the source with new data and push its mtime past the sidecar
        src.write_bytes(b"name,value,date\nZoe,999,2026-02-02\n")
        future = time.time() + 10
        os.utime(src, (future, future))
        r = client.post("/api/ml/query", json={
            "file_id": up["file_id"], "sql": "SELECT name, value FROM data",
        }).json()
        assert r["rows"][0] == ["Zoe", 999], "stale cache served instead of rebuilding"
    finally:
        client.delete(f"/api/ml/{up['file_id']}")


def test_datasets_columns_via_schema(client):
    """/datasets must still report correct columns (now via parquet schema)."""
    up = client.post(
        "/api/ml/upload",
        files={"file": ("cache_cols.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
    ).json()
    try:
        ds = client.get("/api/ml/datasets").json()
        mine = next(d for d in ds if d["file_id"] == up["file_id"])
        assert [c["name"] for c in mine["columns"]] == ["name", "value", "date"]
    finally:
        client.delete(f"/api/ml/{up['file_id']}")


# ── Correlation matrix endpoint (Component 3) ──────────────────────────────
CORR_CONST_CSV = (
    b"x,y,flag\n"
    b"1,2,1\n2,4,1\n3,6,1\n4,8,1\n5,10,1\n"
)  # x,y perfectly correlated; flag constant -> excluded (used to 500)


def test_correlation_excludes_constant_column(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("corr.csv", io.BytesIO(CORR_CONST_CSV), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{up['file_id']}/correlation")
    assert resp.status_code == 200
    d = resp.json()
    assert "flag" not in d["columns"]
    assert {e["name"] for e in d["excluded_columns"]} == {"flag"}
    assert d["excluded_columns"][0]["reason"] == "constant"
    i = d["columns"].index("x")
    j = d["columns"].index("y")
    assert d["matrix"][i][i] == 1.0
    assert d["matrix"][i][j] == pytest.approx(1.0, abs=0.01)


def test_correlation_handles_nulls_pairwise(client):
    csv = b"a,b\n1,10\n2,\n3,30\n4,40\n,50\n"
    up = client.post(
        "/api/ml/upload",
        files={"file": ("corrn.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{up['file_id']}/correlation")
    assert resp.status_code == 200
    d = resp.json()
    assert d["matrix"][0][0] == 1.0  # diagonal always 1.0


def test_correlation_too_few_varying_columns(client):
    csv = b"k,c\n1,9\n2,9\n3,9\n"  # only k varies; c constant -> <2 usable
    up = client.post(
        "/api/ml/upload",
        files={"file": ("corr1.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{up['file_id']}/correlation")
    assert resp.status_code == 400


# ── /timeseries endpoint (Component 1) ─────────────────────────────────────
def test_timeseries_monthly_pop(client):
    csv = (
        b"date,rev\n"
        b"2024-01-05,10\n2024-01-20,20\n"
        b"2024-02-10,30\n2024-02-15,5\n"
        b"2024-03-01,40\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("tsm.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/timeseries", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "rev",
        "grain": "month", "agg": "sum", "comparisons": ["pop"],
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["grain"] == "month"
    assert d["series"]["labels"] == ["2024-01", "2024-02", "2024-03"]
    assert d["series"]["values"] == [30.0, 35.0, 40.0]
    assert d["comparisons"]["pop"]["values"] == [None, 30.0, 35.0]
    assert "yoy" not in d["comparisons"]   # only requested keys present


def test_timeseries_yoy(client):
    csv = (
        b"date,rev\n"
        b"2023-01-15,100\n2023-02-15,200\n"
        b"2024-01-15,150\n2024-02-15,180\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("tsy.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/timeseries", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "rev",
        "grain": "month", "agg": "sum", "comparisons": ["yoy"],
    })
    d = resp.json()
    assert d["series"]["values"] == [100.0, 200.0, 150.0, 180.0]
    assert d["comparisons"]["yoy"]["values"] == [None, None, 100.0, 200.0]
    assert d["comparisons"]["yoy"]["delta_pct"] == [None, None, 50.0, -10.0]


def test_timeseries_auto_grain_meta(client):
    # ~2.4 years of monthly rows -> auto should pick "month"
    rows = b"date,v\n"
    for y in (2022, 2023, 2024):
        for m in range(1, 13):
            rows += f"{y}-{m:02d}-01,{y + m}\n".encode()
    up = client.post("/api/ml/upload",
                     files={"file": ("tsa.csv", io.BytesIO(rows), "text/csv")}).json()
    resp = client.post("/api/ml/timeseries", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "v",
        "grain": "auto", "agg": "sum",
    })
    d = resp.json()
    assert d["grain"] == "month"
    assert d["meta"]["suggested_grain"] == "month"
    assert d["meta"]["periods"] == 36


# ── Forecast by grain (Component 2) ────────────────────────────────────────
def _daily_csv(start_year=2024, n_days=150):
    import datetime as _dt
    base = _dt.date(start_year, 1, 1)
    rows = b"date,val\n"
    for i in range(n_days):
        d = base + _dt.timedelta(days=i)
        rows += f"{d.isoformat()},{100 + i}\n".encode()
    return rows


def test_forecast_grain_month_steps_by_month(client):
    up = client.post("/api/ml/upload",
                     files={"file": ("fc.csv", io.BytesIO(_daily_csv()), "text/csv")}).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "val",
        "periods": 3, "method": "linear", "grain": "month", "agg": "sum",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert len(d["forecast"]) == 3
    from datetime import date as _D
    ds = [_D.fromisoformat(f["date"]) for f in d["forecast"]]
    # consecutive forecast points are ~1 month apart, not 1 day
    assert (ds[1] - ds[0]).days >= 27
    assert d["forecast"][0]["value"] > 0


def test_forecast_raw_grain_steps_by_day(client):
    up = client.post("/api/ml/upload",
                     files={"file": ("fcr.csv", io.BytesIO(_daily_csv(n_days=30)), "text/csv")}).json()
    resp = client.post("/api/ml/forecast", json={
        "file_id": up["file_id"], "date_col": "date", "value_col": "val",
        "periods": 3, "method": "linear", "grain": "raw",
    })
    d = resp.json()
    from datetime import date as _D
    ds = [_D.fromisoformat(f["date"]) for f in d["forecast"]]
    assert (ds[1] - ds[0]).days == 1


# ── /profile endpoint (Component 4) ────────────────────────────────────────
def test_profile_roles(client):
    csv = (
        b"order_date,customer_id,region,amount,is_paid\n"
        b"2024-01-01,C001,North,100,1\n"
        b"2024-01-02,C002,South,200,1\n"
        b"2024-01-03,C003,North,150,0\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("prof.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.get(f"/api/ml/profile/{up['file_id']}")
    assert resp.status_code == 200
    cols = {c["name"]: c for c in resp.json()["columns"]}
    assert cols["order_date"]["role"] == "date"
    assert cols["customer_id"]["role"] == "id"
    assert cols["region"]["role"] == "dimension"
    assert cols["amount"]["role"] == "metric"
    assert cols["is_paid"]["role"] == "flag"
    assert cols["amount"]["min"] == 100.0
    assert cols["amount"]["max"] == 200.0


# ── Cohort suitability gate (Component 5) ──────────────────────────────────
def test_cohort_gate_blocks_no_recurrence(client):
    csv = b"date,cust\n2024-01-01,A\n2024-02-01,B\n2024-03-01,C\n2024-04-01,D\n"
    up = client.post("/api/ml/upload",
                     files={"file": ("coh1.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/cohort", json={
        "file_id": up["file_id"], "date_col": "date", "user_col": "cust", "period": "month",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["suitable"] is False
    assert d["reasons"]
    assert d["role_hint"]["user"] == "cust"


def test_cohort_gate_allows_recurring(client):
    csv = (
        b"date,user\n"
        b"2024-01-05,U1\n2024-02-05,U1\n2024-01-06,U2\n2024-03-06,U2\n2024-02-10,U3\n"
    )
    up = client.post("/api/ml/upload",
                     files={"file": ("coh2.csv", io.BytesIO(csv), "text/csv")}).json()
    resp = client.post("/api/ml/cohort", json={
        "file_id": up["file_id"], "date_col": "date", "user_col": "user", "period": "month",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d.get("suitable") is not False    # normal result, no gate
    assert "matrix" in d


# ── Cohort quarter period (Component 5, Task 12) ──────────────────────────────
def test_cohort_quarter_offsets_are_monotonic(client):
    # Both users acquired 2024-Q1. U1 returns in Q2 (offset 1); U2 in Q4 (offset 3).
    # Each user also spans 2 distinct months → passes the suitability gate
    # (check_suitability measures recurrence by month, not by the chosen period).
    csv = (
        b"date,user\n"
        b"2024-01-15,U1\n2024-04-15,U1\n"
        b"2024-02-10,U2\n2024-10-10,U2\n"
    )
    up = client.post(
        "/api/ml/upload",
        files={"file": ("cohq.csv", io.BytesIO(csv), "text/csv")},
    ).json()
    resp = client.post("/api/ml/cohort", json={
        "file_id": up["file_id"], "date_col": "date", "user_col": "user",
        "period": "quarter",
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d.get("suitable") is not False     # gate passed → full result (no suitable key)
    assert d["cohorts"] == ["2024-Q1"]        # both acquired Q1 2024 → one cohort
    assert d["periods"] == [0, 1, 2, 3]       # max offset 3 ⇒ 4 columns
    assert d["matrix"][0][0] == 100.0         # offset 0 = 2/2 users
    assert d["matrix"][0][1] == 50.0          # offset 1 = U1 only
    assert d["matrix"][0][3] == 50.0          # offset 3 = U2 only


def test_describe_endpoint_returns_rows_and_code(client):
    upload = client.post(
        "/api/ml/upload",
        files={"file": ("num.csv", io.BytesIO(NUMERIC_CSV), "text/csv")},
    ).json()
    resp = client.get(f"/api/ml/{upload['file_id']}/describe")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"rows", "code"}
    a = next(r for r in body["rows"] if r["col"] == "a")
    assert a["median"] == pytest.approx(3.0)
    assert a["range"] == pytest.approx(4.0)      # max 5 − min 1
    # non-numeric column: present in rows but without numeric stats
    date_row = next(r for r in body["rows"] if r["col"] == "date")
    assert "median" not in date_row
    assert "range" not in date_row
    assert "import polars" in body["code"]


DRILL_CSV = (
    b"d,v\n"
    b"2024-01-15,10\n2024-01-20,5\n2024-07-03,7\n"
    b"2025-03-10,20\n2025-03-11,2\n"
)


def test_drilldown_year_level(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(DRILL_CSV), "text/csv")},
    ).json()
    r = client.get(f"/api/ml/{up['file_id']}/drilldown",
                   params={"date_col": "d", "value_col": "v", "agg": "sum", "grain": "year"})
    assert r.status_code == 200
    b = r.json()
    assert b["labels"] == ["2024", "2025"]
    assert b["values"] == [22.0, 22.0]          # 2024: 10+5+7 ; 2025: 20+2
    assert "code" in b


def test_drilldown_month_within_year(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(DRILL_CSV), "text/csv")},
    ).json()
    r = client.get(f"/api/ml/{up['file_id']}/drilldown",
                   params={"date_col": "d", "value_col": "v", "grain": "month", "year": 2024})
    assert r.status_code == 200
    b = r.json()
    assert b["labels"] == ["2024-01", "2024-07"]
    assert b["values"] == [15.0, 7.0]           # Jan: 10+5 ; Jul: 7


def test_drilldown_empty_after_filter(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(DRILL_CSV), "text/csv")},
    ).json()
    r = client.get(f"/api/ml/{up['file_id']}/drilldown",
                   params={"date_col": "d", "value_col": "v", "grain": "month", "year": 9999})
    assert r.status_code == 200
    b = r.json()
    assert b["labels"] == []
    assert b["values"] == []
    assert "code" in b                          # snippet still returned for empty result


def test_drilldown_missing_column_returns_400(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(DRILL_CSV), "text/csv")},
    ).json()
    r = client.get(f"/api/ml/{up['file_id']}/drilldown",
                   params={"date_col": "nope", "value_col": "v", "grain": "year"})
    assert r.status_code == 400
