from pathlib import Path

VAULT_PATH = Path(r"D:\ai_brain")


def list_files() -> list[Path]:
    return sorted(VAULT_PATH.rglob("*.md"))


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _score(path: Path, kw_lower: list[str]) -> int:
    """Tính điểm liên quan: tên file match > nội dung match, nhiều keyword match > ít."""
    score = 0
    stem = path.stem.lower()
    content = read_file(path).lower()
    for k in kw_lower:
        if k in stem:
            score += 3          # match tên file — ưu tiên cao
        elif k in content:
            score += 1          # match nội dung
    return score


def get_context(keywords: list[str] | None = None) -> str:
    """Trả về snippets từ vault phù hợp nhất với keywords (tên task + ghi chú)."""
    all_files = list_files()
    if not all_files:
        return "(vault trống hoặc đường dẫn sai)"

    # Lọc bỏ từ ngắn/stop words không có nghĩa
    stop = {"và", "hoặc", "để", "cho", "với", "trên", "trong", "của", "là",
            "kỹ", "lại", "thêm", "check", "the", "and", "or", "to", "a", "an"}
    if keywords:
        kw_lower = [k.lower() for k in keywords if len(k) > 2 and k.lower() not in stop]
    else:
        kw_lower = []

    if kw_lower:
        scored = [(f, _score(f, kw_lower)) for f in all_files]
        scored = [(f, s) for f, s in scored if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        candidates = [f for f, _ in scored[:5]] if scored else all_files[:3]
    else:
        candidates = all_files[:3]

    snippets = []
    for f in candidates[:4]:
        content = read_file(f)
        if content.strip():
            rel = f.relative_to(VAULT_PATH)
            snippets.append(f"**{rel}**:\n{content[:800]}")

    return "\n\n---\n\n".join(snippets) if snippets else "(không tìm thấy context liên quan)"


