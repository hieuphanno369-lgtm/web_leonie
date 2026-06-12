import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.sql_analyzer import _slugify, build_note_content, save_note


def test_slugify_basic():
    assert _slugify("doanh thu san pham") == "doanh-thu-san-pham"


def test_slugify_strips_special_chars():
    assert _slugify("Hello, World!") == "hello-world"


def test_slugify_truncates_at_60():
    long_text = "word " * 20
    assert len(_slugify(long_text)) <= 60


def test_slugify_handles_vietnamese_diacritics():
    result = _slugify("Doanh thu sản phẩm")
    assert result == "doanh-thu-san-pham"


def test_build_note_content_has_yaml_frontmatter():
    analysis = {
        "title": "Test Query",
        "description": "What is revenue?",
        "tables": ["orders"],
        "filters": ["status = active"],
        "tags": ["sql", "revenue"],
        "keywords": ["doanh_thu"],
    }
    content = build_note_content(analysis, "SELECT SUM(amount) FROM orders")
    assert content.startswith("---")
    assert "title: Test Query" in content
    assert "tables: ['orders']" in content


def test_build_note_content_includes_sql():
    analysis = {
        "title": "T", "description": "D",
        "tables": [], "filters": [], "tags": [], "keywords": [],
    }
    content = build_note_content(analysis, "SELECT 1")
    assert "SELECT 1" in content


def test_save_note_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.sql_analyzer.SQL_NOTES_DIR", tmp_path)
    analysis = {
        "title": "Test query",
        "description": "Desc",
        "tables": ["orders"],
        "filters": ["status = active"],
        "tags": ["sql"],
        "keywords": ["thu_thap"],
    }
    path = save_note(analysis, "SELECT * FROM orders")
    assert path.exists()
    assert "test-query" in path.name


def test_save_note_filename_has_date_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.sql_analyzer.SQL_NOTES_DIR", tmp_path)
    analysis = {
        "title": "Doanh thu", "description": "",
        "tables": [], "filters": [], "tags": [], "keywords": [],
    }
    path = save_note(analysis, "SELECT 1")
    assert re.match(r"\d{4}-\d{2}-\d{2}_doanh-thu\.md", path.name)


def test_analyze_query_parses_json():
    mock_resp = json.dumps({
        "title": "Doanh thu tháng",
        "description": "Doanh thu từng sản phẩm tháng này là bao nhiêu?",
        "tables": ["orders"],
        "filters": ["month = 5"],
        "tags": ["revenue", "monthly"],
        "keywords": ["doanh_thu"],
    })
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import analyze_query
        result = analyze_query("SELECT SUM(amount) FROM orders WHERE month=5")
    assert result["title"] == "Doanh thu tháng"
    assert result["tables"] == ["orders"]
    assert "description" in result


def test_analyze_query_handles_markdown_wrapped_json():
    inner = '{"title":"T","description":"D","tables":[],"filters":[],"tags":[],"keywords":[]}'
    mock_resp = f"```json\n{inner}\n```"
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import analyze_query
        result = analyze_query("SELECT 1")
    assert result["title"] == "T"


def test_optimize_query_returns_improvements_and_sql():
    mock_resp = json.dumps({
        "improvements": ["Thêm index cho cột month", "Tránh dùng SELECT *"],
        "optimized_sql": "SELECT SUM(amount) FROM orders WHERE month=5",
    })
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import optimize_query
        result = optimize_query("SELECT * FROM orders WHERE month=5")
    assert len(result["improvements"]) == 2
    assert "optimized_sql" in result


def test_optimize_query_handles_markdown_wrapped_json():
    inner = '{"improvements":["Fix"],"optimized_sql":"SELECT 1"}'
    mock_resp = f"```json\n{inner}\n```"
    with patch("modules.sql_analyzer.call_ai", return_value=mock_resp):
        from modules.sql_analyzer import optimize_query
        result = optimize_query("SELECT 1")
    assert result["optimized_sql"] == "SELECT 1"
