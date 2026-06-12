# modules/sql_snippets.py
"""
SQL SNIPPETS — Reusable T-SQL query library.
CRUD + search + category filter, stored in data/sql_snippets.json.
"""
import json
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import streamlit as st

_DATA_FILE = Path("data/sql_snippets.json")

CATEGORIES = [
    "Analysis",
    "Data Cleaning",
    "Sales & KPI",
    "Customer",
    "Time Series",
    "Join Patterns",
    "Admin / DBA",
]

_CAT_ICON = {
    "Analysis":      "◈",
    "Data Cleaning": "⬢",
    "Sales & KPI":   "◉",
    "Customer":      "⟁",
    "Time Series":   "⏱",
    "Join Patterns": "⬡",
    "Admin / DBA":   "⊛",
}

_CAT_COLOR = {
    "Analysis":      "#00d4ff",
    "Data Cleaning": "#7c3aed",
    "Sales & KPI":   "#30d158",
    "Customer":      "#bd00ff",
    "Time Series":   "#ff9f0a",
    "Join Patterns": "#0a84ff",
    "Admin / DBA":   "#ff453a",
}


# ── Storage ──────────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if not _DATA_FILE.exists():
        return []
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(snippets: list[dict]):
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(
        json.dumps(snippets, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Section header helper (matches project style) ────────────────────────────

def _sh(icon: str, title: str, color: str = "#00d4ff",
        anim: str = "pulse", subtitle: str = ""):
    sub = (
        f'<div style="font-size:9px;color:#3d5a6b;letter-spacing:.18em;'
        f'margin-top:1px;font-family:\'JetBrains Mono\',monospace">{subtitle}</div>'
    ) if subtitle else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:9px;padding:2px 0 8px;">'
        f'<span class="anim-{anim}" style="color:{color};font-size:22px;line-height:1">{icon}</span>'
        f'<div>'
        f'<div style="font-size:13px;font-weight:700;color:#e6edf3;letter-spacing:.07em;'
        f'font-family:\'JetBrains Mono\',monospace">{title}</div>'
        f'{sub}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ── Form (Add / Edit) ─────────────────────────────────────────────────────────

def _render_form(snippets: list[dict], mode: str, edit_id: str | None):
    label = "NEW SNIPPET" if mode == "add" else "EDIT SNIPPET"
    st.markdown(
        f'<div style="font-size:11px;font-weight:700;color:#bd00ff;'
        f'font-family:\'JetBrains Mono\',monospace;letter-spacing:.12em;'
        f'padding-bottom:8px">⟁ {label}</div>',
        unsafe_allow_html=True,
    )

    existing: dict = {}
    if mode == "edit" and edit_id:
        existing = next((s for s in snippets if s["id"] == edit_id), {})

    with st.form("snip_form", clear_on_submit=False):
        title = st.text_input(
            "Title *",
            value=existing.get("title", ""),
            placeholder="e.g. Rolling 7-day AVG by Store",
        )
        col1, col2 = st.columns(2)
        with col1:
            cat_idx = CATEGORIES.index(existing["category"]) \
                if existing.get("category") in CATEGORIES else 0
            category = st.selectbox("Category *", CATEGORIES, index=cat_idx)
        with col2:
            description = st.text_input(
                "Description",
                value=existing.get("description", ""),
                placeholder="One-line summary (optional)",
            )
        sql_code = st.text_area(
            "SQL *",
            value=existing.get("sql", ""),
            height=220,
            placeholder="-- paste your T-SQL here",
        )

        col_save, col_cancel, _ = st.columns([1, 1, 5])
        with col_save:
            submitted = st.form_submit_button("◈  Save", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("✕  Cancel", use_container_width=True)

        if cancelled:
            st.session_state.pop("snip_mode", None)
            st.session_state.pop("snip_edit_id", None)
            st.rerun()

        if submitted:
            if not title.strip() or not sql_code.strip():
                st.error("Title và SQL là bắt buộc.")
            else:
                now = datetime.now().isoformat()
                if mode == "add":
                    snippets.append({
                        "id":          str(uuid.uuid4()),
                        "title":       title.strip(),
                        "category":    category,
                        "description": description.strip(),
                        "sql":         sql_code.strip(),
                        "created_at":  now,
                        "updated_at":  now,
                    })
                else:
                    for s in snippets:
                        if s["id"] == edit_id:
                            s.update({
                                "title":       title.strip(),
                                "category":    category,
                                "description": description.strip(),
                                "sql":         sql_code.strip(),
                                "updated_at":  now,
                            })
                _save(snippets)
                st.session_state.pop("snip_mode", None)
                st.session_state.pop("snip_edit_id", None)
                st.rerun()


# ── Snippet card ──────────────────────────────────────────────────────────────

def _render_card(snip: dict, all_snippets: list[dict]):
    sid = snip["id"]
    color = _CAT_COLOR.get(snip.get("category", ""), "#00d4ff")
    expand_key = f"snip_expand_{sid}"

    col_info, col_btns = st.columns([7, 1])

    with col_info:
        desc = snip.get("description", "")
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:#e6edf3;'
            f'font-family:\'JetBrains Mono\',monospace">{snip["title"]}</div>'
            + (f'<div style="font-size:10px;color:#6e7681;margin-top:2px">{desc}</div>'
               if desc else ""),
            unsafe_allow_html=True,
        )

    with col_btns:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("▶", key=f"snip_exp_{sid}", help="Xem SQL"):
                st.session_state[expand_key] = not st.session_state.get(expand_key, False)
                st.rerun()
        with b2:
            if st.button("✏", key=f"snip_edit_{sid}", help="Sửa"):
                st.session_state["snip_mode"] = "edit"
                st.session_state["snip_edit_id"] = sid
                st.rerun()
        with b3:
            if st.button("✕", key=f"snip_del_{sid}", help="Xoá"):
                st.session_state[f"snip_confirm_{sid}"] = True
                st.rerun()

    # Delete confirm
    if st.session_state.get(f"snip_confirm_{sid}"):
        st.warning(f'Xoá **"{snip["title"]}"**?')
        c1, c2, _ = st.columns([1, 1, 6])
        with c1:
            if st.button("◈ Xoá", key=f"snip_ok_{sid}"):
                _save([s for s in all_snippets if s["id"] != sid])
                st.session_state.pop(f"snip_confirm_{sid}", None)
                st.session_state.pop(expand_key, None)
                st.rerun()
        with c2:
            if st.button("Huỷ", key=f"snip_no_{sid}"):
                st.session_state.pop(f"snip_confirm_{sid}", None)
                st.rerun()

    # Expanded SQL view
    if st.session_state.get(expand_key):
        st.code(snip["sql"], language="sql")

    st.markdown(
        '<hr style="border:none;border-top:1px solid #21262d;margin:6px 0">',
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render_sql_snippets():
    _sh("⌥", "SQL SNIPPETS", color="#00d4ff", anim="pulse",
        subtitle="T-SQL // REUSABLE QUERY LIBRARY")

    snippets = _load()

    # ── Toolbar: search + new button
    col_search, col_new = st.columns([5, 1])
    with col_search:
        search = st.text_input(
            "", placeholder="⌕  search title · description · SQL...",
            key="snip_search", label_visibility="collapsed",
        )
    with col_new:
        if st.button("＋  New", key="snip_new_btn", use_container_width=True):
            st.session_state["snip_mode"] = "add"
            st.session_state.pop("snip_edit_id", None)
            st.rerun()

    # ── Category pills
    all_cats = ["All"] + CATEGORIES
    selected_cat = st.radio(
        "", all_cats, horizontal=True,
        key="snip_cat_filter", label_visibility="collapsed",
    )

    st.divider()

    # ── Add / Edit form
    mode = st.session_state.get("snip_mode")
    edit_id = st.session_state.get("snip_edit_id")
    if mode in ("add", "edit"):
        _render_form(snippets, mode, edit_id)
        st.divider()

    # ── Filter
    filtered = snippets
    if selected_cat != "All":
        filtered = [s for s in filtered if s.get("category") == selected_cat]
    if search.strip():
        q = search.strip().lower()
        filtered = [
            s for s in filtered
            if q in s.get("title", "").lower()
            or q in s.get("description", "").lower()
            or q in s.get("sql", "").lower()
        ]

    # ── Empty state
    if not filtered:
        total = len(snippets)
        msg = "◌  Không tìm thấy snippet nào." if (search or selected_cat != "All") \
            else "◌  Chưa có snippet nào. Bấm ＋ New để thêm."
        st.markdown(
            f'<div style="color:#3d5a6b;font-family:\'JetBrains Mono\','
            f'monospace;font-size:11px;padding:20px 0">{msg}</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Count badge
    st.markdown(
        f'<div style="font-size:9px;color:#3d5a6b;font-family:\'JetBrains Mono\','
        f'monospace;padding-bottom:8px">◈ {len(filtered)} snippet(s)</div>',
        unsafe_allow_html=True,
    )

    # ── Group by category
    grouped: dict[str, list] = defaultdict(list)
    for s in filtered:
        grouped[s.get("category", "Uncategorized")].append(s)

    cat_order = CATEGORIES if selected_cat == "All" else [selected_cat]
    for cat in cat_order:
        if cat not in grouped:
            continue
        icon  = _CAT_ICON.get(cat, "◈")
        color = _CAT_COLOR.get(cat, "#00d4ff")
        st.markdown(
            f'<div style="color:{color};font-family:\'JetBrains Mono\',monospace;'
            f'font-size:10px;font-weight:700;letter-spacing:.15em;'
            f'padding:10px 0 4px">{icon}  {cat.upper()}'
            f'<span style="color:#3d5a6b;font-weight:400"> · {len(grouped[cat])}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        for snip in grouped[cat]:
            _render_card(snip, snippets)
