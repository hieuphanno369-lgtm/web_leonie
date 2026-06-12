import json
import os
import tempfile
import pytest
from modules.ml_pipeline.notebook_gen import generate_notebook


def _base_context():
    return {
        "dataset_name": "sales_test.csv",
        "target": "revenue",
        "features": ["month", "region"],
        "skip_rows": 0,
        "header_row": 0,
        "timestamp": "2026-05-09T16:00:00",
        "problem_type": "regression",
        "clean_steps": ["Removed 3 duplicates", "Filled 2 nulls in revenue"],
        "metrics": {"rmse": 1200.0, "r2": 0.85},
        "horizon": 30,
        "date_col": "date",
    }


def test_generates_ipynb_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_notebook(tmpdir, "regression", _base_context())
        assert os.path.exists(path)
        assert path.endswith(".ipynb")


def test_notebook_is_valid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_notebook(tmpdir, "regression", _base_context())
        with open(path) as f:
            nb = json.load(f)
        assert "nbformat" in nb
        assert "cells" in nb


def test_notebook_contains_dataset_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_notebook(tmpdir, "regression", _base_context())
        content = open(path).read()
        assert "sales_test.csv" in content


def test_notebook_contains_target():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_notebook(tmpdir, "regression", _base_context())
        content = open(path).read()
        assert "revenue" in content


def test_all_four_templates_render():
    ctx = _base_context()
    for template in ["regression", "classification", "clustering", "timeseries"]:
        ctx["problem_type"] = template
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_notebook(tmpdir, template, ctx)
            assert os.path.exists(path), f"Template {template} failed to generate"
