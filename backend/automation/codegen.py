from automation.models import JobConfig


def shape_sql_text(config: JobConfig) -> str:
    return config.shape_sql.strip() or "SELECT * FROM raw"


def python_script(config: JobConfig) -> str:
    """Render a read-only, runnable reference script from the job config."""
    s = config.source
    sql = shape_sql_text(config)

    L: list[str] = []
    L.append(f"# Read-only reference script for job {config.name!r}.")
    L.append("# Secrets are read from environment variables (never hard-coded).")
    L.append("")

    if s.source_type == "salesforce":
        _sf_imports(L, s, sql, config)
    else:
        _rest_imports(L, s, sql, config)

    L.append("print('rows:', con.execute('SELECT count(*) FROM data').fetchone()[0])")
    return "\n".join(L) + "\n"


def _rest_imports(L, s, sql, config):
    a = s.auth
    has_page = s.pagination is not None
    start = s.pagination.start if has_page else 0
    page_param = s.pagination.param if has_page else "page"

    L.append("import os, json, tempfile")
    L.append("import httpx, duckdb")
    L.append("")
    L.append(f"URL = {s.url!r}")
    L.append(f"RECORDS_PATH = {s.records_path!r}")
    L.append(f"TIMEOUT = {s.timeout_seconds}")
    L.append("")
    L.append(f"headers = {dict(s.headers)!r}")
    if a.type == "api_key" and a.header_name and a.value_ref:
        L.append(f"headers[{a.header_name!r}] = os.environ[{a.value_ref!r}]")
        L.append("auth = None")
    elif a.type == "bearer" and a.value_ref:
        L.append(f"headers['Authorization'] = 'Bearer ' + os.environ[{a.value_ref!r}]")
        L.append("auth = None")
    elif a.type == "basic" and a.user_ref and a.pass_ref:
        L.append(f"auth = httpx.BasicAuth(os.environ[{a.user_ref!r}], os.environ[{a.pass_ref!r}])")
    else:
        L.append("auth = None")
    L.append("")
    L.append("def dig(obj, path):")
    L.append("    if not path: return obj")
    L.append("    for part in path.split('.'): obj = obj.get(part) if isinstance(obj, dict) else None")
    L.append("    return obj")
    L.append("")
    L.append("def fetch_pages():")
    L.append("    with httpx.Client(timeout=TIMEOUT) as client:")
    L.append(f"        page = {start}")
    L.append("        while True:")
    L.append("            params = {}")
    if has_page:
        L.append(f"            params[{page_param!r}] = page")
    L.append("            resp = client.get(URL, params=params, headers=headers, auth=auth)")
    L.append("            resp.raise_for_status()")
    L.append("            records = dig(resp.json(), RECORDS_PATH) or []")
    L.append("            if not isinstance(records, list): records = [records]")
    L.append("            if not records: break")
    L.append("            yield records")
    if has_page:
        L.append("            page += 1")
    else:
        L.append("            break")
    L.append("")
    _append_ingest_and_export(L, sql, config)


def _sf_imports(L, s, sql, config):
    L.append("import os, csv, io, json, tempfile")
    L.append("import duckdb")
    L.append("from simple_salesforce import Salesforce")
    L.append("")
    L.append(f"SOQL = {s.soql!r}")
    L.append(f"OBJECT_NAME = {s.object_name!r}")
    L.append(f"INSTANCE_URL = {s.instance_url!r}")
    L.append(f"USE_BULK = {s.use_bulk!r}")
    L.append("")
    L.append(f"sf = Salesforce(")
    L.append(f"    username=os.environ[{s.user_ref!r}],")
    L.append(f"    password=os.environ[{s.pass_ref!r}],")
    if s.token_ref:
        L.append(f"    security_token=os.environ.get({s.token_ref!r}, ''),")
    else:
        L.append("    security_token='',")
    L.append(f"    instance_url=INSTANCE_URL,")
    L.append(")")
    L.append("")
    L.append("def fetch_pages():")
    L.append("    if USE_BULK:")
    L.append("        chunks = list(getattr(sf.bulk2, OBJECT_NAME).query(SOQL))")
    L.append("        if not chunks:")
    L.append("            yield []")
    L.append("            return")
    L.append("        parts = []")
    L.append("        for i, c in enumerate(chunks):")
    L.append("            t = c if isinstance(c, str) else c.decode('utf-8')")
    L.append("            if i > 0 and '\\n' in t: t = t.split('\\n', 1)[1]")
    L.append("            parts.append(t)")
    L.append("        reader = csv.DictReader(io.StringIO(''.join(parts)))")
    L.append("        yield [dict(r) for r in reader]")
    L.append("    else:")
    L.append("        result = sf.query_all(SOQL)")
    L.append("        records = result.get('records', [])")
    L.append("        for r in records: r.pop('attributes', None)")
    L.append("        yield records")
    L.append("")
    _append_ingest_and_export(L, sql, config)


def _append_ingest_and_export(L, sql, config):
    L.append("con = duckdb.connect('work.duckdb')")
    L.append("con.execute('CREATE TABLE IF NOT EXISTS raw (rec JSON)')")
    L.append("for pg in fetch_pages():")
    L.append("    fd, path = tempfile.mkstemp(suffix='.json')")
    L.append("    with os.fdopen(fd, 'w', encoding='utf-8') as fh:")
    L.append("        for rec in pg:")
    L.append("            fh.write(json.dumps(rec) + chr(10))")
    L.append("    p = path.replace(chr(92), '/')")
    L.append("    con.execute(\"INSERT INTO raw SELECT json FROM \"")
    L.append("                \"read_json('\" + p + \"', format='newline_delimited', records='false')\")")
    L.append("    os.unlink(path)")
    L.append("")
    L.append("con.execute('DROP TABLE IF EXISTS data')")
    L.append(f"con.execute({('CREATE TABLE data AS ' + sql)!r})")
    L.append("")
    for fmt in config.export.formats:
        if fmt == "parquet":
            L.append(f"con.execute(\"COPY (SELECT * FROM data) TO '{config.export.dest_dir}/{config.name}.parquet' (FORMAT parquet)\")")
        elif fmt == "csv":
            L.append(f"con.execute(\"COPY (SELECT * FROM data) TO '{config.export.dest_dir}/{config.name}.csv' (FORMAT csv, HEADER)\")")
    L.append("")
