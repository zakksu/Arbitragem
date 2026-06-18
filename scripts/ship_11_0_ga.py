#!/usr/bin/env python3
"""11.0 GA readiness checklist — archaeology, NTSL pack, motor, Phase C snapshot."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _get(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="11.0 GA software gate checklist")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    from src.models import get_session_factory, init_db
    from src.models import Trade, StoredStrategy

    init_db()
    session = get_session_factory()()
    arch_count = session.query(Trade).filter(Trade.source == "archaeology").count()
    ntsl_count = session.query(StoredStrategy).count()
    session.close()

    arch_summary = _get(f"{args.api}/api/v1/archaeology/summary?limit=5")
    phase_c = _get(f"{args.api}/api/v1/phase-c/status")
    ladder = _get(f"{args.api}/api/v1/integrations/profit/execution-ladder")
    core17 = _get(f"{args.api}/api/v1/universe/filipe-core17")

    pack_path = ROOT / "data" / ".dev" / "ntsl_pack_version.json"
    pack_ok = pack_path.is_file()

    checks = {
        "archaeology_rows_db": {"ok": arch_count >= 100, "value": arch_count, "target": ">=9000 manual"},
        "archaeology_summary_api": {"ok": arch_summary is not None, "value": arch_summary.get("total_trades") if arch_summary else 0},
        "ntsl_indexed": {"ok": ntsl_count >= 10, "value": ntsl_count, "target": ">=50 after scan"},
        "ntsl_pack_version": {"ok": pack_ok, "path": str(pack_path)},
        "core17_universe": {"ok": (core17 or {}).get("count") == 17, "value": (core17 or {}).get("count")},
        "execution_ladder": {"ok": ladder is not None, "mode": (ladder or {}).get("active_mode")},
        "phase_c": phase_c,
    }
    software_ok = all(
        c.get("ok")
        for k, c in checks.items()
        if k != "phase_c" and isinstance(c, dict) and "ok" in c
    )

    payload = {"software_gates_ok": software_ok, "checks": checks, "manual": ["Phase C sign-off", "XP P&L reconcile"]}

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"[11.0 GA] software_gates_ok={software_ok}")
        for k, c in checks.items():
            if isinstance(c, dict) and "ok" in c:
                mark = "OK" if c["ok"] else "FAIL"
                print(f"  {mark} {k}: {c}")
        if phase_c:
            print(f"  Phase C: {phase_c.get('signed_off')} — {phase_c.get('blockers', [])}")

    return 0 if software_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
