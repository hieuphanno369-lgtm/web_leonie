import os

import duckdb
import httpx
import pytest
from unittest.mock import patch
from automation import ingest
from automation import shape
from automation import export
from automation import notify
from automation import codegen
from automation import runner
from automation.sources.rest import RestFetcher

from automation.models import (
    RestAuth, Pagination, RestSource, ExportSpec, EmailSpec,
    NotifySpec, JobConfig, RunResult, AutomationJob,
)
from automation import store
from automation.models import RunResult as _RR


def test_model_defaults():
    s = RestSource(url="https://api.test/x")
    assert s.method == "GET"
    assert s.auth.type == "none"
    assert s.records_path == ""
    assert s.timeout_seconds == 30 and s.max_retries == 3
    assert s.pagination is None

    e = ExportSpec(formats=["parquet"], dest_dir="/tmp/out")
    assert e.duckdb_mode == "overwrite" and e.xlsx_row_guard == 1_000_000

    n = NotifySpec()
    assert n.discord_enabled is False and n.email.enabled is False
    assert n.email.attach_max_bytes == 10_485_760


def test_jobconfig_json_round_trip():
    cfg = JobConfig(
        name="daily",
        source=RestSource(url="https://api.test/x",
                          auth=RestAuth(type="bearer", value_ref="TOK"),
                          pagination=Pagination(param="page", start=1)),
        shape_sql="SELECT * FROM raw",
        export=ExportSpec(formats=["duckdb", "csv"], dest_dir="/tmp/out", duckdb_mode="append"),
    )
    again = JobConfig.model_validate_json(cfg.model_dump_json())
    assert again.source.auth.value_ref == "TOK"
    assert again.export.duckdb_mode == "append"
    assert again.source.pagination.param == "page"


def _make_cfg(name="job"):
    return JobConfig(name=name,
                     source=RestSource(url="https://api.test/x"),
                     export=ExportSpec(formats=["parquet"], dest_dir="/tmp/out"))


def test_store_crud_and_status():
    job = store.create_job(_make_cfg("first"))
    assert job.id and job.config.name == "first"
    assert job.last_status is None

    assert store.get_job(job.id).config.name == "first"
    assert [j.id for j in store.list_jobs()] == [job.id]

    updated = store.update_job(job.id, _make_cfg("renamed"))
    assert updated.config.name == "renamed"

    store.set_running(job.id)
    assert store.get_job(job.id).last_status == "running"

    store.set_run_status(job.id, _RR(status="ok", rows=42, duration_seconds=1.2,
                                     output_files=["/tmp/out/x.parquet"]))
    done = store.get_job(job.id)
    assert done.last_status == "ok" and done.last_rows == 42
    assert done.last_run_at is not None

    assert store.delete_job(job.id) is True
    assert store.get_job(job.id) is None
    assert store.delete_job("nonexistent") is False


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_pagination_stops_on_empty():
    pages = {1: [{"id": 1}], 2: [{"id": 2}], 3: []}
    def handler(req):
        return httpx.Response(200, json=pages[int(req.url.params["page"])])
    src = RestSource(url="https://api.test/items", pagination=Pagination(param="page", start=1))
    out = list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert out == [[{"id": 1}], [{"id": 2}]]


def test_records_path_nested():
    def handler(req):
        page = int(req.url.params.get("page", 1))
        body = {"data": {"items": [{"id": 1}] if page == 1 else []}}
        return httpx.Response(200, json=body)
    src = RestSource(url="https://api.test/x", records_path="data.items",
                     pagination=Pagination(param="page", start=1))
    assert list(RestFetcher(src).fetch_pages(client=_client(handler))) == [[{"id": 1}]]


def test_retry_on_503_then_success():
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200, json=[{"id": 1}])
    src = RestSource(url="https://api.test/x", max_retries=2)
    with patch("automation.sources.rest.time.sleep"):
        out = list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert out == [[{"id": 1}]] and calls["n"] == 2


def test_4xx_raises_without_retry():
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(404)
    src = RestSource(url="https://api.test/x", max_retries=3)
    with patch("automation.sources.rest.time.sleep"), pytest.raises(httpx.HTTPStatusError):
        list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert calls["n"] == 1


def test_bearer_env_var_resolution(monkeypatch):
    monkeypatch.setenv("TOK", "secret123")
    seen = {}
    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json=[])
    src = RestSource(url="https://api.test/x", auth=RestAuth(type="bearer", value_ref="TOK"))
    list(RestFetcher(src).fetch_pages(client=_client(handler)))
    assert seen["auth"] == "Bearer secret123"


def test_missing_env_var_raises():
    src = RestSource(url="https://api.test/x", auth=RestAuth(type="bearer", value_ref="NOPE_X"))
    with pytest.raises(Exception):
        list(RestFetcher(src).fetch_pages(client=_client(lambda r: httpx.Response(200, json=[]))))


def test_ingest_preserves_nested_json(tmp_path):
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    ingest.ensure_raw(con)
    n = ingest.append_page(con, [{"id": 1, "meta": {"r": "north"}},
                                 {"id": 2, "meta": {"r": "south"}}])
    assert n == 2
    assert con.execute("SELECT count(*) FROM raw").fetchone()[0] == 2
    regions = con.execute(
        "SELECT rec->>'$.meta.r' FROM raw ORDER BY CAST(rec->>'$.id' AS INT)"
    ).fetchall()
    assert [r[0] for r in regions] == ["north", "south"]
    assert ingest.append_page(con, []) == 0   # empty page is a no-op
    con.close()


def test_shape_passthrough_and_custom(tmp_path):
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    ingest.ensure_raw(con)
    ingest.append_page(con, [{"id": 1}, {"id": 2}])

    # Empty SQL => passthrough: data == raw (single `rec` column)
    assert shape.run(con, "") == 2
    assert [d[0] for d in con.execute("DESCRIBE data").fetchall()] == ["rec"]

    # Custom SQL over raw
    n = shape.run(con, "SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw "
                       "WHERE CAST(rec->>'$.id' AS INT) = 1")
    assert n == 1
    assert con.execute("SELECT id FROM data").fetchone()[0] == 1
    con.close()


def _prep(tmp_path, rows=3):
    con = duckdb.connect(str(tmp_path / "w.duckdb"))
    ingest.ensure_raw(con)
    ingest.append_page(con, [{"id": i} for i in range(rows)])
    shape.run(con, "SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw")
    return con


def test_export_parquet_csv_atomic(tmp_path):
    con = _prep(tmp_path)
    dest = tmp_path / "out"
    files, warns = export.write(
        con, ExportSpec(formats=["parquet", "csv"], dest_dir=str(dest)),
        "job", "20260604_120000")
    assert len(files) == 2 and all(os.path.exists(f) for f in files)
    assert not any(name.endswith(".tmp") for name in os.listdir(dest))
    assert warns == []
    con.close()


def test_export_xlsx_guard_skips(tmp_path):
    con = _prep(tmp_path, rows=5)
    dest = tmp_path / "out"
    files, warns = export.write(
        con, ExportSpec(formats=["xlsx"], dest_dir=str(dest), xlsx_row_guard=2),
        "job", "20260604_120000")
    assert files == [] and any("xlsx" in w for w in warns)
    con.close()


def test_export_duckdb_append_accumulates(tmp_path):
    con = _prep(tmp_path, rows=3)
    dest = tmp_path / "out"
    spec = ExportSpec(formats=["duckdb"], dest_dir=str(dest), duckdb_mode="append")
    export.write(con, spec, "acc", "t1")
    export.write(con, spec, "acc", "t2")
    dbf = os.path.join(str(dest), "acc.duckdb").replace("\\", "/")
    c2 = duckdb.connect()
    c2.execute(f"ATTACH '{dbf}' AS s")
    assert c2.execute("SELECT count(*) FROM s.data").fetchone()[0] == 6
    c2.close()
    con.close()


def test_export_duckdb_overwrite_replaces(tmp_path):
    con = _prep(tmp_path, rows=3)
    dest = tmp_path / "out"
    spec = ExportSpec(formats=["duckdb"], dest_dir=str(dest), duckdb_mode="overwrite")
    export.write(con, spec, "ow", "t1")
    export.write(con, spec, "ow", "t2")
    dbf = os.path.join(str(dest), "ow.duckdb").replace("\\", "/")
    c2 = duckdb.connect()
    c2.execute(f"ATTACH '{dbf}' AS s")
    assert c2.execute("SELECT count(*) FROM s.data").fetchone()[0] == 3
    c2.close()
    con.close()


def _notify_cfg(**nk):
    return JobConfig(name="J", source=RestSource(url="http://x"),
                     export=ExportSpec(formats=[], dest_dir="."),
                     notify=NotifySpec(**nk))


def test_notify_discord_called_with_summary():
    cfg = _notify_cfg(discord_enabled=True)
    res = _RR(status="ok", rows=5, duration_seconds=1.0, output_files=[])
    with patch("automation.notify._discord") as m:
        warns = notify.send(cfg, res)
    m.assert_called_once()
    assert "Rows: 5" in m.call_args[0][0]
    assert warns == []


def test_notify_failure_is_collected_not_raised():
    cfg = _notify_cfg(discord_enabled=True)
    res = _RR(status="error", rows=0, duration_seconds=0.0, error="boom")
    with patch("automation.notify._discord", side_effect=RuntimeError("down")):
        warns = notify.send(cfg, res)
    assert any("Discord" in w for w in warns)


def test_codegen_compiles_and_hides_secrets():
    cfg = JobConfig(
        name="J",
        source=RestSource(url="https://api/x", records_path="data",
                          auth=RestAuth(type="bearer", value_ref="TOK"),
                          pagination=Pagination(param="page", start=1)),
        shape_sql="SELECT * FROM raw",
        export=ExportSpec(formats=["parquet"], dest_dir="out"))
    script = codegen.python_script(cfg)
    compile(script, "<gen>", "exec")               # raises if not valid Python
    assert "httpx" in script and "read_json" in script
    assert "os.environ" in script                  # secrets via env, not literals
    assert "CREATE TABLE data" in script
    assert codegen.shape_sql_text(cfg) == "SELECT * FROM raw"


class _FakeFetcher:
    def __init__(self, pages):
        self.pages = pages

    def fetch_pages(self, limit_pages=None):
        for i, p in enumerate(self.pages):
            if limit_pages is not None and i >= limit_pages:
                break
            yield p


def _run_job(tmp_path, sql="SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw", fmts=("parquet",)):
    cfg = JobConfig(name="job", source=RestSource(url="http://x"), shape_sql=sql,
                    export=ExportSpec(formats=list(fmts), dest_dir=str(tmp_path / "out")))
    return AutomationJob(id="abc", config=cfg, created="t", updated="t")


def test_runner_run_ok(tmp_path):
    job = _run_job(tmp_path)
    with patch("automation.runner.make_fetcher", return_value=_FakeFetcher([[{"id": 1}, {"id": 2}]])), \
         patch("automation.notify.send") as nsend:
        res = runner.run(job)
    assert res.status == "ok" and res.rows == 2 and len(res.output_files) == 1
    nsend.assert_called_once()


def test_runner_zero_rows_warns_no_export(tmp_path):
    job = _run_job(tmp_path, sql="SELECT CAST(rec->>'$.id' AS INT) AS id FROM raw WHERE 1=0")
    with patch("automation.runner.make_fetcher", return_value=_FakeFetcher([[{"id": 1}]])), \
         patch("automation.notify.send"):
        res = runner.run(job)
    assert res.status == "warning" and res.rows == 0 and res.output_files == []


def test_runner_error_path_notifies(tmp_path):
    job = _run_job(tmp_path)
    boom = _FakeFetcher([[{"id": 1}]])
    def explode(*_a, **_k):
        raise RuntimeError("fetch down")
    boom.fetch_pages = explode
    with patch("automation.runner.make_fetcher", return_value=boom), \
         patch("automation.notify.send") as nsend:
        res = runner.run(job)
    assert res.status == "error" and "fetch down" in res.error
    nsend.assert_called_once()


def test_runner_preview_one_page_no_export(tmp_path):
    job = _run_job(tmp_path)
    with patch("automation.runner.make_fetcher",
               return_value=_FakeFetcher([[{"id": 1}, {"id": 2}], [{"id": 3}]])):
        out = runner.preview(job, n_rows=10)
    assert out["columns"] == ["id"] and len(out["rows"]) == 2   # only first page
    assert not (tmp_path / "out").exists()                      # nothing exported


def test_runner_open_work_failure_returns_error(tmp_path):
    job = _run_job(tmp_path)
    with patch("automation.runner._open_work", side_effect=OSError("disk full")), \
         patch("automation.notify.send") as nsend:
        res = runner.run(job)
    assert res.status == "error" and "disk full" in res.error
    nsend.assert_called_once()


from fastapi.testclient import TestClient
from main import app

api = TestClient(app)


def _cfg_json(tmp_path, name="J"):
    return {"name": name, "source": {"url": "http://x"},
            "export": {"formats": ["parquet"], "dest_dir": str(tmp_path / "o")}}


def test_api_crud(tmp_path):
    r = api.post("/api/automation/jobs", json=_cfg_json(tmp_path))
    assert r.status_code == 200
    jid = r.json()["id"]
    assert api.get("/api/automation/jobs").json()[0]["id"] == jid
    assert api.get(f"/api/automation/jobs/{jid}").json()["config"]["name"] == "J"
    upd = _cfg_json(tmp_path, name="J2")
    assert api.put(f"/api/automation/jobs/{jid}", json=upd).json()["config"]["name"] == "J2"
    assert api.delete(f"/api/automation/jobs/{jid}").json()["ok"] is True
    assert api.get(f"/api/automation/jobs/{jid}").status_code == 404


def test_api_run_returns_running_then_409(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]
    with patch("routers.automation._spawn") as sp:
        r1 = api.post(f"/api/automation/jobs/{jid}/run")
        assert r1.status_code == 200 and r1.json()["status"] == "running"
        sp.assert_called_once()
        assert api.post(f"/api/automation/jobs/{jid}/run").status_code == 409


def test_api_code_endpoint(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]
    body = api.get(f"/api/automation/jobs/{jid}/code").json()
    assert "httpx" in body["python"] and "sql" in body


def test_api_preview(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]

    class _F:
        def fetch_pages(self, limit_pages=None):
            yield [{"id": 1}]

    with patch("automation.runner.make_fetcher", return_value=_F()):
        r = api.post(f"/api/automation/jobs/{jid}/preview", json={"n_rows": 5})
    assert r.status_code == 200 and len(r.json()["rows"]) == 1


def test_run_bg_clears_latch_on_unexpected_failure(tmp_path):
    from routers.automation import _run_bg
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]
    # Put the job into the 'running' state without starting the real thread.
    with patch("routers.automation._spawn"):
        assert api.post(f"/api/automation/jobs/{jid}/run").json()["status"] == "running"
    # Simulate an unexpected failure in the worker (runner.run is normally no-raise).
    with patch("automation.runner.run", side_effect=RuntimeError("kaboom")):
        _run_bg(jid)
    # The 'running' latch must be cleared so the job stays runnable, not stuck at 409.
    assert api.get(f"/api/automation/jobs/{jid}").json()["last_status"] == "error"


def test_email_skips_login_without_password(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "u@test")
    monkeypatch.delenv("SMTP_PASS", raising=False)
    with patch("automation.notify.smtplib.SMTP") as smtp_ctor:
        notify._email("subj", "body", ["to@test"], [])
        s = smtp_ctor.return_value.__enter__.return_value
        s.starttls.assert_called_once()
        s.login.assert_not_called()
        s.send_message.assert_called_once()


def test_email_logs_in_with_user_and_password(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "u@test")
    monkeypatch.setenv("SMTP_PASS", "secret")
    with patch("automation.notify.smtplib.SMTP") as smtp_ctor:
        notify._email("subj", "body", ["to@test"], [])
        s = smtp_ctor.return_value.__enter__.return_value
        s.login.assert_called_once_with("u@test", "secret")
        s.send_message.assert_called_once()


def test_api_preview_rejects_out_of_range_n_rows(tmp_path):
    jid = api.post("/api/automation/jobs", json=_cfg_json(tmp_path)).json()["id"]
    assert api.post(f"/api/automation/jobs/{jid}/preview", json={"n_rows": 0}).status_code == 422
    assert api.post(f"/api/automation/jobs/{jid}/preview", json={"n_rows": 10_000_000}).status_code == 422


# ── verify-path endpoint ──────────────────────────────────────────────────────

def test_verify_path_existing_dir_ok(tmp_path):
    r = api.post("/api/automation/verify-path", json={"path": str(tmp_path)})
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True and d["exists"] is True and d["will_create"] is False


def test_verify_path_missing_dir_will_create(tmp_path):
    target = tmp_path / "exports" / "sales"      # neither level exists yet
    d = api.post("/api/automation/verify-path", json={"path": str(target)}).json()
    assert d["ok"] is True and d["exists"] is False and d["will_create"] is True


def test_verify_path_file_not_dir(tmp_path):
    f = tmp_path / "afile.txt"
    f.write_text("x", encoding="utf-8")
    d = api.post("/api/automation/verify-path", json={"path": str(f)}).json()
    assert d["ok"] is False and d["exists"] is True


def test_verify_path_empty():
    d = api.post("/api/automation/verify-path", json={"path": "   "}).json()
    assert d["ok"] is False and "empty" in d["message"].lower()
