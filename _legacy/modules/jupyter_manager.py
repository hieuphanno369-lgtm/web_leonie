import subprocess
import sys
import os
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

_jupyter_proc: subprocess.Popen | None = None
_jupyter_port: int = 8888
_jupyter_token: str = "chooper_notebook_2025"

NOTEBOOK_DIR = Path(os.getenv("NOTEBOOK_DIR", r"D:\ai_notebooks"))


def _ensure_notebook_dir() -> Path:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    return NOTEBOOK_DIR


def is_running() -> bool:
    global _jupyter_proc
    if _jupyter_proc is None:
        return False
    return _jupyter_proc.poll() is None


def get_url() -> str:
    return f"http://localhost:{_jupyter_port}/lab?token={_jupyter_token}"


def start() -> tuple[bool, str]:
    global _jupyter_proc, _jupyter_port, _jupyter_token

    if is_running():
        return True, get_url()

    nb_dir = _ensure_notebook_dir()

    # find free port starting from 8888
    import socket
    port = _jupyter_port
    for candidate in range(8888, 8920):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", candidate)) != 0:
                port = candidate
                break
    _jupyter_port = port

    # Locate jupyter executable — prefer project venv, fall back to system PATH
    import shutil
    _project_root = Path(__file__).parent.parent
    _venv_jupyter = _project_root / ".venv" / "Scripts" / "jupyter.exe"
    if _venv_jupyter.exists():
        jupyter_exe = str(_venv_jupyter)
    else:
        jupyter_exe = shutil.which("jupyter")
    if not jupyter_exe:
        return False, "Không tìm thấy jupyter trong PATH. Cài bằng: uv add jupyterlab"

    # JupyterLab 4.x uses ServerApp; allow iframe embedding
    tornado_settings = (
        '{"headers":{"Content-Security-Policy":"frame-ancestors * \'self\'","X-Frame-Options":""}}'
    )
    cmd = [
        jupyter_exe, "lab",
        "--no-browser",
        f"--port={port}",
        f"--ServerApp.token={_jupyter_token}",
        "--ServerApp.password=",
        "--ServerApp.allow_origin=*",
        "--ServerApp.allow_remote_access=True",
        "--ServerApp.disable_check_xsrf=True",
        f"--ServerApp.tornado_settings={tornado_settings}",
        f"--ServerApp.root_dir={nb_dir}",
    ]

    try:
        _jupyter_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except FileNotFoundError:
        return False, f"Không khởi động được jupyter tại: {jupyter_exe}"

    # wait up to 12s for server to be ready
    url = get_url()
    for _ in range(24):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://localhost:{port}/api", timeout=1)
            return True, url
        except Exception:
            pass

    if is_running():
        return True, url
    return False, "Jupyter không khởi động được — kiểm tra log."


def stop():
    global _jupyter_proc
    if _jupyter_proc and _jupyter_proc.poll() is None:
        _jupyter_proc.terminate()
        _jupyter_proc = None
