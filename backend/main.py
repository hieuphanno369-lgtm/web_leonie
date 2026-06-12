from contextlib import asynccontextmanager
from pathlib import Path
import os
from dotenv import dotenv_values
_env = dotenv_values(Path(__file__).parent.parent / ".env", encoding="utf-8")
for _k, _v in _env.items():
    if _v:  # chỉ set nếu .env có giá trị (override Windows env rỗng)
        os.environ[_k] = _v

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import create_tables
from routers.tasks          import router as tasks_router
from routers.eda            import router as eda_router
from routers.wip            import router as wip_router
from routers.discord_notify import router as discord_router
from routers.kpi            import router as kpi_router
from routers.performance    import router as performance_router
from routers.ml             import router as ml_router
from routers.notes          import router as notes_router
from routers.sql_sandbox    import router as sql_router
from routers.snippets       import router as snippets_router
from routers.fabric_views   import router as fabric_router
from routers.action_plan    import router as action_plan_router
from routers.automation     import router as automation_router

APP_VERSION = "1.0.0"
DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Leonie API", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5177", "http://localhost:5178", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes (prefix /api) ─────────────────────────────────────────────────
app.include_router(tasks_router,       prefix="/api")
app.include_router(eda_router,         prefix="/api")
app.include_router(wip_router,         prefix="/api")
app.include_router(discord_router,     prefix="/api")
app.include_router(kpi_router,         prefix="/api")
app.include_router(performance_router, prefix="/api")
app.include_router(ml_router,          prefix="/api")
app.include_router(notes_router,       prefix="/api")
app.include_router(sql_router,         prefix="/api")
app.include_router(snippets_router,    prefix="/api")
app.include_router(fabric_router,      prefix="/api")
app.include_router(action_plan_router, prefix="/api")
app.include_router(automation_router,  prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


# ── Serve built frontend (production) ────────────────────────────────────────
if DIST.exists():
    # Static assets (JS, CSS, images…)
    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="assets")

    # SPA catch-all — return index.html for any unknown path
    @app.get("/{full_path:path}")
    async def serve_spa(_full_path: str = ""):
        return FileResponse(str(DIST / "index.html"))
