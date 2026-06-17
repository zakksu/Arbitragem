#!/usr/bin/env python3
"""Lightweight tracemalloc peak for one PatternScanner cycle (Release 7.0).

Usage:
  python scripts/bench_memory.py
  python scripts/bench_memory.py --low-ram --json
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("PROFIT_BRIDGE_ENABLED", "false")
os.environ.setdefault("OLLAMA_ENABLED", "false")
os.environ.setdefault("SCANNER_OLLAMA_ON_SCAN", "false")
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("SCANNER_MODE", "custom")
os.environ.setdefault("SCANNER_SYMBOLS", "PETR4,VALE3")
os.environ.setdefault("SCANNER_INCLUDE_BOVA_OPTIONS", "false")


def _run_scan_cycle(*, low_ram: bool) -> dict:
    if low_ram:
        os.environ["LOW_RAM_MODE"] = "true"
    else:
        os.environ.pop("LOW_RAM_MODE", None)

    from src.config import get_settings
    from src.models import get_session_factory, init_db
    from src.services.scanner import PatternScanner

    get_settings.cache_clear()
    symbols = get_settings().scanner_symbol_list

    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]

    init_db()
    session = get_session_factory()()
    try:

        class _NoOllama:
            def is_available(self) -> bool:
                return False

        import src.services.scanner as scanner_mod

        scanner_mod.get_ollama_client = lambda: _NoOllama()  # type: ignore[method-assign]
        results = PatternScanner(session).run_daily_scan()
        session.rollback()
    finally:
        session.close()

    current, peak = tracemalloc.get_traced_memory()
    snap = tracemalloc.take_snapshot()
    tracemalloc.stop()

    top = [str(stat) for stat in snap.statistics("lineno")[:5]]

    return {
        "low_ram_mode": low_ram,
        "symbol_count": len(symbols),
        "scan_results": len(results),
        "tracemalloc_current_kb": round(current / 1024, 1),
        "tracemalloc_peak_kb": round(peak / 1024, 1),
        "tracemalloc_delta_peak_kb": round((peak - baseline) / 1024, 1),
        "top_allocations": top,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark scanner cycle memory (tracemalloc)")
    parser.add_argument("--low-ram", action="store_true", help="Set LOW_RAM_MODE=true")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    payload = _run_scan_cycle(low_ram=args.low_ram)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        mode = "low-ram" if payload["low_ram_mode"] else "normal"
        print(
            f"Scanner cycle ({mode}): {payload['scan_results']} results, "
            f"peak {payload['tracemalloc_peak_kb']} KB "
            f"(delta {payload['tracemalloc_delta_peak_kb']} KB)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
