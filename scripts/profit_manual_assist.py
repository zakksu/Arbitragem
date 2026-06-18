#!/usr/bin/env python3
"""Copy latest Profit Chart Trading hint + open NTSL export folder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.profit_execution_ladder import build_ladder_status, read_latest_outbox_hint


def _copy_windows(text: str) -> bool:
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value {json.dumps(text)}"],
            check=True,
            timeout=10,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> int:
    status = build_ladder_status()
    hint = read_latest_outbox_hint()
    print(f"Active mode: {status['active_mode']}")
    if status.get("automation_module_missing"):
        print(status.get("automation_hint", ""))

    if hint:
        print(f"Chart Trading hint: {hint}")
        if sys.platform == "win32" and _copy_windows(hint):
            print("Copied to clipboard.")
        else:
            print("(clipboard copy skipped)")
    else:
        print("No pending outbox hint — confirm/execute an idea first.")

    ntsl_dir = Path(status["ntsl_dir"])
    ntsl_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        import os

        os.startfile(str(ntsl_dir))  # noqa: S606
        print(f"Opened {ntsl_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
