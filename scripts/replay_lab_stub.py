#!/usr/bin/env python3
"""Replay lab sandbox CLI stub — POST /api/v1/replay/run."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description="Start ProfitChart replay sandbox job")
    p.add_argument("--symbol", default="PETR4")
    p.add_argument("--strategy", default="scalp_default")
    p.add_argument("--speed", type=float, default=10.0)
    p.add_argument("--api", default="http://localhost:8000/api/v1")
    args = p.parse_args()

    payload = json.dumps(
        {
            "symbol": args.symbol,
            "strategy": args.strategy,
            "speed": args.speed,
            "mode": "sandbox",
        }
    ).encode()
    req = urllib.request.Request(
        f"{args.api.rstrip('/')}/replay/run",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(resp.read().decode())
            return 0
    except Exception as exc:
        print(f"Replay stub failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
