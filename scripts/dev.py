#!/usr/bin/env python3
"""Arbitragem dev orchestrator — full autonomous setup, start, stop, health checks.

Agents and beginners: run one command, everything else is automatic.

  python scripts/dev.py setup          # venv, deps, .env, folders, DB
  python scripts/dev.py start --wait   # start API + dashboard, wait until healthy
  python scripts/dev.py status         # human-readable status
  python scripts/dev.py status --json  # machine-readable (for agents)
  python scripts/dev.py stop           # stop background services
  python scripts/dev.py restart --wait
  python scripts/dev.py open           # open dashboard in default browser

Exit codes: 0 = success, 1 = error, 2 = services unhealthy after timeout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "data" / ".dev"
STATE_FILE = STATE_DIR / "state.json"
LOG_DIR = ROOT / "logs"
VENV_DIR = ROOT / ".venv"

API_URL = "http://localhost:8000/api/v1/health/live"
API_HEALTH_FULL = "http://localhost:8000/api/v1/health"
DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_HEALTH = "http://localhost:8501/_stcore/health"
PROFIT_BRIDGE_HEALTH = "http://localhost:9100/health"
API_PORT = 8000
DASHBOARD_PORT = 8501
PROFIT_BRIDGE_PORT = 9100

DEFAULT_TIMEOUT = 90


def _python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _pip() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["API_BASE_URL"] = "http://localhost:8000/api/v1"
    return env


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


def _find_python_launcher() -> str:
    for cmd in ("python", "python3", "py"):
        if shutil.which(cmd):
            return cmd
    raise RuntimeError("Python not found. Install Python 3.12+ from https://python.org")


def cmd_setup(_: argparse.Namespace) -> int:
    print("[dev] Setting up Arbitragem...")
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "exports" / "profit").mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    env_file = ROOT / ".env"
    if not env_file.exists():
        example = ROOT / ".env.example"
        if example.exists():
            shutil.copy(example, env_file)
            print("[dev] Created .env from .env.example")

    if not VENV_DIR.exists():
        launcher = _find_python_launcher()
        print(f"[dev] Creating virtual environment ({launcher})...")
        subprocess.run([launcher, "-m", "venv", str(VENV_DIR)], cwd=ROOT, check=True)

    py = _python()
    if not py.exists():
        raise RuntimeError(f"Virtualenv python missing: {py}")

    print("[dev] Installing dependencies...")
    subprocess.run([str(_pip()), "install", "-r", "requirements.txt"], cwd=ROOT, check=True)

    print("[dev] Initializing database...")
    subprocess.run(
        [str(py), "-c", "from src.models import init_db; init_db()"],
        cwd=ROOT,
        env=_env(),
        check=True,
    )

    print("[dev] Setup complete.")
    return 0


def _ensure_env_profit_bridge() -> None:
    """Enable local Profit bridge in process env and .env for API."""
    env_path = ROOT / ".env"
    if not env_path.exists() and (ROOT / ".env.example").exists():
        shutil.copy(ROOT / ".env.example", env_path)

    if env_path.exists():
        text = env_path.read_text(encoding="utf-8")
        if "PROFIT_BRIDGE_ENABLED=false" in text.replace(" ", "").lower():
            return
        if "PROFIT_BRIDGE_ENABLED" not in text:
            text += "\nPROFIT_BRIDGE_ENABLED=true\nPROFIT_BRIDGE_URL=http://localhost:9100\n"
            env_path.write_text(text, encoding="utf-8")

    os.environ["PROFIT_BRIDGE_ENABLED"] = "true"
    os.environ["PROFIT_BRIDGE_URL"] = "http://localhost:9100"
    os.environ["SCANNER_MODE"] = "filipe_core14"
    sys.path.insert(0, str(ROOT))
    from src.config import get_settings

    get_settings.cache_clear()


def _start_profit_bridge_if_needed() -> int | None:
    if _http_ok(PROFIT_BRIDGE_HEALTH):
        print("[dev] Profit bridge already running on :9100")
        return None
    _ensure_env_profit_bridge()
    py = str(_python())
    bridge_script = os.getenv("PROFIT_BRIDGE_SCRIPT", "profit_bridge_stub.py")
    bridge_path = ROOT / "scripts" / bridge_script
    if not bridge_path.exists():
        bridge_path = ROOT / "scripts" / "profit_bridge_stub.py"
    print(f"[dev] Starting Profit bridge ({bridge_path.name}) on port 9100...")
    proc = _start_process(
        "profit_bridge",
        [py, str(bridge_path)],
        "profit_bridge.log",
    )
    for _ in range(15):
        if _http_ok(PROFIT_BRIDGE_HEALTH):
            print("[dev] Profit bridge healthy.")
            return proc.pid
        time.sleep(0.5)
    return proc.pid


def _start_process(name: str, args: list[str], log_name: str) -> subprocess.Popen:
    log_path = LOG_DIR / log_name
    log_file = open(log_path, "a", encoding="utf-8")
    log_file.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_file.flush()
    kwargs: dict[str, Any] = {
        "cwd": ROOT,
        "env": _env(),
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(args, **kwargs)


def _wait_healthy(timeout: int) -> tuple[bool, dict[str, Any]]:
    deadline = time.time() + timeout
    status = {"api": False, "dashboard": False}
    while time.time() < deadline:
        status["api"] = _http_ok(API_URL)
        status["dashboard"] = _http_ok(DASHBOARD_HEALTH)
        if status["api"] and status["dashboard"]:
            return True, status
        time.sleep(1)
    return False, status


def cmd_start(args: argparse.Namespace) -> int:
    if not VENV_DIR.exists():
        print("[dev] No venv — running setup first...")
        cmd_setup(args)

    healthy, _ = _wait_healthy(timeout=2)
    if healthy:
        print("[dev] Services already running and healthy.")
        _print_urls()
        if args.json:
            print(json.dumps(get_status_dict(), indent=2))
        return 0

    cmd_stop(args)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    py = str(_python())

    bridge_pid = _start_profit_bridge_if_needed()

    print("[dev] Starting API on port 8000...")
    api_proc = _start_process(
        "api",
        [py, "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", str(API_PORT)],
        "api.log",
    )

    time.sleep(2)

    print("[dev] Starting dashboard on port 8501...")
    ui_proc = _start_process(
        "dashboard",
        [
            py,
            "-m",
            "streamlit",
            "run",
            "dashboard/app.py",
            "--server.port",
            str(DASHBOARD_PORT),
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        "dashboard.log",
    )

    state = {
        "api_pid": api_proc.pid,
        "dashboard_pid": ui_proc.pid,
        "profit_bridge_pid": bridge_pid or 0,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _save_state(state)

    if args.wait:
        print(f"[dev] Waiting for health (timeout {args.timeout}s)...")
        ok, health = _wait_healthy(args.timeout)
        if not ok:
            print(f"[dev] ERROR: Services not healthy: {health}", file=sys.stderr)
            print(f"[dev] Check logs: {LOG_DIR / 'api.log'}, {LOG_DIR / 'dashboard.log'}", file=sys.stderr)
            return 2
        print("[dev] All services healthy.")

    _print_urls()

    if args.json:
        print(json.dumps(get_status_dict(), indent=2))

    if args.open:
        webbrowser.open(DASHBOARD_URL)

    return 0


def _print_urls() -> None:
    print("")
    print("  Dashboard:  http://localhost:8501")
    print("  Blackboard: http://localhost:8000/board")
    print("  API docs:   http://localhost:8000/docs")
    print("  Profit:     http://localhost:9100/health")
    print("  Stop:       python scripts/dev.py stop")
    print("")


def get_status_dict() -> dict[str, Any]:
    state = _load_state()
    api_pid = state.get("api_pid", 0)
    dash_pid = state.get("dashboard_pid", 0)
    return {
        "running": {
            "api_process": _pid_alive(int(api_pid)),
            "dashboard_process": _pid_alive(int(dash_pid)),
        },
        "healthy": {
            "api": _http_ok(API_URL),
            "dashboard": _http_ok(DASHBOARD_HEALTH),
            "profit_bridge": _http_ok(PROFIT_BRIDGE_HEALTH),
        },
        "urls": {
            "dashboard": DASHBOARD_URL,
            "api_docs": "http://localhost:8000/docs",
            "api_health": API_HEALTH_FULL,
        },
        "pids": {
            "api": api_pid,
            "dashboard": dash_pid,
            "profit_bridge": state.get("profit_bridge_pid", 0),
        },
        "started_at": state.get("started_at"),
        "logs": {"api": str(LOG_DIR / "api.log"), "dashboard": str(LOG_DIR / "dashboard.log")},
    }


def cmd_status(args: argparse.Namespace) -> int:
    data = get_status_dict()
    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    h = data["healthy"]
    r = data["running"]
    icon = lambda ok: "OK" if ok else "DOWN"
    print(f"API:        {icon(h['api'])} (process: {icon(r['api_process'])})")
    print(f"Dashboard:  {icon(h['dashboard'])} (process: {icon(r['dashboard_process'])})")
    if h["api"] and h["dashboard"]:
        _print_urls()
    else:
        print("Start with: python scripts/dev.py start --wait")
    return 0 if h["api"] and h["dashboard"] else 1


def cmd_stop(_: argparse.Namespace) -> int:
    state = _load_state()
    stopped = False
    for key in ("api_pid", "dashboard_pid", "profit_bridge_pid"):
        pid = int(state.get(key, 0) or 0)
        if pid and _pid_alive(pid):
            print(f"[dev] Stopping PID {pid} ({key})...")
            _kill_pid(pid)
            stopped = True
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    if stopped:
        print("[dev] Stopped.")
    else:
        print("[dev] No managed processes running.")
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    cmd_stop(args)
    time.sleep(1)
    return cmd_start(args)


def cmd_open(_: argparse.Namespace) -> int:
    if not _http_ok(DASHBOARD_HEALTH):
        print("[dev] Dashboard not running. Starting...")
        ns = argparse.Namespace(wait=True, timeout=DEFAULT_TIMEOUT, json=False, open=True)
        return cmd_start(ns)
    webbrowser.open(DASHBOARD_URL)
    print(f"[dev] Opened {DASHBOARD_URL}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Arbitragem dev orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="Create venv, install deps, init DB")
    p_setup.set_defaults(func=cmd_setup)

    for name in ("start", "restart"):
        p = sub.add_parser(name, help="Start or restart all services")
        p.add_argument("--wait", action="store_true", help="Block until API + dashboard healthy")
        p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
        p.add_argument("--json", action="store_true", help="Print status JSON")
        p.add_argument("--open", action="store_true", help="Open dashboard in browser")
        p.set_defaults(func=cmd_restart if name == "restart" else cmd_start)

    p_status = sub.add_parser("status", help="Show service status")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_stop = sub.add_parser("stop", help="Stop background services")
    p_stop.set_defaults(func=cmd_stop)

    p_open = sub.add_parser("open", help="Open dashboard (start if needed)")
    p_open.set_defaults(func=cmd_open)

    args = parser.parse_args()
    try:
        return int(args.func(args))
    except subprocess.CalledProcessError as exc:
        print(f"[dev] Command failed: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[dev] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
