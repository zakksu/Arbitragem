#!/usr/bin/env python3
"""Archive stale Profit outbox tickets (paper backlog cleanup)."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTBOX = ROOT / "data" / "profit_outbox"
PENDING = OUTBOX / "pending"
ARCHIVE = OUTBOX / "archived"


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    moved = 0
    for path in sorted(PENDING.glob("*.json")):
        shutil.move(str(path), str(ARCHIVE / path.name))
        moved += 1

    next_order = OUTBOX / "next_order.json"
    if next_order.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.move(str(next_order), str(ARCHIVE / f"next_order_{stamp}.json"))

    summary = {"archived_pending": moved, "archived_at": datetime.now(timezone.utc).isoformat()}
    (ARCHIVE / "_last_archive.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
