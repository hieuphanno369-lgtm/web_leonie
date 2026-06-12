# Leonie — Project Guide

Personal "Work Hub": **React (Vite) frontend + FastAPI backend**. Single-user
desktop-style web app for tasks, analytics, ML/forecast, SQL and automation.

> The old Streamlit app + its `modules/` now live in **`_legacy/`** (kept for
> reference, NOT run). Don't edit `_legacy/` when working on the live app.

## Parent context
→ Global rules + ON LOAD: `D:\claude-workspace\CLAUDE.md`
→ Skills: `00_Claude_Skills/SKILLS_INDEX.md`
→ Output doc/analysis: `07_Outputs/Ad-hoc/` hoặc `Personal/`

---

## Run

```powershell
python run.py          # starts BOTH servers + opens Edge (recommended)
```

`run.py` launches the Vite dev server (5177) and uvicorn (8000) together and
opens the app in Edge. To run the halves separately:

```powershell
# Backend (FastAPI, uv-managed) — http://localhost:8000  (API docs: /docs)
cd backend ; uv run uvicorn main:app --reload --port 8000

# Frontend (dev, hot-reload) — http://localhost:5177
cd frontend ; npm run dev

# Frontend (production build → served by backend at :8000)
cd frontend ; npm run build      # = tsc -b && vite build  → frontend/dist
```

**Tests**

```powershell
cd backend ; uv run pytest -q          # backend tests (backend/tests/)
.venv\Scripts\python.exe -m pytest tests/ -v   # legacy root tests (tests/)
```

## Architecture

- **Frontend** (`frontend/`): React 19 · Vite 6 · TypeScript ~5.7 · TailwindCSS
  3.4 · Zustand 5 (module-level stores) · react-router-dom 7 · recharts ·
  CodeMirror (SQL editor) · lucide-react. ML Studio / SQL Sandbox queries run on
  **DuckDB** in the backend (`routers/ml.py`, `routers/sql_sandbox.py`).
- **Backend** (`backend/`): FastAPI (`main:app`) on uvicorn :8000, dependencies
  managed by **uv** (`pyproject.toml` + `uv.lock`). All API routes under `/api`;
  `create_tables()` (SQLite via `database.py`) runs on startup. In production it
  also serves the built `frontend/dist` (mounts `/assets`, SPA catch-all returns
  `index.html`). Loads repo-root `.env` (only non-empty values override env).

## Module Map — Frontend (`frontend/src/`)

| Path | Responsibility |
|------|----------------|
| `App.tsx` | Routes + `<AppShell>`; `*` catch-all → `pages/NotFound.tsx` (friendly 404) |
| `components/layout/Sidebar.tsx` | Nav: HOME · WORK · ANALYTICS · SQL SANDBOX |
| `pages/Dashboard.tsx` | Landing / overview |
| `pages/work/*` | TaskManager, EdaTracker, WipBuilder, QuickNotes, ActionPlan, DiscordNotify |
| `pages/analytics/*` | KpiTracker, **MlStudio** (stats/charts/forecast/cohort), Performance |
| `pages/data/*` | SqlSandbox, SnippetLibrary, FabricViews, Automation |
| `components/{ml,automation,sql,action_plan}/` | Per-feature UI panels |
| `stores/` | Zustand stores (e.g. `mlStudioStore` — survives navigation) |
| `api/` | axios clients per feature · `types.ts` shared types |

## Module Map — Backend (`backend/`)

| Path | Responsibility |
|------|----------------|
| `main.py` | FastAPI app, router wiring (`/api`), CORS, static-serve `frontend/dist` |
| `database.py` | SQLite engine + `create_tables()` |
| `routers/` | `tasks · eda · wip · notes · discord_notify · kpi · performance · ml · sql_sandbox · snippets · fabric_views · action_plan · automation` |
| `routers/ml.py` | ML/forecast endpoints + AI helper (see AI Priority) |
| `automation/` | REST/Salesforce → DuckDB jobs: `models · runner · codegen · sources/` |

## Key Paths

| Path | Notes |
|------|-------|
| `data/` | `tasks.json`, `ml_sessions/`, `snippets.json`, `sql_snippets.json`, … |
| `_legacy/` | Old Streamlit app + `modules/` — reference only, NOT run |
| `docs/superpowers/{specs,plans}/` | Dated design + plan docs per feature |
| `docs/dictionary/content/{vn,en}/` | In-app Help/glossary content (not yet wired into nav) |
| `docs/GUIDE.md` | Non-technical end-user usage guide |
| `.env` | Secrets (see `.env.example`) — never commit real values |
| `D:\claude-workspace` | Obsidian vault root |

## AI Priority
`backend/routers/ml.py`: Claude API (`ANTHROPIC_API_KEY`, model
`claude-haiku-4-5-20251001`) → Ollama fallback (`OLLAMA_BASE_URL`,
`OLLAMA_MODEL`) → fail gracefully.
