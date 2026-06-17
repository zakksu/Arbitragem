#!/usr/bin/env python3
"""Measure peak RSS for core imports + golden path evaluate (Release 7.0).

Writes data/.dev/ram_benchmark.json. Target: scanner-loop equivalent <500 MB peak.
"""

from __future__ import annotations

import argparse
import json
import sys
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / ".dev" / "ram_benchmark.json"
TARGET_MB = 500


def _rss_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
    except ImportError:
        return None


def _run_benchmark() -> dict:
    tracemalloc.start()
    rss_start = _rss_mb()

    import src.config  # noqa: F401
    import src.integrations.profit_bridge  # noqa: F401
    import src.services.enriched_watchlist  # noqa: F401
    import src.services.golden_path  # noqa: F401
    import src.services.scanner  # noqa: F401
    from src.config import get_settings
    from src.models import get_session_factory, init_db
    from src.services.golden_path import evaluate_golden_path

    rss_after_imports = _rss_mb()

    init_db()
    session = get_session_factory()()
    try:
        evaluate_golden_path(session)
    finally:
        session.close()

    rss_peak = _rss_mb()
    _, tracemalloc_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    tracemalloc_peak_mb = round(tracemalloc_peak / (1024 * 1024), 1)

    peak = max(v for v in (rss_start, rss_after_imports, rss_peak, tracemalloc_peak_mb) if v)
    over_target = peak > TARGET_MB if peak is not None else None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "low_ram_enabled": get_settings().low_ram_enabled,
        "rss_start_mb": rss_start,
        "rss_after_imports_mb": rss_after_imports,
        "rss_after_evaluate_mb": rss_peak,
        "tracemalloc_peak_mb": tracemalloc_peak_mb,
        "peak_mb": peak,
        "target_mb": TARGET_MB,
        "over_target": over_target,
        "note": (
            f"Peak {peak} MB exceeds {TARGET_MB} MB scanner-loop target — enable LOW_RAM_MODE."
            if over_target
            else f"Peak {peak} MB within {TARGET_MB} MB scanner-loop target."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark peak RSS for core stack")
    parser.add_argument("--json", action="store_true", help="Print payload to stdout")
    args = parser.parse_args()

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    payload = _run_benchmark()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload["note"])
        print(f"Wrote {OUT}")
    return 1 if payload.get("over_target") else 0


if __name__ == "__main__":
    raise SystemExit(main())
