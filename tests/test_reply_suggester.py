import pytest
from unittest.mock import patch
from modules.reply_suggester import suggest_replies

SAMPLE_EMAIL = {
    "subject": "Nhờ xác nhận biên bản nghiệm thu",
    "sender_name": "Quỳnh Như",
    "body": "Dear anh Hiếu, nhờ anh xác nhận.",
    "priority": "normal",
}

STYLE = "Phong cách lịch sự, ngắn gọn, dùng 'Em' và 'Anh/Chị', kết thúc bằng 'Trân trọng'."


def test_suggest_replies_returns_3_options():
    with patch("modules.reply_suggester._call_ai", return_value="Option 1\nOption 2\nOption 3"):
        result = suggest_replies(SAMPLE_EMAIL, style_summary=STYLE)
    assert len(result) == 3


def test_suggest_replies_fallback_on_error():
    with patch("modules.reply_suggester._call_ai", side_effect=Exception("fail")):
        result = suggest_replies(SAMPLE_EMAIL, style_summary=STYLE)
    assert len(result) == 3
    assert all(isinstance(r, str) for r in result)


def test_suggest_replies_empty_style():
    with patch("modules.reply_suggester._call_ai", return_value="A\nB\nC"):
        result = suggest_replies(SAMPLE_EMAIL, style_summary="")
    assert len(result) == 3
