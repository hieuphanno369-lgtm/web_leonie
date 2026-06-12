"""
sql_analyzer.py — SQL → Obsidian note.
Phân tích business intent, tối ưu query, lưu markdown vào vault.

Naming convention (Obsidian standard):
  YYYY-MM-DD - <Title>.md
  ví dụ: 2026-05-09 - Doanh thu phân phối theo brand tháng.md
"""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from modules.ai_client import call_ai
VAULT_PATH    = Path(r"D:\claude-workspace")
SQL_NOTES_DIR = VAULT_PATH / "07_Outputs"


# ── Sanitize ──────────────────────────────────────────────────────────────────

def _sanitize_sql(sql: str) -> str:
    """
    Làm sạch SQL paste từ SSMS / Fabric / VSCode:
    - Thay \t bằng 4 spaces
    - Thay non-breaking space (U+00A0, U+202F, ...) bằng space thường
    - Xóa null bytes và control chars không hợp lệ (trừ \n, \r, \t)
    - Chuẩn hoá line ending về \n
    """
    # Replace various non-standard space chars
    sql = sql.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    # Normalize CRLF
    sql = sql.replace("\r\n", "\n").replace("\r", "\n")
    # Replace tabs with spaces
    sql = sql.replace("\t", "    ")
    # Remove control characters except \n and printable
    sql = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sql)
    return sql.strip()


def _sanitize_json_str(raw: str) -> str:
    """Xóa control chars trong chuỗi JSON trước khi parse."""
    # Strip markdown code fence
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    # Remove all control characters except \n, \r, \t (valid in JSON strings as escaped)
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw)
    return raw


def _slugify(text: str) -> str:
    """
    Chuyển text thành slug: lowercase, remove diacritics, replace spaces with dashes.
    Max 60 ký tự. Dùng cho URL-safe slugs và test.
    """
    # Normalize diacritics
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Lowercase, remove special chars, replace spaces with dashes
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    # Collapse multiple dashes
    text = re.sub(r"-+", "-", text)
    return text[:60]


def _title_to_filename(title: str) -> str:
    """
    Chuyển title sang tên file Obsidian:
    - Xóa ký tự không hợp lệ trong tên file Windows
    - Giữ nguyên tiếng Việt (không slug hóa)
    - Trim whitespace dư
    - Max 80 ký tự
    """
    # Remove chars invalid in Windows filenames
    title = re.sub(r'[\\/:*?"<>|]', "", title)
    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title).strip()
    return title[:80]


# ── Note content ──────────────────────────────────────────────────────────────

def build_note_content(analysis: dict, sql: str) -> str:
    today = date.today().isoformat()
    # YAML-safe values (use Python list repr for YAML compatibility)
    tags_yaml   = str(analysis.get("tags", []))
    tables_yaml = str(analysis.get("tables", []))
    filters_yaml= str(analysis.get("filters", []))
    kw_yaml     = str(analysis.get("keywords", []))

    return (
        f"---\n"
        f"title: {analysis.get('title', '')}\n"
        f"date: {today}\n"
        f"tags: {tags_yaml}\n"
        f"tables: {tables_yaml}\n"
        f"filters: {filters_yaml}\n"
        f"keywords: {kw_yaml}\n"
        f"description: \"{analysis.get('description', '')}\"\n"
        f"---\n\n"
        f"## Business Question\n\n"
        f"{analysis.get('description', '')}\n\n"
        f"## SQL Query\n\n"
        f"```sql\n{_sanitize_sql(sql)}\n```\n\n"
        f"## Tables\n\n"
        + "".join(f"- `{t}`\n" for t in analysis.get("tables", []))
        + "\n"
        f"## Notes\n\n"
        f"_Tạo tự động bởi CHOOPER SQL Analyzer — {today}_\n"
    )


def save_note(analysis: dict, sql: str) -> Path:
    """
    Lưu note vào vault với naming convention:
    YYYY-MM-DD_<slug>.md
    """
    SQL_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    today    = date.today().isoformat()
    slug     = _slugify(analysis.get("title", "Query không tiêu đề"))
    filename = f"{today}_{slug}.md"
    path     = SQL_NOTES_DIR / filename
    path.write_text(build_note_content(analysis, sql), encoding="utf-8")
    return path


# ── AI calls ──────────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> dict:
    raw = _sanitize_json_str(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try to extract first {...} block
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def analyze_query(sql: str) -> dict:
    sql = _sanitize_sql(sql)
    prompt = (
        "Phân tích SQL query sau và trả về JSON với các field:\n"
        "- title: tên ngắn gọn mô tả mục đích query (tiếng Việt, max 60 ký tự)\n"
        "- description: câu hỏi business mà query này trả lời (1 câu, tiếng Việt)\n"
        "- tables: danh sách tên bảng được dùng (array of strings)\n"
        "- filters: danh sách điều kiện WHERE chính (array of strings)\n"
        "- tags: 3-5 từ khóa ngắn liên quan (array of strings, tiếng Anh lowercase)\n"
        "- keywords: 3-5 từ khóa tiếng Việt để link Obsidian graph (array of strings)\n\n"
        "Chỉ trả về JSON thuần, không markdown code fence, không giải thích thêm.\n\n"
        f"SQL:\n{sql}"
    )
    return _parse_json_response(call_ai(prompt, max_tokens=500))


def _rule_based_optimize(sql: str) -> dict:
    """
    Phân tích SQL bằng rule-based khi AI không khả dụng.
    Trả về gợi ý nếu có antipattern, hoặc báo "đã tối ưu" nếu query sạch.
    """
    sql_upper = sql.upper()
    hints = []

    if re.search(r"SELECT\s+\*", sql_upper):
        hints.append("Tránh SELECT * — chỉ định rõ các cột cần thiết để giảm I/O và tăng tốc.")
    if re.search(r"\bSELECT\b.+\bSELECT\b", sql_upper, re.DOTALL):
        hints.append("Subquery lồng nhau — cân nhắc dùng CTE (WITH ...) để tối ưu execution plan.")
    if sql_upper.count("JOIN") >= 3 and "WITH" not in sql_upper:
        hints.append("Nhiều JOIN — thêm CTE để tách logic, giúp query planner tối ưu tốt hơn.")
    if re.search(r"\bOR\b.+\bOR\b", sql_upper):
        hints.append("Nhiều điều kiện OR — cân nhắc dùng IN (...) hoặc UNION để tận dụng index.")
    if re.search(r"LIKE\s+'%[^']+", sql_upper):
        hints.append("LIKE '%...' với wildcard đầu không dùng được index — xem xét Full-Text Search.")
    if re.search(r"\b(CONVERT|CAST)\s*\(", sql_upper) and "WHERE" in sql_upper:
        hints.append("CONVERT/CAST trong WHERE clause ngăn index — tránh dùng hàm trực tiếp trên cột lọc.")

    if not hints:
        return {
            "already_optimal": True,
            "improvements": [],
            "optimized_sql": sql,
            "note": "Query của bạn hiện tại đã được viết tốt — không phát hiện antipattern nào cần tối ưu.",
        }
    return {
        "already_optimal": False,
        "improvements": hints,
        "optimized_sql": sql,
        "note": "Phân tích rule-based (AI không khả dụng). Trên đây là gợi ý cải tiến tiềm năng.",
    }


def optimize_query(sql: str) -> dict:
    sql = _sanitize_sql(sql)
    prompt = (
        "Tối ưu SQL query sau. Giữ nguyên kết quả output (same columns, same rows).\n"
        "Nếu query đã viết tốt và không cần tối ưu thêm, hãy nói rõ điều đó.\n"
        "Trả về JSON với:\n"
        "- already_optimal: true nếu query đã tốt, false nếu có điểm cần cải tiến\n"
        "- improvements: mảng các điểm cải tiến (tiếng Việt, mỗi item 1 câu). [] nếu không có.\n"
        "- optimized_sql: câu query đã tối ưu (string). Giữ nguyên nếu không cần đổi.\n"
        "- note: nhận xét tổng quan 1 câu (tiếng Việt)\n\n"
        "Chỉ trả về JSON thuần, không markdown code fence, không giải thích thêm.\n\n"
        f"SQL:\n{sql}"
    )
    try:
        result = _parse_json_response(call_ai(prompt, max_tokens=900))
        result.setdefault("already_optimal", not bool(result.get("improvements")))
        result.setdefault("improvements", [])
        result.setdefault("optimized_sql", sql)
        result.setdefault("note", "")
        return result
    except RuntimeError:
        # AI không khả dụng → rule-based fallback
        return _rule_based_optimize(sql)
    except Exception:
        # JSON parse error → rule-based fallback
        return _rule_based_optimize(sql)
