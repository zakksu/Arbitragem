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


def build_archaeology_summary(session: Session, *, limit: int = 15) -> dict[str, Any]:
    """Top symbols by archaeology trade count with win rate and net flow."""
    from sqlalchemy import func

    rows = (
        session.query(
            Trade.symbol,
            func.count(Trade.id).label("trade_count"),
            func.sum(Trade.pnl).label("net_pnl"),
        )
        .filter(Trade.source == "archaeology")
        .group_by(Trade.symbol)
        .order_by(func.count(Trade.id).desc())
        .limit(max(1, min(limit, 50)))
        .all()
    )
    symbols: list[dict[str, Any]] = []
    total_trades = 0
    total_pnl = 0.0
    for sym, count, net in rows:
        sym_trades = (
            session.query(Trade.pnl)
            .filter(Trade.source == "archaeology", Trade.symbol == sym, Trade.pnl.isnot(None))
            .all()
        )
        pnls = [float(t[0]) for t in sym_trades]
        wins = [p for p in pnls if p > 0]
        symbols.append(
            {
                "symbol": sym,
                "trade_count": int(count or 0),
                "win_rate": round(len(wins) / len(pnls), 3) if pnls else None,
                "net_pnl": round(float(net or 0), 2),
            }
        )
        total_trades += int(count or 0)
        total_pnl += float(net or 0)

    lanes = {"futures": 0, "cash": 0, "options": 0}
    for sym, count, _ in rows:
        s = str(sym).upper()
        n = int(count or 0)
        if s.startswith(("WIN", "WDO", "BIT", "MBR", "IND", "DOL")):
            lanes["futures"] += n
        elif len(s) > 6:
            lanes["options"] += n
        else:
            lanes["cash"] += n

    return {
        "total_trades": total_trades,
        "net_pnl": round(total_pnl, 2),
        "symbol_count": len(symbols),
        "top_symbols": symbols,
        "lanes": lanes,
    }
