#!/usr/bin/env python3
"""Cloudflare Tunnel helper for Arbitragem (Windows-first).

Used by `python scripts/dev.py tunnel <setup|start|stop|status>`.

  python scripts/tunnel.py setup    # login/create tunnel hints + write config
  python scripts/tunnel.py start    # run cloudflared (stack should be healthy)
  python scripts/tunnel.py stop
  python scripts/tunnel.py status [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config" / "cloudflared"
CONFIG_FILE = CONFIG_DIR / "config.yml"
CONFIG_EXAMPLE = ROOT / "docker" / "cloudflared" / "config.yml.example"
TUNNEL_STATE = ROOT / "data" / ".dev" / "tunnel.json"
LOG_DIR = ROOT / "logs"
TUNNEL_LOG = LOG_DIR / "cloudflared.log"
QUICK_TUNNEL_STATE = ROOT / "data" / ".dev" / "quick_tunnel.json"
QUICK_API_LOG = LOG_DIR / "cloudflared-quick-api.log"
QUICK_DASH_LOG = LOG_DIR / "cloudflared-quick-dashboard.log"
TRYCF_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)

DEFAULT_TUNNEL_NAME = "arbitragem"
DEFAULT_TRADING_HOST = "trading.dmconsultoria.seg.br"
DEFAULT_DASHBOARD_HOST = "dashboard.dmconsultoria.seg.br"

API_HEALTH = "http://localhost:8000/api/v1/health/live"
DASHBOARD_HEALTH = "http://localhost:8501/_stcore/health"


def _cloudflared_home() -> Path:
    return Path(os.environ.get("USERPROFILE", Path.home())) / ".cloudflared"


def find_cloudflared() -> str | None:
    bundled = ROOT / "tools" / "cloudflared.exe"
    if bundled.is_file():
        return str(bundled)
    return shutil.which("cloudflared")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
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
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _load_env_file() -> dict[str, str]:
    out: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        return out
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip().strip('"')
    return out


def _tunnel_name() -> str:
    return os.getenv("CLOUDFLARE_TUNNEL_NAME") or _load_env_file().get("CLOUDFLARE_TUNNEL_NAME") or DEFAULT_TUNNEL_NAME


def _trading_hostname() -> str:
    return (
        os.getenv("CLOUDFLARE_TUNNEL_HOSTNAME")
        or _load_env_file().get("CLOUDFLARE_TUNNEL_HOSTNAME")
        or _load_env_file().get("DOMAIN")
        or DEFAULT_TRADING_HOST
    )


def _dashboard_hostname() -> str:
    return (
        os.getenv("CLOUDFLARE_DASHBOARD_HOSTNAME")
        or _load_env_file().get("CLOUDFLARE_DASHBOARD_HOSTNAME")
        or DEFAULT_DASHBOARD_HOST
    )


def print_install_hint() -> None:
    print("[tunnel] cloudflared not found on PATH or in tools/.")
    print("[tunnel] Install on Windows:")
    print("  python scripts/dev.py tunnel install")
    print("  winget install --id Cloudflare.cloudflared")
    print("  — or download: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")


def cmd_install(_args: argparse.Namespace) -> int:
    """Download cloudflared into tools/ (no admin, works when winget is missing)."""
    tools_dir = ROOT / "tools"
    dest = tools_dir / "cloudflared.exe"
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    if dest.is_file():
        print(f"[tunnel] Already present: {dest}")
        try:
            subprocess.run([str(dest), "--version"], check=False)
        except OSError:
            print("[tunnel] File locked — wait a moment and retry.")
        return 0
    tools_dir.mkdir(parents=True, exist_ok=True)
    print(f"[tunnel] Downloading cloudflared → {dest}")
    try:
        import urllib.request

        urllib.request.urlretrieve(url, dest)
    except Exception as exc:
        print(f"[tunnel] Download failed: {exc}", file=sys.stderr)
        return 1
    print(f"[tunnel] Installed: {dest}")
    subprocess.run([str(dest), "--version"], check=False)
    return 0


def _list_tunnel_credentials() -> list[Path]:
    home = _cloudflared_home()
    if not home.is_dir():
        return []
    return sorted(home.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def _tunnel_id_from_credentials(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return str(data.get("TunnelID") or data.get("tunnel_id") or "").strip() or None


def _pick_credentials_file(tunnel_name: str) -> Path | None:
    """Prefer credentials JSON whose tunnel name matches, else newest file."""
    files = _list_tunnel_credentials()
    if not files:
        return None
    cf = find_cloudflared()
    if cf:
        try:
            result = subprocess.run(
                [cf, "tunnel", "list", "--output", "json"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                tunnels = json.loads(result.stdout)
                for row in tunnels:
                    if str(row.get("name", "")).lower() == tunnel_name.lower():
                        tid = str(row.get("id", ""))
                        for f in files:
                            if _tunnel_id_from_credentials(f) == tid:
                                return f
        except (json.JSONDecodeError, OSError):
            pass
    return files[0]


def _render_config(credentials_file: Path) -> str:
    cred = str(credentials_file).replace("/", "\\") if sys.platform == "win32" else str(credentials_file)
    trading = _trading_hostname()
    dashboard = _dashboard_hostname()
    name = _tunnel_name()
    return f"""# Generated by scripts/tunnel.py — edit hostnames in .env if needed
tunnel: {name}
credentials-file: {cred}

ingress:
  - hostname: {trading}
    service: http://localhost:8000
  - hostname: {dashboard}
    service: http://localhost:8501
  - service: http_status:404
"""


def _write_config(credentials_file: Path) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(_render_config(credentials_file), encoding="utf-8")
    print(f"[tunnel] Wrote {CONFIG_FILE}")


def _load_tunnel_state() -> dict[str, Any]:
    if not TUNNEL_STATE.exists():
        return {}
    try:
        return json.loads(TUNNEL_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_tunnel_state(state: dict[str, Any]) -> None:
    TUNNEL_STATE.parent.mkdir(parents=True, exist_ok=True)
    TUNNEL_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _run_cloudflared(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    cf = find_cloudflared()
    if not cf:
        raise RuntimeError("cloudflared not found")
    return subprocess.run([cf, *args], capture_output=True, text=True, check=check)


def _ensure_tunnel_auth_reminder() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        print("[tunnel] No .env — copy .env.tunnel.example values before sharing URLs.")
        return
    text = env_path.read_text(encoding="utf-8")
    changed = False
    for key in ("BOARD_AUTH_ENABLED", "DASHBOARD_AUTH_ENABLED"):
        if re.search(rf"^{key}=", text, re.MULTILINE):
            if re.search(rf"^{key}=false", text, re.MULTILINE | re.IGNORECASE):
                text = re.sub(rf"^{key}=false.*$", f"{key}=true", text, flags=re.MULTILINE | re.IGNORECASE)
                changed = True
        else:
            text = text.rstrip() + f"\n{key}=true\n"
            changed = True
    for key in ("BOARD_PASSWORD", "DASHBOARD_PASSWORD"):
        if not re.search(rf"^{key}=.+", text, re.MULTILINE):
            text = text.rstrip() + f"\n{key}=CHANGE_ME_BEFORE_SHARING\n"
            changed = True
    if "CLOUDFLARE_TUNNEL_HOSTNAME=" not in text:
        text = text.rstrip() + f"\nCLOUDFLARE_TUNNEL_HOSTNAME={_trading_hostname()}\n"
        changed = True
    if "DOMAIN=trading.yourdomain.com" in text:
        text = text.replace("DOMAIN=trading.yourdomain.com", f"DOMAIN={_trading_hostname()}")
        changed = True
    if changed:
        env_path.write_text(text, encoding="utf-8")
        print("[tunnel] Updated .env: enabled BOARD/DASHBOARD auth flags (set strong passwords!).")
    else:
        print("[tunnel] .env auth flags look OK — verify passwords before sharing URLs.")


def cmd_setup(args: argparse.Namespace) -> int:
    cf = find_cloudflared()
    if not cf:
        print_install_hint()
        return 1

    name = _tunnel_name()
    print(f"[tunnel] Using tunnel name: {name}")
    print(f"[tunnel] Trading host: {_trading_hostname()}")
    print(f"[tunnel] Dashboard host: {_dashboard_hostname()}")

    if not args.skip_login:
        print("\n[tunnel] Step 1 — Cloudflare login (browser opens once):")
        print(f"  {cf} tunnel login")
        if args.run:
            subprocess.run([cf, "tunnel", "login"], check=False)

    cred = _pick_credentials_file(name)
    if not cred and not args.skip_create:
        print("\n[tunnel] Step 2 — Create tunnel:")
        print(f"  {cf} tunnel create {name}")
        if args.run:
            result = subprocess.run([cf, "tunnel", "create", name], capture_output=True, text=True, check=False)
            print(result.stdout or result.stderr)
        cred = _pick_credentials_file(name)

    if not cred:
        print("\n[tunnel] No credentials JSON in %USERPROFILE%\\.cloudflared\\")
        print(f"[tunnel] Run: {cf} tunnel create {name}")
        print("[tunnel] Then re-run: python scripts/dev.py tunnel setup")
        return 1

    _write_config(cred)
    tunnel_id = _tunnel_id_from_credentials(cred) or "TUNNEL_UUID"
    trading = _trading_hostname()
    dashboard = _dashboard_hostname()

    print("\n[tunnel] Step 3 — DNS (Cloudflare-managed zone):")
    print(f"  {cf} tunnel route dns {name} {trading}")
    print(f"  {cf} tunnel route dns {name} {dashboard}")
    if args.run:
        subprocess.run([cf, "tunnel", "route", "dns", name, trading], check=False)
        subprocess.run([cf, "tunnel", "route", "dns", name, dashboard], check=False)

    print("\n[tunnel] Step 3 (alt) — GoDaddy partial DNS:")
    print(f"  CNAME {trading.split('.')[0]} -> {tunnel_id}.cfargotunnel.com")
    print(f"  CNAME {dashboard.split('.')[0]} -> {tunnel_id}.cfargotunnel.com")
    print("  (Or move nameservers to Cloudflare and use route dns above.)")

    _ensure_tunnel_auth_reminder()
    print("\n[tunnel] Setup complete. Start stack + tunnel:")
    print("  python scripts/dev.py start --wait")
    print("  python scripts/dev.py tunnel start")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    cf = find_cloudflared()
    if not cf:
        print_install_hint()
        return 1

    if not CONFIG_FILE.exists():
        print(f"[tunnel] Missing {CONFIG_FILE}")
        print("[tunnel] Run: python scripts/dev.py tunnel setup")
        return 1

    state = _load_tunnel_state()
    pid = int(state.get("pid", 0) or 0)
    if pid and _pid_alive(pid):
        print(f"[tunnel] Already running (PID {pid})")
        return 0

    if args.require_healthy:
        if not _http_ok(API_HEALTH) or not _http_ok(DASHBOARD_HEALTH):
            print("[tunnel] API or dashboard not healthy on localhost.")
            print("[tunnel] Run: python scripts/dev.py start --wait")
            return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = open(TUNNEL_LOG, "a", encoding="utf-8")
    log_file.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_file.flush()

    kwargs: dict[str, Any] = {
        "cwd": ROOT,
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [cf, "tunnel", "--config", str(CONFIG_FILE), "run"],
        **kwargs,
    )
    _save_tunnel_state({"pid": proc.pid, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})

    print(f"[tunnel] Started cloudflared (PID {proc.pid})")
    print(f"[tunnel] Log: {TUNNEL_LOG}")
    print(f"[tunnel] Public: https://{_trading_hostname()}/board")
    print(f"[tunnel] Dashboard: https://{_dashboard_hostname()}")
    return 0


def _load_quick_state() -> dict[str, Any]:
    if not QUICK_TUNNEL_STATE.exists():
        return {}
    try:
        return json.loads(QUICK_TUNNEL_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_quick_state(state: dict[str, Any]) -> None:
    QUICK_TUNNEL_STATE.parent.mkdir(parents=True, exist_ok=True)
    QUICK_TUNNEL_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _spawn_quick_tunnel(cf: str, local_url: str, log_path: Path) -> subprocess.Popen[Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    log_file = open(log_path, "a", encoding="utf-8")
    log_file.write(f"\n--- quick {time.strftime('%Y-%m-%d %H:%M:%S')} {local_url} ---\n")
    log_file.flush()
    kwargs: dict[str, Any] = {
        "cwd": ROOT,
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen([cf, "tunnel", "--url", local_url], **kwargs)


def _wait_trycloudflare_url(log_path: Path, timeout: float = 60.0) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.is_file():
            matches = TRYCF_URL_RE.findall(log_path.read_text(encoding="utf-8", errors="replace"))
            if matches:
                return matches[-1]
        time.sleep(1)
    return None


def cmd_quick(args: argparse.Namespace) -> int:
    """Instant public HTTPS via trycloudflare.com — no DNS, no login. Best for urgent go-live."""
    cf = find_cloudflared()
    if not cf:
        print_install_hint()
        return 1

    if args.require_healthy:
        if not _http_ok(API_HEALTH) or not _http_ok(DASHBOARD_HEALTH):
            print("[tunnel] API or dashboard not healthy on localhost.")
            print("[tunnel] Run: python scripts/dev.py start --wait")
            return 2

    qstate = _load_quick_state()
    for key in ("api_pid", "dashboard_pid"):
        pid = int(qstate.get(key, 0) or 0)
        if pid and _pid_alive(pid):
            print(f"[tunnel] Quick tunnel already running ({key} PID {pid})")
            if qstate.get("api_url"):
                print(f"[tunnel] API+Board:  {qstate['api_url']}/board")
            if qstate.get("dashboard_url"):
                print(f"[tunnel] Dashboard:  {qstate['dashboard_url']}")
            return 0

    print("[tunnel] Starting quick tunnels (trycloudflare.com)...")
    api_proc = _spawn_quick_tunnel(cf, "http://localhost:8000", QUICK_API_LOG)
    dash_proc = _spawn_quick_tunnel(cf, "http://localhost:8501", QUICK_DASH_LOG)

    api_url = _wait_trycloudflare_url(QUICK_API_LOG)
    dash_url = _wait_trycloudflare_url(QUICK_DASH_LOG)

    state = {
        "api_pid": api_proc.pid,
        "dashboard_pid": dash_proc.pid,
        "api_url": api_url,
        "dashboard_url": dash_url,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "quick",
    }
    _save_quick_state(state)

    if not api_url or not dash_url:
        print("[tunnel] URLs not ready yet — check logs:")
        print(f"  {QUICK_API_LOG}")
        print(f"  {QUICK_DASH_LOG}")
        return 1

    print("\n[tunnel] LIVE (quick mode — URLs change each restart):\n")
    print(f"  API + Blackboard: {api_url}/board")
    print(f"  Dashboard:        {dash_url}")
    print("\n[tunnel] Stop: python scripts/dev.py tunnel stop")
    return 0


def cmd_hostname(args: argparse.Namespace) -> int:
    """Point named tunnel at new hostnames (e.g. freedomain.one work.gd). Updates .env + config."""
    cf = find_cloudflared()
    if not cf:
        print_install_hint()
        return 1

    trading = args.trading.strip().lower()
    dashboard = (args.dashboard or f"dashboard.{trading.split('.', 1)[-1]}").strip().lower()
    if "." not in trading:
        print("[tunnel] trading must be a full hostname (e.g. arbitragem.work.gd)")
        return 1

    env_path = ROOT / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    keys = {
        "CLOUDFLARE_TUNNEL_HOSTNAME": trading,
        "CLOUDFLARE_DASHBOARD_HOSTNAME": dashboard,
        "DOMAIN": trading,
    }
    for key, val in keys.items():
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={val}"
                found = True
                break
        if not found:
            lines.append(f"{key}={val}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cred = _pick_credentials_file(_tunnel_name())
    if cred:
        _write_config(cred)
    name = _tunnel_name()

    if args.run:
        subprocess.run([cf, "tunnel", "route", "dns", name, trading], check=False)
        subprocess.run([cf, "tunnel", "route", "dns", name, dashboard], check=False)

    uuid = _tunnel_uuid() or "TUNNEL_UUID"
    print(f"[tunnel] Hostnames set in .env:")
    print(f"  trading:   {trading}")
    print(f"  dashboard: {dashboard}")
    print(f"\n[tunnel] FreeDomain.one — add CNAME at https://freedomain.one/Direct.sv?cmd=userDNSList")
    print(f"  trading    -> {uuid}.cfargotunnel.com")
    print(f"  dashboard  -> {uuid}.cfargotunnel.com")
    print("\n[tunnel] Then: python scripts/dev.py tunnel start")
    return 0


def cmd_stop(_: argparse.Namespace) -> int:
    state = _load_tunnel_state()
    pid = int(state.get("pid", 0) or 0)
    if pid and _pid_alive(pid):
        print(f"[tunnel] Stopping named tunnel PID {pid}...")
        _kill_pid(pid)
    if TUNNEL_STATE.exists():
        TUNNEL_STATE.unlink()

    qstate = _load_quick_state()
    for key in ("api_pid", "dashboard_pid"):
        qpid = int(qstate.get(key, 0) or 0)
        if qpid and _pid_alive(qpid):
            print(f"[tunnel] Stopping quick tunnel {key} PID {qpid}...")
            _kill_pid(qpid)
    if QUICK_TUNNEL_STATE.exists():
        QUICK_TUNNEL_STATE.unlink()

    print("[tunnel] Stopped.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cf = find_cloudflared()
    state = _load_tunnel_state()
    pid = int(state.get("pid", 0) or 0)
    running = pid > 0 and _pid_alive(pid)
    qstate = _load_quick_state()
    q_api = int(qstate.get("api_pid", 0) or 0)
    q_dash = int(qstate.get("dashboard_pid", 0) or 0)
    quick_running = (q_api > 0 and _pid_alive(q_api)) or (q_dash > 0 and _pid_alive(q_dash))

    data: dict[str, Any] = {
        "cloudflared_installed": bool(cf),
        "cloudflared_path": cf,
        "config_exists": CONFIG_FILE.exists(),
        "config_path": str(CONFIG_FILE),
        "running": running,
        "pid": pid if running else 0,
        "quick_running": quick_running,
        "quick_urls": {
            "api": qstate.get("api_url"),
            "board": f"{qstate['api_url']}/board" if qstate.get("api_url") else None,
            "dashboard": qstate.get("dashboard_url"),
        }
        if quick_running
        else None,
        "trading_hostname": _trading_hostname(),
        "dashboard_hostname": _dashboard_hostname(),
        "urls": {
            "trading": f"https://{_trading_hostname()}",
            "board": f"https://{_trading_hostname()}/board",
            "dashboard": f"https://{_dashboard_hostname()}",
        },
        "log": str(TUNNEL_LOG),
        "started_at": state.get("started_at"),
    }
    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print(f"cloudflared: {'installed' if cf else 'NOT FOUND'}")
    print(f"config:      {'OK' if CONFIG_FILE.exists() else 'missing (run tunnel setup)'}")
    print(f"process:     {'running PID ' + str(pid) if running else 'stopped'}")
    if quick_running and qstate.get("api_url"):
        print(f"quick:       {qstate.get('api_url')}/board")
        print(f"  dashboard: {qstate.get('dashboard_url')}")
    elif running:
        print(f"  trading:   https://{_trading_hostname()}")
        print(f"  dashboard: https://{_dashboard_hostname()}")
    return 0 if cf else 1


def _tunnel_uuid() -> str | None:
    if CONFIG_FILE.is_file():
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("credentials-file:"):
                cred = Path(line.split(":", 1)[1].strip().strip('"'))
                if cred.suffix == ".json":
                    return cred.stem
    for cred in _list_tunnel_credentials():
        tid = _tunnel_id_from_credentials(cred)
        if tid:
            return tid
    return None


def cmd_dns_fix(_: argparse.Namespace) -> int:
    """Print GoDaddy / Cloudflare DNS fix steps (wrong CNAME target or hostname typo)."""
    uuid = _tunnel_uuid()
    if not uuid:
        print("[tunnel] No tunnel UUID — run: python scripts/dev.py tunnel setup --run")
        return 1
    target = f"{uuid}.cfargotunnel.com"
    trading = _trading_hostname()
    dashboard = _dashboard_hostname()
    print("[tunnel] DNS fix — your GoDaddy records must match this tunnel:\n")
    print(f"  Tunnel UUID: {uuid}")
    print(f"  CNAME target: {target}\n")
    print("OPTION A (recommended): Cloudflare nameservers")
    print("  1. Cloudflare dashboard -> dmconsultoria.seg.br -> Overview -> copy 2 nameservers")
    print("  2. GoDaddy -> Dominio -> Servidores de nome -> Alterar -> Colar NS da Cloudflare")
    print("  3. Wait 30-60 min (banner 'alteracoes em andamento' is normal)\n")
    print("OPTION B: Fix CNAMEs at GoDaddy (keep ns73/ns74.domaincontrol.com)")
    print("  URL: https://dcc.godaddy.com/control/dnsmanagement?domainName=dmconsultoria.seg.br")
    print("  - DELETE record 'tracing' (typo — must be 'trading')")
    print("  - DELETE wrong target *.cloud.com (not cfargotunnel.com)")
    print(f"  - ADD CNAME  trading    -> {target}")
    print(f"  - EDIT CNAME dashboard  -> {target}")
    print(f"\n  Hostnames: {trading} , {dashboard}")
    print("\nVerify:")
    print("  nslookup trading.dmconsultoria.seg.br ns73.domaincontrol.com")
    print("  python scripts/dev.py tunnel status --json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Arbitragem Cloudflare Tunnel")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="Login/create tunnel + write config/cloudflared/config.yml")
    p_setup.add_argument("--run", action="store_true", help="Run cloudflared login/create/route commands")
    p_setup.add_argument("--skip-login", action="store_true")
    p_setup.add_argument("--skip-create", action="store_true")
    p_setup.set_defaults(func=cmd_setup)

    p_start = sub.add_parser("start", help="Start cloudflared with project config")
    p_start.add_argument("--no-wait-healthy", action="store_true", help="Skip localhost health check")
    p_start.set_defaults(func=cmd_start, require_healthy=True)

    p_stop = sub.add_parser("stop", help="Stop cloudflared process")
    p_stop.set_defaults(func=cmd_stop)

    p_status = sub.add_parser("status", help="Tunnel install/config/process status")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_install = sub.add_parser("install", help="Download cloudflared into tools/ (no winget needed)")
    p_install.set_defaults(func=cmd_install)

    p_dns = sub.add_parser("dns-fix", help="Print GoDaddy/Cloudflare DNS correction steps")
    p_dns.set_defaults(func=cmd_dns_fix)

    p_quick = sub.add_parser("quick", help="Instant trycloudflare.com URLs (no DNS — urgent go-live)")
    p_quick.add_argument("--no-wait-healthy", action="store_true")
    p_quick.set_defaults(func=cmd_quick, require_healthy=True)

    p_host = sub.add_parser("hostname", help="Set custom hostnames (e.g. freedomain.one) in .env")
    p_host.add_argument("trading", help="Full hostname e.g. arbitragem.work.gd")
    p_host.add_argument("--dashboard", help="Dashboard hostname (default: dashboard.<domain>)")
    p_host.add_argument("--run", action="store_true", help="Run cloudflared tunnel route dns")
    p_host.set_defaults(func=cmd_hostname)

    args = parser.parse_args(argv)
    if args.command == "start" and getattr(args, "no_wait_healthy", False):
        args.require_healthy = False
    if args.command == "quick" and getattr(args, "no_wait_healthy", False):
        args.require_healthy = False
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"[tunnel] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
