"""Tests for dictionary_data.py schema and dictionary.py builder."""
import pytest
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

CARD_FIELDS = ("when_to_use", "fields", "output", "conditions", "fmcg_case", "business_value")
GUIDE_CATEGORIES = {"guide", "ref"}


# ── dictionary_data schema ────────────────────────────────────────────────────

def test_no_duplicate_ids():
    from modules.dictionary_data import SECTIONS
    ids = [s["id"] for s in SECTIONS]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"


def test_all_card_sections_have_required_fields():
    from modules.dictionary_data import SECTIONS
    card_sections = [s for s in SECTIONS if not s.get("md_file")]
    for s in card_sections:
        for f in CARD_FIELDS:
            assert f in s and s[f], f"Section '{s['id']}' missing or empty field '{f}'"


def test_all_guide_sections_have_md_file():
    from modules.dictionary_data import SECTIONS
    guide_sections = [s for s in SECTIONS if s.get("category") in GUIDE_CATEGORIES]
    for s in guide_sections:
        assert s.get("md_file"), f"Guide section '{s['id']}' missing 'md_file'"


def test_all_sections_have_required_base_fields():
    from modules.dictionary_data import SECTIONS
    base = ("id", "title", "category", "icon", "group")
    for s in SECTIONS:
        for f in base:
            assert f in s, f"Section '{s.get('id', '?')}' missing base field '{f}'"


def test_categories_match_section_categories():
    from modules.dictionary_data import SECTIONS, CATEGORIES
    cat_ids = {c["id"] for c in CATEGORIES}
    for s in SECTIONS:
        assert s["category"] in cat_ids, \
            f"Section '{s['id']}' has unknown category '{s['category']}'"


# ── dictionary.py builder ─────────────────────────────────────────────────────

def test_md_to_html_converts_heading():
    from modules.dictionary import _md_to_html
    result = _md_to_html("# Hello")
    assert "<h1>" in result
    assert "Hello" in result


def test_md_to_html_converts_table():
    from modules.dictionary import _md_to_html
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = _md_to_html(md)
    assert "<table>" in result


def test_load_md_files_converts_existing_file(tmp_path):
    (tmp_path / "myfile.md").write_text("# Hi\nContent", encoding="utf-8")
    import modules.dictionary as d
    orig = d._CONTENT_DIR
    d._CONTENT_DIR = tmp_path
    try:
        result = d._load_md_files([{"id": "x", "md_file": "myfile"}])
        assert "myfile" in result
        assert "<h1>" in result["myfile"]
    finally:
        d._CONTENT_DIR = orig


def test_load_md_files_skips_sections_without_md_file():
    import modules.dictionary as d
    result = d._load_md_files([{"id": "xgboost"}])  # no md_file key
    assert result == {}


def test_load_md_files_returns_empty_string_for_missing_file(tmp_path):
    import modules.dictionary as d
    orig = d._CONTENT_DIR
    d._CONTENT_DIR = tmp_path
    try:
        result = d._load_md_files([{"id": "x", "md_file": "nonexistent"}])
        assert result["nonexistent"] == ""
    finally:
        d._CONTENT_DIR = orig


def test_build_wiki_html_is_valid_document():
    from modules.dictionary import build_wiki_html
    from modules.dictionary_data import SECTIONS
    html = build_wiki_html(SECTIONS, {})
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "__WIKI_DATA__" not in html


def test_build_wiki_html_injects_section_id():
    from modules.dictionary import build_wiki_html
    from modules.dictionary_data import SECTIONS
    html = build_wiki_html(SECTIONS, {})
    assert SECTIONS[0]["id"] in html


def test_build_wiki_html_injects_md_content():
    from modules.dictionary import build_wiki_html
    from modules.dictionary_data import SECTIONS
    html = build_wiki_html(SECTIONS, {"00_welcome": "<h1>UNIQUE_MARKER</h1>"})
    assert "UNIQUE_MARKER" in html
