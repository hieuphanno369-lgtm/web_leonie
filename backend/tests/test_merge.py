from analytics.merge import normalize_field, clean_phone


def test_normalize_field_strips_case_space_colon():
    assert normalize_field("  Số điện thoại liên hệ:  ") == "số điện thoại liên hệ"
    assert normalize_field("Phone") == "phone"
    assert normalize_field("PHONE ") == "phone"
    assert normalize_field("first   name") == "first name"


def test_normalize_field_handles_non_str():
    assert normalize_field(123) == "123"


def test_clean_phone_normalizes_vn():
    assert clean_phone("0987.654.321") == "0987654321"
    assert clean_phone("84987654321") == "0987654321"
    assert clean_phone("(+84) 987 654 321") == "0987654321"


def test_clean_phone_rejects_short_or_empty():
    assert clean_phone("12345") is None
    assert clean_phone("") is None
    assert clean_phone(None) is None
    assert clean_phone("abc") is None


from analytics.merge import common_fields


def test_common_fields_intersection_default():
    schemas = [
        ["Phone", "Name", "Age"],
        ["phone ", "name", "Product"],
        ["PHONE", "Branch"],
    ]
    # Only the normalized field present in ALL three is "phone"
    # (Name is in 2/3, Age/Product/Branch in 1/3 — all excluded by strict intersection).
    assert common_fields(schemas) == ["Phone"]


def test_common_fields_preserves_first_display_name_and_order():
    schemas = [
        ["Email:", "Phone"],
        ["email", "phone"],
    ]
    assert common_fields(schemas) == ["Email:", "Phone"]


def test_common_fields_threshold_below_one():
    schemas = [
        ["a", "b"],
        ["a", "c"],
        ["a", "b"],
    ]
    # threshold 0.5 -> present in >= 1.5 schemas: a(3), b(2) qualify; c(1) does not.
    assert common_fields(schemas, threshold=0.5) == ["a", "b"]


def test_common_fields_empty():
    assert common_fields([]) == []


import polars as pl
from analytics.merge import align_and_merge, MergeSummary


def test_align_and_merge_unions_and_aligns_by_normalized_name():
    f1 = pl.DataFrame({"Phone": ["0987654321"], "Name": ["A"]})
    f2 = pl.DataFrame({"phone ": ["0912345678"], "Product": ["X"]})
    clean, _rej, summary = align_and_merge(
        [f1, f2], selected=["Phone", "Name", "Product"],
    )
    assert clean.columns == ["Phone", "Name", "Product"]
    assert clean.height == 2
    assert clean["Name"].to_list() == ["A", None]
    assert clean["Product"].to_list() == [None, "X"]
    assert summary.total_raw == 2


def test_align_and_merge_dedup_and_phone_clean():
    f1 = pl.DataFrame({"phone": ["0987.654.321", "0987654321", None],
                       "name": ["A", "B", "C"]})
    f2 = pl.DataFrame({"phone": ["84987654321"], "name": ["D"]})
    clean, _rej, summary = align_and_merge(
        [f1, f2], selected=["phone", "name"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        drop_invalid_key=True,
    )
    assert summary.total_raw == 4
    assert summary.null_or_wrong == 1
    assert summary.valid_format == 3
    assert summary.distinct == 1
    assert summary.dup_removed_clean == 2
    assert clean.height == 1
    assert clean["phone"].to_list() == ["0987654321"]


def test_align_and_merge_complete_records():
    f1 = pl.DataFrame({"phone": ["0987654321", "0912345678"],
                       "name": ["A", None], "age": ["5", "6"]})
    clean, _rej, summary = align_and_merge(
        [f1], selected=["phone", "name", "age"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        required_fields=["name", "age"],
    )
    assert summary.complete == 1
    assert isinstance(summary, MergeSummary)


def test_align_and_merge_keeps_null_keys_when_not_dropping():
    f1 = pl.DataFrame({"phone": ["0987654321", None], "name": ["A", "B"]})
    clean, _rej, summary = align_and_merge(
        [f1], selected=["phone", "name"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        drop_invalid_key=False,
    )
    assert clean.height == 2
    assert summary.null_or_wrong == 1


def test_read_source_reads_parquet(tmp_path):
    from routers.ml import _read_source
    p = tmp_path / "x.parquet"
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_parquet(p)
    df = _read_source(str(p))
    assert df.columns == ["a", "b"]
    assert df.height == 2


import io
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


CSV_A = b"Phone,Name,Age\n0987654321,Alice,5\n0912345678,Bob,6\n"
CSV_B = b"phone,Name,Product\n0987654321,Alice,Milk\n0900000000,Carol,Juice\n"


def test_merge_stage_returns_common_fields_profiles_suggestions(client):
    resp = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["session_id"]
    assert len(d["files"]) == 2
    assert set(normalize_field(f) for f in d["common_fields"]) == {"phone", "name"}
    assert "Age" in d["all_fields"] and "Product" in d["all_fields"]
    # NEW: profiles for every (file, column) + value-aware suggestions.
    assert any(p["name"] == "Phone" and p["inferred_type"] == "phone" for p in d["profiles"])
    assert isinstance(d["suggestions"], list)
    # Phone present in both files -> a unify suggestion of type "phone".
    assert any(s["inferred_type"] == "phone" for s in d["suggestions"])


def test_merge_run_registers_dataset(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    ).json()
    resp = client.post("/api/ml/merge/run", json={
        "session_id": stage["session_id"],
        "selected_fields": ["Phone", "Name"],
        "alias_map": {},
        "options": {"dedup_key": "Phone", "drop_invalid_key": True, "trim": True,
                    "semantic_types": {"Phone": "phone"},
                    "field_groups": {"Phone": ["Phone", "phone"]},
                    "required_fields": ["Name"], "coalesce": True},
        "dry_run": False,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["summary"]["total_raw"] == 4
    assert d["summary"]["distinct"] == 3
    assert d["summary"]["dup_removed_clean"] == 1
    assert d["dataset"] is not None
    assert d["rejected_url"]
    fid = d["dataset"]["file_id"]
    assert d["dataset"]["rows"] == 3
    q = client.post("/api/ml/query", json={
        "file_id": fid, "sql": "SELECT COUNT(*) AS n FROM data",
    })
    assert q.status_code == 200
    assert q.json()["rows"][0][0] == 3


def test_merge_run_dry_run_returns_preview_no_dataset(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("a.csv", io.BytesIO(CSV_A), "text/csv"))],
    ).json()
    resp = client.post("/api/ml/merge/run", json={
        "session_id": stage["session_id"],
        "selected_fields": ["Phone", "Name", "Age"],
        "options": {"dedup_key": "Phone", "semantic_types": {"Phone": "phone"}},
        "dry_run": True,
    })
    assert resp.status_code == 200
    d = resp.json()
    assert d["dataset"] is None
    assert isinstance(d["preview"], list) and len(d["preview"]) >= 1
    assert "Phone" in d["preview"][0]
    assert d["summary"]["total_raw"] == 2


def test_merge_run_unknown_session(client):
    resp = client.post("/api/ml/merge/run", json={
        "session_id": "nope", "selected_fields": ["a"],
    })
    assert resp.status_code == 404


def test_merge_delete_session(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("a.csv", io.BytesIO(CSV_A), "text/csv"))],
    ).json()
    sid = stage["session_id"]
    assert client.delete(f"/api/ml/merge/{sid}").status_code == 204
    # Running a deleted session is a 404.
    resp = client.post("/api/ml/merge/run", json={
        "session_id": sid, "selected_fields": ["Phone"],
    })
    assert resp.status_code == 404


def test_download_csv_and_xlsx(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d.csv", io.BytesIO(CSV_A), "text/csv")},
    ).json()
    fid = up["file_id"]

    csv = client.get(f"/api/ml/{fid}/download?fmt=csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert b"Phone" in csv.content

    xlsx = client.get(f"/api/ml/{fid}/download?fmt=xlsx")
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert xlsx.content[:2] == b"PK"  # xlsx is a zip


def test_download_bad_fmt(client):
    up = client.post(
        "/api/ml/upload",
        files={"file": ("d2.csv", io.BytesIO(CSV_A), "text/csv")},
    ).json()
    assert client.get(f"/api/ml/{up['file_id']}/download?fmt=json").status_code == 400


from analytics.merge import normalize_value, is_valid


def test_normalize_value_phone_lenient():
    assert normalize_value("0987.654.321", "phone") == "0987654321"
    assert normalize_value("84987654321", "phone") == "0987654321"
    assert normalize_value("123", "phone") is None
    assert is_valid("84987654321", "phone") is True
    assert is_valid("123", "phone") is False


def test_normalize_value_email_trims_lowercases():
    assert normalize_value("  Foo@Bar.COM ", "email") == "foo@bar.com"
    assert is_valid("Foo@Bar.com", "email") is True
    assert is_valid("not-an-email", "email") is False


def test_normalize_value_date_to_iso():
    assert normalize_value("31/12/2024", "date") == "2024-12-31"
    assert normalize_value("2024-01-05", "date") == "2024-01-05"
    assert normalize_value("05-06-2024", "date") == "2024-06-05"
    assert normalize_value("nope", "date") is None
    assert is_valid("31/12/2024", "date") is True


def test_normalize_value_number_strips_separators():
    # MVP rule: '.', ',', spaces are thousands separators (decimals not kept).
    assert normalize_value("1.234", "number") == "1234"
    assert normalize_value("1,234", "number") == "1234"
    assert normalize_value("12 345", "number") == "12345"
    assert normalize_value("abc", "number") is None
    assert is_valid("12 345", "number") is True


def test_normalize_value_category_and_text():
    assert normalize_value("  Ha   Noi ", "category") == "Ha Noi"
    assert normalize_value("  free   text ", "text") == "free   text"
    assert is_valid("", "category") is False
    assert is_valid("  ", "text") is False


from analytics.merge import profile_columns, ColumnProfile


def test_profile_columns_infers_types_and_samples():
    f1 = pl.DataFrame({
        "SĐT":   ["0987654321", "0912345678", "84900000000"],
        "Email": ["a@x.com", "b@y.com", "c@z.com"],
        "Ngày":  ["01/02/2024", "2024-03-04", "05-06-2024"],
        "Tỉnh":  ["Hà Nội", "Hà Nội", "Đà Nẵng"],
    })
    profs = profile_columns([f1], ["f1.csv"])
    by_name = {p.name: p for p in profs}
    assert by_name["SĐT"].inferred_type == "phone"
    assert by_name["Email"].inferred_type == "email"
    assert by_name["Ngày"].inferred_type == "date"
    assert by_name["Tỉnh"].inferred_type == "category"
    p = by_name["SĐT"]
    assert isinstance(p, ColumnProfile)
    assert p.file == "f1.csv"
    assert p.non_null == 3 and p.distinct == 3
    assert 0.0 < p.confidence <= 1.0
    assert len(p.samples) <= 5 and len(p.samples) >= 1


def test_profile_columns_fill_rate_and_text_fallback():
    f1 = pl.DataFrame({"note": ["hello world this is free text", None, "another distinct sentence"]})
    profs = profile_columns([f1], ["n.csv"])
    p = profs[0]
    assert p.inferred_type == "text"
    assert p.non_null == 2
    assert p.fill_rate == round(2 / 3, 3)


from analytics.merge import suggest_groups, FieldGroupSuggestion


def test_suggest_groups_unifies_phone_columns_under_different_names():
    # Three differently-named columns that all hold phone values (the core
    # "value giống nhau, tên khác" case) → one canonical group.
    f1 = pl.DataFrame({"SĐT": ["0987654321", "0912345678"]})
    f2 = pl.DataFrame({"Mobile": ["0900000001", "0900000002"]})
    f3 = pl.DataFrame({"Liên hệ": ["0900000003", "0900000004"]})
    profs = profile_columns([f1, f2, f3], ["a", "b", "c"])
    sugg = suggest_groups(profs)
    phone_groups = [s for s in sugg if s.inferred_type == "phone"]
    assert len(phone_groups) == 1
    g = phone_groups[0]
    assert isinstance(g, FieldGroupSuggestion)
    assert set(g.members) == {"SĐT", "Mobile", "Liên hệ"}
    assert g.reason in ("type", "name+type")


def test_suggest_groups_clusters_similar_names_for_generic_types():
    f1 = pl.DataFrame({"Tỉnh thành": ["Hà Nội", "Đà Nẵng", "Huế"]})
    f2 = pl.DataFrame({"Tỉnh": ["Hà Nội", "HCM", "Cần Thơ"]})
    profs = profile_columns([f1, f2], ["a", "b"])
    sugg = suggest_groups(profs)
    cat = [s for s in sugg if s.inferred_type == "category"]
    assert len(cat) == 1
    assert set(cat[0].members) == {"Tỉnh thành", "Tỉnh"}
    assert cat[0].reason == "name"


def test_suggest_groups_ignores_singletons():
    f1 = pl.DataFrame({"only": ["unique long free text value here", "another one entirely"]})
    profs = profile_columns([f1], ["a"])
    assert suggest_groups(profs) == []


from analytics.merge import align_and_merge as merge_v2


def test_merge_v2_returns_clean_rejected_summary_and_coalesces():
    # Same phone under two names; one row complete, its duplicate fills the gap.
    f1 = pl.DataFrame({"SĐT": ["0987654321", "0912345678", ""],
                       "Tên":  ["An", None, "Z"],
                       "Email": ["an@x.com", None, None]})
    f2 = pl.DataFrame({"Phone": ["84987654321"],
                       "Tên":   [None],
                       "Email": ["an2@x.com"]})
    clean, rejected, summary = merge_v2(
        [f1, f2], selected=["SĐT", "Tên", "Email"],
        filenames=["f1", "f2"],
        field_groups={"SĐT": ["SĐT", "Phone"]},
        semantic_types={"SĐT": "phone", "Email": "email", "Tên": "text"},
        dedup_key="SĐT", required_fields=["Tên", "Email"],
        coalesce=True, drop_invalid_key=True,
    )
    # 4 raw rows; "" phone is invalid -> rejected; 0987654321 appears 3x (f1 + f2)
    assert summary.total_raw == 4
    assert summary.null_or_wrong == 1
    assert summary.valid_format == 3
    assert summary.distinct == 2                 # 0987654321, 0912345678
    assert summary.dup_removed_clean == 1        # 3 valid - 2 distinct
    assert summary.dup_removed_raw == 2          # 4 raw - 2 distinct
    assert summary.rejected == 1
    assert clean.height == 2
    assert rejected.height == 1
    # Coalesce: the 0987654321 group fills Tên="An" (from f1 row 1).
    row = clean.filter(pl.col("SĐT") == "0987654321").to_dicts()[0]
    assert row["Tên"] == "An" and row["Email"] == "an@x.com"
    # complete = groups with Tên AND Email non-null after coalesce.
    assert summary.complete == 1
    assert summary.incomplete == 1
    assert set(summary.per_file_contribution) == {"f1", "f2"}
    assert "Email" in summary.per_field_fill_rate


def test_merge_v2_keeps_invalid_when_not_dropping():
    f1 = pl.DataFrame({"phone": ["0987654321", ""], "name": ["A", "B"]})
    clean, rejected, summary = merge_v2(
        [f1], selected=["phone", "name"], filenames=["f"],
        semantic_types={"phone": "phone"}, dedup_key="phone",
        drop_invalid_key=False,
    )
    assert clean.height == 2          # 1 valid distinct + 1 invalid kept
    assert rejected.height == 0
    assert summary.null_or_wrong == 1


def test_merge_v2_no_key_passthrough():
    f1 = pl.DataFrame({"a": ["1", "2"], "b": ["x", "y"]})
    clean, rejected, summary = merge_v2(
        [f1], selected=["a", "b"], filenames=["f"], required_fields=["b"],
    )
    assert clean.height == 2
    assert summary.distinct == 2
    assert summary.complete == 2
    assert summary.dup_removed_raw == 0


def _notebook_fixture():
    """Two frames engineered to reproduce the notebook's 8 gold metrics.

    612 complete groups + 361 duplicates of the first 361 of them (in file1),
    2320 incomplete groups (email missing) + 190 invalid-phone rows (in file2).
      total_raw      = 612 + 361 + 2320 + 190 = 3483
      valid_format   = 612 + 361 + 2320       = 3293
      null_or_wrong  = 190
      distinct       = 612 + 2320             = 2932   (361 dups reuse phones)
      dup_clean      = 3293 - 2932 = 361
      dup_raw        = 3483 - 2932 = 551
      complete       = 612    incomplete = 2932 - 612 = 2320
    """
    def phone(i: int) -> str:
        return f"09{i:08d}"          # 10 digits, valid, distinct per i

    file1 = []
    for i in range(612):             # complete groups
        file1.append({"phone": phone(i), "name": f"N{i}", "email": f"u{i}@x.com"})
    for i in range(361):             # duplicates of first 361 complete groups
        file1.append({"phone": phone(i), "name": f"N{i}", "email": f"u{i}@x.com"})

    file2 = []
    for i in range(612, 612 + 2320):  # incomplete groups (email missing)
        file2.append({"phone": phone(i), "name": f"N{i}", "email": None})
    for i in range(190):              # invalid phones (rejected)
        file2.append({"phone": "123", "name": f"bad{i}", "email": None})

    return pl.DataFrame(file1), pl.DataFrame(file2)


def test_align_and_merge_reproduces_notebook_numbers():
    f1, f2 = _notebook_fixture()
    clean, rejected, s = merge_v2(
        [f1, f2], selected=["phone", "name", "email"],
        filenames=["file1.xlsx", "file2.xlsx"],
        semantic_types={"phone": "phone", "name": "text", "email": "email"},
        dedup_key="phone", required_fields=["name", "email"],
        coalesce=True, drop_invalid_key=True,
    )
    assert s.total_raw == 3483
    assert s.valid_format == 3293
    assert s.null_or_wrong == 190
    assert s.distinct == 2932
    assert s.dup_removed_clean == 361
    assert s.dup_removed_raw == 551
    assert s.complete == 612
    assert s.incomplete == 2320
    assert clean.height == 2932
    assert rejected.height == 190
    assert s.per_file_contribution == {"file1.xlsx": 973, "file2.xlsx": 2320}
    assert s.per_field_fill_rate["phone"] == 1.0
    assert s.per_field_fill_rate["email"] == round(612 / 2932, 3)


def test_merge_rejected_csv_download(client):
    # CSV_B's 0900000000 is fine; craft a file with an invalid phone to reject.
    csv_bad = b"Phone,Name\n0987654321,Alice\n12,Bad\n"
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("c.csv", io.BytesIO(csv_bad), "text/csv"))],
    ).json()
    sid = stage["session_id"]
    run = client.post("/api/ml/merge/run", json={
        "session_id": sid,
        "selected_fields": ["Phone", "Name"],
        "options": {"dedup_key": "Phone", "semantic_types": {"Phone": "phone"},
                    "drop_invalid_key": True},
        "dry_run": False,
    })
    assert run.json()["summary"]["null_or_wrong"] == 1
    rej = client.get(f"/api/ml/merge/{sid}/rejected.csv")
    assert rej.status_code == 200
    assert rej.headers["content-type"].startswith("text/csv")
    assert b"Bad" in rej.content


def test_merge_rejected_csv_missing_is_404(client):
    assert client.get("/api/ml/merge/nope/rejected.csv").status_code == 404


# ── Show Code + cleaned-result export (Request #2) ───────────────────────────

def test_merge_run_returns_show_code_both_paths(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[
            ("files", ("a.csv", io.BytesIO(CSV_A), "text/csv")),
            ("files", ("b.csv", io.BytesIO(CSV_B), "text/csv")),
        ],
    ).json()
    body = {
        "session_id": stage["session_id"],
        "selected_fields": ["Phone", "Name"],
        "alias_map": {},
        "options": {"dedup_key": "Phone", "drop_invalid_key": True, "trim": True,
                    "semantic_types": {"Phone": "phone"},
                    "field_groups": {"Phone": ["Phone", "phone"]},
                    "required_fields": ["Name"], "coalesce": True},
    }
    for dry in (True, False):
        d = client.post("/api/ml/merge/run", json={**body, "dry_run": dry}).json()
        code = d["code"]
        assert isinstance(code, str) and code.strip()
        # Faithful, runnable, end-to-end: reads files, calls the real engine, exports.
        assert "import polars as pl" in code
        assert "from analytics.merge import align_and_merge" in code
        assert "align_and_merge(" in code
        assert "write_csv" in code and "write_excel" in code
        # Resolved wizard params are baked in as literals.
        assert "'Phone'" in code and "dedup_key = 'Phone'" in code


def test_merge_download_clean_csv_and_xlsx_after_dry_run(client):
    # Dry-run must persist clean.parquet so export works straight from the preview.
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("a.csv", io.BytesIO(CSV_A), "text/csv"))],
    ).json()
    sid = stage["session_id"]
    run = client.post("/api/ml/merge/run", json={
        "session_id": sid,
        "selected_fields": ["Phone", "Name", "Age"],
        "options": {"dedup_key": "Phone", "semantic_types": {"Phone": "phone"}},
        "dry_run": True,
    })
    assert run.status_code == 200

    csv = client.get(f"/api/ml/merge/{sid}/download?fmt=csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert b"Phone" in csv.content

    xlsx = client.get(f"/api/ml/merge/{sid}/download?fmt=xlsx")
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert xlsx.content[:2] == b"PK"  # xlsx is a zip


def test_merge_download_clean_bad_fmt_and_missing(client):
    stage = client.post(
        "/api/ml/merge/stage",
        files=[("files", ("a.csv", io.BytesIO(CSV_A), "text/csv"))],
    ).json()
    sid = stage["session_id"]
    client.post("/api/ml/merge/run", json={
        "session_id": sid, "selected_fields": ["Phone"],
        "options": {"semantic_types": {"Phone": "phone"}}, "dry_run": True,
    })
    assert client.get(f"/api/ml/merge/{sid}/download?fmt=json").status_code == 400
    # No clean.parquet for an unknown session -> 404 (not a 500).
    assert client.get("/api/ml/merge/nope/download?fmt=csv").status_code == 404
