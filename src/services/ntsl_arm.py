"""One-click NTSL arm — export strategy to folder (4.0-beta)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.config import PROJECT_ROOT
from src.models import TradeIdea
from src.services.ntsl_templates import ntsl_for_idea

NTSL_DIR = PROJECT_ROOT / "exports" / "ntsl"


def arm_ntsl(
    *,
    symbol: str,
    structure_type: str,
    side: str,
    legs: list[dict] | None = None,
    ntsl_code: str | None = None,
    stop_ticks: int | None = None,
    target_ticks: int | None = None,
) -> dict:
    NTSL_DIR.mkdir(parents=True, exist_ok=True)
    code = ntsl_code or _ntsl_from_legs(
        symbol=symbol,
        structure_type=structure_type,
        side=side,
        legs=legs or [],
        stop_ticks=stop_ticks,
        target_ticks=target_ticks,
    )
    fname = f"{symbol}_{structure_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.ntsl"
    path = NTSL_DIR / fname
    path.write_text(code, encoding="utf-8")
    return {
        "status": "armed",
        "path": str(path),
        "filename": fname,
        "leg_count": len(legs or []),
        "message": "NTSL written — load in ProfitChart or enable folder watcher.",
    }


def _ntsl_from_legs(
    *,
    symbol: str,
    structure_type: str,
    side: str,
    legs: list[dict],
    stop_ticks: int | None,
    target_ticks: int | None,
) -> str:
    idea = TradeIdea(
        id=0,
        symbol=symbol.upper(),
        structure_type=structure_type,
        side=side,
        legs=legs,
        stop_ticks=stop_ticks or 5,
        target_ticks=target_ticks or 8,
    )
    return ntsl_for_idea(idea)


def arm_ntsl_for_idea(idea: dict) -> dict:
    """Export NTSL for a trade idea dict (execution ladder)."""
    legs = idea.get("legs") or []
    return arm_ntsl(
        symbol=str(idea.get("symbol", "PETR4")),
        structure_type=str(idea.get("structure_type") or "scalp"),
        side=str(idea.get("side") or "buy"),
        legs=legs,
        stop_ticks=idea.get("stop_ticks"),
        target_ticks=idea.get("target_ticks"),
    )
