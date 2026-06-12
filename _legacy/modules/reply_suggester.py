from modules.ai_client import _call_ai

_FALLBACK_REPLIES = [
    "Em đã nhận, sẽ xử lý và phản hồi sớm ạ.",
    "Dạ em đang xem xét, sẽ update ngay khi có kết quả.",
    "Anh/Chị có thể cung cấp thêm thông tin để em hỗ trợ tốt hơn không ạ?",
]


def suggest_replies(email: dict, style_summary: str) -> list[str]:
    """
    Trả về list 3 reply options (string). Fallback về default nếu AI fail.
    """
    style_block = f"\nPhong cách viết của bạn: {style_summary}" if style_summary else ""
    prompt = (
        f"Gợi ý 3 câu trả lời ngắn (mỗi câu 1-2 câu) cho email bên dưới bằng tiếng Việt.{style_block}\n"
        "Mỗi option theo hướng khác nhau: 1) xác nhận/đồng ý, 2) đang xử lý/cần thời gian, 3) cần thêm thông tin.\n"
        "Định dạng: mỗi option trên 1 dòng riêng, không đánh số, không bullet.\n\n"
        f"Từ: {email['sender_name']}\n"
        f"Tiêu đề: {email['subject']}\n"
        f"Nội dung: {email.get('body', '')[:300]}"
    )
    try:
        raw = _call_ai(prompt, max_tokens=200)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if len(lines) >= 3:
            return lines[:3]
        while len(lines) < 3:
            lines.append(_FALLBACK_REPLIES[len(lines)])
        return lines
    except Exception:
        return list(_FALLBACK_REPLIES)
