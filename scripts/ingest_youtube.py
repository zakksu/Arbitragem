#!/usr/bin/env python3
"""Ingest YouTube transcript (.vtt / .txt) into knowledge FTS (10.0)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest transcript into knowledge.db")
    parser.add_argument("--path", required=True, help=".vtt or .txt transcript file")
    parser.add_argument("--title", default="", help="Display title")
    parser.add_argument("--symbol", default="PETR4")
    parser.add_argument("--tags", default="youtube,transcript")
    args = parser.parse_args()

    from src.services.knowledge.store import ingest_file

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    result = ingest_file(
        Path(args.path),
        tags=tags,
        symbols=[args.symbol.strip().upper()],
    )
    print(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
