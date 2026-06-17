#!/usr/bin/env python3
"""Write stack RSS snapshot to data/.dev/ram_snapshot.json (Release 7.0)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / ".dev" / "ram_snapshot.json"


def _stack_rss_mb() -> dict:
    try:
        import psutil
    except ImportError:
        return {"stack_rss_mb": None, "available": False, "error": "psutil not installed"}

    proc = psutil.Process()
    total = proc.memory_info().rss
    processes = [
        {
            "pid": proc.pid,
            "name": proc.name(),
            "rss_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
        }
    ]
    for child in proc.children(recursive=True):
        try:
            cm = child.memory_info()
            total += cm.rss
            processes.append(
                {
                    "pid": child.pid,
                    "name": child.name(),
                    "rss_mb": round(cm.rss / (1024 * 1024), 1),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    stack_mb = round(total / (1024 * 1024), 1)
    return {
        "stack_rss_mb": stack_mb,
        "process_count": len(processes),
        "processes": processes[:12],
        "available": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture stack RSS for ops panel")
    parser.add_argument("--json", action="store_true", help="Print payload to stdout")
    args = parser.parse_args()

    payload = _stack_rss_mb()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        rss = payload.get("stack_rss_mb")
        if rss is not None:
            print(f"RAM snapshot: {rss} MB -> {OUT}")
        else:
            print(f"RAM snapshot unavailable -> {OUT}", file=sys.stderr)
    return 0 if payload.get("available") else 1


if __name__ == "__main__":
    raise SystemExit(main())
