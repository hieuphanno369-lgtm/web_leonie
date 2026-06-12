"""Leonie launcher — starts frontend + backend in one terminal, auto-opens Edge."""
import subprocess
import threading
import sys
import os
import signal
import time
import urllib.request

ROOT     = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND  = os.path.join(ROOT, "backend")

FRONTEND_URL = "http://localhost:5177"
BACKEND_URL  = "http://localhost:8000"

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

processes = []


def stream(proc, prefix, color):
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            print(f"{color}{prefix}{RESET} {text}", flush=True)


def shutdown(sig=None, frame=None):
    print(f"\n{BOLD}Shutting down Leonie...{RESET}")
    for p in processes:
        p.terminate()
    sys.exit(0)


def wait_and_open_browser(url: str, timeout: int = 30):
    """Poll until the server responds, then open Edge."""
    print(f"{YELLOW}[  ] Waiting for {url} ...{RESET}", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            print(f"{GREEN}[ ✓] Server ready — opening Edge{RESET}", flush=True)
            subprocess.Popen(
                ["cmd", "/c", "start", "msedge", "--app=" + url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            time.sleep(1)
    print(f"{YELLOW}[  ] Timed out waiting for {url} — open manually{RESET}", flush=True)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

print(f"{BOLD}")
print("=" * 46)
print("  Leonie — Starting up")
print("=" * 46)
print(f"  Frontend : {FRONTEND_URL}")
print(f"  Backend  : {BACKEND_URL}")
print(f"  API Docs : {BACKEND_URL}/docs")
print("=" * 46)
print(f"  Ctrl+C to stop both servers")
print("=" * 46)
print(f"{RESET}")

fe = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=FRONTEND,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    shell=True,
)
be = subprocess.Popen(
    ["uv", "run", "uvicorn", "main:app", "--reload", "--port", "8000"],
    cwd=BACKEND,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    shell=True,
)

processes.extend([fe, be])

threading.Thread(target=stream, args=(fe, "[FE]", CYAN),  daemon=True).start()
threading.Thread(target=stream, args=(be, "[BE]", GREEN), daemon=True).start()

# Open Edge as an App (no browser chrome) once frontend is up
threading.Thread(target=wait_and_open_browser, args=(FRONTEND_URL,), daemon=True).start()

fe.wait()
be.wait()
