#!/usr/bin/env python3
"""Detect ProfitDLL install path on Windows — prints PROFIT_DLL_PATH= for .env."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integrations.profit_dll_detect import detect_profit_dll, env_line_for_best_match


def main() -> int:
    as_json = "--json" in sys.argv
    result = detect_profit_dll()

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        if result["found"]:
            print(f"Found {result['count']} candidate(s):")
            for path in result["candidates"]:
                print(f"  {path}")
            line = env_line_for_best_match()
            if line:
                print(f"\n{line}")
        else:
            print("ProfitDLL not found in common Nelogica paths.")
            print("Install ProfitChart or set PROFIT_DLL_PATH manually in .env")

    return 0 if result["found"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
