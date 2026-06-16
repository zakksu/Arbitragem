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
  python scripts/dev.py go-live          # fastest public URLs (trycloudflare)
  python scripts/dev.py tunnel quick     # instant HTTPS, no DNS setup
  python scripts/dev.py tunnel start   # expose trading/dashboard hostnames
  python scripts/dev.py tunnel status  # tunnel process + config status

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

    _auto_detect_profit_dll(env_file)

    print("[dev] Setup complete.")
    return 0


def _auto_detect_profit_dll(env_path: Path) -> None:
    """On Windows, write PROFIT_DLL_PATH when a single unambiguous DLL is found."""
    if sys.platform != "win32":
        return
    sys.path.insert(0, str(ROOT))
    from src.integrations.profit_dll_detect import detect_profit_dll

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key = line.split("=", 1)[0].strip()
            if key == "PROFIT_DLL_PATH":
                val = line.split("=", 1)[1].strip().strip('"')
                if val and Path(val).exists():
                    return

    result = detect_profit_dll()
    if not result.get("recommended"):
        print("[dev] ProfitDLL not auto-detected — run scripts/detect_profit_dll.py")
        return

    line = f"PROFIT_DLL_PATH={result['recommended']}"
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "PROFIT_DLL_PATH=" in text:
        lines = []
        for row in text.splitlines():
            if row.startswith("PROFIT_DLL_PATH="):
                lines.append(line)
            else:
                lines.append(row)
        text = "\n".join(lines)
        if not text.endswith("\n"):
            text += "\n"
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += f"{line}\n"
    env_path.write_text(text, encoding="utf-8")
    os.environ["PROFIT_DLL_PATH"] = result["recommended"]
    print(f"[dev] Auto-detected ProfitDLL → {result['recommended']}")


def _maybe_start_profitchart() -> None:
    """Optional ProfitChart co-start when PROFITCHART_EXE is set (4.0-rc)."""
    if sys.platform != "win32":
        return
    sys.path.insert(0, str(ROOT))
    from src.config import get_settings

    settings = get_settings()
    if not settings.profitchart_co_start:
        return
    exe = settings.profitchart_exe.strip() or os.getenv("PROFITCHART_EXE", "").strip()
    env_path = ROOT / ".env"
    if not exe and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PROFITCHART_EXE="):
                exe = line.split("=", 1)[1].strip().strip('"')
                break
    if not exe:
        return
    path = Path(exe)
    if not path.is_file():
        print(f"[dev] PROFITCHART_EXE not found: {exe}")
        return
    try:
        subprocess.Popen(
            [str(path)],
            cwd=str(path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[dev] Launched ProfitChart: {path.name}")
    except OSError as exc:
        print(f"[dev] ProfitChart launch failed: {exc}")


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
    env_path = ROOT / ".env"
    if env_path.exists():
        _auto_detect_profit_dll(env_path)
    dll_path = os.getenv("PROFIT_DLL_PATH", "").strip()
    if not dll_path and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("PROFIT_DLL_PATH="):
                dll_path = line.split("=", 1)[1].strip().strip('"')
                break
    if dll_path and Path(dll_path).exists() and sys.platform == "win32":
        bridge_script = "profit_dll_bridge.py"
        print(f"[dev] PROFIT_DLL_PATH set — using {bridge_script}")
    else:
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


def _start_test_worker() -> int | None:
    if os.getenv("ARBITRAGEM_BG_TESTS", "1") == "0":
        return None
    worker = ROOT / "scripts" / "test_worker.py"
    if not worker.exists():
        return None
    py = str(_python())
    print("[dev] Starting background test worker (non-blocking)...")
    proc = _start_process("test_worker", [py, str(worker)], "test_worker.log")
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
    _maybe_start_profitchart()

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
        "test_worker_pid": _start_test_worker() or 0,
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
            "test_worker": state.get("test_worker_pid", 0),
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
    for key in ("api_pid", "dashboard_pid", "profit_bridge_pid", "test_worker_pid"):
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


def cmd_tunnel(args: argparse.Namespace) -> int:
    """Delegate to scripts/tunnel.py (Cloudflare Tunnel)."""
    tunnel_script = ROOT / "scripts" / "tunnel.py"
    if not tunnel_script.exists():
        print("[dev] tunnel.py missing", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(tunnel_script), args.tunnel_command]
    if args.tunnel_command == "setup":
        if getattr(args, "tunnel_run", False):
            cmd.append("--run")
        if getattr(args, "tunnel_skip_login", False):
            cmd.append("--skip-login")
        if getattr(args, "tunnel_skip_create", False):
            cmd.append("--skip-create")
    elif args.tunnel_command == "start" and getattr(args, "tunnel_no_wait", False):
        cmd.append("--no-wait-healthy")
    elif args.tunnel_command == "quick" and getattr(args, "tunnel_no_wait", False):
        cmd.append("--no-wait-healthy")
    elif args.tunnel_command == "hostname":
        cmd.append(getattr(args, "tunnel_hostname", ""))
        if getattr(args, "tunnel_dashboard", None):
            cmd.extend(["--dashboard", args.tunnel_dashboard])
        if getattr(args, "tunnel_run", False):
            cmd.append("--run")
    elif args.tunnel_command == "status" and getattr(args, "json", False):
        cmd.append("--json")
    result = subprocess.run(cmd, cwd=ROOT)
    return int(result.returncode)


def cmd_go_live(args: argparse.Namespace) -> int:
    """Start stack + instant trycloudflare tunnel — fastest public access."""
    ns = argparse.Namespace(wait=True, timeout=DEFAULT_TIMEOUT, json=False, open=getattr(args, "open", False))
    if cmd_start(ns) != 0:
        return 1
    time.sleep(2)
    tunnel_ns = argparse.Namespace(tunnel_command="quick", tunnel_no_wait=False)
    rc = cmd_tunnel(tunnel_ns)
    if rc == 0 and getattr(args, "open", False):
        q = json.loads(
            (ROOT / "data" / ".dev" / "quick_tunnel.json").read_text(encoding="utf-8")
        ) if (ROOT / "data" / ".dev" / "quick_tunnel.json").exists() else {}
        if q.get("dashboard_url"):
            webbrowser.open(q["dashboard_url"])
    return rc


def cmd_paper_today(_: argparse.Namespace) -> int:
    if not _http_ok(API_URL):
        print("[dev] API not running. Starting stack...")
        ns = argparse.Namespace(wait=True, timeout=DEFAULT_TIMEOUT, json=False, open=False)
        if cmd_start(ns) != 0:
            return 1
    py = _python()
    env = _env()
    env["PAPER_TRADING_MODE"] = "true"
    print("[dev] Running paper_trade_today...")
    result = subprocess.run([str(py), str(ROOT / "scripts" / "paper_trade_today.py")], env=env, cwd=ROOT)
    return result.returncode


def cmd_test_worker(args: argparse.Namespace) -> int:
    worker = ROOT / "scripts" / "test_worker.py"
    py = str(_python())
    cmd = [py, str(worker)]
    if getattr(args, "once", False):
        cmd.append("--once")
    if getattr(args, "interval", None):
        cmd.extend(["--interval", str(args.interval)])
    result = subprocess.run(cmd, cwd=ROOT, env=_env())
    return int(result.returncode)


def cmd_launch(_: argparse.Namespace) -> int:
    """One-shot local launcher (setup + start + sleeves)."""
    py = _python()
    result = subprocess.run([str(py), str(ROOT / "scripts" / "launch.py")], cwd=ROOT)
    return int(result.returncode)


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

    p_paper = sub.add_parser("paper-today", help="Scan + paper confirm/execute top ideas")
    p_paper.set_defaults(func=cmd_paper_today)

    p_launch = sub.add_parser("launch", help="Local launcher — setup, start, open sleeves")
    p_launch.set_defaults(func=cmd_launch)

    p_tw = sub.add_parser("test-worker", help="Run background pytest worker")
    p_tw.add_argument("--once", action="store_true", help="Run pytest once and exit")
    p_tw.add_argument("--interval", type=int, default=300, help="Loop interval when not --once")
    p_tw.set_defaults(func=cmd_test_worker)

    p_tunnel = sub.add_parser(
        "tunnel",
        help="Cloudflare Tunnel — public HTTPS from this PC (see docs/cloudflare_tunnel.md)",
    )
    tunnel_sub = p_tunnel.add_subparsers(dest="tunnel_command", required=True)

    p_tsetup = tunnel_sub.add_parser("setup", help="Login, create tunnel, write config/cloudflared/config.yml")
    p_tsetup.add_argument("--run", dest="tunnel_run", action="store_true", help="Run cloudflared login/create/route")
    p_tsetup.add_argument("--skip-login", dest="tunnel_skip_login", action="store_true")
    p_tsetup.add_argument("--skip-create", dest="tunnel_skip_create", action="store_true")
    p_tsetup.set_defaults(func=cmd_tunnel, tunnel_command="setup")

    p_tstart = tunnel_sub.add_parser("start", help="Start cloudflared (stack should be healthy)")
    p_tstart.add_argument("--no-wait-healthy", dest="tunnel_no_wait", action="store_true")
    p_tstart.set_defaults(func=cmd_tunnel, tunnel_command="start")

    p_tstop = tunnel_sub.add_parser("stop", help="Stop cloudflared process")
    p_tstop.set_defaults(func=cmd_tunnel, tunnel_command="stop")

    p_tstatus = tunnel_sub.add_parser("status", help="Tunnel install, config, and process status")
    p_tstatus.add_argument("--json", action="store_true")
    p_tstatus.set_defaults(func=cmd_tunnel, tunnel_command="status")

    p_tinstall = tunnel_sub.add_parser("install", help="Download cloudflared into tools/ (no winget)")
    p_tinstall.set_defaults(func=cmd_tunnel, tunnel_command="install")

    p_tdns = tunnel_sub.add_parser("dns-fix", help="Print GoDaddy/Cloudflare DNS fix steps")
    p_tdns.set_defaults(func=cmd_tunnel, tunnel_command="dns-fix")

    p_tquick = tunnel_sub.add_parser("quick", help="Instant trycloudflare.com URLs (no DNS)")
    p_tquick.add_argument("--no-wait-healthy", dest="tunnel_no_wait", action="store_true")
    p_tquick.set_defaults(func=cmd_tunnel, tunnel_command="quick")

    p_thost = tunnel_sub.add_parser("hostname", help="Set FreeDomain/custom hostnames in .env")
    p_thost.add_argument("tunnel_hostname", help="e.g. arbitragem.work.gd")
    p_thost.add_argument("--dashboard", dest="tunnel_dashboard", help="dashboard subdomain hostname")
    p_thost.add_argument("--run", dest="tunnel_run", action="store_true")
    p_thost.set_defaults(func=cmd_tunnel, tunnel_command="hostname")

    p_live = sub.add_parser("go-live", help="Start stack + instant public URLs (trycloudflare)")
    p_live.add_argument("--open", action="store_true", help="Open dashboard in browser")
    p_live.set_defaults(func=cmd_go_live)

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
