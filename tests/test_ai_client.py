import pytest
from unittest.mock import patch, MagicMock
from modules.ai_client import summarize_email, classify_email_ai

SAMPLE_EMAIL = {
    "subject": "Nhờ xác nhận biên bản",
    "sender_name": "Quỳnh Như",
    "body": "Dear anh Hiếu, nhờ anh xác nhận biên bản nghiệm thu tháng 4.",
    "received_time": "2026-05-04T08:00:00",
}


def test_summarize_returns_string_on_claude_success():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Quỳnh Như nhờ anh Hiếu xác nhận biên bản nghiệm thu tháng 4/2026.")]
    )
    with patch("modules.ai_client._get_claude_client", return_value=mock_client):
        result = summarize_email(SAMPLE_EMAIL, priority="normal")
    assert isinstance(result, str)
    assert len(result) > 10


def test_summarize_falls_back_to_rule_when_claude_fails():
    with patch("modules.ai_client._get_claude_client", side_effect=Exception("API Error")):
        with patch("modules.ai_client._ollama_available", return_value=False):
            result = summarize_email(SAMPLE_EMAIL, priority="normal")
    assert "Quỳnh Như" in result or "Nhờ xác nhận biên bản" in result


def test_classify_email_ai_returns_valid_priority():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="normal")]
    )
    with patch("modules.ai_client._get_claude_client", return_value=mock_client):
        result = classify_email_ai(SAMPLE_EMAIL)
    assert result in ("urgent", "normal", "fyi")


def test_classify_email_ai_defaults_fyi_on_error():
    with patch("modules.ai_client._get_claude_client", side_effect=Exception("fail")):
        with patch("modules.ai_client._ollama_available", return_value=False):
            result = classify_email_ai(SAMPLE_EMAIL)
    assert result == "fyi"
