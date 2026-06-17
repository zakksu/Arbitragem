"""Archaeology ↔ backtest cross-link (4.2 A4.26)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.models import BacktestRun, Trade


def archaeology_symbol_insights(session: Session, symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    trades = (
        session.query(Trade)
        .filter(Trade.source == "archaeology", Trade.symbol == sym)
        .order_by(desc(Trade.executed_at))
        .limit(500)
        .all()
    )
    pnls = [float(t.pnl) for t in trades if t.pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    backtests = (
        session.query(BacktestRun)
        .filter(BacktestRun.symbol == sym)
        .order_by(desc(BacktestRun.created_at))
        .limit(10)
        .all()
    )
    bt_rows: list[dict[str, Any]] = []
    for run in backtests:
        metrics = run.metrics or {}
        bt_rows.append(
            {
                "id": run.id,
                "engine": run.engine,
                "profit_factor": metrics.get("profit_factor"),
                "max_drawdown_pct": metrics.get("max_drawdown_pct"),
                "win_rate": metrics.get("win_rate"),
                "net_pnl": metrics.get("net_pnl"),
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
        )

    return {
        "symbol": sym,
        "archaeology": {
            "trade_count": len(trades),
            "win_rate": round(len(wins) / len(pnls), 3) if pnls else None,
            "net_pnl": round(sum(pnls), 2) if pnls else 0.0,
            "avg_trade": round(sum(pnls) / len(pnls), 2) if pnls else None,
        },
        "backtests": bt_rows,
        "backtest_count": len(bt_rows),
        "has_live_history": len(trades) > 0,
        "has_backtest_proof": len(bt_rows) > 0,
    }
