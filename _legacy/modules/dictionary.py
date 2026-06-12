# modules/dictionary.py
"""
DICTIONARY TAB — Full HTML/CSS/JS wiki via st.components.v1.html().
Content comes from modules/dictionary_data.SECTIONS.
App Guide sections are loaded from docs/dictionary/content/vn/*.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_CONTENT_DIR = Path(__file__).parent.parent / "docs/dictionary/content/vn"

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:#0d1117;color:#e6edf3;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px}
#app{display:flex;flex-direction:column;height:100%}
/* Search */
#search-row{display:flex;align-items:center;gap:10px;padding:10px 14px;
  border-bottom:1px solid #21262d;flex-shrink:0}
#search-input{flex:1;background:#161b22;border:1px solid #30363d;border-radius:6px;
  padding:6px 12px;color:#e6edf3;font-size:12px;outline:none;
  font-family:'JetBrains Mono',monospace}
#search-input::placeholder{color:#6e7681}
#search-input:focus{border-color:#00d4ff}
#search-count{font-size:11px;color:#6e7681;font-family:'JetBrains Mono',monospace;
  white-space:nowrap;min-width:60px;text-align:right}
/* Columns */
#main{display:flex;flex:1;overflow:hidden}
#col-tree{width:18%;min-width:130px;border-right:1px solid #21262d;
  overflow-y:auto;padding:12px 6px;flex-shrink:0}
#col-list{width:22%;min-width:150px;border-right:1px solid #21262d;
  overflow-y:auto;padding:10px 6px;flex-shrink:0}
#col-detail{flex:1;overflow-y:auto;padding:20px 24px}
/* Scrollbar */
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:2px}
/* Category buttons */
.cat-btn{display:flex;align-items:center;gap:8px;width:100%;padding:8px 10px;
  background:transparent;border:none;border-radius:6px;cursor:pointer;
  color:#8b949e;font-size:12px;text-align:left;transition:background .15s,color .15s}
.cat-btn:hover{background:rgba(255,255,255,.05);color:#c9d1d9}
.cat-btn.active{background:rgba(0,212,255,.1);color:#00d4ff}
.cat-icon{font-size:15px;flex-shrink:0;width:22px;text-align:center}
.cat-count{margin-left:auto;font-size:10px;background:#21262d;
  padding:1px 7px;border-radius:8px;color:#6e7681}
.cat-btn.active .cat-count{background:rgba(0,212,255,.15);color:#00d4ff}
/* Method list */
.group-label{font-size:9px;font-weight:700;text-transform:uppercase;
  letter-spacing:.1em;color:#6e7681;padding:10px 10px 4px;
  font-family:'JetBrains Mono',monospace}
.method-btn{display:block;width:100%;padding:7px 10px;background:transparent;
  border:none;border-left:2px solid transparent;border-radius:0 5px 5px 0;
  cursor:pointer;text-align:left;transition:background .15s;margin-bottom:1px}
.method-btn:hover{background:rgba(255,255,255,.05)}
.method-btn.active{background:rgba(0,212,255,.08);border-left-color:#00d4ff}
.m-row{display:flex;align-items:center;gap:6px}
.m-icon{font-size:13px;flex-shrink:0}
.m-title{font-size:12px;color:#c9d1d9}
.method-btn.active .m-title{color:#00d4ff}
.m-sub{font-size:10px;color:#6e7681;margin-top:2px;padding-left:19px}
/* Detail — Structured Cards */
.method-heading{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.method-icon-box{width:40px;height:40px;border-radius:8px;
  background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.2);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;flex-shrink:0}
.method-name{font-size:18px;font-weight:700;color:#e6edf3}
.method-subtitle{font-size:12px;color:#8b949e;margin-top:2px}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.tag{font-size:10px;padding:2px 9px;border-radius:10px}
.tag-stat{background:rgba(0,212,255,.1);color:#00d4ff;border:1px solid rgba(0,212,255,.2)}
.tag-ml{background:rgba(63,185,80,.1);color:#3fb950;border:1px solid rgba(63,185,80,.2)}
.tag-cluster{background:rgba(163,113,247,.1);color:#a371f7;border:1px solid rgba(163,113,247,.2)}
.tag-ts{background:rgba(230,134,42,.1);color:#e6862a;border:1px solid rgba(230,134,42,.2)}
.tag-guide{background:rgba(139,148,158,.1);color:#8b949e;border:1px solid rgba(139,148,158,.2)}
.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.info-card{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 12px}
.info-label{font-size:9px;text-transform:uppercase;letter-spacing:.08em;
  color:#6e7681;font-weight:700;margin-bottom:4px;
  font-family:'JetBrains Mono',monospace}
.info-val{font-size:12px;color:#c9d1d9;line-height:1.5}
.info-val code{background:#21262d;padding:1px 5px;border-radius:3px;
  font-family:'JetBrains Mono',monospace;font-size:10px;color:#79c0ff}
.fmcg-block{background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.12);
  border-left:3px solid #00d4ff;border-radius:0 6px 6px 0;
  padding:12px 14px;margin-bottom:10px}
.fmcg-eyebrow{font-size:9px;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;color:#00d4ff;margin-bottom:5px;
  font-family:'JetBrains Mono',monospace}
.fmcg-case{font-size:12px;color:#c9d1d9;line-height:1.6}
.fmcg-result{font-size:11px;color:#8b949e;margin-top:5px;font-style:italic}
.value-block{background:rgba(35,134,54,.07);border:1px solid rgba(35,134,54,.2);
  border-radius:6px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start}
.value-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.value-label{font-size:9px;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;color:#3fb950;margin-bottom:3px;
  font-family:'JetBrains Mono',monospace}
.value-text{font-size:12px;color:#c9d1d9;line-height:1.5}
/* Detail — Prose (App Guide) */
.prose{font-size:13px;line-height:1.7;color:#c9d1d9;max-width:720px}
.prose h1{font-size:20px;color:#e6edf3;margin:0 0 12px;font-weight:700}
.prose h2{font-size:16px;color:#e6edf3;margin:20px 0 8px;font-weight:600}
.prose h3{font-size:14px;color:#e6edf3;margin:16px 0 6px;font-weight:600}
.prose p{margin-bottom:10px}
.prose code{background:#21262d;padding:2px 6px;border-radius:3px;
  font-family:'JetBrains Mono',monospace;font-size:11px;color:#79c0ff}
.prose pre{background:#161b22;border:1px solid #21262d;border-radius:6px;
  padding:14px;overflow-x:auto;margin-bottom:12px}
.prose pre code{background:none;padding:0;font-size:12px;color:#e6edf3}
.prose table{border-collapse:collapse;width:100%;margin-bottom:12px;font-size:12px}
.prose th{text-align:left;padding:6px 10px;border-bottom:2px solid #21262d;
  color:#8b949e;font-size:11px;text-transform:uppercase}
.prose td{padding:6px 10px;border-bottom:1px solid #161b22}
.prose ul,.prose ol{margin:0 0 10px 20px}
.prose li{margin-bottom:4px}
.prose blockquote{border-left:3px solid #30363d;padding-left:12px;
  color:#8b949e;margin-bottom:10px;font-style:italic}
.prose hr{border:none;border-top:1px solid #21262d;margin:16px 0}
.prose a{color:#58a6ff;text-decoration:none}
.prose strong{color:#e6edf3;font-weight:600}
/* Empty state */
.empty-state{display:flex;align-items:center;justify-content:center;
  height:200px;color:#6e7681;font-size:13px;font-style:italic}
</style>
</head>
<body>
<div id="app">
  <div id="search-row">
    <span style="color:#6e7681;font-size:14px">⌕</span>
    <input id="search-input" type="text"
           placeholder="__SEARCH_PLACEHOLDER__"
           oninput="onSearch()" autocomplete="off">
    <span id="search-count"></span>
  </div>
  <div id="main">
    <nav id="col-tree"></nav>
    <nav id="col-list"></nav>
    <main id="col-detail"></main>
  </div>
</div>
<script>
const WIKI = __WIKI_DATA__;
const LANG = "__LANG__";
const L = {
  vn: {
    results: "kết quả", notFound: "Không tìm thấy",
    emptyDetail: "Chọn một mục từ menu bên trái",
    whenToUse: "◈ Khi nào dùng", fields: "◫ Fields cần",
    output: "◎ Output", conditions: "⊟ Điều kiện",
    fmcgEyebrow: "⬡ FMCG Case — VitaDairy", bizLabel: "Business Value",
  },
  en: {
    results: "results", notFound: "Not found",
    emptyDetail: "Select an item from the left menu",
    whenToUse: "◈ When to use", fields: "◫ Fields needed",
    output: "◎ Output", conditions: "⊟ Conditions",
    fmcgEyebrow: "⬡ FMCG Case — VitaDairy", bizLabel: "Business Value",
  }
};
const T = L[LANG] || L.vn;
let _cat = 'guide', _sid = null;

const TAG_CLASS = {stat:'tag-stat',ml:'tag-ml',cluster:'tag-cluster',
                   ts:'tag-ts',guide:'tag-guide',ref:'tag-guide'};

function init() {
  const first = WIKI.sections.find(s => s.category === _cat);
  if (first) _sid = first.id;
  renderTree(); renderList(); renderDetail();
}

// ── Category tree ──
function renderTree() {
  document.getElementById('col-tree').innerHTML = WIKI.categories.map(c => {
    const n = WIKI.sections.filter(s => s.category === c.id).length;
    return `<button class="cat-btn${c.id===_cat?' active':''}" onclick="selectCat('${c.id}')">
      <span class="cat-icon">${c.icon}</span><span>${c.label}</span>
      <span class="cat-count">${n}</span></button>`;
  }).join('');
}

function selectCat(cat) {
  _cat = cat;
  document.getElementById('search-input').value = '';
  const first = WIKI.sections.find(s => s.category === cat);
  _sid = first ? first.id : null;
  renderTree(); renderList(); renderDetail();
}

// ── Method list ──
function _filtered() {
  const q = document.getElementById('search-input').value.toLowerCase().trim();
  return WIKI.sections.filter(s => {
    if (!q) return s.category === _cat;
    return s.title.toLowerCase().includes(q)
      || (s.tags||[]).some(t => t.toLowerCase().includes(q))
      || (s.subtitle||'').toLowerCase().includes(q);
  });
}

function renderList() {
  const q = document.getElementById('search-input').value.trim();
  const filtered = _filtered();
  document.getElementById('search-count').textContent =
    q ? filtered.length + ' ' + T.results : '';

  if (!filtered.length) {
    document.getElementById('col-list').innerHTML =
      `<div class="empty-state">${T.notFound}</div>`;
    return;
  }

  const grouped = {};
  filtered.forEach(s => {
    const key = q
      ? (WIKI.categories.find(c=>c.id===s.category)||{label:s.category}).label
      : (s.group||'');
    (grouped[key] = grouped[key]||[]).push(s);
  });

  let html = '';
  Object.entries(grouped).forEach(([g, secs]) => {
    if (g) html += `<div class="group-label">${g}</div>`;
    secs.forEach(s => {
      html += `<button class="method-btn${s.id===_sid?' active':''}"
        onclick="selectSection('${s.id}')">
        <div class="m-row"><span class="m-icon">${s.icon||'◈'}</span>
          <span class="m-title">${s.title}</span></div>
        ${s.subtitle?`<div class="m-sub">${s.subtitle}</div>`:''}
      </button>`;
    });
  });
  document.getElementById('col-list').innerHTML = html;
}

function selectSection(id) {
  _sid = id;
  const s = WIKI.sections.find(x=>x.id===id);
  if (s && s.category !== _cat) { _cat = s.category; renderTree(); }
  renderList(); renderDetail();
}

function onSearch() {
  renderList();
  const first = _filtered()[0];
  if (first && first.id !== _sid) { _sid = first.id; renderDetail(); }
}

// ── Detail panel ──
function renderDetail() {
  const el = document.getElementById('col-detail');
  if (!_sid) {
    el.innerHTML = `<div class="empty-state">${T.emptyDetail}</div>`;
    return;
  }
  const s = WIKI.sections.find(x=>x.id===_sid);
  if (!s) { el.innerHTML = ''; return; }
  el.innerHTML = s.md_file ? renderProse(s) : renderCards(s);
  el.scrollTop = 0;
}

function renderCards(s) {
  const tc = TAG_CLASS[s.category]||'tag-stat';
  const tags = (s.tags||[]).map(t=>`<span class="tag ${tc}">${t}</span>`).join('');
  const fieldsHtml = (s.fields||'—').replace(/`([^`]+)`/g,'<code>$1</code>');
  return `<div class="method-heading">
    <div class="method-icon-box">${s.icon||'◈'}</div>
    <div><div class="method-name">${s.title}</div>
      ${s.subtitle?`<div class="method-subtitle">${s.subtitle}</div>`:''}</div>
  </div>
  <div class="tags">${tags}</div>
  <div class="info-grid">
    <div class="info-card"><div class="info-label">${T.whenToUse}</div>
      <div class="info-val">${s.when_to_use||'—'}</div></div>
    <div class="info-card"><div class="info-label">${T.fields}</div>
      <div class="info-val">${fieldsHtml}</div></div>
    <div class="info-card"><div class="info-label">${T.output}</div>
      <div class="info-val">${s.output||'—'}</div></div>
    <div class="info-card"><div class="info-label">${T.conditions}</div>
      <div class="info-val">${s.conditions||'—'}</div></div>
  </div>
  <div class="fmcg-block">
    <div class="fmcg-eyebrow">${T.fmcgEyebrow}</div>
    <div class="fmcg-case">${s.fmcg_case||'—'}</div>
    ${s.fmcg_result?`<div class="fmcg-result">→ ${s.fmcg_result}</div>`:''}
  </div>
  <div class="value-block">
    <div class="value-icon">◈</div>
    <div><div class="value-label">${T.bizLabel}</div>
      <div class="value-text">${s.business_value||'—'}</div></div>
  </div>`;
}

function renderProse(s) {
  const html = WIKI.md[s.md_file]||'<p style="color:#6e7681">Nội dung đang cập nhật...</p>';
  return `<div class="prose">${html}</div>`;
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""


def _md_to_html(text: str) -> str:
    """Convert Markdown text to HTML string."""
    import markdown
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
    )


def _load_md_files(sections: list[dict]) -> dict[str, str]:
    """
    For each section with a 'md_file' key, read the corresponding .md file
    from _CONTENT_DIR and convert to HTML.
    Returns {md_file_id: html_string}. Missing files -> empty string.
    """
    result: dict[str, str] = {}
    for s in sections:
        md_file = s.get("md_file")
        if not md_file:
            continue
        path = _CONTENT_DIR / f"{md_file}.md"
        result[md_file] = _md_to_html(path.read_text(encoding="utf-8")) if path.exists() else ""
    return result


def build_wiki_html(sections: list[dict], md_contents: dict[str, str], lang: str = "vn") -> str:
    """
    Assemble the full HTML document by injecting sections and md_contents
    into _HTML_TEMPLATE as a JS constant WIKI.
    """
    from modules.dictionary_data import CATEGORIES
    payload = json.dumps(
        {"categories": CATEGORIES, "sections": sections, "md": md_contents},
        ensure_ascii=False,
    )
    _lang = lang if lang in ("vn", "en") else "vn"
    _placeholders = {
        "vn": "Tìm kiếm... (vd: anova, xgboost, forecast)",
        "en": "Search... (e.g. anova, xgboost, forecast)",
    }
    return (
        _HTML_TEMPLATE
        .replace("__WIKI_DATA__", payload)
        .replace("__LANG__", _lang)
        .replace("__SEARCH_PLACEHOLDER__", _placeholders[_lang])
    )


def render_dictionary_tab() -> None:
    """Entry point from app.py — renders the full wiki iframe."""
    from modules.dictionary_data import SECTIONS
    lang = st.session_state.get("lang", "vn")
    md_contents = _load_md_files(SECTIONS)
    html = build_wiki_html(SECTIONS, md_contents, lang=lang)
    # height=900: inner columns scroll via CSS overflow-y:auto
    components.html(html, height=900, scrolling=False)
