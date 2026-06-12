import pytest
from unittest.mock import patch, MagicMock
from modules.email_digest import run_digest

MOCK_EMAILS = [
    {
        "entry_id": "id-001",
        "subject": "[URGENT] Lỗi hệ thống",
        "sender_name": "Nguyễn Thị Huỳnh Cúc",
        "sender_email": "boss@example.com",
        "to": "user@example.com",
        "cc": "",
        "body": "Anh Hiếu ơi, hệ thống bị lỗi cần xử lý ngay.",
        "received_time": "2026-05-04T07:00:00",
        "folder": "Inbox",
    },
    {
        "entry_id": "id-002",
        "subject": "Thông báo lịch họp",
        "sender_name": "Trần Lan Phương",
        "sender_email": "carol@example.com",
        "to": "all@example.com",
        "cc": "user@example.com",
        "body": "FYI: Lịch họp tuần tới.",
        "received_time": "2026-05-04T06:00:00",
        "folder": "Inbox",
    },
]


def test_run_digest_returns_classified_list():
    with patch("modules.email_digest.get_recent_emails", return_value=MOCK_EMAILS), \
         patch("modules.email_digest.is_processed", return_value=False), \
         patch("modules.email_digest.summarize_email", return_value="Tóm tắt test."), \
         patch("modules.email_digest.suggest_replies", return_value=["R1", "R2", "R3"]), \
         patch("modules.email_digest.save_entry"), \
         patch("modules.email_digest.load_style_profile", return_value=""):
        results = run_digest()

    assert isinstance(results, dict)
    assert "urgent" in results
    assert "normal" in results
    assert "fyi" in results
    total = sum(len(v) for v in results.values())
    assert total == 2


def test_run_digest_skips_processed_emails():
    with patch("modules.email_digest.get_recent_emails", return_value=MOCK_EMAILS), \
         patch("modules.email_digest.is_processed", return_value=True), \
         patch("modules.email_digest.save_entry"):
        results = run_digest()
    total = sum(len(v) for v in results.values())
    assert total == 0
