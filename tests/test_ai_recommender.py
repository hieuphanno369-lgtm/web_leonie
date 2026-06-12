# tests/test_ai_recommender.py
import numpy as np
import polars as pl
from unittest.mock import patch
from modules.ml_pipeline.ai_recommender import recommend


def _df():
    np.random.seed(42)
    n = 80
    return pl.DataFrame({
        "sales": np.random.randn(n) * 100 + 500,
        "cost": np.random.randn(n) * 20 + 100,
        "profit": np.random.randn(n) * 50 + 200,
    })


_VALID_RESPONSE = (
    '{"method":"supervised","problem_type":"regression",'
    '"target":"profit","features":["sales","cost"],'
    '"algorithm":"Random Forest","reasoning":"profit looks numeric"}'
)


def test_recommend_returns_required_keys():
    with patch("modules.ml_pipeline.ai_recommender.call_ai", return_value=_VALID_RESPONSE):
        result = recommend(_df())
    for key in ("method", "problem_type", "target", "features", "algorithm", "reasoning"):
        assert key in result


def test_recommend_parses_values():
    with patch("modules.ml_pipeline.ai_recommender.call_ai", return_value=_VALID_RESPONSE):
        result = recommend(_df())
    assert result["method"] == "supervised"
    assert result["problem_type"] == "regression"
    assert result["target"] == "profit"
    assert "sales" in result["features"]


def test_recommend_falls_back_on_ai_error():
    with patch("modules.ml_pipeline.ai_recommender.call_ai", side_effect=RuntimeError("no AI")):
        result = recommend(_df())
    for key in ("method", "problem_type", "target", "features", "algorithm", "reasoning"):
        assert key in result


def test_recommend_falls_back_on_invalid_json():
    with patch("modules.ml_pipeline.ai_recommender.call_ai", return_value="not json"):
        result = recommend(_df())
    assert "method" in result


def test_recommend_strips_markdown_fences():
    fenced = "```json\n" + _VALID_RESPONSE + "\n```"
    with patch("modules.ml_pipeline.ai_recommender.call_ai", return_value=fenced):
        result = recommend(_df())
    assert result["method"] == "supervised"
