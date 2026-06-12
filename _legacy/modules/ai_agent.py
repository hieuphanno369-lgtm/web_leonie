# modules/ai_agent.py
"""
AI Agent Chatbox — Claude API + Vault RAG
Tab riêng, vault status bar, suggested follow-ups, free-text Q&A.
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import streamlit as st

from modules.ai_client import call_ai
from modules.obsidian_client import VAULT_PATH, _score, get_context, list_files


# ── Vault status ───────────────────────────────────────────────────────────────

def _vault_status_bar() -> tuple[bool, int]:
    """Render connection/status bar. Returns (vault_ok, n_files)."""
    all_files = list_files()
    n_files = len(all_files)
    vault_ok = n_files > 0

    status_color = "#30d158" if vault_ok else "#ff2d55"
    status_text = "CONNECTED" if vault_ok else "VAULT EMPTY"
    last_sync = datetime.now().strftime("%H:%M")

    sources: list[str] = st.session_state.get("ai_agent_sources", [])
    sources_html = ""
    if sources:
        chips = "".join(
            f'<span style="background:#1d2733;border:1px solid #30363d;border-radius:3px;'
            f'padding:1px 6px;font-size:9px;color:#8b949e;margin-right:4px">'
            f'{html.escape(s)}</span>'
            for s in sources[:4]
        )
        sources_html = (
            f'<div style="margin-top:4px;font-size:9px;color:#5a7a8a;">'
            f'đang dùng: {chips}</div>'
        )

    st.markdown(
        f'<div style="background:#0f1923;border:1px solid #1d2733;border-radius:6px;'
        f'padding:8px 12px;margin-bottom:12px;font-family:\'JetBrains Mono\',monospace;">'
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f'<span style="color:{status_color};font-size:13px">●</span>'
        f'<span style="font-size:10px;font-weight:700;color:{status_color};letter-spacing:.1em">'
        f'VAULT {status_text}</span>'
        f'<span style="color:#2a3a4a">│</span>'
        f'<span style="font-size:10px;color:#8b949e">◫ {n_files} files indexed</span>'
        f'<span style="color:#2a3a4a">│</span>'
        f'<span style="font-size:10px;color:#8b949e">⊡ Last sync {last_sync}</span>'
        f'</div>'
        f'{sources_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
    return vault_ok, n_files


# ── System prompt ──────────────────────────────────────────────────────────────

def _build_system_prompt(vault_context: str) -> str:
    return (
        "Bạn là AI Agent chuyên biệt hỗ trợ Data Analyst ngành FMCG (VitaDairy).\n"
        "Bạn đang truy cập vault kiến thức cá nhân của người dùng.\n\n"
        "=== VAULT CONTEXT ===\n"
        f"{vault_context}\n"
        "====================\n\n"
        "NGUYÊN TẮC:\n"
        "- Ưu tiên dùng thông tin từ vault trước; cite tên file khi dùng\n"
        "- Khi vault không đủ: dùng kiến thức FMCG/DA chung và nói rõ\n"
        "- Trả lời bằng tiếng Việt, thân thiện, business-focused\n"
        "- Cuối mỗi câu trả lời: đề xuất đúng 3 câu hỏi follow-up ngắn\n"
        "  format: ❓ [câu hỏi ngắn]\n"
        "- Không bịa số liệu cụ thể khi không có trong vault"
    )


def _call_with_history(history: list[dict], vault_context: str) -> str:
    system = _build_system_prompt(vault_context)
    turns = "\n".join(
        f"{'User' if m['role'] == 'user' else 'AI'}: {m['content']}"
        for m in history[-8:]
    )
    prompt = f"{system}\n\nHỘI THOẠI:\n{turns}\n\nAI:"
    return call_ai(prompt, max_tokens=800)


# ── Source resolution ──────────────────────────────────────────────────────────

def _resolve_sources(query: str) -> list[str]:
    stop = {"và", "hoặc", "để", "cho", "với", "trên", "trong", "của", "là",
            "the", "and", "or", "to", "a", "an"}
    kw = [w.lower() for w in query.split() if len(w) > 2 and w.lower() not in stop]
    all_files = list_files()
    if not kw or not all_files:
        return [f.stem for f in all_files[:3]]
    scored = [(f, _score(f, kw)) for f in all_files]
    scored = [(f, s) for f, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [f.stem for f, _ in scored[:4]] if scored else [f.stem for f in all_files[:3]]


# ── Message rendering ──────────────────────────────────────────────────────────

def _render_message(role: str, content: str):
    if role == "user":
        st.markdown(
            f'<div style="background:#1d2733;border:1px solid #21262d;border-radius:8px;'
            f'padding:10px 14px;margin:5px 0;margin-left:12%;">'
            f'<div style="font-size:9px;color:#3d5a6b;letter-spacing:.1em;margin-bottom:4px">YOU</div>'
            f'<div style="color:#e6edf3;font-size:13px;line-height:1.5">{html.escape(content)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # AI message — allow markdown-like content (already sanitised by call_ai)
        st.markdown(
            f'<div style="background:#0f1923;border:1px solid #1e3a4f;border-radius:8px;'
            f'padding:10px 14px;margin:5px 0;margin-right:5%;">'
            f'<div style="font-size:9px;color:#bd00ff;letter-spacing:.1em;margin-bottom:4px">AI AGENT</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(content)


# ── Main render ────────────────────────────────────────────────────────────────

def render_ai_agent():
    # ── Header
    st.markdown(
        '<div style="display:flex;align-items:center;gap:9px;padding:2px 0 8px;">'
        '<span style="color:#bd00ff;font-size:22px;line-height:1">⬡</span>'
        '<div>'
        '<div style="font-size:13px;font-weight:700;color:#e6edf3;letter-spacing:.07em;'
        'font-family:\'JetBrains Mono\',monospace">AI AGENT</div>'
        '<div style="font-size:9px;color:#3d5a6b;letter-spacing:.18em;'
        'font-family:\'JetBrains Mono\',monospace">'
        'CLAUDE // VAULT RAG // FMCG SPECIALIST // SELF-LEARNING</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Vault status bar
    vault_ok, n_files = _vault_status_bar()

    # ── Session state init
    if "ai_agent_history" not in st.session_state:
        st.session_state["ai_agent_history"] = []
    if "ai_agent_pending" not in st.session_state:
        st.session_state["ai_agent_pending"] = ""
    history: list[dict] = st.session_state["ai_agent_history"]

    # ── Config expander
    with st.expander("⊛ Config & Vault Info", expanded=False):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.caption(f"Vault path: `{VAULT_PATH}`")
            st.caption(f"Files indexed: **{n_files}** .md files")
            if n_files > 0:
                recent = sorted(list_files(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
                st.caption("Files mới nhất: " + ", ".join(f.stem for f in recent))
        with col_c2:
            if st.button("⌫ Xóa lịch sử chat", key="agent_clear_hist"):
                st.session_state["ai_agent_history"] = []
                st.session_state["ai_agent_sources"] = []
                st.session_state["ai_agent_pending"] = ""
                st.rerun()
            if not vault_ok:
                st.warning(f"Vault tại `{VAULT_PATH}` trống hoặc không tồn tại.")

    # ── Starter questions (only when history is empty)
    if not history:
        st.markdown(
            '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.1em;'
            'font-family:\'JetBrains Mono\',monospace;margin:8px 0 6px">GỢI Ý CÂU HỎI</div>',
            unsafe_allow_html=True,
        )
        starters = [
            "Tóm tắt các kiến thức chính trong vault của tôi",
            "Hướng dẫn phân tích A/B test cho FMCG",
            "Metric quan trọng cần track cho brand FMCG là gì?",
            "Cách giải thích kết quả ML model cho sếp không biết tech",
        ]
        sc1, sc2 = st.columns(2)
        for i, q in enumerate(starters):
            with (sc1 if i % 2 == 0 else sc2):
                if st.button(q, key=f"starter_{i}", use_container_width=True):
                    st.session_state["ai_agent_pending"] = q
                    st.rerun()

    # ── Chat history display
    if history:
        for msg in history:
            _render_message(msg["role"], msg["content"])

    # ── Input area
    st.divider()

    pending = st.session_state.get("ai_agent_pending", "")
    col_inp, col_snd = st.columns([5, 1])
    with col_inp:
        user_input = st.text_input(
            "Tin nhắn",
            value=pending,
            placeholder="Hỏi AI Agent... (vault + kiến thức FMCG)",
            key="agent_input_box",
            label_visibility="collapsed",
        )
    with col_snd:
        send = st.button("▶ Gửi", key="agent_send_btn", use_container_width=True)

    # ── Process message
    if (send or pending) and user_input.strip():
        query = user_input.strip()
        st.session_state["ai_agent_pending"] = ""

        # Resolve vault context + sources
        with st.spinner("⌕ Đang tìm kiếm trong vault..."):
            keywords = query.split()
            vault_ctx = get_context(keywords)
            sources = _resolve_sources(query)
        st.session_state["ai_agent_sources"] = sources

        history.append({"role": "user", "content": query})

        with st.spinner("⬡ AI đang suy nghĩ..."):
            try:
                response = _call_with_history(history, vault_ctx)
            except Exception as e:
                response = f"Lỗi kết nối AI: {e}"
        history.append({"role": "assistant", "content": response})
        st.rerun()
