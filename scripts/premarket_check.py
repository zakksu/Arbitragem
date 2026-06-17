#!/usr/bin/env python3
"""Pre-market live readiness check — run before B3 open."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _get(url: str, timeout: float = 6.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-market readiness for live stock scalps")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--symbol", default="PETR4")
    parser.add_argument("--price", type=float, default=38.0)
    parser.add_argument("--capital-brl", type=float, default=500.0)
    parser.add_argument("--leverage", type=float, default=50.0)
    parser.add_argument("--lot", type=int, default=100)
    args = parser.parse_args()

    from src.config import get_settings
    from src.services.clear_cost_model import cost_summary_for_symbol

    settings = get_settings()
    health = _get("http://127.0.0.1:8000/api/v1/health/live")
    bridge = _get("http://127.0.0.1:9100/health")
    orch = _get("http://127.0.0.1:8000/api/v1/orchestrator/status")
    clear_st = _get("http://127.0.0.1:8000/api/v1/execution/clear/status")

    costs = cost_summary_for_symbol(
        args.symbol, args.price, quantity=args.lot, leverage=args.leverage
    )
    margin = costs["margin_estimate_brl"]
    positions_affordable = int(args.capital_brl // margin) if margin > 0 else 0

    blockers: list[str] = []
    if not health:
        blockers.append("api_offline")
    if not bridge:
        blockers.append("profit_bridge_offline")
    if settings.paper_trading_mode:
        blockers.append("paper_mode_on")
    if not settings.profit_bridge_enabled:
        blockers.append("profit_bridge_disabled")
    if orch and not orch.get("active"):
        blockers.append("motor_idle")

    # Phase C — DLL auto not required for manual Chart Trading
    ready_manual = not any(b in blockers for b in ("api_offline", "profit_bridge_offline"))

    payload = {
        "ready_manual_live": ready_manual,
        "ready_auto_live": False,
        "blockers": blockers,
        "paper_trading_mode": settings.paper_trading_mode,
        "execution_backend": settings.execution_backend,
        "symbol": args.symbol,
        "lot_shares": args.lot,
        "capital_brl": args.capital_brl,
        "costs": costs,
        "positions_at_margin": positions_affordable,
        "recommended_max_concurrent_lots": min(1, positions_affordable),
        "daily_loss_limit_brl": settings.default_daily_loss_limit_brl,
        "crypto_live": "deferred — Binance read-only; no broker fee/margin contract",
    }

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"Manual live ready: {'YES' if ready_manual else 'NO'}")
        if blockers:
            print(f"Blockers: {', '.join(blockers)}")
        print(f"{args.symbol} @ R${args.price:.2f} × {args.lot} shares")
        print(f"  Margin ~R${margin:.2f} @ {args.leverage}x")
        print(f"  B3 round-trip fees ~R${costs['breakeven']['b3_round_trip_brl']:.2f}")
        print(f"  Breakeven ~{costs['breakeven']['breakeven_ticks']} ticks (R${costs['breakeven']['tick_value_brl']:.2f}/tick)")
        print(f"  Max lots at R${args.capital_brl:.0f}: {positions_affordable} (trade 1)")

    return 0 if ready_manual else 1


if __name__ == "__main__":
    raise SystemExit(main())
