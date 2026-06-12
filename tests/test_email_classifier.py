import pytest
from modules.email_classifier import classify_priority, _score_email

SAMPLE_EMAIL = {
    "entry_id": "test-001",
    "subject": "Báo cáo tháng 4",
    "sender_name": "Nguyễn Văn A",
    "sender_email": "alice@example.com",
    "to": "Test User <user@example.com>; Nguyen B",
    "cc": "",
    "body": "Dear anh Hiếu, nhờ anh xác nhận báo cáo.",
    "received_time": "2026-05-04T08:00:00",
    "folder": "Inbox",
}


def test_boss_email_always_urgent(monkeypatch):
    monkeypatch.setenv("BOSS_EMAIL", "boss@example.com")
    import importlib, modules.email_classifier as ec
    importlib.reload(ec)
    email = {**SAMPLE_EMAIL, "sender_email": "boss@example.com"}
    assert ec.classify_priority(email, ai_classify_fn=None) == "urgent"


def test_urgent_keyword_in_subject():
    email = {**SAMPLE_EMAIL, "subject": "[URGENT] Cần xử lý ngay"}
    score = _score_email(email)
    assert score >= 4


def test_direct_to_recipient_increases_score():
    email = {**SAMPLE_EMAIL, "to": "user@example.com"}
    score = _score_email(email)
    assert score >= 2


def test_cc_only_low_score():
    email = {
        **SAMPLE_EMAIL,
        "to": "someone@example.com",
        "cc": "user@example.com",
        "body": "Gửi đến team, đính kèm file tham khảo.",  # no keywords
    }
    score = _score_email(email)
    assert score == 1  # chỉ CC, không có keyword


def test_mention_in_body_increases_score():
    email = {**SAMPLE_EMAIL, "body": "Nhờ @Test User xác nhận giúp em nhé."}
    score = _score_email(email)
    assert score >= 2


def test_no_mention_no_keywords_returns_fyi():
    email = {
        **SAMPLE_EMAIL,
        "subject": "FYI thông báo lịch",
        "to": "all@example.com",
        "cc": "",
        "body": "FYI: đính kèm lịch họp tháng 5.",
        "sender_email": "hr@example.com",
    }
    result = classify_priority(email, ai_classify_fn=lambda e: "fyi")
    assert result == "fyi"


def test_score_3_returns_normal():
    email = {**SAMPLE_EMAIL, "subject": "Nhờ anh xác nhận deadline"}
    # to match → +2, "deadline" keyword → +1 = 3 → normal
    result = classify_priority(email, ai_classify_fn=None)
    assert result == "normal"
