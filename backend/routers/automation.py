import os
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from automation import store, runner, codegen
from automation.models import JobConfig, AutomationJob, RunResult

router = APIRouter(prefix="/automation", tags=["automation"])


class PreviewIn(BaseModel):
    n_rows: int = Field(100, ge=1, le=10000)


@router.get("/jobs", response_model=list[AutomationJob])
def list_jobs():
    return store.list_jobs()


@router.post("/jobs", response_model=AutomationJob)
def create_job(config: JobConfig):
    return store.create_job(config)


@router.get("/jobs/{job_id}", response_model=AutomationJob)
def get_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/jobs/{job_id}", response_model=AutomationJob)
def update_job(job_id: str, config: JobConfig):
    job = store.update_job(job_id, config)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    if not store.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.post("/jobs/{job_id}/preview")
def preview_job(job_id: str, body: PreviewIn):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return runner.preview(job, body.n_rows)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _run_bg(job_id: str) -> None:
    try:
        job = store.get_job(job_id)
        if job:
            result = runner.run(job)
            store.set_run_status(job_id, result)
    except Exception as e:
        # runner.run is contractually no-raise, but if anything in this worker
        # fails after the 'running' latch was set, clear it (best-effort) so the
        # job can't get stuck permanently un-runnable (perma-409). If the store
        # itself is the failing component, this inner attempt is simply a no-op.
        try:
            store.set_run_status(job_id, RunResult(status="error", error=str(e)))
        except Exception:
            pass


def _spawn(job_id: str) -> None:
    threading.Thread(target=_run_bg, args=(job_id,), daemon=True).start()


@router.post("/jobs/{job_id}/run")
def run_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.last_status == "running":
        raise HTTPException(status_code=409, detail="Job already running")
    store.set_running(job_id)
    _spawn(job_id)
    return {"status": "running"}


@router.get("/jobs/{job_id}/code")
def get_code(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"python": codegen.python_script(job.config),
            "sql": codegen.shape_sql_text(job.config)}


# ── Verify export path ────────────────────────────────────────────────────────

class VerifyPathIn(BaseModel):
    path: str


class VerifyPathOut(BaseModel):
    ok:          bool
    exists:      bool
    will_create: bool
    writable:    bool
    message:     str


def _is_writable(d: Path) -> bool:
    """True if we can create (and remove) a probe file inside *d*."""
    try:
        probe = d / f".__leonie_write_test_{os.getpid()}"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


@router.post("/verify-path", response_model=VerifyPathOut)
def verify_path(body: VerifyPathIn):
    """Check whether an export ``dest_dir`` is usable before a job runs.

    A non-existent directory is reported OK when its nearest existing parent is
    writable — the runner creates it on first run (``os.makedirs``).
    """
    raw = (body.path or "").strip()
    if not raw:
        return VerifyPathOut(ok=False, exists=False, will_create=False,
                             writable=False, message="Path is empty.")

    p = Path(raw)
    if p.exists():
        if not p.is_dir():
            return VerifyPathOut(ok=False, exists=True, will_create=False,
                                 writable=False,
                                 message="Path exists but is not a directory.")
        w = _is_writable(p)
        return VerifyPathOut(
            ok=w, exists=True, will_create=False, writable=w,
            message="Directory exists and is writable." if w
                    else "Directory exists but is not writable.",
        )

    parent = p
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    if not parent.exists():
        return VerifyPathOut(ok=False, exists=False, will_create=False,
                             writable=False,
                             message="Drive or root of the path does not exist.")
    w = _is_writable(parent)
    if w:
        return VerifyPathOut(
            ok=True, exists=False, will_create=True, writable=True,
            message="Directory does not exist yet; it will be created on first run.",
        )
    return VerifyPathOut(ok=False, exists=False, will_create=False, writable=False,
                         message="Directory does not exist and its parent is not writable.")
