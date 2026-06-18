"""Core17 options chain refresh — update strike templates from Profit bridge (A11.9)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT
from src.logging_config import get_logger

logger = get_logger(__name__)

OPTIONS_CSV = PROJECT_ROOT / "data" / "core17_options.csv"
META_PATH = PROJECT_ROOT / "data" / ".dev" / "core17_options_meta.json"


def _load_rows() -> list[dict[str, str]]:
    if not OPTIONS_CSV.is_file():
        return []
    with OPTIONS_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def refresh_core17_options(*, client: Any | None = None) -> dict[str, Any]:
    """Mark refresh attempt; verify option tickers exist in bridge quotes when available."""
    rows = _load_rows()
    if not rows:
        return {"ok": False, "reason": "csv_missing", "path": str(OPTIONS_CSV)}

    checked = 0
    live = 0
    missing: list[str] = []
    if client is None:
        try:
            from src.integrations.profit_bridge import get_profit_client

            client = get_profit_client()
        except Exception:
            client = None

    for row in rows:
        for key in ("sample_call", "sample_put"):
            sym = (row.get(key) or "").strip().upper()
            if not sym:
                continue
            checked += 1
            if not client:
                continue
            try:
                q = client.get_quote(sym)
                if q and getattr(q, "last", None):
                    live += 1
                else:
                    missing.append(sym)
            except Exception:
                missing.append(sym)

    meta = {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "tickers_checked": checked,
        "tickers_live": live,
        "missing_sample": missing[:10],
        "source": "profit_bridge" if client else "offline",
        "note": "Strike templates in core17_options.csv — manual weekly refresh in Profit when bridge offline",
    }
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("core17_options_refresh", **{k: meta[k] for k in ("rows", "tickers_live", "source")})
    return {"ok": True, **meta}
