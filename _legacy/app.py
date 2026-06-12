import os
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime
from dotenv import load_dotenv, find_dotenv

from modules.task_manager import load_tasks as _load_tasks_raw, add_task, update_task, delete_task, get_active_tasks
from modules.discord_notifier import send_confirm, send_all_reminders, send_email_digest
from modules.deadline import calculate_deadline, get_label
# generate_checklist removed — no longer auto-generated on task create
from app_helpers import get_stats, group_by_priority, filter_tasks

load_dotenv(find_dotenv(), encoding='utf-8')

st.set_page_config(page_title="Chooper", page_icon="⬡", layout="wide",
                   initial_sidebar_state="expanded")


@st.cache_data(ttl=2, show_spinner=False)
def load_tasks() -> list[dict]:
    """Cached wrapper — busted automatically every 2 s (fast enough for interactive use)."""
    return _load_tasks_raw()


PRIORITY_COLORS = {
    "high":   "#ff2d55",
    "medium": "#ff9f0a",
    "low":    "#30d158",
    "ad-hoc": "#64d2ff",
}

CATEGORY_OPTIONS = {
    "◈ High":   "high",
    "◆ Medium": "medium",
    "◇ Low":    "low",
    "⚡Ad-hoc": "ad-hoc",
}

RECUR_OPTIONS = {
    "Không lặp":     None,
    "↺ Hằng tháng": "monthly",
    "↻ Hằng năm":   "yearly",
}
RECUR_REVERSE = {v: k for k, v in RECUR_OPTIONS.items()}

PRIORITY_GROUP_CONFIG = [
    ("high",   "◈ HIGH",   True),
    ("medium", "◆ MEDIUM", True),
    ("low",    "◇ LOW",    False),
    ("ad-hoc", "⚡ AD-HOC", False),
]

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [data-testid="stApp"] { background: #0d1117 !important; }

.block-container {
  padding-top: 1rem !important;
  padding-bottom: 0.4rem !important;
  padding-left: 1.2rem !important;
  padding-right: 1.2rem !important;
  max-width: 100% !important;
  min-width: 960px !important;   /* zoom-lock: layout doesn't reflow */
}
/* Allow horizontal scroll when zoomed instead of breaking layout */
section[data-testid="stMain"],
div[data-testid="stAppViewContainer"] > section.main {
  overflow-x: auto !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: #0d1117 !important;
  border-right: 1px solid #21262d !important;
  min-width: 260px !important;
  max-width: 260px !important;
}
section[data-testid="stSidebar"] .block-container {
  padding: 0 1rem 1.5rem !important;
}
/* Xóa toàn bộ padding/margin top của mọi wrapper trong sidebar */
[data-testid="stSidebarContent"],
[data-testid="stSidebarContent"] > div,
[data-testid="stSidebarContent"] > div > div,
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div {
  padding-top: 0 !important;
  margin-top: 0 !important;
}
/* Ẩn header bar mặc định của Streamlit sidebar (chứa collapse btn) */
section[data-testid="stSidebar"] > div:first-child > div:first-child:has(button) {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
}

/* ── Metrics ── */
div[data-testid="metric-container"] {
  background: #0f1923 !important;
  border: 1px solid #1d2733 !important;
  border-radius: 5px !important;
  padding: 7px 10px 5px !important;
}
div[data-testid="stMetricValue"] {
  font-size: 20px !important; font-weight: 700 !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
}
div[data-testid="stMetricLabel"] {
  font-size: 9px !important; color: #8b949e !important;
  letter-spacing: .1em !important; text-transform: uppercase !important;
}

/* ── Animations ── */
@keyframes neon-pulse {
  0%,100% { filter: brightness(1); opacity: .8; }
  50%      { filter: brightness(1.7) drop-shadow(0 0 7px currentColor); opacity: 1; }
}
@keyframes float-y {
  0%,100% { transform: translateY(0px); }
  50%     { transform: translateY(-4px); }
}
@keyframes scan-line {
  0%,100% { opacity: .55; }
  50%     { opacity: 1; }
}
@keyframes spin-slow  { to { transform: rotate(360deg); } }
@keyframes blink-caret { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
@keyframes matrix-drop {
  0%   { transform: translateY(-6px); opacity: 0; }
  30%  { opacity: 1; }
  100% { transform: translateY(0); opacity: 1; }
}

.anim-pulse  { animation: neon-pulse  2.2s ease-in-out infinite; display:inline-block; }
.anim-float  { animation: float-y     3.0s ease-in-out infinite; display:inline-block; }
.anim-scan   { animation: scan-line   1.8s ease-in-out infinite; display:inline-block; }
.anim-spin   { animation: spin-slow   7.0s linear infinite;      display:inline-block; }
.anim-blink  { animation: blink-caret 1.0s step-end infinite;    display:inline-block; }
.anim-matrix { animation: matrix-drop 0.6s ease-out both;        display:inline-block; }

/* ── Buttons ── */
div[data-testid="stButton"] > button {
  background: #0f1923 !important;
  border: 1px solid #21262d !important;
  color: #c9d1d9 !important;
  border-radius: 3px !important;
  font-size: 11px !important;
  padding: 3px 10px !important;
  font-family: 'JetBrains Mono', monospace !important;
  min-height: 28px !important;
  transition: border-color .15s, color .15s, box-shadow .15s !important;
  letter-spacing: .04em !important;
}
div[data-testid="stButton"] > button:hover {
  border-color: #00d4ff !important;
  color: #00d4ff !important;
  box-shadow: 0 0 8px rgba(0,212,255,.25) !important;
}

/* Primary-style button (notebook launch) */
.btn-primary div[data-testid="stButton"] > button {
  border-color: #00d4ff !important;
  color: #00d4ff !important;
}

/* ══════════════════════════════════════════════════════════════════
   INPUT SYSTEM — one border per field, zero double shapes
   Rule: border lives on the OUTERMOST baseweb wrapper.
         Everything nested inside → transparent / borderless.
   ══════════════════════════════════════════════════════════════════ */

/* ── Text / Date inputs: border on div[data-baseweb="input"] ── */
div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stDateInput"]  div[data-baseweb="input"] {
  background: #0f1923 !important;
  border: 1px solid #21262d !important;
  border-radius: 5px !important;
  box-shadow: none !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"]  input {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
  outline: none !important;
}
div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
div[data-testid="stDateInput"]  div[data-baseweb="input"]:focus-within {
  border-color: #00d4ff !important;
  box-shadow: 0 0 0 1px rgba(0,212,255,.35) !important;
}

/* ── Number input: style the baseweb wrapper + step buttons consistently ── */
div[data-testid="stNumberInput"] div[data-baseweb="input"] {
  background: #0f1923 !important;
  border: 1px solid #21262d !important;
  border-radius: 5px !important;
  box-shadow: none !important;
}
div[data-testid="stNumberInput"] input {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
  outline: none !important;
}
div[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within {
  border-color: #00d4ff !important;
  box-shadow: 0 0 0 1px rgba(0,212,255,.35) !important;
}
/* Step buttons — borderless, no box */
button[data-testid="stNumberInputStepDown"],
button[data-testid="stNumberInputStepUp"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #6e7681 !important;
  font-size: 14px !important;
  line-height: 1 !important;
  cursor: pointer !important;
  padding: 0 6px !important;
  transition: color .15s !important;
}
button[data-testid="stNumberInputStepDown"]:hover,
button[data-testid="stNumberInputStepUp"]:hover {
  color: #00d4ff !important;
}

/* ── TextArea: strip wrapper, border on <textarea> ── */
div[data-testid="stTextArea"] div[data-baseweb="textarea"],
div[data-testid="stTextArea"] > div > div {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
div[data-testid="stTextArea"] textarea {
  background: #0f1923 !important;
  border: 1px solid #21262d !important;
  color: #e6edf3 !important;
  border-radius: 5px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}
div[data-testid="stTextArea"] textarea:focus {
  border-color: #00d4ff !important;
  box-shadow: 0 0 0 1px rgba(0,212,255,.35) !important;
  outline: none !important;
}

/* ── Selectbox: nuclear strip at every level, ONE border on control box ── */
/* Level 1-3 wrappers: all transparent/borderless */
div[data-testid="stSelectbox"] > div,
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
/* Control box = first div child of baseweb select — THE only visible border */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child {
  background: #0f1923 !important;
  border: 1px solid #21262d !important;
  border-radius: 5px !important;
  box-shadow: none !important;
  min-height: 38px !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}
/* Strip everything inside the control box */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:first-child > div > div {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}

/* ── MultiSelect: same nuclear strip ── */
div[data-testid="stMultiSelect"] > div,
div[data-testid="stMultiSelect"] > div > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:first-child {
  background: #0f1923 !important;
  border: 1px solid #21262d !important;
  border-radius: 5px !important;
  box-shadow: none !important;
  min-height: 38px !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:first-child > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:first-child > div > div {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}
/* Tag pills inside multiselect */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background: #1d2733 !important;
  border: 1px solid #30363d !important;
  border-radius: 3px !important;
  color: #e6edf3 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important;
  letter-spacing: .1em !important;
  color: #8b949e !important;
  padding: 5px 14px !important;
  text-transform: uppercase !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #00d4ff !important;
  border-bottom: 2px solid #00d4ff !important;
}
div[data-testid="stTabs"] div[role="tablist"] {
  border-bottom: 1px solid #1d2733 !important;
  gap: 0 !important;
  margin-bottom: 5px !important;
  flex-wrap: nowrap !important;       /* tabs never wrap to next line */
  overflow-x: auto !important;        /* scroll if needed, no overflow cut */
  scrollbar-width: none !important;   /* hide scrollbar on the tab row */
}
button[data-baseweb="tab"] {
  flex-shrink: 0 !important;          /* tabs don't compress when zoomed */
}

/* ── Expanders ── */
div[data-testid="stExpander"] {
  border: 1px solid #1d2733 !important;
  border-radius: 3px !important;
  margin-bottom: 2px !important;
  background: #090e14 !important;
}
details > summary {
  padding: 4px 10px !important;
  font-size: 11px !important;
  font-family: 'JetBrains Mono', monospace !important;
  color: #8b949e !important;
  letter-spacing: .06em !important;
}

/* ── Dividers ── */
hr { border-color: #1d2733 !important; margin: 5px 0 !important; }

/* ── Typography ── */
h1,h2,h3 { font-family: 'JetBrains Mono', monospace !important; color: #e6edf3 !important; }
h1 { font-size: 17px !important; font-weight: 700 !important; margin: 0 0 2px !important; }
h2, h3 { font-size: 12px !important; font-weight: 600 !important; margin: 3px 0 2px !important; }

/* ── Alerts ── */
div[data-testid="stSuccess"] {
  background: rgba(48,209,88,.07) !important;
  border: 1px solid rgba(48,209,88,.28) !important;
  border-radius: 3px !important; font-size: 11px !important; padding: 5px 10px !important;
}
div[data-testid="stError"] {
  background: rgba(255,45,85,.07) !important;
  border: 1px solid rgba(255,45,85,.28) !important;
  border-radius: 3px !important; font-size: 11px !important;
}
div[data-testid="stInfo"] {
  background: rgba(0,212,255,.05) !important;
  border: 1px solid rgba(0,212,255,.2) !important;
  border-radius: 3px !important; font-size: 11px !important;
}
div[data-testid="stWarning"] {
  background: rgba(255,159,10,.06) !important;
  border: 1px solid rgba(255,159,10,.25) !important;
  border-radius: 3px !important; font-size: 11px !important;
}
div[data-testid="stCaptionContainer"] p {
  font-size: 10px !important; color: #6e7681 !important;
  margin: 0 0 4px !important;
  font-family: 'JetBrains Mono', monospace !important; letter-spacing: .04em !important;
}
code, pre {
  background: #161b22 !important; color: #79c0ff !important;
  font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important;
}
/* stDateInput styled in the unified input block above */

/* ── Sidebar widgets ── */
section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {
  font-size: 22px !important;
  font-weight: 700 !important;
  color: #e6edf3 !important;
}
section[data-testid="stSidebar"] div[data-testid="metric-container"] {
  padding: 10px 12px 8px !important;
  background: #161b22 !important;
  border: 1px solid #21262d !important;
  border-radius: 8px !important;
}
section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] {
  font-size: 11px !important;
  color: #8b949e !important;
}
/* Sidebar buttons — larger, more readable */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
  font-size: 12px !important;
  padding: 6px 12px !important;
  min-height: 34px !important;
  border-radius: 6px !important;
  letter-spacing: .02em !important;
  text-align: left !important;
  justify-content: flex-start !important;
}

/* ── Fully remove Streamlit header (fixes logo-covered + sidebar-flicker bugs) ── */
header[data-testid="stHeader"],
header[data-testid="stHeader"] * { display: none !important; }
#MainMenu { display: none !important; }
footer    { display: none !important; }

/* ── Sidebar: always visible — force open regardless of Streamlit state ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"][aria-expanded="false"],
section[data-testid="stSidebar"][aria-expanded="true"] {
  display:    flex !important;
  visibility: visible !important;
  transform:  translateX(0px) !important;
  min-width:  260px !important;
  max-width:  260px !important;
  width:      260px !important;
  position:   relative !important;
  flex-shrink: 0 !important;
  pointer-events: auto !important;
}
/* Hide ALL sidebar toggle / collapse controls — sidebar is permanently open */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[data-testid="baseButton-header"],
button[kind="header"],
div[data-testid="stSidebarResizeHandle"],
div[class*="ResizeHandle"],
div[class*="resizeHandle"],
svg[data-testid="stSidebarResizeHandleIcon"] {
  display: none !important;
  pointer-events: none !important;
}
/* Make main area shrink correctly next to always-open sidebar */
section.main { margin-left: 0 !important; }
div[data-testid="stAppViewContainer"] > section.main { margin-left: 260px !important; }

/* Main content: no header, flush top */
.block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
for key, val in [
    ("show_add_form",          False),
    ("editing_task_id",        None),
    ("digest_results",         None),
    ("checklist_result",       None),
    ("selected_task_id",       None),
    ("sql_analysis",           None),
    ("sql_optimization",       None),
    ("jupyter_url",            None),
    ("jupyter_running",        False),
    ("email_to_task_prefill",  None),   # {task_name, note} from email→task
    ("daily_briefing_text",    None),
    ("daily_briefing_date",    None),
    ("smart_deadline_hint",    None),
    ("active_tag_filter",      None),   # tag string or None
]:
    if key not in st.session_state:
        st.session_state[key] = val


# ── UI helpers ────────────────────────────────────────────────────────────────
def section_header(icon: str, title: str, color: str = "#00d4ff",
                   anim: str = "pulse", subtitle: str = ""):
    sub = (f'<div style="font-size:9px;color:#3d5a6b;letter-spacing:.18em;'
           f'margin-top:1px;font-family:\'JetBrains Mono\',monospace">{subtitle}</div>') if subtitle else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:9px;padding:2px 0 5px;">'
        f'<span class="anim-{anim}" style="color:{color};font-size:22px;line-height:1">{icon}</span>'
        f'<div>'
        f'<div style="font-size:13px;font-weight:700;color:#e6edf3;letter-spacing:.07em;'
        f'font-family:\'JetBrains Mono\',monospace">{title}</div>'
        f'{sub}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def priority_group_header(label: str, count: int, raw_key: str):
    color = PRIORITY_COLORS.get(raw_key, "#8b949e")
    st.markdown(
        f'<div style="background:linear-gradient(90deg,{color}1a 0%,transparent 75%);'
        f'border-left:3px solid {color};padding:5px 11px;border-radius:3px;'
        f'margin:7px 0 2px;font-weight:700;font-size:11px;letter-spacing:.14em;'
        f'color:{color};font-family:\'JetBrains Mono\',monospace;">'
        f'{label} <span style="opacity:.4;font-weight:400">({count})</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def sidebar_divider(label: str = ""):
    st.markdown(
        f'<div style="color:#2a3a4a;font-size:9px;letter-spacing:.15em;'
        f'font-family:\'JetBrains Mono\',monospace;padding:6px 0 3px">── {label} ──</div>',
        unsafe_allow_html=True,
    )


# ── Sidebar context helpers (cached 5 min) ───────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _get_inbox_unread() -> int:
    """Đếm email chưa đọc trong Inbox qua win32com. -1 nếu không khả dụng."""
    try:
        import pythoncom, win32com.client
        pythoncom.CoInitialize()
        try:
            try:
                ol = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                ol = win32com.client.Dispatch("Outlook.Application")
            return ol.GetNamespace("MAPI").GetDefaultFolder(6).UnReadItemCount
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return -1


@st.cache_data(ttl=300, show_spinner=False)
def _get_today_meetings() -> list[dict]:
    """Lấy cuộc họp hôm nay từ Outlook Calendar qua win32com."""
    from datetime import datetime, timedelta
    meetings = []
    try:
        import pythoncom, win32com.client
        pythoncom.CoInitialize()
        try:
            try:
                ol = win32com.client.GetActiveObject("Outlook.Application")
            except Exception:
                ol = win32com.client.Dispatch("Outlook.Application")
            ns  = ol.GetNamespace("MAPI")
            cal = ns.GetDefaultFolder(9)   # 9 = Calendar
            items = cal.Items
            items.IncludeRecurrences = True
            items.Sort("[Start]")
            today    = datetime.now()
            tomorrow = today + timedelta(days=1)
            fmt = "%m/%d/%Y %I:%M %p"
            filtered = items.Restrict(
                f"[Start] >= '{today.strftime(fmt)}' AND [Start] < '{tomorrow.strftime(fmt)}'"
            )
            for item in filtered:
                try:
                    meetings.append({
                        "subject": (item.Subject or "")[:35],
                        "start":   item.Start.strftime("%H:%M"),
                        "end":     item.End.strftime("%H:%M"),
                    })
                except Exception:
                    continue
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        pass
    return meetings


# ── Sidebar ───────────────────────────────────────────────────────────────────
def _sb_section(label: str):
    """Thin labelled divider for sidebar sections."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;margin:12px 0 6px;">'
        f'<span style="font-size:10px;font-weight:600;letter-spacing:.12em;'
        f'color:#4a6a7a;text-transform:uppercase;font-family:\'JetBrains Mono\',monospace">'
        f'{label}</span>'
        f'<div style="flex:1;height:1px;background:#1d2733"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        # ── Branding ──────────────────────────────────────────────────────────
        now = datetime.now()
        st.markdown(
            f'<div style="padding:4px 0 12px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
            f'<span style="font-size:22px;color:#00d4ff;animation:spin-slow 10s linear infinite;'
            f'display:inline-block">⬡</span>'
            f'<div>'
            f'<div style="font-size:16px;font-weight:700;color:#e6edf3;'
            f'font-family:\'JetBrains Mono\',monospace;letter-spacing:.12em">CHOOPER</div>'
            f'<div style="font-size:10px;color:#4a6a7a;font-family:\'JetBrains Mono\',monospace">'
            f'Productivity · AI</div>'
            f'</div></div>'
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;'
            f'padding:10px 12px;display:flex;justify-content:space-between;align-items:center;">'
            f'<div>'
            f'<div style="font-size:22px;font-weight:700;color:#00d4ff;'
            f'font-family:\'JetBrains Mono\',monospace;letter-spacing:.04em;line-height:1">'
            f'{now.strftime("%H:%M")}</div>'
            f'<div style="font-size:11px;color:#8b949e;margin-top:2px">'
            f'{now.strftime("%A, %d/%m/%Y")}</div>'
            f'</div>'
            f'<div style="font-size:28px;opacity:.12">📅</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Quick stats ───────────────────────────────────────────────────────
        all_tasks = load_tasks()
        stats = get_stats(all_tasks)
        active_tasks = [t for t in all_tasks if t.get("active")]

        col1, col2 = st.columns(2)
        with col1:
            over_color = "#ff2d55" if stats["overdue"] > 0 else "#3d3d3d"
            st.markdown(
                f'<div style="background:rgba(255,45,85,.07);border:1px solid rgba(255,45,85,.25);'
                f'border-radius:7px;padding:8px 10px;text-align:center;">'
                f'<div style="font-size:9px;color:{over_color};letter-spacing:.12em;opacity:.8;'
                f'font-family:\'JetBrains Mono\',monospace">⬥ QUÁ HẠN</div>'
                f'<div style="font-size:22px;font-weight:700;color:{over_color};'
                f'font-family:\'JetBrains Mono\',monospace;line-height:1.2">{stats["overdue"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div style="background:rgba(0,212,255,.06);border:1px solid rgba(0,212,255,.22);'
                f'border-radius:7px;padding:8px 10px;text-align:center;">'
                f'<div style="font-size:9px;color:#00d4ff;letter-spacing:.12em;opacity:.8;'
                f'font-family:\'JetBrains Mono\',monospace">◈ ĐANG LÀM</div>'
                f'<div style="font-size:22px;font-weight:700;color:#00d4ff;'
                f'font-family:\'JetBrains Mono\',monospace;line-height:1.2">{stats["active"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Quick actions ─────────────────────────────────────────────────────
        _sb_section("Thao tác nhanh")
        if st.button("＋  Task mới", use_container_width=True, key="sb_add"):
            st.session_state.show_add_form = True
            st.rerun()
        st.selectbox(
            "filter",
            options=["", "high", "medium", "low", "ad-hoc"],
            format_func=lambda x: "◇  Phân loại task" if x == "" else {
                "high": "◈  High", "medium": "◆  Medium",
                "low": "◇  Low", "ad-hoc": "⚡  Ad-hoc",
            }.get(x, x),
            label_visibility="collapsed",
            key="sb_priority_filter",
        )
        if st.button("◈  Discord", use_container_width=True, key="sb_discord"):
            tasks = get_active_tasks()
            send_all_reminders(tasks)
            st.success("[ ok ]  Đã gửi!")
        nb_label = "◉  Jupyter [ running ]" if st.session_state.jupyter_running else "◎  Jupyter"
        if st.button(nb_label, use_container_width=True, key="sb_jupyter"):
            _launch_jupyter()
            st.rerun()

        # ── Upcoming deadlines ────────────────────────────────────────────────
        _sb_section("Deadline sắp tới")
        today = date.today().isoformat()
        upcoming = sorted(active_tasks, key=lambda t: t.get("deadline", "9999"))[:5]

        if upcoming:
            for task in upcoming:
                dl = task.get("deadline", "")
                days_left = (date.fromisoformat(dl) - date.today()).days if dl else 99
                if days_left < 0:
                    badge_color, badge_bg, badge_text = "#ff2d55", "rgba(255,45,85,.12)", f"Trễ {-days_left}d"
                elif days_left == 0:
                    badge_color, badge_bg, badge_text = "#ff9f0a", "rgba(255,159,10,.12)", "Hôm nay"
                elif days_left <= 2:
                    badge_color, badge_bg, badge_text = "#ff9f0a", "rgba(255,159,10,.08)", f"Còn {days_left}d"
                else:
                    badge_color, badge_bg, badge_text = "#8b949e", "rgba(139,148,158,.06)", f"Còn {days_left}d"
                bar_color = PRIORITY_COLORS.get(task.get("category_raw", "low"), "#8b949e")
                name = task["task_name"][:28] + ("…" if len(task["task_name"]) > 28 else "")
                st.markdown(
                    f'<div style="border-left:3px solid {bar_color};padding:6px 10px;'
                    f'margin-bottom:4px;background:#161b22;border-radius:0 6px 6px 0;">'
                    f'<div style="font-size:12px;color:#c9d1d9;font-weight:500;margin-bottom:3px">{name}</div>'
                    f'<div style="display:flex;align-items:center;gap:6px;">'
                    f'<span style="font-size:10px;color:#6e7681">⏱ {dl}</span>'
                    f'<span style="font-size:10px;color:{badge_color};background:{badge_bg};'
                    f'padding:1px 6px;border-radius:10px;font-weight:600">{badge_text}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="font-size:12px;color:#4a6a7a;text-align:center;'
                'padding:10px 0">Không có task nào ✓</div>',
                unsafe_allow_html=True,
            )

        # ── Daily Briefing ────────────────────────────────────────────────────
        _sb_section("Tóm tắt hôm nay")
        today_str = date.today().isoformat()

        # AI mode toggle (full-width row, above button)
        briefing_ai = st.toggle(
            "◈ Dùng AI viết briefing", key="briefing_ai_toggle",
            value=st.session_state.get("briefing_ai_mode", False),
            help="Bật để AI tổng hợp nội dung; tắt để dùng template nhanh"
        )
        st.session_state.briefing_ai_mode = briefing_ai

        if st.button(">>  Briefing", use_container_width=True, key="gen_briefing"):
            from modules.daily_briefing import generate
            with st.spinner("Đang tạo..."):
                text = generate(load_tasks(), use_ai=briefing_ai)
            st.session_state.daily_briefing_text = text
            st.session_state.daily_briefing_date = today_str
            st.rerun()

        if st.session_state.get("daily_briefing_text"):
            briefing_html = (
                st.session_state.daily_briefing_text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            st.markdown(
                f'<div style="background:#0f1923;border:1px solid #1d2733;border-radius:6px;'
                f'padding:10px 12px;font-size:11px;color:#c9d1d9;'
                f'line-height:1.7;margin-top:6px;max-height:200px;overflow-y:auto">'
                f'{briefing_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Email unread + Week calendar ─────────────────────────────────────
        _sb_section("Email & Lịch")

        # Email unread badge
        unread = _get_inbox_unread()
        if unread >= 0:
            u_color = "#ff2d55" if unread > 10 else "#ff9f0a" if unread > 0 else "#30d158"
            u_label = f"{unread} chưa đọc" if unread > 0 else "Inbox sạch"
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'background:#0f1923;border:1px solid #1d2733;border-radius:6px;'
                f'padding:6px 10px;margin-bottom:6px;">'
                f'<span style="font-size:11px;color:#8b949e;font-family:\'JetBrains Mono\',monospace">'
                f'◉  Inbox</span>'
                f'<span style="font-size:11px;font-weight:700;color:{u_color};'
                f'background:{u_color}18;padding:1px 8px;border-radius:10px;'
                f'font-family:\'JetBrains Mono\',monospace">{u_label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Mini week calendar
        from datetime import timedelta
        today_d   = date.today()
        week_start = today_d - timedelta(days=today_d.weekday())   # Monday
        all_tasks  = load_tasks()
        deadline_days = {
            t["deadline"] for t in all_tasks
            if t.get("active") and t.get("deadline")
        }
        DAY_LABELS = ["T2","T3","T4","T5","T6","T7","CN"]
        cells_html = ""
        for i in range(7):
            d     = week_start + timedelta(days=i)
            d_str = d.isoformat()
            is_today   = (d == today_d)
            is_past    = (d < today_d)
            has_task   = (d_str in deadline_days)

            if is_today:
                bg, border_c, num_c, lbl_c = "#00d4ff18", "#00d4ff", "#00d4ff", "#00d4ff"
            elif is_past:
                bg, border_c, num_c, lbl_c = "transparent", "#1d2733", "#2a3a4a", "#2a3a4a"
            else:
                bg, border_c, num_c, lbl_c = "#0f192308", "#1d2733", "#8b949e", "#4a6a7a"

            dot = (f'<div style="width:4px;height:4px;border-radius:50%;'
                   f'background:{"#ff9f0a" if has_task else "transparent"};'
                   f'margin:1px auto 0"></div>') if not is_past else ""

            cells_html += (
                f'<div style="flex:1;text-align:center;background:{bg};'
                f'border:1px solid {border_c};border-radius:5px;padding:4px 2px 2px;">'
                f'<div style="font-size:8px;color:{lbl_c};font-family:\'JetBrains Mono\',monospace;'
                f'letter-spacing:.03em">{DAY_LABELS[i]}</div>'
                f'<div style="font-size:12px;font-weight:700;color:{num_c};'
                f'font-family:\'JetBrains Mono\',monospace;line-height:1.3">{d.day}</div>'
                f'{dot}'
                f'</div>'
            )

        st.markdown(
            f'<div style="display:flex;gap:3px;margin-bottom:4px">{cells_html}</div>'
            f'<div style="font-size:9px;color:#2a3a4a;font-family:\'JetBrains Mono\',monospace;'
            f'text-align:right;margin-bottom:4px">● deadline</div>',
            unsafe_allow_html=True,
        )

        # Today's meetings
        meetings = _get_today_meetings()
        if meetings:
            for m in meetings[:3]:
                st.markdown(
                    f'<div style="display:flex;align-items:flex-start;gap:6px;'
                    f'padding:4px 0;border-bottom:1px solid #1d2733;">'
                    f'<span style="font-size:9px;color:#ff9f0a;font-family:\'JetBrains Mono\','
                    f'monospace;min-width:36px;margin-top:1px">{m["start"]}</span>'
                    f'<span style="font-size:10px;color:#c9d1d9;font-family:\'JetBrains Mono\','
                    f'monospace;line-height:1.4">{m["subject"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── System status ─────────────────────────────────────────────────────
        _sb_section("Trạng thái hệ thống")
        has_claude = bool(os.getenv("ANTHROPIC_API_KEY"))
        has_ollama = bool(os.getenv("OLLAMA_BASE_URL"))
        # AI priority note
        if has_claude:
            ai_priority_label = "⬡  Claude API"
            ai_priority_note  = "[ priority ]"
            ai_priority_color = "#00d4ff"
        elif has_ollama:
            ai_priority_label = "⬡  Ollama"
            ai_priority_note  = "[ fallback ]"
            ai_priority_color = "#ff9f0a"
        else:
            ai_priority_label = "⬡  AI"
            ai_priority_note  = "[ offline ]"
            ai_priority_color = "#3d3d3d"

        st.markdown(
            f'<div style="background:#0f1923;border:1px solid #1d2733;border-radius:5px;'
            f'padding:5px 9px;margin-bottom:6px;display:flex;justify-content:space-between;'
            f'align-items:center;">'
            f'<span style="font-size:11px;color:{ai_priority_color};font-weight:600">'
            f'{ai_priority_label}</span>'
            f'<span style="font-size:10px;color:{ai_priority_color};opacity:.7">'
            f'{ai_priority_note}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        checks = [
            ("⬡  Claude API",  has_claude),
            ("⬡  Ollama",      has_ollama),
            ("◈  Discord",     bool(os.getenv("DISCORD_WEBHOOK_URL"))),
            ("◈  Obsidian",    bool(os.getenv("OBSIDIAN_API_KEY"))),
            ("◈  Jupyter",     st.session_state.jupyter_running),
        ]
        for name, ok in checks:
            status_color = "#30d158" if ok else "#3d3d3d"
            status_text  = "[ ok ]" if ok else "[ -- ]"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:2px 0;font-size:11px;color:#8b949e;'
                f'font-family:\'JetBrains Mono\',monospace;">'
                f'<span>{name}</span>'
                f'<span style="color:{status_color};font-size:10px;font-weight:600">{status_text}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Stat card SVG icons ───────────────────────────────────────────────────────
# Each icon is inline SVG, fill="currentColor" → inherits CSS color
_ICON_OVERDUE = (
    # Hourglass — time's up
    '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="4" y="1" width="12" height="2" rx="1" fill="currentColor"/>'
    '<rect x="4" y="17" width="12" height="2" rx="1" fill="currentColor"/>'
    '<path d="M5.5 3 Q5.5 8.5 10 10 Q5.5 11.5 5.5 17 L14.5 17 Q14.5 11.5 10 10 Q14.5 8.5 14.5 3 Z"'
    ' fill="currentColor" opacity=".85"/>'
    '</svg>'
)
_ICON_ACTIVE = (
    # Task list with staggered progress bars + right arrow
    '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="2" y="3.5" width="3" height="3" rx=".6" fill="currentColor"/>'
    '<rect x="2" y="8.5" width="3" height="3" rx=".6" fill="currentColor" opacity=".65"/>'
    '<rect x="2" y="13.5" width="3" height="3" rx=".6" fill="currentColor" opacity=".35"/>'
    '<rect x="7" y="4.5" width="7" height="1.5" rx=".75" fill="currentColor"/>'
    '<rect x="7" y="9.5" width="5" height="1.5" rx=".75" fill="currentColor" opacity=".65"/>'
    '<rect x="7" y="14.5" width="3.5" height="1.5" rx=".75" fill="currentColor" opacity=".35"/>'
    '<path d="M15.5 8 L19 10 L15.5 12 L15.5 10.7 L13 10.7 L13 9.3 L15.5 9.3 Z" fill="currentColor"/>'
    '</svg>'
)
_ICON_DONE = (
    # Bar chart going up + check arrow on top
    '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="1.5" y="13" width="4" height="6" rx="1" fill="currentColor" opacity=".4"/>'
    '<rect x="7.5" y="9"  width="4" height="10" rx="1" fill="currentColor" opacity=".7"/>'
    '<rect x="13.5" y="4" width="4" height="15" rx="1" fill="currentColor"/>'
    '<polyline points="2,7 5,10.5 10,4" stroke="currentColor" stroke-width="1.8"'
    ' stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
    '</svg>'
)
_ICON_TODAY = (
    # Bullseye / target — today's focus
    '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="10" cy="10" r="9"   stroke="currentColor" stroke-width="1.4" fill="none" opacity=".35"/>'
    '<circle cx="10" cy="10" r="6"   stroke="currentColor" stroke-width="1.4" fill="none" opacity=".6"/>'
    '<circle cx="10" cy="10" r="3"   stroke="currentColor" stroke-width="1.4" fill="none" opacity=".85"/>'
    '<circle cx="10" cy="10" r="1.3" fill="currentColor"/>'
    '</svg>'
)

# ── Stats ─────────────────────────────────────────────────────────────────────
def render_stats(tasks: list[dict]):
    stats = get_stats(tasks)
    _STAT_CARDS = [
        (_ICON_OVERDUE, "QUÁ HẠN",    stats["overdue"],  "#ff2d55", "rgba(255,45,85,.08)",  "rgba(255,45,85,.3)"),
        (_ICON_ACTIVE,  "ĐANG LÀM",   stats["active"],   "#00d4ff", "rgba(0,212,255,.06)",  "rgba(0,212,255,.25)"),
        (_ICON_DONE,    "HOÀN THÀNH", stats["done"],     "#30d158", "rgba(48,209,88,.06)",  "rgba(48,209,88,.25)"),
        (_ICON_TODAY,   "HÔM NAY",    stats["today"],    "#ff9f0a", "rgba(255,159,10,.07)", "rgba(255,159,10,.28)"),
    ]
    cols = st.columns(4)
    for col, (icon_svg, label, val, color, bg, border) in zip(cols, _STAT_CARDS):
        with col:
            # Small icon (label row) — 18px
            icon_sm = f'<span style="color:{color};display:inline-flex;opacity:.9">{icon_svg}</span>'
            # Large ghost icon — resize SVG to 58px directly (avoid scale+clip issue)
            icon_lg_svg = icon_svg.replace('width="18" height="18"', 'width="58" height="58"')
            icon_lg = f'<span style="color:{color};display:inline-flex;opacity:.13">{icon_lg_svg}</span>'
            st.markdown(
                f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
                f'padding:12px 14px 10px;position:relative;overflow:hidden;min-height:76px;">'
                # label row: svg icon + text
                f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:8px">'
                f'{icon_sm}'
                f'<span style="font-size:9px;letter-spacing:.15em;color:{color};opacity:.65;'
                f'font-family:\'JetBrains Mono\',monospace;font-weight:600">{label}</span>'
                f'</div>'
                # value
                f'<span style="font-size:30px;font-weight:700;color:{color};'
                f'font-family:\'JetBrains Mono\',monospace;line-height:1">{val}</span>'
                # ghost watermark — absolute right, vertically centered
                f'<div style="position:absolute;right:-4px;top:50%;transform:translateY(-50%);'
                f'line-height:0;user-select:none;pointer-events:none">{icon_lg}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Action bar ────────────────────────────────────────────────────────────────
def render_action_bar() -> tuple[str, str]:
    query = st.text_input(
        "s", label_visibility="collapsed",
        placeholder="/ tìm kiếm task...",
        key="task_search_input",
    )
    # priority_filter được điều khiển từ sidebar selectbox
    priority_filter = st.session_state.get("sb_priority_filter", "")
    return query, priority_filter


# ── Edit form ─────────────────────────────────────────────────────────────────
def render_edit_form(task: dict):
    tid = task["task_id"]
    with st.container():
        st.markdown("---")
        st.markdown(
            f'<div style="font-size:11px;color:#8b949e;font-family:\'JetBrains Mono\',monospace;'
            f'letter-spacing:.06em;padding:2px 0 4px">✐ EDIT → {task["task_name"]}</div>',
            unsafe_allow_html=True,
        )
        task_name = st.text_input("Tên task", value=task["task_name"], key=f"en_{tid}")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Bắt đầu", value=date.fromisoformat(task["start_date"]), key=f"es_{tid}")
        with col2:
            end_date = st.date_input("Kết thúc", value=date.fromisoformat(task["end_date"]), key=f"ee_{tid}")

        cat_labels = list(CATEGORY_OPTIONS.keys())
        cat_index = cat_labels.index(task["category_label"]) if task["category_label"] in cat_labels else 0
        category_display = st.selectbox("Priority", cat_labels, index=cat_index, key=f"ec_{tid}")
        category = CATEGORY_OPTIONS[category_display]
        note = st.text_area("Ghi chú", value=task.get("note", ""), key=f"en2_{tid}")
        recur_labels = list(RECUR_OPTIONS.keys())
        recur_label_current = RECUR_REVERSE.get(task.get("recur"), "Không lặp")
        recur_index = recur_labels.index(recur_label_current)
        recur_display = st.selectbox("Lặp lại", recur_labels, index=recur_index, key=f"er_{tid}")
        recur = RECUR_OPTIONS[recur_display]

        from modules.analytics import DEFAULT_TAGS
        current_tags = task.get("tags", [])
        tags = st.multiselect("Tags", options=DEFAULT_TAGS, default=current_tags, key=f"etags_{tid}",
                              placeholder="Chọn tag liên quan...")

        col_save, col_cancel = st.columns([1, 4])
        with col_save:
            if st.button("▶ LƯU", key=f"esave_{tid}", use_container_width=True):
                if not task_name.strip():
                    st.error("Tên task không được để trống.")
                    return
                new_deadline = calculate_deadline(end_date.isoformat(), category)
                update_task(tid, {
                    "task_name":      task_name.strip(),
                    "start_date":     start_date.isoformat(),
                    "end_date":       end_date.isoformat(),
                    "category_raw":   category,
                    "category_label": get_label(category),
                    "deadline":       new_deadline,
                    "note":           note.strip() or "(none)",
                    "recur":          recur,
                    "tags":           tags,
                })
                load_tasks.clear()
                st.session_state.editing_task_id = None
                st.rerun()
        with col_cancel:
            if st.button("✕ HỦY", key=f"ecancel_{tid}"):
                st.session_state.editing_task_id = None
                st.rerun()
        st.markdown("---")


# ── Task card ─────────────────────────────────────────────────────────────────
def render_task_card(task: dict):
    raw   = task.get("category_raw", "low")
    color = PRIORITY_COLORS.get(raw, "#888")
    today = date.today().isoformat()
    is_overdue = task.get("active") and task.get("deadline", "") < today
    overdue_html = (
        ' <span class="anim-blink" style="color:#ff2d55;font-size:9px;'
        'font-family:\'JetBrains Mono\',monospace;letter-spacing:.1em"> ⚠ OVERDUE</span>'
        if is_overdue else ""
    )
    tags = task.get("tags", [])
    tags_html = "".join(
        f'<span style="background:#1d2733;color:#79c0ff;font-size:9px;padding:1px 5px;'
        f'border-radius:2px;margin-left:4px;font-family:\'JetBrains Mono\',monospace">{tag}</span>'
        for tag in tags
    )
    st.markdown(
        f'<div style="border-left:3px solid {color};'
        f'background:linear-gradient(90deg,{color}0d,#090e14 55%);'
        f'padding:7px 12px;border-radius:3px;margin-bottom:2px;">'
        f'<span style="color:#e6edf3;font-size:13px;font-weight:500">{task["task_name"]}</span>'
        f'{overdue_html}{tags_html}<br>'
        f'<span style="color:#6e7681;font-size:10px;font-family:\'JetBrains Mono\',monospace">'
        f'⏱ {task["deadline"]} &nbsp;·&nbsp; {task["category_label"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    tid = task["task_id"]
    c1, c2, c3, _ = st.columns([1, 1, 1, 7])
    with c1:
        if st.button("✓", key=f"done_{tid}", help="Hoàn thành"):
            update_task(tid, {"active": False, "completed_at": today})
            load_tasks.clear()
            st.rerun()
    with c2:
        if st.button("✐", key=f"edit_{tid}", help="Sửa"):
            st.session_state.editing_task_id = tid
            st.session_state.show_add_form = False
            st.rerun()
    with c3:
        if st.button("⌫", key=f"del_{tid}", help="Xóa"):
            delete_task(tid)
            load_tasks.clear()
            st.rerun()


# ── Priority group ────────────────────────────────────────────────────────────
def render_priority_group(label: str, tasks: list[dict], expanded: bool, raw_key: str):
    if not tasks:
        return
    priority_group_header(label, len(tasks), raw_key)
    toggle_key = f"grp_{raw_key}"
    if toggle_key not in st.session_state:
        st.session_state[toggle_key] = expanded
    col_tasks, col_btn = st.columns([12, 1])
    with col_btn:
        arrow = "▲" if st.session_state[toggle_key] else "▼"
        if st.button(arrow, key=f"tog_{raw_key}"):
            st.session_state[toggle_key] = not st.session_state[toggle_key]
            st.rerun()
    if st.session_state[toggle_key]:
        for task in sorted(tasks, key=lambda t: t.get("deadline", "")):
            render_task_card(task)
            if st.session_state.editing_task_id == task["task_id"]:
                render_edit_form(task)


# ── Add form ──────────────────────────────────────────────────────────────────
def render_add_form():
    from modules.analytics import DEFAULT_TAGS
    # Pre-fill from email→task if available
    prefill = st.session_state.email_to_task_prefill or {}
    with st.expander("+ THÊM TASK MỚI", expanded=True):
        task_name = st.text_input("Tên task *", key="add_name",
                                  value=prefill.get("task_name", ""))
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Bắt đầu *", value=date.today(), key="add_start")
        with col2:
            end_date = st.date_input("Kết thúc *", value=date.today(), key="add_end")

        col_cat, col_dl_btn = st.columns([3, 1])
        with col_cat:
            cat_labels = list(CATEGORY_OPTIONS.keys())
            category_display = st.selectbox("Priority *", cat_labels, key="add_cat")
            category = CATEGORY_OPTIONS[category_display]
        with col_dl_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬡ Gợi deadline", key="suggest_deadline", use_container_width=True,
                         help="AI đề xuất deadline phù hợp"):
                _suggest_deadline(task_name, category, end_date)

        if st.session_state.smart_deadline_hint:
            st.markdown(
                f'<div style="background:#0f1923;border:1px solid #30d15844;border-radius:3px;'
                f'padding:5px 10px;font-size:11px;color:#30d158;'
                f'font-family:\'JetBrains Mono\',monospace;margin-bottom:4px">'
                f'⬡ {st.session_state.smart_deadline_hint}</div>',
                unsafe_allow_html=True,
            )

        note = st.text_area("Ghi chú", key="add_note",
                            value=prefill.get("note", ""),
                            placeholder="Không bắt buộc")
        tags = st.multiselect("Tags", options=DEFAULT_TAGS, key="add_tags",
                              placeholder="Chọn tag liên quan...")

        recur_labels = list(RECUR_OPTIONS.keys())
        recur_display = st.selectbox("Lặp lại", recur_labels, key="add_recur")
        recur = RECUR_OPTIONS[recur_display]

        col_submit, col_cancel = st.columns([1, 4])
        with col_submit:
            submitted = st.button("▶ LƯU TASK", key="add_submit", use_container_width=True)
        with col_cancel:
            if st.button("✕ HỦY", key="add_cancel"):
                st.session_state.show_add_form = False
                st.session_state.email_to_task_prefill = None
                st.session_state.smart_deadline_hint = None
                st.rerun()

        if submitted:
            if not task_name.strip():
                st.error("Tên task không được để trống.")
                return
            if end_date < start_date:
                st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                return
            deadline = calculate_deadline(end_date.isoformat(), category)
            task = {
                "task_name":      task_name.strip(),
                "start_date":     start_date.isoformat(),
                "end_date":       end_date.isoformat(),
                "category_raw":   category,
                "category_label": get_label(category),
                "deadline":       deadline,
                "note":           note.strip() or "(none)",
                "recur":          recur,
                "checklist":      "",
                "tags":           tags,
            }
            saved = add_task(task)
            load_tasks.clear()
            send_confirm(saved)
            st.session_state.show_add_form = False
            st.session_state.email_to_task_prefill = None
            st.session_state.smart_deadline_hint = None
            st.success(f"◈ Task created: {saved['task_name']}")
            st.rerun()


def _suggest_deadline(task_name: str, category: str, end_date):
    """Gọi AI để gợi ý deadline, lưu vào session_state."""
    from modules.ai_client import call_ai
    from modules.task_manager import get_active_tasks
    active_count = len(get_active_tasks())
    prompt = (
        f"Tôi cần gợi ý deadline cho task sau. Trả lời bằng 1 câu ngắn tiếng Việt, "
        f"nêu rõ ngày cụ thể hoặc khoảng thời gian hợp lý.\n\n"
        f"Task: {task_name or '(chưa có tên)'}\n"
        f"Priority: {category}\n"
        f"Ngày kết thúc dự kiến: {end_date}\n"
        f"Số task đang làm: {active_count}\n"
        f"Gợi ý deadline phù hợp (không quá ngắn, không quá dài):"
    )
    try:
        hint = call_ai(prompt, max_tokens=80)
        st.session_state.smart_deadline_hint = hint
    except Exception:
        st.session_state.smart_deadline_hint = "Không kết nối được AI."


# ── AI Checklist ──────────────────────────────────────────────────────────────
def render_ai_checklist_section():
    st.markdown("---")
    section_header("⟁", "AI CHECKLIST", color="#bd00ff", anim="pulse",
                   subtitle="chọn task · AI sinh checklist bước thực hiện")
    active_tasks = get_active_tasks()
    if not active_tasks:
        st.info("Không có task đang hoạt động.")
        return
    task_options = {t["task_name"]: t for t in active_tasks}
    selected_name = st.selectbox(
        "task", options=list(task_options.keys()),
        key="checklist_task_select", label_visibility="collapsed",
    )
    selected_task = task_options[selected_name]
    col_gen, col_save, col_pad = st.columns([1, 1, 2])
    with col_gen:
        if st.button("◈ CHECKLIST", key="gen_checklist", use_container_width=True):
            with st.spinner("AI đang phân tích..."):
                try:
                    result = generate_checklist(
                        selected_task["task_name"],
                        selected_task["category_label"],
                        selected_task["deadline"],
                        selected_task.get("note", "(none)"),
                        "",
                    )
                    st.session_state.checklist_result = result
                    st.session_state.selected_task_id = selected_task["task_id"]
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    if st.session_state.checklist_result:
        st.markdown(
            '<div style="border-left:2px solid #bd00ff;padding:6px 12px;'
            'background:rgba(189,0,255,.05);border-radius:3px;margin:4px 0;">',
            unsafe_allow_html=True,
        )
        for line in st.session_state.checklist_result.splitlines():
            if line.strip():
                st.markdown(f'<div style="font-size:12px;color:#c9d1d9;padding:1px 0">{line}</div>',
                            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        with col_save:
            if st.button("▶ LƯU", key="save_checklist", use_container_width=True):
                update_task(
                    st.session_state.selected_task_id,
                    {"checklist": st.session_state.checklist_result},
                )
                load_tasks.clear()
                st.session_state.checklist_result = None
                st.success("◈ Đã lưu checklist!")
                st.rerun()


# ── Tasks tab ─────────────────────────────────────────────────────────────────
@st.fragment
def render_tasks_tab():
    from modules.analytics import DEFAULT_TAGS
    all_tasks = load_tasks()
    render_stats(all_tasks)
    # query đọc từ global search bar (đặt cùng row với tabs trong main())
    query          = st.session_state.get("global_search", "")
    priority_filter = st.session_state.get("sb_priority_filter", "")

    # ── Tag filter pills ──────────────────────────────────────────────────────
    used_tags = sorted({tag for t in all_tasks for tag in t.get("tags", [])})
    if used_tags:
        pills_html = ""
        for tag in used_tags:
            active = st.session_state.active_tag_filter == tag
            bg = "#79c0ff22" if active else "#1d2733"
            border = "#79c0ff" if active else "#2d3748"
            color  = "#79c0ff" if active else "#8b949e"
            pills_html += (
                f'<span style="background:{bg};color:{color};border:1px solid {border};'
                f'font-size:9px;padding:2px 8px;border-radius:10px;margin-right:4px;'
                f'font-family:\'JetBrains Mono\',monospace;cursor:pointer">{tag}</span>'
            )
        st.markdown(pills_html, unsafe_allow_html=True)
        tag_opts = ["── tất cả ──"] + used_tags
        chosen = st.selectbox("Lọc tag", tag_opts, key="tag_filter_sel",
                              label_visibility="collapsed")
        st.session_state.active_tag_filter = None if chosen == "── tất cả ──" else chosen

    if st.session_state.show_add_form or st.session_state.email_to_task_prefill:
        render_add_form()

    active_tasks = [t for t in all_tasks if t.get("active")]

    # Apply tag filter
    tag_f = st.session_state.active_tag_filter
    if tag_f:
        active_tasks = [t for t in active_tasks if tag_f in t.get("tags", [])]

    filtered = filter_tasks(active_tasks, query, priority_filter)
    groups = group_by_priority(filtered)
    for raw_key, label, expanded in PRIORITY_GROUP_CONFIG:
        render_priority_group(label, groups[raw_key], expanded, raw_key)
    render_ai_checklist_section()


# ── Data Studio tab ───────────────────────────────────────────────────────────
@st.fragment
def render_data_studio_tab():
    """Data Studio with sub-navigation for ML STUDIO, DATA EXPLORER, SQL SNIPPETS."""
    ds_view = st.radio(
        "",
        [
            "⚗ ML STUDIO",
            "◈ DATA EXPLORER",
            "⌥ SQL SNIPPETS",
        ],
        horizontal=True,
        key="ds_view",
        label_visibility="collapsed",
    )

    st.divider()

    if ds_view == "⚗ ML STUDIO":
        from modules.ml_studio import render_ml_studio
        render_ml_studio()
    elif ds_view == "◈ DATA EXPLORER":
        render_data_explorer_tab()
    elif ds_view == "⌥ SQL SNIPPETS":
        from modules.sql_snippets import render_sql_snippets
        render_sql_snippets()


# ── Email history (fallback when queue empty) ─────────────────────────────────
def _render_email_history(vip_only: bool = False):
    """Hiển thị email đã xử lý từ email_history.json khi queue rỗng."""
    import json
    from pathlib import Path
    from modules.email_classifier import VIP_SENDERS

    hist_path = Path("data/email_history.json")
    if not hist_path.exists():
        return
    try:
        history = json.loads(hist_path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not history:
        return

    # Sort newest first
    history = sorted(history, key=lambda e: e.get("processed_at", ""), reverse=True)
    if vip_only:
        history = [e for e in history if e.get("sender_email", "").lower() in VIP_SENDERS]
    if not history:
        return

    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#4a6a7a;letter-spacing:.12em;'
        'font-family:\'JetBrains Mono\',monospace;padding:4px 0 6px">'
        '── LỊCH SỬ ĐÃ XỬ LÝ ──</div>',
        unsafe_allow_html=True,
    )

    PCOL = {"urgent": "#ff2d55", "normal": "#ff9f0a", "fyi": "#30d158"}
    PICO = {"urgent": "[!]", "normal": "[~]", "fyi": "[i]"}

    for e in history[:30]:
        p     = e.get("priority", "fyi")
        color = PCOL.get(p, "#8b949e")
        ico   = PICO.get(p, "[ ]")
        ts    = e.get("processed_at", "")[:16].replace("T", "  ")
        is_vip = e.get("sender_email", "").lower() in VIP_SENDERS
        vip_badge = (
            '<span style="background:#ff9f0a22;color:#ff9f0a;font-size:9px;'
            'padding:1px 5px;border-radius:2px;margin-left:5px">VIP</span>'
            if is_vip else ""
        )
        st.markdown(
            f'<div style="background:#0d1117;border:1px solid {"#ff9f0a44" if is_vip else "#1a2030"};'
            f'border-left:3px solid {color};border-radius:0 4px 4px 0;'
            f'padding:6px 10px;margin-bottom:3px;display:flex;justify-content:space-between;align-items:center">'
            f'<div>'
            f'<span style="color:{color};font-size:10px;font-family:\'JetBrains Mono\',monospace">'
            f'{ico}</span> '
            f'<span style="color:#e6edf3;font-size:12px;font-weight:500">'
            f'{e.get("sender_name","?")}</span>{vip_badge}'
            f'<span style="color:#6e7681;font-size:11px"> — {e.get("subject","?")[:70]}</span>'
            f'</div>'
            f'<span style="color:#4a6a7a;font-size:9px;font-family:\'JetBrains Mono\',monospace'
            f';white-space:nowrap">{ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Email tab ─────────────────────────────────────────────────────────────────
@st.fragment
def render_email_tab():
    section_header("◉", "EMAIL DIGEST", color="#30d158", anim="scan",
                   subtitle="đọc outlook · phân loại · tóm tắt bằng AI")

    # Diagnostic banner
    try:
        from modules.outlook_reader import get_queue_status
        qs = get_queue_status()
        src_color = {"queue": "#30d158", "win32com": "#00d4ff", "none": "#ff2d55"}.get(qs["source"], "#8b949e")
        src_label = {"queue": "Power Automate queue", "win32com": "Outlook win32com", "none": "Không tìm thấy nguồn email"}.get(qs["source"], "?")
        st.markdown(
            f'<div style="background:#090e14;border:1px solid #1d2733;border-radius:3px;'
            f'padding:6px 10px;margin-bottom:8px;display:flex;gap:14px;flex-wrap:wrap;'
            f'font-family:\'JetBrains Mono\',monospace;font-size:10px;">'
            f'<span style="color:#6e7681">Nguồn:</span>'
            f'<span style="color:{src_color}">{src_label}</span>'
            f'<span style="color:#3d5a6b">|</span>'
            f'<span style="color:#6e7681">Queue path:</span>'
            f'<span style="color:#8b949e">{qs["queue_path"]}</span>'
            f'<span style="color:#3d5a6b">|</span>'
            f'<span style="color:#6e7681">Files:</span>'
            f'<span style="color:#e6edf3">{qs["queue_files"]}</span>'
            f'<span style="color:#3d5a6b">|</span>'
            f'<span style="color:#6e7681">win32com:</span>'
            f'<span style="color:{"#30d158" if qs["win32_available"] else "#ff2d55"}">'
            f'{"OK" if qs["win32_available"] else "not installed"}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if not qs["queue_exists"] and not qs["win32_available"]:
            st.warning(
                f"⚠ EmailQueue không tồn tại: `{qs['queue_path']}` và win32com không khả dụng.  \n"
                "Cài pywin32 (`pip install pywin32`) hoặc cấu hình Power Automate."
            )
        elif qs["source"] == "win32com":
            st.info(
                "◈ Đang đọc trực tiếp từ **Outlook** qua win32com "
                f"(EmailQueue trống — {qs['queue_files']} files)."
            )
    except Exception:
        pass

    # Row 1: controls
    col_h, col_vip, _ = st.columns([1, 1.5, 2])
    with col_h:
        hours = st.number_input("Giờ gần nhất", min_value=1, max_value=168, value=24, key="digest_hours")
    with col_vip:
        vip_only = st.toggle("VIP only", value=False, key="digest_vip",
                             help="Chỉ hiện email từ VIP senders (colleague1, colleague2...)")

    # Row 2: action buttons — 50% each
    col_btn, col_clear = st.columns(2)
    with col_btn:
        if st.button("▶ TẠO DIGEST", key="run_digest", use_container_width=True):
            try:
                from modules.email_digest import run_digest
                with st.spinner("Đang đọc và phân loại email..."):
                    st.session_state.digest_results = run_digest(hours=int(hours))
                    st.session_state.digest_error = None
            except Exception as e:
                import traceback
                st.session_state.digest_error = f"{type(e).__name__}: {e}\n\n```\n{traceback.format_exc()}\n```"
    with col_clear:
        if st.button("↺ CLEAR HISTORY", key="clear_history", use_container_width=True,
                     help="Xóa lịch sử đã xử lý để đọc lại email cũ"):
            from pathlib import Path
            h = Path("data/email_history.json")
            if h.exists():
                h.write_text("[]", encoding="utf-8")
            st.session_state.digest_results = None
            st.success("Đã xóa history!")
            st.rerun()

    # Hiển thị lỗi digest ngay dưới nút (persistent)
    if st.session_state.get("digest_error"):
        st.error(st.session_state.digest_error)

    if st.session_state.digest_results is not None:
        from modules.email_classifier import VIP_SENDERS
        results = st.session_state.digest_results

        # Apply VIP filter if toggled
        if vip_only:
            filtered = {
                lvl: [e for e in emails if e.get("sender_email", "").lower() in VIP_SENDERS]
                for lvl, emails in results.items()
            }
        else:
            filtered = results

        total = sum(len(v) for v in filtered.values())
        if total == 0:
            st.info("◇ Không có email mới trong queue hôm nay." if not vip_only
                    else "◇ Không có email nào từ VIP senders.")
            # Show history as fallback
            _render_email_history(vip_only)
        else:
            st.success(f"◈ {total} email{'  |  VIP filter ON' if vip_only else ''}")
            if st.button("◈ DIGEST → DISCORD", key="send_digest"):
                send_email_digest(filtered)
                st.success("Đã gửi!")
            PRIORITY_LABELS = {"urgent": "⬥ URGENT", "normal": "◆ NORMAL", "fyi": "◇ FYI"}
            PRIORITY_COLORS_EMAIL = {"urgent": "#ff2d55", "normal": "#ff9f0a", "fyi": "#30d158"}
            for level in ("urgent", "normal", "fyi"):
                emails = filtered.get(level, [])
                if not emails:
                    continue
                color = PRIORITY_COLORS_EMAIL[level]
                st.markdown(
                    f'<div style="background:linear-gradient(90deg,{color}1a,transparent 75%);'
                    f'border-left:3px solid {color};padding:5px 10px;border-radius:3px;'
                    f'margin:6px 0 2px;font-weight:700;font-size:11px;letter-spacing:.12em;'
                    f'color:{color};font-family:\'JetBrains Mono\',monospace;">'
                    f'{PRIORITY_LABELS[level]} <span style="opacity:.4">({len(emails)})</span></div>',
                    unsafe_allow_html=True,
                )
                for email in emails:
                    # VIP badge
                    is_vip = email.get("sender_email", "").lower() in VIP_SENDERS
                    vip_badge = ('<span style="background:#ff9f0a22;color:#ff9f0a;font-size:9px;'
                                 'padding:1px 5px;border-radius:2px;margin-left:5px">VIP</span>'
                                 if is_vip else "")
                    st.markdown(
                        f'<div style="background:#090e14;border:1px solid {"#ff9f0a55" if is_vip else "#1d2733"};'
                        f'border-radius:3px;padding:7px 10px;margin-bottom:2px;">'
                        f'<span style="color:#e6edf3;font-size:12px;font-weight:600">'
                        f'{email.get("sender_name","?")}</span>{vip_badge}'
                        f'<span style="color:#6e7681;font-size:11px"> — {email.get("subject","?")}</span><br>'
                        f'<span style="color:#8b949e;font-size:10px">{email.get("summary","")}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    col_reply, col_task = st.columns([6, 1])
                    with col_reply:
                        replies = email.get("replies", [])
                        if replies:
                            st.markdown(
                                '<span style="color:#6e7681;font-size:10px">◈ reply: </span>'
                                + " · ".join(f'<code style="font-size:10px">{r}</code>' for r in replies[:3]),
                                unsafe_allow_html=True,
                            )
                    with col_task:
                        if st.button("➕ Task", key=f"email_task_{email.get('entry_id','')}",
                                     help="Tạo task từ email này"):
                            subj = email.get("subject", "")
                            st.session_state.email_to_task_prefill = {
                                "task_name": subj[:80],
                                "note": f"From: {email.get('sender_name','')} — {subj}",
                            }
                            st.session_state.show_add_form = True
                            st.rerun()

    # ── Email Templates section ───────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⌥ EMAIL TEMPLATES", expanded=False):
        from modules.email_templates import load_templates, add_template, delete_template, CATEGORIES

        templates = load_templates()
        cat_filter = st.selectbox("Lọc category", ["All"] + CATEGORIES, key="tmpl_cat_filter")
        shown = templates if cat_filter == "All" else [t for t in templates if t["category"] == cat_filter]

        for tmpl in shown:
            col_t, col_del = st.columns([5, 1])
            with col_t:
                with st.expander(f"**{tmpl['name']}**  `{tmpl['category']}`"):
                    st.markdown(
                        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                        f'color:#79c0ff;margin-bottom:3px">Subject: {tmpl["subject"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.text_area("Body", value=tmpl["body"], height=110,
                                 key=f"tmpl_body_{tmpl['id']}", disabled=True)
            with col_del:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✕", key=f"del_tmpl_{tmpl['id']}", help="Xóa template"):
                    delete_template(tmpl["id"])
                    st.rerun()

        st.markdown("**➕ Tạo template mới**")
        cn, cc = st.columns([3, 1])
        new_name = cn.text_input("Tên template", key="new_tmpl_name", placeholder="VD: Gửi báo cáo tuần")
        new_cat  = cc.selectbox("Category", CATEGORIES, key="new_tmpl_cat")
        new_subj = st.text_input("Subject", key="new_tmpl_subj", placeholder="Re: {subject}")
        new_body = st.text_area("Body", key="new_tmpl_body", height=90,
                                placeholder="Chào {sender_name},\n\n...")
        if st.button("➕ LƯU TEMPLATE", key="save_tmpl"):
            if new_name and new_body:
                add_template(new_name, new_subj, new_body, new_cat)
                st.success("Đã lưu!")
                st.rerun()
            else:
                st.warning("Nhập tên và body.")


# ── Jupyter launch helper ─────────────────────────────────────────────────────
def _launch_jupyter():
    from modules.jupyter_manager import start
    with st.spinner("Đang khởi động JupyterLab..."):
        ok, url = start()
    if ok:
        st.session_state.jupyter_running = True
        st.session_state.jupyter_url = url
    else:
        st.error(url)


# ── Notebook tab ──────────────────────────────────────────────────────────────
@st.fragment
def render_notebook_tab():
    section_header("⬡", "PYTHON NOTEBOOK", color="#f7cc00", anim="float",
                   subtitle="jupyterlab · meeting notes · project log · DA / DS / DE stack")
    nb_view = st.radio("", ["▶ JupyterLab", "📋 Meeting Notes", "📂 Project Log"],
                       horizontal=True, key="nb_view", label_visibility="collapsed")

    # ── Active project banner ──────────────────────────────────────────────────
    from modules.project_log import load_projects
    _active_projects = [p for p in load_projects() if p["status"] == "active"]
    if _active_projects:
        # Show the most recently updated (last entry date, fall back to start_date)
        _ap = sorted(
            _active_projects,
            key=lambda p: max(
                (e["date"] for e in p["entries"]), default=p["start_date"]
            ),
        )[-1]
        _pct       = min(max(_ap["progress"], 0), 100)
        _bar       = "█" * (_pct // 10) + "░" * (10 - _pct // 10)
        _n_entries = len(_ap["entries"])
        _n_files   = sum(len(e.get("files", [])) for e in _ap["entries"])
        _last_date = max(
            (e["date"] for e in _ap["entries"]), default=_ap["start_date"]
        )
        st.markdown(
            f'<div style="background:#0d1f12;border:1px solid #30d158;border-radius:6px;'
            f'padding:10px 16px;margin-bottom:10px;display:flex;align-items:center;gap:16px;">'
            f'<span style="color:#f7cc00;font-size:11px;font-family:\'JetBrains Mono\',monospace;">'
            f'🟡 ĐANG ACTIVE</span>'
            f'<span style="color:#e6edf3;font-size:12px;font-weight:600;">{_ap["title"]}</span>'
            f'<span style="color:#30d158;font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
            f'{_bar} {_pct}%</span>'
            f'<span style="color:#3d5a6b;font-size:11px;">'
            f'Cập nhật: {_last_date} · {_n_entries} entries · {_n_files} files</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("→ Mở Project Log", key="banner_open_pl"):
            st.session_state["nb_view"] = "📂 Project Log"
            st.rerun()

    # ── JupyterLab ────────────────────────────────────────────────────────────
    if nb_view == "▶ JupyterLab":
        DS_LIBS = [
            ("pandas",        "3.x",   "DataFrames, groupby, merge"),
            ("polars",        "latest","Fast DataFrame (Rust engine)"),
            ("numpy",         "2.x",   "Array, linalg, fft"),
            ("scipy",         "latest","Stats, optimize, signal"),
            ("statsmodels",   "latest","SARIMAX, OLS, ARIMA, VAR"),
            ("scikit-learn",  "latest","ML: classification, regression, clustering"),
            ("xgboost",       "latest","Gradient Boosting"),
            ("lightgbm",      "latest","Fast GBDT"),
            ("pmdarima",      "latest","Auto-ARIMA"),
            ("matplotlib",    "latest","Plotting"),
            ("seaborn",       "latest","Statistical viz"),
            ("plotly",        "latest","Interactive charts"),
            ("pyarrow",       "latest","Parquet, Arrow columnar"),
            ("dask",          "latest","Parallel / out-of-core compute"),
            ("sqlalchemy",    "latest","ORM + raw SQL"),
            ("openpyxl",      "latest","Excel read/write"),
            ("tqdm",          "latest","Progress bars"),
        ]

        col_launch, col_open, col_stop = st.columns([2, 1.5, 0.5])
        with col_launch:
            if not st.session_state.jupyter_running:
                if st.button("▶ JUPYTER", key="nb_start", use_container_width=True):
                    _launch_jupyter()
                    st.rerun()
            else:
                st.markdown(
                    '<div style="color:#30d158;font-size:11px;font-family:\'JetBrains Mono\',monospace;'
                    'padding:6px 0">● JupyterLab đang chạy</div>',
                    unsafe_allow_html=True,
                )

        if st.session_state.jupyter_running and st.session_state.jupyter_url:
            url = st.session_state.jupyter_url
            with col_open:
                st.markdown(
                    f'<a href="{url}" target="_blank" style="text-decoration:none;">'
                    f'<div style="background:#0f1923;border:1px solid #f7cc00;color:#f7cc00;'
                    f'border-radius:3px;padding:4px 10px;font-size:11px;text-align:center;'
                    f'font-family:\'JetBrains Mono\',monospace;letter-spacing:.06em;cursor:pointer;">'
                    f'⬡ MỞ TRONG TAB MỚI</div></a>',
                    unsafe_allow_html=True,
                )
            with col_stop:
                if st.button("■ STOP", key="nb_stop", use_container_width=True):
                    from modules.jupyter_manager import stop
                    stop()
                    st.session_state.jupyter_running = False
                    st.session_state.jupyter_url = None
                    st.rerun()

            st.markdown("---")
            components.html(
                f'<iframe src="{url}" width="100%" height="680" '
                f'style="border:1px solid #1d2733;border-radius:4px;background:#0d1117;" '
                f'allow="clipboard-read; clipboard-write"></iframe>',
                height=690,
            )

        else:
            st.markdown("---")
            st.markdown(
                '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.15em;'
                'font-family:\'JetBrains Mono\',monospace;padding:3px 0 6px">'
                '── PRE-INSTALLED LIBRARIES ──</div>',
                unsafe_allow_html=True,
            )
            rows = "".join(
                f'<tr>'
                f'<td style="color:#79c0ff;padding:3px 12px 3px 0;font-weight:600">{lib}</td>'
                f'<td style="color:#6e7681;padding:3px 12px 3px 0">{ver}</td>'
                f'<td style="color:#8b949e;padding:3px 0">{desc}</td>'
                f'</tr>'
                for lib, ver, desc in DS_LIBS
            )
            st.markdown(
                f'<table style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                f'border-collapse:collapse;width:100%">{rows}</table>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="margin-top:16px;padding:10px 14px;background:#090e14;'
                'border:1px solid #1d2733;border-radius:4px;'
                'font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#8b949e">'
                '<div style="color:#f7cc00;margin-bottom:6px;letter-spacing:.06em">⬡ QUICK START</div>'
                '<div style="color:#79c0ff">import pandas as pd</div>'
                '<div style="color:#79c0ff">import polars as pl</div>'
                '<div style="color:#79c0ff">import numpy as np</div>'
                '<div style="color:#79c0ff">from statsmodels.tsa.statespace.sarimax import SARIMAX</div>'
                '<div style="color:#79c0ff">from sklearn.model_selection import train_test_split</div>'
                '<div style="color:#6e7681;margin-top:6px"># notebooks lưu tại D:\\ai_notebooks\\</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Meeting Notes ─────────────────────────────────────────────────────────
    if nb_view == "📋 Meeting Notes":
        from modules.meeting_notes import load_notes, add_note, delete_note, export_markdown

        notes = load_notes()

        # ── New meeting form ──
        with st.expander("➕ GHI CHÉP CUỘC HỌP MỚI", expanded=not notes):
            mn_title     = st.text_input("Tiêu đề cuộc họp", key="mn_title",
                                         placeholder="VD: Weekly sync CRM team")
            mn_col_d, mn_col_a = st.columns([1, 2])
            mn_date      = mn_col_d.date_input("Ngày", key="mn_date")
            mn_attendees = mn_col_a.text_input("Thành viên (phân cách bằng dấu phẩy)", key="mn_att",
                                               placeholder="Hiếu, Oanh, Thiện...")
            mn_agenda    = st.text_area("Agenda / nội dung họp", key="mn_agenda", height=70)
            mn_decisions = st.text_area("Quyết định / kết luận", key="mn_decisions", height=60)

            st.markdown(
                '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.1em;'
                'font-family:\'JetBrains Mono\',monospace;padding:4px 0">── ACTION ITEMS ──</div>',
                unsafe_allow_html=True,
            )
            if "mn_actions" not in st.session_state:
                st.session_state.mn_actions = [{"task": "", "owner": "", "due": ""}]

            updated_actions = []
            for i, act in enumerate(st.session_state.mn_actions):
                ac1, ac2, ac3, ac_del = st.columns([3, 1.5, 1.2, 0.4])
                task  = ac1.text_input("Task", value=act["task"],  key=f"mn_act_task_{i}",
                                       placeholder="Việc cần làm")
                owner = ac2.text_input("Owner", value=act["owner"], key=f"mn_act_own_{i}",
                                       placeholder="Người chịu trách nhiệm")
                due   = ac3.text_input("Due", value=act["due"],   key=f"mn_act_due_{i}",
                                       placeholder="YYYY-MM-DD")
                with ac_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✕", key=f"mn_del_act_{i}"):
                        continue
                updated_actions.append({"task": task, "owner": owner, "due": due})

            st.session_state.mn_actions = updated_actions
            if st.button("＋ Thêm action item", key="mn_add_action"):
                st.session_state.mn_actions.append({"task": "", "owner": "", "due": ""})
                st.rerun()

            if st.button("💾 LƯU CUỘC HỌP", key="mn_save", use_container_width=True):
                if mn_title:
                    valid_actions = [a for a in st.session_state.mn_actions if a["task"].strip()]
                    add_note(
                        title=mn_title,
                        date=str(mn_date),
                        attendees=mn_attendees,
                        agenda=mn_agenda,
                        decisions=mn_decisions,
                        action_items=valid_actions,
                    )
                    st.session_state.mn_actions = [{"task": "", "owner": "", "due": ""}]
                    st.success("Đã lưu!")
                    st.rerun()
                else:
                    st.warning("Nhập tiêu đề cuộc họp.")

        # ── List existing notes ──
        if notes:
            st.markdown(
                f'<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
                f'font-family:\'JetBrains Mono\',monospace;padding:6px 0 3px">'
                f'── {len(notes)} CUỘC HỌP ──</div>',
                unsafe_allow_html=True,
            )
            for note in notes:
                actions = note.get("action_items", [])
                done_count = 0
                col_note, col_exp, col_del = st.columns([4, 1, 0.5])
                with col_note:
                    st.markdown(
                        f'<div style="background:#090e14;border:1px solid #1d2733;'
                        f'border-radius:3px;padding:7px 10px;margin-bottom:2px;">'
                        f'<div style="color:#f7cc00;font-size:12px;font-weight:600">'
                        f'{note["title"]}</div>'
                        f'<div style="color:#6e7681;font-size:10px;font-family:\'JetBrains Mono\',monospace">'
                        f'{note["date"]}  |  {note.get("attendees","")[:40]}</div>'
                        f'<div style="color:#8b949e;font-size:10px;margin-top:3px">'
                        f'✅ {len(actions)} action items</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_exp:
                    if st.button("📄 MD", key=f"mn_export_{note['id']}",
                                 help="Copy markdown"):
                        md = export_markdown(note)
                        st.code(md, language="markdown")
                with col_del:
                    if st.button("✕", key=f"mn_del_{note['id']}"):
                        delete_note(note["id"])
                        st.rerun()
        else:
            st.markdown(
                '<div style="color:#6e7681;font-size:11px;font-family:\'JetBrains Mono\',monospace;'
                'padding:10px 0">◇ Chưa có cuộc họp nào được ghi chép.</div>',
                unsafe_allow_html=True,
            )

    # ── Project Log ───────────────────────────────────────────────────────────
    if nb_view == "📂 Project Log":
        from modules.project_log import (
            load_projects, add_project, update_project, delete_project,
            add_entry, update_progress, save_attachment,
            generate_sop_and_template, save_outputs, clone_for_next_cycle,
        )

        pl_projects = load_projects()
        n_active = sum(1 for p in pl_projects if p["status"] == "active")
        n_done   = sum(1 for p in pl_projects if p["status"] == "done")

        st.markdown(
            f'<div style="color:#3d5a6b;font-size:10px;font-family:\'JetBrains Mono\','
            f'monospace;letter-spacing:.08em;padding:2px 0 8px 0">'
            f'Đang active: {n_active}  |  Done: {n_done}</div>',
            unsafe_allow_html=True,
        )

        # ── Create new project form ────────────────────────────────────────────
        with st.expander("➕ TẠO PROJECT MỚI", expanded=not pl_projects):
            pl_title = st.text_input("Tên project *", key="pl_title",
                                     placeholder="VD: Campaign Tết 2026")
            pl_type  = st.radio("Loại", ["one-time", "recurring"],
                                horizontal=True, key="pl_type",
                                format_func=lambda x: "📌 One-time" if x == "one-time" else "🔄 Recurring")

            if st.session_state.get("pl_type") == "recurring":
                pl_recur = st.selectbox("Chu kỳ", ["weekly", "monthly", "quarterly"], key="pl_recur")
            else:
                pl_recur = None

            pl_goal  = st.text_area("Mục tiêu", key="pl_goal", height=60,
                                    placeholder="VD: Tăng GMV ColosBaby 20% trong T01")
            pl_col_s, pl_col_e = st.columns(2)
            pl_start = pl_col_s.date_input("Ngày bắt đầu", key="pl_start")
            if st.session_state.get("pl_type") == "one-time":
                pl_end = pl_col_e.date_input("Ngày kết thúc", key="pl_end")
            else:
                pl_end = None

            # Milestones
            st.markdown(
                '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.1em;'
                'font-family:\'JetBrains Mono\',monospace;padding:4px 0">── MILESTONES ──</div>',
                unsafe_allow_html=True,
            )
            if "pl_milestones" not in st.session_state:
                st.session_state["pl_milestones"] = [{"label": "", "date": ""}]
            for mi, ms in enumerate(st.session_state["pl_milestones"]):
                ms_col_l, ms_col_d, ms_col_x = st.columns([3, 1.5, 0.3])
                ms["label"] = ms_col_l.text_input("Milestone", value=ms["label"],
                                                   key=f"pl_ms_l_{mi}", label_visibility="collapsed",
                                                   placeholder=f"Milestone {mi+1}")
                ms["date"]  = ms_col_d.text_input("Ngày", value=ms["date"],
                                                   key=f"pl_ms_d_{mi}", label_visibility="collapsed",
                                                   placeholder="YYYY-MM-DD")
                if ms_col_x.button("✕", key=f"pl_ms_x_{mi}"):
                    st.session_state["pl_milestones"].pop(mi)
                    st.rerun()
            if st.button("＋ Thêm milestone", key="pl_ms_add"):
                st.session_state["pl_milestones"].append({"label": "", "date": ""})
                st.rerun()

            if st.button("💾 TẠO PROJECT", key="pl_create"):
                if not pl_title.strip():
                    st.error("Tên project không được để trống.")
                elif pl_end and pl_end < pl_start and st.session_state.get("pl_type") == "one-time":
                    st.error("Ngày kết thúc phải sau ngày bắt đầu.")
                else:
                    milestones_init = [
                        {"label": m["label"], "done": False, "date": m["date"]}
                        for m in st.session_state.get("pl_milestones", [])
                        if m["label"].strip()
                    ]
                    new_p = add_project(
                        title=pl_title.strip(),
                        type_=st.session_state.get("pl_type", "one-time"),
                        goal=pl_goal.strip(),
                        start_date=str(pl_start),
                        end_date=str(pl_end) if pl_end else None,
                        recur_pattern=pl_recur,
                    )
                    if milestones_init:
                        update_project(new_p["id"], milestones=milestones_init)
                    st.session_state.pop("pl_milestones", None)
                    st.success(f"✅ Đã tạo project: {pl_title}")
                    st.rerun()

        # ── Project list ───────────────────────────────────────────────────────
        pl_projects = load_projects()
        if not pl_projects:
            st.markdown(
                '<div style="color:#3d5a6b;font-size:11px;text-align:center;padding:24px 0">'
                'Chưa có project nào. Tạo project đầu tiên ở trên.</div>',
                unsafe_allow_html=True,
            )

        for proj in reversed(pl_projects):  # newest first
            status_icon = {"active": "🟡", "paused": "⏸", "done": "✅"}.get(proj["status"], "")
            recur_label = f" 🔄 {proj.get('recur_pattern','')}" if proj["type"] == "recurring" else ""
            pct  = proj["progress"]
            bar  = "█" * (min(max(pct, 0), 100) // 10) + "░" * (10 - min(max(pct, 0), 100) // 10)
            with st.expander(
                f"{status_icon} {proj['title']}{recur_label}  {bar} {pct}%",
                expanded=(proj["status"] == "active"),
            ):
                # ── Milestone progress ─────────────────────────────────────────
                if proj["milestones"]:
                    _n_ms_cols = min(len(proj["milestones"]), 5)
                    ms_cols = st.columns(_n_ms_cols)
                    for mi, ms in enumerate(proj["milestones"]):
                        with ms_cols[mi % _n_ms_cols]:
                            icon = "✅" if ms["done"] else "⬜"
                            st.markdown(
                                f'<div style="font-size:10px;color:#8b949e;">'
                                f'{icon} {ms["label"]}<br>'
                                f'<span style="color:#3d5a6b">{ms.get("date","")}</span></div>',
                                unsafe_allow_html=True,
                            )

                # ── Progress slider ────────────────────────────────────────────
                new_pct = st.slider("Tiến độ %", 0, 100, pct,
                                    key=f"pl_pct_{proj['id']}")
                if new_pct != pct:
                    update_progress(proj["id"], new_pct, proj["milestones"])
                    st.rerun()

                # ── Entry log ─────────────────────────────────────────────────
                for entry in reversed(proj["entries"]):
                    e_icon = "📝" if entry["type"] == "daily" else "⚖️"
                    fnames = ", ".join(f.get("name","") for f in entry.get("files",[]))
                    st.markdown(
                        f'<div style="font-size:11px;color:#8b949e;padding:2px 0">'
                        f'{e_icon} <span style="color:#3d5a6b">{entry["date"]}</span> '
                        f'<span style="color:#e6edf3">{entry["content"]}</span>'
                        + (f' <span style="color:#3d5a6b">📎 {fnames}</span>' if fnames else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )

                # ── Add entry form ─────────────────────────────────────────────
                if proj["status"] == "active":
                    with st.expander("➕ Ghi hôm nay / Decision", expanded=False):
                        ae_type = st.radio(
                            "Loại", ["daily", "decision"],
                            horizontal=True, key=f"pl_ae_type_{proj['id']}",
                            format_func=lambda x: "📝 Daily log" if x == "daily" else "⚖️ Decision",
                        )
                        ae_content = st.text_area(
                            "Nội dung *", key=f"pl_ae_content_{proj['id']}", height=80,
                        )
                        # File: upload or URL (one file per entry; list built inside button block)
                        ae_uploaded = st.file_uploader(
                            "📎 Upload file (tuỳ chọn)", key=f"pl_ae_upload_{proj['id']}",
                        )
                        ae_url  = st.text_input("🔗 Hoặc paste URL", key=f"pl_ae_url_{proj['id']}",
                                                placeholder="https://drive.google.com/...")
                        ae_name = st.text_input("Tên hiển thị (nếu paste URL)",
                                                key=f"pl_ae_name_{proj['id']}",
                                                placeholder="VD: Brief v1")

                        if st.button("💾 Lưu entry", key=f"pl_ae_save_{proj['id']}"):
                            if not ae_content.strip():
                                st.error("Nội dung không được để trống.")
                            else:
                                ae_files: list[dict] = []  # built fresh each button press
                                if ae_uploaded:
                                    dest = save_attachment(proj["id"], ae_uploaded)
                                    ae_files.append({"name": ae_uploaded.name, "path": dest})
                                if ae_url.strip():
                                    ae_files.append({
                                        "name": ae_name.strip() or ae_url.strip(),
                                        "url": ae_url.strip(),
                                    })
                                add_entry(proj["id"], ae_type, ae_content.strip(), ae_files)
                                st.success("✅ Đã lưu entry.")
                                st.rerun()

                # ── Action buttons ─────────────────────────────────────────────
                if proj["status"] == "active":
                    btn_col_done, btn_col_pause, btn_col_del = st.columns([2, 1.5, 0.5])

                    with btn_col_pause:
                        if st.button("⏸ Pause", key=f"pl_pause_{proj['id']}"):
                            update_project(proj["id"], status="paused")
                            st.rerun()

                    with btn_col_del:
                        if st.button("🗑", key=f"pl_del_{proj['id']}"):
                            delete_project(proj["id"])
                            st.rerun()

                    with btn_col_done:
                        if st.button("⚑ Mark as Done", key=f"pl_done_{proj['id']}",
                                     type="primary", use_container_width=True):
                            st.session_state[f"pl_confirming_done_{proj['id']}"] = True

                    if st.session_state.get(f"pl_ai_err_{proj['id']}"):
                        _ai_err_key = f"pl_ai_err_{proj['id']}"
                        st.error(f"⚠ AI lỗi: {st.session_state[_ai_err_key]}\nThử lại bằng cách nhấn ✅ Xác nhận lại.")

                    if st.session_state.get(f"pl_confirming_done_{proj['id']}"):
                        st.warning(
                            f"Done project **{proj['title']}**? "
                            "AI sẽ đọc toàn bộ log và tạo SOP + Template."
                        )
                        conf_col_yes, conf_col_no = st.columns(2)
                        with conf_col_no:
                            if st.button("↩ Quay lại", key=f"pl_done_cancel_{proj['id']}"):
                                st.session_state.pop(f"pl_confirming_done_{proj['id']}", None)
                                st.rerun()
                        with conf_col_yes:
                            if st.button("✅ Xác nhận Done + Generate",
                                         key=f"pl_done_confirm_{proj['id']}",
                                         type="primary", use_container_width=True):
                                with st.spinner("🤖 AI đang đọc log và tạo SOP..."):
                                    try:
                                        _sop, _tmpl = generate_sop_and_template(proj)
                                    except Exception as _e:
                                        st.session_state[f"pl_ai_err_{proj['id']}"] = str(_e)
                                        st.rerun()
                                st.session_state.pop(f"pl_ai_err_{proj['id']}", None)
                                st.session_state[f"pl_sop_{proj['id']}"]  = _sop
                                st.session_state[f"pl_tmpl_{proj['id']}"] = _tmpl
                                st.session_state.pop(f"pl_confirming_done_{proj['id']}", None)
                                st.rerun()

                    # Preview + save
                    if st.session_state.get(f"pl_saved_flash_{proj['id']}"):
                        st.success(st.session_state.pop(f"pl_saved_flash_{proj['id']}"))

                    if st.session_state.get(f"pl_sop_{proj['id']}"):
                        _sop  = st.session_state[f"pl_sop_{proj['id']}"]
                        _tmpl = st.session_state[f"pl_tmpl_{proj['id']}"]
                        with st.expander("📄 SOP Preview", expanded=True):
                            st.markdown(_sop[:800] + ("..." if len(_sop) > 800 else ""))
                        with st.expander("📋 Template Preview"):
                            st.markdown(_tmpl[:800] + ("..." if len(_tmpl) > 800 else ""))

                        save_col, back_col = st.columns(2)
                        with back_col:
                            if st.button("↩ Chưa done, quay lại",
                                         key=f"pl_save_cancel_{proj['id']}"):
                                st.session_state.pop(f"pl_sop_{proj['id']}", None)
                                st.session_state.pop(f"pl_tmpl_{proj['id']}", None)
                                st.rerun()
                        with save_col:
                            if st.button("💾 Lưu vào 07_Outputs/",
                                         key=f"pl_save_confirm_{proj['id']}",
                                         type="primary", use_container_width=True):
                                try:
                                    _sop_path, _tmpl_path = save_outputs(
                                        proj["id"], _sop, _tmpl
                                    )
                                    if proj.get("type") == "recurring":
                                        clone_for_next_cycle(proj)
                                except Exception as _save_e:
                                    st.error(f"⚠ Lưu thất bại: {_save_e}")
                                    st.stop()
                                else:
                                    st.session_state.pop(f"pl_sop_{proj['id']}", None)
                                    st.session_state.pop(f"pl_tmpl_{proj['id']}", None)
                                    st.session_state[f"pl_saved_flash_{proj['id']}"] = (
                                        f"✅ Đã lưu!\n📄 SOP: `{_sop_path}`\n📋 Template: `{_tmpl_path}`"
                                    )
                                    st.rerun()

                elif proj["status"] == "paused":
                    btn_resume_col, btn_del_col = st.columns([3, 0.5])
                    with btn_resume_col:
                        if st.button("▶ Resume", key=f"pl_resume_{proj['id']}"):
                            update_project(proj["id"], status="active")
                            st.rerun()
                    with btn_del_col:
                        if st.button("🗑", key=f"pl_del_p_{proj['id']}"):
                            delete_project(proj["id"])
                            st.rerun()

                elif proj["status"] == "done":
                    sop_path  = proj.get("sop_path")
                    tmpl_path = proj.get("template_path")
                    if sop_path:
                        st.markdown(
                            f'<div style="font-size:11px;color:#3d5a6b">📄 SOP: <code>{sop_path}</code></div>',
                            unsafe_allow_html=True,
                        )
                    if tmpl_path:
                        st.markdown(
                            f'<div style="font-size:11px;color:#3d5a6b">📋 Template: <code>{tmpl_path}</code></div>',
                            unsafe_allow_html=True,
                        )
                    if st.button("🗑 Xoá", key=f"pl_del_d_{proj['id']}"):
                        delete_project(proj["id"])
                        st.rerun()


# ── Settings tab ──────────────────────────────────────────────────────────────
def render_settings_tab():
    section_header("⊛", "SYSTEM CONFIG", color="#8b949e", anim="float",
                   subtitle="biến môi trường từ .env · chỉ xem")

    def status_row(key: str, label: str):
        val = os.getenv(key, "")
        icon  = '<span style="color:#30d158">●</span>' if val else '<span style="color:#ff2d55">●</span>'
        masked = val[:8] + "…" if val and len(val) > 8 else val
        display = f'`{masked}`' if val else '<span style="color:#6e7681">chưa cấu hình</span>'
        st.markdown(
            f'<div style="display:flex;gap:8px;align-items:center;padding:3px 0;'
            f'font-size:11px;font-family:\'JetBrains Mono\',monospace;">'
            f'{icon} <span style="color:#8b949e;min-width:160px">{label}</span>'
            f'<span style="color:#c9d1d9">{display}</span></div>',
            unsafe_allow_html=True,
        )

    for section, keys in [
        ("INTEGRATIONS", [
            ("ANTHROPIC_API_KEY",   "Anthropic API Key"),
            ("DISCORD_WEBHOOK_URL", "Discord Webhook"),
            ("OBSIDIAN_API_KEY",    "Obsidian API Key"),
            ("OBSIDIAN_BASE_URL",   "Obsidian URL"),
        ]),
        ("LOCAL LLM", [
            ("OLLAMA_BASE_URL", "Ollama URL"),
            ("OLLAMA_MODEL",    "Ollama Model"),
        ]),
        ("EMAIL / OUTLOOK", [
            ("USER_EMAIL",       "User Email"),
            ("BOSS_EMAIL",       "Boss Email"),
            ("EMAIL_QUEUE_PATH", "Email Queue Path"),
        ]),
    ]:
        st.markdown(
            f'<div style="color:#3d5a6b;font-size:10px;letter-spacing:.15em;'
            f'font-family:\'JetBrains Mono\',monospace;padding:8px 0 3px">── {section} ──</div>',
            unsafe_allow_html=True,
        )
        for env_key, label in keys:
            status_row(env_key, label)

    st.markdown(
        '<div style="color:#3d5a6b;font-size:10px;letter-spacing:.15em;'
        'font-family:\'JetBrains Mono\',monospace;padding:8px 0 3px">── SCHEDULER ──</div>',
        unsafe_allow_html=True,
    )
    t = os.getenv("REMINDER_TIME", "08:00")
    st.markdown(
        f'<div style="font-size:11px;color:#8b949e;font-family:\'JetBrains Mono\',monospace">'
        f'⊛ reminder daily @ <span style="color:#00d4ff">{t}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Chỉnh sửa file `.env` rồi restart app để thay đổi config.")


# ── Analytics tab ─────────────────────────────────────────────────────────────
@st.fragment
def render_analytics_tab():
    from modules.analytics import (
        get_priority_breakdown, get_status_breakdown,
        get_creation_trend, get_upcoming_deadlines, get_overdue,
        get_priority_color_map, get_burndown_data, get_tag_breakdown,
    )
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        HAS_PLOTLY = True
    except ImportError:
        HAS_PLOTLY = False

    section_header("◎", "ANALYTICS", color="#00d4ff", anim="scan",
                   subtitle="task metrics · priority breakdown · trend · deadlines")

    all_tasks = load_tasks()
    if not all_tasks:
        st.info("Chưa có task nào. Thêm task ở tab TASKS trước.")
        return

    # Row 1: summary metrics
    status = get_status_breakdown(all_tasks)
    overdue = get_overdue(all_tasks)
    upcoming = get_upcoming_deadlines(all_tasks, days=14)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("◈ ACTIVE",    status["active"])
    c2.metric("◇ DONE",      status["done"])
    c3.metric("⬥ OVERDUE",   len(overdue))
    c4.metric("⏱ DUE 14D",   len(upcoming))

    st.markdown("---")
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown(
            '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
            'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── PRIORITY BREAKDOWN ──</div>',
            unsafe_allow_html=True,
        )
        priority = get_priority_breakdown(all_tasks)
        color_map = get_priority_color_map()
        if HAS_PLOTLY and priority:
            labels = list(priority.keys())
            values = list(priority.values())
            colors = [color_map.get(k, "#8b949e") for k in labels]
            fig = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color="#0d1117", width=2)),
                hole=0.55,
                textfont=dict(family="JetBrains Mono", size=10, color="#e6edf3"),
                hovertemplate="%{label}: %{value}<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="#090e14", plot_bgcolor="#090e14",
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(font=dict(family="JetBrains Mono", size=9, color="#8b949e"),
                            bgcolor="#090e14"),
                height=230,
                hoverlabel=dict(bgcolor="#161b22", font_size=11,
                                font_family="JetBrains Mono", bordercolor="#21262d"),
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": True, "displaylogo": False,
                                    "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"]})
        else:
            for k, v in priority.items():
                color = color_map.get(k, "#8b949e")
                st.markdown(
                    f'<div style="border-left:3px solid {color};padding:3px 8px;margin-bottom:3px;">'
                    f'<span style="color:#c9d1d9;font-size:11px;font-family:\'JetBrains Mono\',monospace">'
                    f'{k.upper()} — {v}</span></div>',
                    unsafe_allow_html=True,
                )

    with col_right:
        st.markdown(
            '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
            'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── CREATION TREND (30D) ──</div>',
            unsafe_allow_html=True,
        )
        trend = get_creation_trend(all_tasks, days=30)
        if HAS_PLOTLY and trend:
            dates = list(trend.keys())
            counts = list(trend.values())
            fig2 = go.Figure(go.Scatter(
                x=dates, y=counts,
                mode="lines+markers",
                line=dict(color="#00d4ff", width=2),
                marker=dict(size=4, color="#00d4ff"),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,0.06)",
                hovertemplate="%{x}: %{y}<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor="#090e14", plot_bgcolor="#090e14",
                xaxis=dict(showgrid=False, tickfont=dict(family="JetBrains Mono", size=8, color="#6e7681"),
                           tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor="#1d2733",
                           tickfont=dict(family="JetBrains Mono", size=8, color="#6e7681")),
                margin=dict(l=10, r=10, t=10, b=40),
                height=230,
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#161b22", font_size=11,
                                font_family="JetBrains Mono", bordercolor="#00d4ff"),
            )
            st.plotly_chart(fig2, use_container_width=True,
                            config={"displayModeBar": True, "displaylogo": False,
                                    "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"]})

    # ── Burndown + Tag breakdown ──────────────────────────────────────────────
    st.markdown("---")
    col_burn, col_tags = st.columns([3, 2])

    with col_burn:
        st.markdown(
            '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
            'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── BURNDOWN (30D) ──</div>',
            unsafe_allow_html=True,
        )
        burndown = get_burndown_data(all_tasks, days=30)
        if HAS_PLOTLY and burndown:
            bd_dates    = list(burndown.keys())
            bd_created  = [v["created"]   for v in burndown.values()]
            bd_done     = [v["completed"] for v in burndown.values()]
            fig_burn = go.Figure()
            fig_burn.add_trace(go.Bar(
                x=bd_dates, y=bd_created, name="Created",
                marker_color="#00d4ff", opacity=0.7,
            ))
            fig_burn.add_trace(go.Bar(
                x=bd_dates, y=bd_done, name="Completed",
                marker_color="#30d158", opacity=0.9,
            ))
            fig_burn.update_layout(
                paper_bgcolor="#090e14", plot_bgcolor="#090e14",
                barmode="group",
                xaxis=dict(showgrid=False, tickfont=dict(family="JetBrains Mono", size=7,
                                                          color="#6e7681"), tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor="#1d2733",
                           tickfont=dict(family="JetBrains Mono", size=8, color="#6e7681")),
                legend=dict(font=dict(family="JetBrains Mono", size=9, color="#8b949e"),
                            bgcolor="#090e14"),
                margin=dict(l=10, r=10, t=10, b=40),
                height=200,
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#161b22", font_size=11,
                                font_family="JetBrains Mono", bordercolor="#21262d"),
            )
            st.plotly_chart(fig_burn, use_container_width=True,
                            config={"displayModeBar": True, "displaylogo": False,
                                    "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"]})
        else:
            st.markdown(
                '<div style="color:#6e7681;font-size:10px;font-family:\'JetBrains Mono\',monospace;'
                'padding:4px 0">Cần Plotly + task có completed_at để hiển thị.</div>',
                unsafe_allow_html=True,
            )

    with col_tags:
        st.markdown(
            '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
            'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── TAGS ──</div>',
            unsafe_allow_html=True,
        )
        tag_bd = get_tag_breakdown(all_tasks)
        if tag_bd and HAS_PLOTLY:
            fig_tags = go.Figure(go.Bar(
                x=list(tag_bd.values()), y=list(tag_bd.keys()),
                orientation="h",
                marker_color="#79c0ff",
                hovertemplate="%{y}: %{x}<extra></extra>",
            ))
            fig_tags.update_layout(
                paper_bgcolor="#090e14", plot_bgcolor="#090e14",
                xaxis=dict(showgrid=True, gridcolor="#1d2733",
                           tickfont=dict(family="JetBrains Mono", size=8, color="#6e7681")),
                yaxis=dict(showgrid=False, tickfont=dict(family="JetBrains Mono", size=8,
                                                          color="#c9d1d9")),
                margin=dict(l=10, r=10, t=10, b=10),
                height=200,
                hoverlabel=dict(bgcolor="#161b22", font_size=11,
                                font_family="JetBrains Mono", bordercolor="#79c0ff"),
            )
            st.plotly_chart(fig_tags, use_container_width=True,
                            config={"displayModeBar": True, "displaylogo": False,
                                    "modeBarButtonsToRemove": ["select2d","lasso2d","autoScale2d"]})
        elif tag_bd:
            for tag, cnt in list(tag_bd.items())[:8]:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:10px;color:#c9d1d9;font-family:\'JetBrains Mono\',monospace;'
                    f'padding:1px 0"><span>{tag}</span><span style="color:#79c0ff">{cnt}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="color:#6e7681;font-size:10px;font-family:\'JetBrains Mono\',monospace;'
                'padding:4px 0">◇ Chưa có task nào được gắn tag.</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown(
            '<div style="font-size:10px;color:#ff2d55;letter-spacing:.14em;'
            'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── ⚠ OVERDUE ──</div>',
            unsafe_allow_html=True,
        )
        if overdue:
            for t in overdue[:8]:
                color = PRIORITY_COLORS.get(t.get("category_raw", "low"), "#888")
                st.markdown(
                    f'<div style="border-left:2px solid {color};padding:3px 7px;margin-bottom:2px;'
                    f'background:#090e14;border-radius:2px;">'
                    f'<div style="font-size:11px;color:#e6edf3;font-family:\'JetBrains Mono\',monospace">'
                    f'{t["task_name"][:40]}</div>'
                    f'<div style="font-size:9px;color:#ff2d55;font-family:\'JetBrains Mono\',monospace">'
                    f'⏱ {t["deadline"]}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="font-size:10px;color:#30d158;font-family:\'JetBrains Mono\',monospace;'
                'padding:4px 0">◇ không có task quá hạn</div>',
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown(
            '<div style="font-size:10px;color:#ff9f0a;letter-spacing:.14em;'
            'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── ⏱ DUE NEXT 14 DAYS ──</div>',
            unsafe_allow_html=True,
        )
        if upcoming:
            for t in upcoming[:8]:
                color = PRIORITY_COLORS.get(t.get("category_raw", "low"), "#888")
                st.markdown(
                    f'<div style="border-left:2px solid {color};padding:3px 7px;margin-bottom:2px;'
                    f'background:#090e14;border-radius:2px;">'
                    f'<div style="font-size:11px;color:#e6edf3;font-family:\'JetBrains Mono\',monospace">'
                    f'{t["task_name"][:40]}</div>'
                    f'<div style="font-size:9px;color:#ff9f0a;font-family:\'JetBrains Mono\',monospace">'
                    f'⏱ {t["deadline"]}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="font-size:10px;color:#6e7681;font-family:\'JetBrains Mono\',monospace;'
                'padding:4px 0">◇ không có deadline sắp tới</div>',
                unsafe_allow_html=True,
            )

    # ── Weekly Report ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
        'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── WEEKLY REPORT ──</div>',
        unsafe_allow_html=True,
    )
    wr_col_days, wr_col_btn, wr_col_discord = st.columns([1, 2, 2])
    with wr_col_days:
        wr_days = st.number_input("Số ngày", min_value=3, max_value=30, value=7, key="wr_days")
    with wr_col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("◎ WEEKLY REPORT", key="gen_wr", use_container_width=True):
            from modules.weekly_report import generate, to_markdown
            with st.spinner("Đang tổng hợp..."):
                st.session_state.weekly_report = generate(days=int(wr_days))
    with wr_col_discord:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get("weekly_report") and st.button(
            "◈ GỬI → DISCORD", key="send_wr", use_container_width=True
        ):
            from modules.weekly_report import to_markdown
            from modules.discord_notifier import _post
            md = to_markdown(st.session_state.weekly_report)
            _post({"embeds": [{"title": "📊 Weekly Report",
                                "description": md[:3800],
                                "color": 0x00d4ff,
                                "footer": {"text": "Task Tracker"}}]})
            st.success("Đã gửi Discord!")

    if st.session_state.get("weekly_report"):
        from modules.weekly_report import to_markdown
        rpt = st.session_state.weekly_report
        c_cr, c_act, c_od, c_mail = st.columns(4)
        c_cr.metric("➕ Created",  len(rpt["tasks_created"]))
        c_act.metric("📋 Active",  len(rpt["tasks_active"]))
        c_od.metric("⚠ Overdue",   len(rpt["tasks_overdue"]))
        c_mail.metric("📧 Emails",
                      sum(len(v) for v in rpt["emails"].values()))
        with st.expander("📄 Xem markdown report"):
            st.code(to_markdown(rpt), language="markdown")

    # ── KPI Tracker ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
        'font-family:\'JetBrains Mono\',monospace;padding:3px 0 5px">── KPI TRACKER ──</div>',
        unsafe_allow_html=True,
    )
    from modules.kpi_tracker import load_kpis, add_kpi, add_actual, delete_kpi, get_achievement_pct, PERIODS

    kpis = load_kpis()

    # Show existing KPIs
    if kpis:
        for kpi in kpis:
            pct = get_achievement_pct(kpi)
            actuals = kpi.get("actuals", [])
            pct_color = "#30d158" if (pct or 0) >= 100 else "#ff9f0a" if (pct or 0) >= 70 else "#ff2d55"
            pct_str = f"{pct}%" if pct is not None else "—"
            latest_val = actuals[-1]["value"] if actuals else None
            latest_str = f"{latest_val} {kpi['unit']}" if latest_val is not None else "—"

            kc1, kc2, kc3, kc4, kc5 = st.columns([3, 1.5, 1.5, 2, 0.6])
            kc1.markdown(
                f'<div style="font-size:12px;color:#e6edf3;font-family:\'JetBrains Mono\',monospace;'
                f'padding:4px 0">{kpi["name"]}'
                f'<span style="color:#6e7681;font-size:10px"> / {kpi["period"]}</span></div>',
                unsafe_allow_html=True,
            )
            kc2.markdown(
                f'<div style="font-size:11px;color:#8b949e;font-family:\'JetBrains Mono\',monospace;'
                f'padding:4px 0">Target: <b style="color:#e6edf3">{kpi["target"]} {kpi["unit"]}</b></div>',
                unsafe_allow_html=True,
            )
            kc3.markdown(
                f'<div style="font-size:11px;font-family:\'JetBrains Mono\',monospace;padding:4px 0">'
                f'Actual: <b style="color:#e6edf3">{latest_str}</b></div>',
                unsafe_allow_html=True,
            )
            kc4.markdown(
                f'<div style="font-size:12px;font-family:\'JetBrains Mono\',monospace;padding:4px 0">'
                f'<b style="color:{pct_color}">{pct_str}</b></div>',
                unsafe_allow_html=True,
            )
            with kc5:
                if st.button("✕", key=f"del_kpi_{kpi['id']}"):
                    delete_kpi(kpi["id"])
                    st.rerun()

            # Chart if ≥2 actuals
            if HAS_PLOTLY and len(actuals) >= 2:
                dates_k = [a["date"] for a in actuals]
                vals_k  = [a["value"] for a in actuals]
                fig_k = go.Figure()
                fig_k.add_trace(go.Scatter(
                    x=dates_k, y=vals_k, mode="lines+markers",
                    line=dict(color="#00d4ff", width=1.5),
                    marker=dict(size=4), name="Actual",
                ))
                fig_k.add_hline(y=kpi["target"], line_dash="dash",
                                line_color="#ff9f0a")
                fig_k.update_layout(
                    paper_bgcolor="#090e14", plot_bgcolor="#090e14",
                    margin=dict(l=10, r=10, t=10, b=30), height=150,
                    xaxis=dict(showgrid=False, tickfont=dict(size=8, color="#6e7681")),
                    yaxis=dict(showgrid=True, gridcolor="#1d2733",
                               tickfont=dict(size=8, color="#6e7681")),
                    showlegend=False,
                )
                st.plotly_chart(fig_k, use_container_width=True, config={"displayModeBar": False})

            # Add actual form
            with st.expander(f"➕ Nhập actual cho: {kpi['name']}", expanded=False):
                av_col, an_col, ab_col = st.columns([1, 2, 1])
                new_val  = av_col.number_input("Giá trị", key=f"kpi_val_{kpi['id']}", value=0.0, step=0.1)
                new_note = an_col.text_input("Ghi chú", key=f"kpi_note_{kpi['id']}", placeholder="VD: Tháng 5")
                with ab_col:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Lưu", key=f"kpi_save_{kpi['id']}", use_container_width=True):
                        add_actual(kpi["id"], new_val, new_note)
                        st.success("Đã lưu!")
                        st.rerun()

    # Add new KPI form
    with st.expander("➕ THÊM KPI MỚI", expanded=not kpis):
        kn1, kn2, kn3, kn4 = st.columns([3, 1, 1.5, 1.5])
        kpi_name   = kn1.text_input("Tên KPI", key="new_kpi_name", placeholder="VD: New Users / tháng")
        kpi_unit   = kn2.text_input("Đơn vị", key="new_kpi_unit", placeholder="users")
        kpi_target = kn3.number_input("Target", key="new_kpi_target", value=0.0, step=1.0)
        kpi_period = kn4.selectbox("Chu kỳ", PERIODS, key="new_kpi_period")
        if st.button("➕ TẠO KPI", key="create_kpi", use_container_width=True):
            if kpi_name and kpi_unit:
                add_kpi(kpi_name, kpi_unit, kpi_target, kpi_period)
                st.success("Đã tạo KPI!")
                st.rerun()
            else:
                st.warning("Nhập tên và đơn vị.")


# ── Data Explorer helpers ─────────────────────────────────────────────────────

def _nb_cell(source: str, cell_type: str = "code") -> dict:
    """Return a minimal Jupyter notebook cell dict."""
    if cell_type == "markdown":
        return {"cell_type": "markdown", "metadata": {},
                "source": source}
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [], "source": source}


def _build_eda_notebook(df, filename: str) -> dict:
    """
    Build a Jupyter notebook dict for an EDA report of *df*.
    Covers: setup, HEAD, DTYPES, MISSING bar chart, STATS, CORRELATION heatmap.
    """
    import json as _json
    stem = filename.rsplit(".", 1)[0]
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"

    num_cols = list(df.select_dtypes("number").columns)
    all_cols = list(df.columns)

    if ext == "parquet":
        read_code = f"df = pd.read_parquet('{filename}')"
    elif ext in ("xlsx", "xls"):
        read_code = f"df = pd.read_excel('{filename}')"
    else:
        read_code = f"df = pd.read_csv('{filename}')"

    cells = [
        _nb_cell(f"# EDA — {stem}", "markdown"),
        _nb_cell(
            "import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\n"
            "import seaborn as sns\n\nplt.rcParams.update({'figure.facecolor': '#0d1117', "
            "'axes.facecolor': '#0d1117', 'axes.edgecolor': '#30363d', "
            "'text.color': '#e6edf3', 'axes.labelcolor': '#e6edf3', "
            "'xtick.color': '#e6edf3', 'ytick.color': '#e6edf3'})"
        ),
        _nb_cell(f"## 1. Load data", "markdown"),
        _nb_cell(f"{read_code}\nprint(df.shape)\ndf.head()"),
        _nb_cell("## 2. Column types & null counts", "markdown"),
        _nb_cell(
            "dtype_df = pd.DataFrame({\n"
            "    'column': df.columns,\n"
            "    'dtype': [str(d) for d in df.dtypes],\n"
            "    'nulls': df.isnull().sum().values,\n"
            "    'pct_null': (df.isnull().sum().values / len(df) * 100).round(2),\n"
            "    'unique': [df[c].nunique() for c in df.columns],\n"
            "})\ndtype_df"
        ),
        _nb_cell("## 3. Missing values", "markdown"),
        _nb_cell(
            "missing = df.isnull().sum().sort_values(ascending=False)\n"
            "pct = (missing / len(df) * 100).round(2)\n"
            "fig, ax = plt.subplots(figsize=(10, max(3, len(missing) * 0.3)))\n"
            "pct[pct > 0].plot(kind='barh', ax=ax, color='#00d4ff')\n"
            "ax.set_xlabel('% missing')\nax.set_title('Missing Value %')\n"
            "plt.tight_layout()\nplt.show()\n"
            "print(pd.concat([missing, pct], axis=1, keys=['count', 'pct']))"
        ),
        _nb_cell("## 4. Descriptive statistics", "markdown"),
        _nb_cell("df.describe(include='all').T"),
    ]

    if len(num_cols) >= 2:
        cells += [
            _nb_cell("## 5. Correlation heatmap", "markdown"),
            _nb_cell(
                f"num_cols = {_json.dumps(num_cols)}\n"
                "corr = df[num_cols].corr()\n"
                "fig, ax = plt.subplots(figsize=(max(6, len(num_cols)), max(5, len(num_cols))))\n"
                "sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm',\n"
                "            vmin=-1, vmax=1, ax=ax, linewidths=0.5)\n"
                "ax.set_title('Correlation Matrix')\n"
                "plt.tight_layout()\nplt.show()"
            ),
        ]

    cells.append(_nb_cell("## 6. Distribution of numeric columns", "markdown"))
    cells.append(_nb_cell(
        f"num_cols = {_json.dumps(num_cols[:12])}\n"  # cap at 12
        "if num_cols:\n"
        "    n = len(num_cols)\n"
        "    cols_per_row = 3\n"
        "    rows = (n + cols_per_row - 1) // cols_per_row\n"
        "    fig, axes = plt.subplots(rows, cols_per_row,\n"
        "                             figsize=(5 * cols_per_row, 4 * rows))\n"
        "    axes = axes.flat if hasattr(axes, 'flat') else [axes]\n"
        "    for ax, col in zip(axes, num_cols):\n"
        "        df[col].dropna().hist(bins=30, ax=ax, color='#00d4ff', edgecolor='#21262d')\n"
        "        ax.set_title(col)\n"
        "    for ax in list(axes)[n:]:\n"
        "        ax.set_visible(False)\n"
        "    plt.tight_layout()\n"
        "    plt.show()"
    ))

    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }


# ── Data Explorer tab ─────────────────────────────────────────────────────────
def render_data_explorer_tab():
    section_header("⬢", "DATA EXPLORER", color="#bd00ff", anim="pulse",
                   subtitle="upload CSV · Excel · Parquet · tự động phân tích")

    uploaded = st.file_uploader(
        "Kéo thả file hoặc chọn từ máy",
        type=["csv", "xlsx", "xls", "parquet"],
        key="data_upload",
        label_visibility="collapsed",
    )
    if not uploaded:
        st.markdown(
            '<div style="border:1px dashed #1d2733;border-radius:4px;padding:30px;'
            'text-align:center;margin-top:10px;">'
            '<div style="font-size:24px;color:#2a3a4a">⬢</div>'
            '<div style="font-size:11px;color:#3d5a6b;font-family:\'JetBrains Mono\',monospace;'
            'margin-top:6px;letter-spacing:.08em">CSV · XLSX · PARQUET</div>'
            '<div style="font-size:10px;color:#2a3a4a;font-family:\'JetBrains Mono\',monospace;'
            'margin-top:3px">drag & drop to explore</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    try:
        import pandas as pd
        import io

        name = uploaded.name.lower()
        if name.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(uploaded.read()))
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded)
        else:
            raw = uploaded.read()
            for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(io.BytesIO(raw), encoding=enc)
                    break
                except Exception:
                    continue

        st.markdown(
            f'<div style="font-size:10px;color:#30d158;font-family:\'JetBrains Mono\',monospace;'
            f'padding:4px 0 8px">◈ {uploaded.name} — {df.shape[0]:,} rows × {df.shape[1]} cols</div>',
            unsafe_allow_html=True,
        )

        # Tabs inside explorer
        t_head, t_types, t_missing, t_stats, t_corr = st.tabs(
            ["HEAD", "DTYPES", "MISSING", "STATS", "CORRELATION"]
        )

        with t_head:
            rows = st.slider("rows", 5, 50, 10, key="de_rows")
            st.dataframe(df.head(rows), use_container_width=True)

        with t_types:
            dtype_df = pd.DataFrame({
                "column": df.columns,
                "dtype":  [str(d) for d in df.dtypes],
                "nulls":  df.isnull().sum().values,
                "unique": [df[c].nunique() for c in df.columns],
            })
            st.dataframe(dtype_df, use_container_width=True, hide_index=True)

        with t_missing:
            missing = df.isnull().sum()
            miss_df = pd.DataFrame({
                "column":  missing.index,
                "missing": missing.values,
                "pct":     (missing.values / len(df) * 100).round(2),
            }).sort_values("missing", ascending=False)
            st.dataframe(miss_df, use_container_width=True, hide_index=True)

        with t_stats:
            num_cols = df.select_dtypes("number")
            cat_cols = df.select_dtypes(exclude="number")
            if num_cols.shape[1] > 0:
                stats = num_cols.describe().T.round(4)
                stats.insert(0, "column", stats.index)
                stats = stats.reset_index(drop=True)
                st.dataframe(stats, use_container_width=True, hide_index=True)
            if cat_cols.shape[1] > 0:
                st.caption("Categorical columns")
                cat_stats = cat_cols.describe().T
                cat_stats.insert(0, "column", cat_stats.index)
                cat_stats = cat_stats.reset_index(drop=True)
                st.dataframe(cat_stats, use_container_width=True, hide_index=True)

        with t_corr:
            try:
                import plotly.express as px
                num_df = df.select_dtypes("number")
                if num_df.shape[1] < 2:
                    st.info("Cần ít nhất 2 cột số để vẽ heatmap.")
                else:
                    corr = num_df.corr()
                    fig = px.imshow(
                        corr,
                        color_continuous_scale="RdBu_r",
                        zmin=-1, zmax=1,
                        text_auto=".2f",
                    )
                    fig.update_layout(
                        paper_bgcolor="#090e14", plot_bgcolor="#090e14",
                        font=dict(family="JetBrains Mono", size=9, color="#e6edf3"),
                        margin=dict(l=5, r=5, t=30, b=5),
                        height=420,
                        coloraxis_colorbar=dict(tickfont=dict(size=8)),
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            except Exception as e:
                st.warning(f"Không vẽ được heatmap: {e}")

        # ── Export EDA Notebook ───────────────────────────────────────────────
        st.divider()
        try:
            import json as _json
            nb = _build_eda_notebook(df, uploaded.name)
            nb_bytes = _json.dumps(nb, ensure_ascii=False, indent=1).encode("utf-8")
            stem = uploaded.name.rsplit(".", 1)[0]
            st.download_button(
                "⬇ Export EDA Notebook (.ipynb)",
                nb_bytes,
                file_name=f"eda_{stem}.ipynb",
                mime="application/x-ipynb+json",
                key="de_download_nb",
                use_container_width=False,
            )
        except Exception as e:
            st.error(f"Không tạo được notebook: {e}")

    except Exception as e:
        st.error(f"Không đọc được file: {e}")


# ── Focus Timer tab ────────────────────────────────────────────────────────────
def render_focus_tab():
    section_header("⏱", "FOCUS TIMER", color="#ff9f0a", anim="blink",
                   subtitle="pomodoro · 25/5 · deep work")

    active_tasks = get_active_tasks()
    task_names = ["— tự do —"] + [t["task_name"] for t in active_tasks]
    selected = st.selectbox("Task đang làm", task_names, key="focus_task",
                            label_visibility="collapsed")

    col_work, col_break = st.columns(2)
    with col_work:
        work_min = st.number_input("Work (phút)", min_value=1, max_value=120, value=25, key="focus_work")
    with col_break:
        break_min = st.number_input("Break (phút)", min_value=1, max_value=30, value=5, key="focus_break")

    task_label = selected if selected != "— tự do —" else "Focus Session"

    timer_html = f"""
<div id="pomodoro" style="font-family:'JetBrains Mono',monospace;text-align:center;
     padding:18px 0 8px;background:#090e14;border:1px solid #1d2733;border-radius:6px;">
  <div id="mode-label" style="font-size:10px;color:#ff9f0a;letter-spacing:.18em;margin-bottom:4px">
    WORK SESSION
  </div>
  <div id="task-label" style="font-size:11px;color:#6e7681;margin-bottom:10px;
       max-width:300px;margin-left:auto;margin-right:auto;overflow:hidden;
       text-overflow:ellipsis;white-space:nowrap">{task_label}</div>
  <div id="display" style="font-size:52px;font-weight:700;color:#ff9f0a;letter-spacing:.04em;
       text-shadow:0 0 18px rgba(255,159,10,.45);line-height:1">
    {work_min:02d}:00
  </div>
  <div style="margin-top:14px;display:flex;gap:10px;justify-content:center">
    <button onclick="toggleTimer()" id="btn-start"
      style="background:#0f1923;border:1px solid #ff9f0a;color:#ff9f0a;border-radius:3px;
             padding:5px 22px;font-family:'JetBrains Mono',monospace;font-size:12px;
             letter-spacing:.06em;cursor:pointer">▶ START</button>
    <button onclick="resetTimer()"
      style="background:#0f1923;border:1px solid #21262d;color:#6e7681;border-radius:3px;
             padding:5px 18px;font-family:'JetBrains Mono',monospace;font-size:12px;
             letter-spacing:.06em;cursor:pointer">↺ RESET</button>
  </div>
  <div id="session-count" style="margin-top:10px;font-size:10px;color:#3d5a6b;
       letter-spacing:.12em">sessions: 0</div>
</div>
<script>
var WORK  = {work_min} * 60;
var BREAK = {break_min} * 60;
var remaining = WORK;
var running = false;
var inBreak = false;
var sessions = 0;
var interval = null;

function fmt(s) {{
  var m = Math.floor(s/60);
  var sec = s % 60;
  return (m<10?'0':'')+m+':'+(sec<10?'0':'')+sec;
}}
function updateDisplay() {{
  document.getElementById('display').innerText = fmt(remaining);
}}
function toggleTimer() {{
  var btn = document.getElementById('btn-start');
  if (running) {{
    clearInterval(interval);
    running = false;
    btn.innerText = '▶ START';
  }} else {{
    running = true;
    btn.innerText = '⏸ PAUSE';
    interval = setInterval(function() {{
      remaining--;
      updateDisplay();
      if (remaining <= 0) {{
        clearInterval(interval);
        running = false;
        btn.innerText = '▶ START';
        if (!inBreak) {{
          sessions++;
          document.getElementById('session-count').innerText = 'sessions: ' + sessions;
          inBreak = true;
          remaining = BREAK;
          document.getElementById('mode-label').innerText = 'BREAK TIME';
          document.getElementById('display').style.color = '#30d158';
          document.getElementById('display').style.textShadow = '0 0 18px rgba(48,209,88,.45)';
        }} else {{
          inBreak = false;
          remaining = WORK;
          document.getElementById('mode-label').innerText = 'WORK SESSION';
          document.getElementById('display').style.color = '#ff9f0a';
          document.getElementById('display').style.textShadow = '0 0 18px rgba(255,159,10,.45)';
        }}
        updateDisplay();
      }}
    }}, 1000);
  }}
}}
function resetTimer() {{
  clearInterval(interval);
  running = false;
  inBreak = false;
  remaining = WORK;
  document.getElementById('btn-start').innerText = '▶ START';
  document.getElementById('mode-label').innerText = 'WORK SESSION';
  document.getElementById('display').style.color = '#ff9f0a';
  document.getElementById('display').style.textShadow = '0 0 18px rgba(255,159,10,.45)';
  updateDisplay();
}}
</script>
"""
    components.html(timer_html, height=240)

    # Pomodoro guide
    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
        'font-family:\'JetBrains Mono\',monospace;padding:3px 0 6px">── POMODORO TECHNIQUE ──</div>',
        unsafe_allow_html=True,
    )
    steps = [
        ("1", "Chọn task cần làm"),
        ("2", f"Set timer {work_min} phút — làm việc tập trung, không distraction"),
        ("3", f"Khi chuông reo → nghỉ {break_min} phút"),
        ("4", "Sau 4 pomodoro → nghỉ dài 15–30 phút"),
    ]
    for num, desc in steps:
        st.markdown(
            f'<div style="display:flex;gap:10px;padding:3px 0;font-size:11px;'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'<span style="color:#ff9f0a;min-width:14px">{num}.</span>'
            f'<span style="color:#8b949e">{desc}</span></div>',
            unsafe_allow_html=True,
        )


# ── Snippets tab ───────────────────────────────────────────────────────────────
def render_snippets_tab():
    from modules.snippets import (
        load_snippets, add_snippet, delete_snippet, CATEGORIES, search_snippets
    )
    section_header("⌥", "CODE SNIPPETS", color="#64d2ff", anim="matrix",
                   subtitle="DA · DS · DE · SQL · Shell — copy-paste ready")

    snippets = load_snippets()

    col_search, col_cat = st.columns([3, 1])
    with col_search:
        query = st.text_input("q", placeholder="/ tìm snippet...", label_visibility="collapsed",
                              key="snip_search")
    with col_cat:
        cat_filter = st.selectbox("c", options=["All"] + CATEGORIES,
                                  label_visibility="collapsed", key="snip_cat")

    if query:
        snippets = search_snippets(snippets, query)
    if cat_filter != "All":
        snippets = [s for s in snippets if s.get("category") == cat_filter]

    # Add new snippet form
    with st.expander("+ ADD SNIPPET", expanded=False):
        s_title = st.text_input("Title *", key="snip_title")
        s_cat   = st.selectbox("Category", CATEGORIES, key="snip_add_cat")
        s_code  = st.text_area("Code *", key="snip_code", height=100,
                               placeholder="# paste your code here")
        s_note  = st.text_input("Note", key="snip_note", placeholder="short description")
        if st.button("▶ SAVE SNIPPET", key="snip_save", use_container_width=True):
            if s_title.strip() and s_code.strip():
                add_snippet(s_title.strip(), s_cat, s_code.strip(), s_note.strip())
                st.success("◈ Saved!")
                st.rerun()
            else:
                st.error("Title và Code không được để trống.")

    st.markdown("---")

    if not snippets:
        st.markdown(
            '<div style="font-size:11px;color:#3d5a6b;font-family:\'JetBrains Mono\',monospace;'
            'text-align:center;padding:20px 0">no snippets found</div>',
            unsafe_allow_html=True,
        )
        return

    CAT_COLORS = {
        "Python": "#79c0ff",
        "SQL":    "#f0883e",
        "Shell":  "#a5d6ff",
        "Markdown": "#8b949e",
    }

    for s in snippets:
        cat   = s.get("category", "")
        color = CAT_COLORS.get(cat, "#8b949e")
        sid   = s["id"]
        st.markdown(
            f'<div style="border-left:3px solid {color};background:#090e14;'
            f'border-radius:3px;padding:7px 10px 3px;margin-bottom:4px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:12px;font-weight:600;color:#e6edf3;'
            f'font-family:\'JetBrains Mono\',monospace">{s["title"]}</span>'
            f'<span style="font-size:9px;color:{color};letter-spacing:.1em;'
            f'background:{color}1a;padding:1px 6px;border-radius:2px">{cat}</span>'
            f'</div>'
            f'<div style="font-size:9px;color:#6e7681;font-family:\'JetBrains Mono\',monospace;'
            f'margin-top:2px">{s.get("note","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander("", expanded=False):
            st.code(s.get("code", ""), language=cat.lower() if cat in ("Python", "SQL", "Shell") else "text")
            if st.button(f"⌫ DELETE", key=f"snip_del_{sid}"):
                delete_snippet(sid)
                st.rerun()


# ── Pipeline Monitor tab ───────────────────────────────────────────────────────
@st.fragment
def render_pipeline_tab():
    section_header("◉", "PIPELINE MONITOR", color="#30d158", anim="scan",
                   subtitle="scheduler jobs · Discord health · manual trigger")

    reminder_time  = os.getenv("REMINDER_TIME",    "08:00")
    digest_time    = os.getenv("EMAIL_DIGEST_TIME", "08:00")
    webhook_url    = os.getenv("DISCORD_WEBHOOK_URL", "")
    anthropic_key  = os.getenv("ANTHROPIC_API_KEY", "")
    obsidian_key   = os.getenv("OBSIDIAN_API_KEY", "")

    # Scheduled jobs display
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
        'font-family:\'JetBrains Mono\',monospace;padding:3px 0 6px">── SCHEDULED JOBS ──</div>',
        unsafe_allow_html=True,
    )

    jobs = [
        ("Daily Reminder",   reminder_time + " daily",  bool(webhook_url),    "#00d4ff"),
        ("Email Digest",     digest_time   + " daily",  bool(webhook_url),    "#64d2ff"),
        ("Style Re-learn",   "Sunday 07:00",            True,                 "#bd00ff"),
    ]

    for job_name, schedule_str, enabled, color in jobs:
        dot = '<span style="color:#30d158">●</span>' if enabled else '<span style="color:#ff2d55">●</span>'
        st.markdown(
            f'<div style="border-left:3px solid {color};background:#090e14;'
            f'border-radius:3px;padding:6px 10px;margin-bottom:4px;'
            f'display:flex;justify-content:space-between;align-items:center;">'
            f'<div>'
            f'<div style="font-size:11px;font-weight:600;color:#e6edf3;'
            f'font-family:\'JetBrains Mono\',monospace">{job_name}</div>'
            f'<div style="font-size:9px;color:#6e7681;font-family:\'JetBrains Mono\',monospace">'
            f'⏱ {schedule_str}</div>'
            f'</div>'
            f'<div style="font-size:10px;font-family:\'JetBrains Mono\',monospace">'
            f'{dot} {"enabled" if enabled else "no webhook"}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
        'font-family:\'JetBrains Mono\',monospace;padding:3px 0 6px">── MANUAL TRIGGER ──</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶ SEND REMINDERS", use_container_width=True, key="pipe_remind"):
            try:
                tasks = get_active_tasks()
                send_all_reminders(tasks)
                st.success(f"◈ Sent {len(tasks)} reminders")
            except Exception as e:
                st.error(f"Error: {e}")
    with col2:
        if st.button("▶ EMAIL DIGEST", use_container_width=True, key="pipe_digest"):
            try:
                from modules.email_digest import run_digest
                classified = run_digest(hours=24)
                total = sum(len(v) for v in classified.values())
                send_email_digest(classified)
                st.success(f"◈ Digest sent ({total} emails)")
            except Exception as e:
                st.error(f"Error: {e}")
    with col3:
        if st.button("▶ STYLE RELEARN", use_container_width=True, key="pipe_style"):
            try:
                from modules.outlook_reader import get_sent_emails
                from modules.style_learner import learn_from_sent
                sent = get_sent_emails(limit=300)
                learn_from_sent(sent)
                st.success(f"◈ Learned from {len(sent)} emails")
            except Exception as e:
                st.error(f"Error: {e}")

    # Services health
    st.markdown("---")
    st.markdown(
        '<div style="font-size:10px;color:#3d5a6b;letter-spacing:.14em;'
        'font-family:\'JetBrains Mono\',monospace;padding:3px 0 6px">── SERVICES HEALTH ──</div>',
        unsafe_allow_html=True,
    )

    services = [
        ("Anthropic API",    bool(anthropic_key),  "ANTHROPIC_API_KEY"),
        ("Discord Webhook",  bool(webhook_url),     "DISCORD_WEBHOOK_URL"),
        ("Obsidian API",     bool(obsidian_key),    "OBSIDIAN_API_KEY"),
        ("Ollama",           bool(os.getenv("OLLAMA_BASE_URL")), "OLLAMA_BASE_URL"),
        ("JupyterLab",       st.session_state.jupyter_running,   "auto-detected"),
    ]

    for svc_name, ok, env_key in services:
        dot   = '<span style="color:#30d158;font-size:12px">●</span>' if ok else '<span style="color:#21262d;font-size:12px">●</span>'
        state = '<span style="color:#30d158">OK</span>' if ok else '<span style="color:#ff2d55">NOT SET</span>'
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:4px 8px;background:#090e14;border-radius:3px;margin-bottom:2px;">'
            f'<div style="display:flex;gap:8px;align-items:center;">'
            f'{dot} <span style="font-size:11px;color:#c9d1d9;font-family:\'JetBrains Mono\',monospace">'
            f'{svc_name}</span></div>'
            f'<div style="display:flex;gap:12px;align-items:center;">'
            f'<span style="font-size:9px;color:#3d5a6b;font-family:\'JetBrains Mono\',monospace">'
            f'{env_key}</span>'
            f'<span style="font-size:9px;font-family:\'JetBrains Mono\',monospace">{state}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # scheduler.py run hint
    st.markdown("---")
    st.markdown(
        '<div style="background:#090e14;border:1px solid #1d2733;border-radius:4px;'
        'padding:10px 14px;font-family:\'JetBrains Mono\',monospace;">'
        '<div style="font-size:9px;color:#3d5a6b;letter-spacing:.14em;margin-bottom:5px">'
        '── BACKGROUND SCHEDULER ──</div>'
        '<div style="font-size:11px;color:#6e7681">Để scheduler chạy nền, mở terminal riêng:</div>'
        '<div style="font-size:12px;color:#79c0ff;margin-top:4px">uv run python scripts/scheduler.py</div>'
        '<div style="font-size:10px;color:#3d5a6b;margin-top:4px">'
        f'reminder @ <span style="color:#00d4ff">{reminder_time}</span> · '
        f'digest @ <span style="color:#64d2ff">{digest_time}</span> · '
        'style re-learn Sunday 07:00'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Process AI chat message submitted via hidden native form
    _cai_pending = st.session_state.pop("_cai_pending_msg", None)
    if _cai_pending:
        from modules.ai_client import call_ai
        _ch = st.session_state.setdefault("cai_history", [])
        _ch.append({"role": "user", "content": _cai_pending})
        _prior = "\n".join(
            f"{"User" if m["role"] == "user" else "AI"}: {m["content"]}"
            for m in _ch[-8:]
        )
        try:
            _resp = call_ai(
                "Bạn là Chooper — AI Agent FMCG (VitaDairy). "
                "Trả lời tiếng Việt, thân thiện, business-focused, ≤5 câu. "
                "Cuối câu đề xuất 2-3 follow-up ngắn.\n\n"
                + _prior + "\n\nAI:",
                max_tokens=600,
            )
        except Exception as _e:
            _resp = f"⚠ Lỗi AI: {_e}"
        _ch.append({"role": "assistant", "content": _resp})

    render_sidebar()

    # ── Nav: search nhỏ + tab bar cùng hàng ──────────────────────────────────
    st.markdown("""<style>
/* Search bar: compact height */
div[data-testid="stTextInput"] { margin-bottom:0!important; padding-bottom:0!important; }
div[data-testid="stTextInput"] input { height:30px!important; color:#6e7681!important; }
div[data-testid="stTextInput"] input::placeholder { color:#3d5a6b!important; }
/* Tabs: tight top margin — no negative margin hack */
div[data-testid="stTabs"] { margin-top:4px!important; }
/* DATA STUDIO sub-nav pills */
div[data-testid="stRadio"] > label { display:none!important; }
div[data-testid="stRadio"] > div {
    display:flex!important; gap:6px!important;
    margin:8px 0 16px!important; flex-wrap:wrap!important;
}
div[data-testid="stRadio"] > div > label {
    background:#0f1923!important; border:1px solid #21262d!important;
    border-radius:5px!important; padding:4px 14px!important;
    font-size:11px!important; font-family:'JetBrains Mono',monospace!important;
    color:#8b949e!important; cursor:pointer!important;
    transition:all .15s!important;
}
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background:#00d4ff12!important; border-color:#00d4ff55!important;
    color:#00d4ff!important;
}
div[data-testid="stRadio"] > div > label input { display:none!important; }
</style>""", unsafe_allow_html=True)

    col_gap, col_search, col_lang = st.columns([4, 1, 1])
    with col_search:
        st.text_input("", placeholder="/ search...", key="global_search",
                      label_visibility="collapsed")
    with col_lang:
        if "lang" not in st.session_state:
            st.session_state["lang"] = "vn"
        _lang = st.session_state["lang"]
        _btn_lbl = "VN ⇄ EN" if _lang == "vn" else "EN ⇄ VN"
        if st.button(_btn_lbl, key="global_lang_toggle", use_container_width=True,
                     help="Switch Dictionary language"):
            st.session_state["lang"] = "en" if _lang == "vn" else "vn"
            st.rerun()

    # ── Main tabs ───────────────────────────────────────────────────────────────
    (tab_data, tab_tasks, tab_perf, tab_email, tab_focus,
     tab_pipeline, tab_nb, tab_dict, tab_ai, tab_settings) = st.tabs([
        "◈ DATA STUDIO",
        "⬡ TASKS",
        "◎ PERFORMANCE",
        "◉ EMAIL",
        "⏱ FOCUS",
        "◉ PIPELINE",
        "⬡ NOTEBOOK",
        "◫ DICTIONARY",
        "⬡ AI AGENT",
        "⊛ CONFIG",
    ])

    with tab_data:
        render_data_studio_tab()
    with tab_tasks:
        render_tasks_tab()
    with tab_perf:
        render_analytics_tab()
    with tab_email:
        render_email_tab()
    with tab_focus:
        render_focus_tab()
    with tab_pipeline:
        render_pipeline_tab()
    with tab_nb:
        render_notebook_tab()
    with tab_dict:
        from modules.dictionary import render_dictionary_tab
        render_dictionary_tab()
    with tab_ai:
        from modules.ai_agent import render_ai_agent
        render_ai_agent()
    with tab_settings:
        render_settings_tab()

    # ── Floating AI chat widget — always in DOM, JS toggles via localStorage (no reload)
    import html as _html, streamlit.components.v1 as _comp
    _history = st.session_state.get("cai_history", [])
    _has_msgs = len(_history) > 0

    # Build message HTML from Python session state (injected server-side)
    _msgs_html = '<div class="cm-a"><div class="cm-lbl">CHOOPER</div>Xin chào! Tôi là Chooper — AI Agent FMCG của bạn. Cần giúp gì không? ◈</div>'
    for m in _history:
        _rc = "u" if m["role"] == "user" else "a"
        _lbl = "YOU" if m["role"] == "user" else "CHOOPER"
        _msgs_html += (
            f'<div class="cm-{_rc}"><div class="cm-lbl">{_lbl}</div>'
            f'<div>{_html.escape(m["content"])}</div></div>'
        )

    # JS (localStorage) controls visibility — Python never forces panel open
    _init_disp = "none"

    st.markdown(f"""
<style>
/* Floating toggle button */
#cai-btn{{position:fixed;bottom:28px;right:28px;z-index:99999;
    width:52px;height:52px;border-radius:50%;
    background:linear-gradient(135deg,#7c3aed,#bd00ff);
    border:2px solid rgba(189,0,255,.6);font-size:24px;
    box-shadow:0 4px 24px rgba(189,0,255,.45);cursor:pointer;
    display:flex;align-items:center;justify-content:center;
    transition:transform .2s,box-shadow .2s;user-select:none;}}
#cai-btn:hover{{transform:scale(1.12);box-shadow:0 6px 32px rgba(189,0,255,.7);}}
/* Chat panel */
#cai{{position:fixed;bottom:20px;right:20px;z-index:99998;
    width:390px;height:560px;
    background:#161b22;
    border:2px solid #00d4ff55;
    border-radius:14px;
    box-shadow:0 8px 48px rgba(0,0,0,.85),0 0 0 1px #00d4ff22;
    display:{_init_disp};flex-direction:column;overflow:hidden;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
#cai-hdr{{background:#0d1117;padding:10px 14px;flex-shrink:0;
    display:flex;align-items:center;justify-content:space-between;
    border-bottom:1px solid #00d4ff22;}}
#cai-t1{{font-size:13px;font-weight:700;color:#e6edf3;letter-spacing:.06em;}}
#cai-t2{{font-size:9px;color:#00d4ff;letter-spacing:.12em;margin-top:2px;}}
#cai-x{{background:none;border:none;color:#8b949e;cursor:pointer;
    font-size:20px;line-height:1;padding:2px 7px;border-radius:5px;}}
#cai-x:hover{{background:rgba(255,255,255,.08);color:#e6edf3;}}
#cai-msgs{{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;}}
#cai-msgs::-webkit-scrollbar{{width:3px;}}
#cai-msgs::-webkit-scrollbar-thumb{{background:#30363d;border-radius:2px;}}
.cm-u{{background:#1d2733;border:1px solid #21262d;border-radius:10px 10px 2px 10px;
    padding:8px 12px;font-size:12px;color:#e6edf3;align-self:flex-end;
    max-width:85%;line-height:1.5;word-break:break-word;}}
.cm-a{{background:#0f1923;border:1px solid #1e3a4f;border-radius:2px 10px 10px 10px;
    padding:8px 12px;font-size:12px;color:#c9d1d9;align-self:flex-start;
    max-width:90%;line-height:1.6;white-space:pre-wrap;word-break:break-word;}}
.cm-lbl{{font-size:8px;letter-spacing:.1em;margin-bottom:3px;}}
.cm-u .cm-lbl{{color:#3d5a6b;}}.cm-a .cm-lbl{{color:#00d4ff;}}
#cai-sending{{display:none;align-self:flex-start;padding:6px 12px;
    background:#0f1923;border:1px solid #1e3a4f;border-radius:2px 10px 10px 10px;
    color:#5a7a8a;font-size:11px;}}
#cai-ftr{{padding:10px;border-top:1px solid #21262d;background:#0d1117;
    display:flex;gap:8px;align-items:flex-end;flex-shrink:0;}}
#cai-inp{{flex:1;background:#161b22;border:1px solid #30363d;border-radius:8px;
    padding:8px 10px;color:#e6edf3;font-size:12px;resize:none;outline:none;
    min-height:36px;max-height:100px;font-family:inherit;line-height:1.4;}}
#cai-inp:focus{{border-color:#00d4ff66;}}
#cai-inp::placeholder{{color:#3d5a6b;}}
#cai-snd{{background:linear-gradient(135deg,#0096c7,#00d4ff);border:none;
    border-radius:8px;color:#0d1117;font-weight:700;cursor:pointer;
    padding:0 14px;font-size:16px;height:36px;flex-shrink:0;transition:opacity .15s;}}
#cai-snd:hover{{opacity:.85;}}
</style>
<div id="cai-btn" title="Chooper AI">⬡</div>
<div id="cai">
  <div id="cai-hdr">
    <div><div id="cai-t1">⬡ CHOOPER AI</div><div id="cai-t2">CLAUDE · VAULT RAG · FMCG SPECIALIST</div></div>
    <button id="cai-x">×</button>
  </div>
  <div id="cai-msgs">{_msgs_html}<div id="cai-sending">▸ Đang suy nghĩ...</div></div>
  <div id="cai-ftr">
    <textarea id="cai-inp" placeholder="Hỏi Chooper..." rows="1"></textarea>
    <button id="cai-snd">▶</button>
  </div>
</div>""", unsafe_allow_html=True)

    _comp_ret = _comp.html("""<script>
(function(){
// Signal Streamlit this component is ready (enables setComponentValue)
window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:componentReady",apiVersion:1},"*");
var doc=window.parent.document;
function $(i){return doc.getElementById(i);}

// Restore open/close state from localStorage
var btn=$("cai-btn");
if(localStorage.getItem("cai_open")==="1"){
    var w=$("cai");if(w){w.style.display="flex";var m=$("cai-msgs");if(m)m.scrollTop=m.scrollHeight;}
    if(btn)btn.style.display="none";
}

// Toggle open/close
if(btn)btn.onclick=function(){
    var w=$("cai");if(!w)return;
    var open=w.style.display==="flex";
    w.style.display=open?"none":"flex";
    btn.style.display=open?"flex":"none";
    localStorage.setItem("cai_open",open?"0":"1");
    if(!open){var m=$("cai-msgs");if(m)m.scrollTop=m.scrollHeight;}
};

// Close button
var x=$("cai-x");
if(x)x.onclick=function(e){
    e.stopPropagation();
    var w=$("cai");if(w)w.style.display="none";
    if(btn)btn.style.display="flex";
    localStorage.setItem("cai_open","0");
};

// Send message
var inp=$("cai-inp"),snd=$("cai-snd");
function send(){
    if(!inp)return;
    var t=inp.value.trim();if(!t)return;
    var msgs=$("cai-msgs");
    var d=doc.createElement("div");d.className="cm-u";
    var l=doc.createElement("div");l.className="cm-lbl";l.textContent="YOU";
    var c=doc.createElement("div");c.textContent=t;
    d.appendChild(l);d.appendChild(c);
    var sending=$("cai-sending");
    if(sending){msgs.insertBefore(d,sending);sending.style.display="block";}
    else msgs.appendChild(d);
    msgs.scrollTop=msgs.scrollHeight;
    inp.value="";inp.style.height="auto";
    // Send to Python via Streamlit component postMessage protocol
    window.parent.postMessage({isStreamlitMessage:true,type:"streamlit:setComponentValue",args:{value:{text:t,ts:Date.now()},dataType:"json"}},"*");
}
if(snd)snd.onclick=send;
if(inp){
    inp.addEventListener("keydown",function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}});
    inp.addEventListener("input",function(){this.style.height="auto";this.style.height=Math.min(this.scrollHeight,100)+"px";});
}
var msgs=$("cai-msgs");if(msgs)msgs.scrollTop=msgs.scrollHeight;
})();
</script>""", height=1)

    # ── Process component value sent via Streamlit postMessage protocol ──
    if isinstance(_comp_ret, dict) and _comp_ret.get("text"):
        if _comp_ret.get("ts", 0) > st.session_state.get("_cai_last_ts", 0):
            st.session_state["_cai_last_ts"] = _comp_ret["ts"]
            st.session_state["_cai_pending_msg"] = _comp_ret["text"]
            st.rerun()


main()
