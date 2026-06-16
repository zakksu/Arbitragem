"""One-click NTSL arm — export strategy to folder (4.0-beta)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.config import PROJECT_ROOT

NTSL_DIR = PROJECT_ROOT / "exports" / "ntsl"


def arm_ntsl(
    *,
    symbol: str,
    structure_type: str,
    side: str,
    ntsl_code: str | None = None,
) -> dict:
    NTSL_DIR.mkdir(parents=True, exist_ok=True)
    code = ntsl_code or _default_ntsl(symbol, structure_type, side)
    fname = f"{symbol}_{structure_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.ntsl"
    path = NTSL_DIR / fname
    path.write_text(code, encoding="utf-8")
    return {
        "status": "armed",
        "path": str(path),
        "filename": fname,
        "message": "NTSL written — load in ProfitChart or enable folder watcher.",
    }


def _default_ntsl(symbol: str, structure_type: str, side: str) -> str:
    return f"""// Arbitragem Scalper — {symbol} {structure_type} {side}
// Generated {datetime.utcnow().isoformat()}Z
Begin
  // TODO: wire legs from structure builder
End;
"""
