#!/usr/bin/env python3
"""Trigger one paper motor cycle via API (avoids SQLite lock with running API)."""

from __future__ import annotations

import json
import sys

import httpx

from src.config import get_settings


def main() -> int:
    base = get_settings().api_base_url.rstrip("/")
    try:
        r = httpx.post(f"{base}/api/v1/orchestrator/run", timeout=120.0)
        r.raise_for_status()
        out = r.json()
        print(json.dumps(out, indent=2, default=str))
        actions = (out.get("autonomy") or {}).get("actions") or []
        if any(a.get("action") == "execute" for a in actions):
            return 0
        if out.get("skipped"):
            print(f"Skipped: {out['skipped']}", file=sys.stderr)
            return 2
        return 1
    except httpx.HTTPError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
