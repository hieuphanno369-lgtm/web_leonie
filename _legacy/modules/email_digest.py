from modules.outlook_reader import get_recent_emails, mark_processed
from modules.email_history import is_processed, save_entry
from modules.email_classifier import classify_priority
from modules.ai_client import summarize_email, classify_email_ai
from modules.style_learner import load_style_profile
from modules.reply_suggester import suggest_replies


def run_digest(hours: int = 24) -> dict:
    """
    Chạy full pipeline. Trả về dict phân loại:
    {"urgent": [...], "normal": [...], "fyi": [...]}
    Mỗi item là classified email dict với summary và replies.
    """
    style_summary = load_style_profile()
    raw_emails = get_recent_emails(hours=hours)

    results = {"urgent": [], "normal": [], "fyi": []}

    for email in raw_emails:
        if is_processed(email["entry_id"]):
            continue

        priority = classify_priority(email, ai_classify_fn=classify_email_ai)
        summary  = summarize_email(email, priority=priority)
        replies  = suggest_replies(email, style_summary=style_summary)

        classified = {
            **email,
            "priority": priority,
            "summary": summary,
            "replies": replies,
        }
        results[priority].append(classified)
        save_entry(classified)
        mark_processed(email)   # xóa file JSON khỏi queue

    return results
