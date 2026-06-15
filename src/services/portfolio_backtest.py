"""Portfolio-level backtest — combined Core14 book simulation (3.0 GA)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from src.services.filipe_universe import symbol_list


def _seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def run_portfolio_backtest(session: Session | None = None, *, days: int = 30) -> dict:
    """Stub aggregate metrics across Core14 scalps + concurrent structures."""
    symbols = symbol_list()
    seed = _seed(f"portfolio:{days}:{datetime.utcnow().date()}")
    pf = round(1.25 + (seed % 50) / 100.0, 2)
    dd = round(4.0 + (seed % 40) / 10.0, 2)
    trades = 120 + seed % 200
    structures = 3 + seed % 5
    margin_peak = round(15_000 + (seed % 20_000), 2)

    per_symbol = []
    for sym in symbols[:8]:
        s = _seed(sym)
        per_symbol.append(
            {
                "symbol": sym,
                "profit_factor": round(1.1 + (s % 60) / 100.0, 2),
                "trades": 10 + s % 30,
                "net_pnl": round((s % 200 - 50) * 10.0, 2),
            }
        )

    return {
        "period_days": days,
        "symbols_count": len(symbols),
        "concurrent_structures": structures,
        "portfolio_profit_factor": pf,
        "portfolio_max_drawdown_pct": dd,
        "total_trades": trades,
        "margin_peak_brl": margin_peak,
        "correlation_streams": round(0.35 + (seed % 30) / 100.0, 2),
        "per_symbol": per_symbol,
        "gates_pass": pf >= 1.3 and dd <= 8.0,
        "source": "stub_simulation",
        "generated_at": datetime.utcnow().isoformat(),
    }
