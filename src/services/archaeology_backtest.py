"""Archaeology ↔ backtest cross-link (4.2 A4.26)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT
from src.models import BacktestRun, Trade

_INSIGHTS_PATH = PROJECT_ROOT / "data" / ".dev" / "b3_history_insights.json"


def _load_b3_history_insights() -> dict[str, Any]:
    if not _INSIGHTS_PATH.exists():
        return {}
    try:
        return json.loads(_INSIGHTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def archaeology_symbol_insights(session: Session, symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    trades = (
        session.query(Trade)
        .filter(Trade.source == "archaeology", Trade.symbol == sym)
        .order_by(desc(Trade.executed_at))
        .limit(500)
        .all()
    )
    from src.services.archaeology_fifo import fifo_realized_trips, fifo_stats, trade_lane

    fifo = fifo_stats(trades)
    trips = fifo_realized_trips(trades)
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
        "lane": trade_lane(sym),
        "archaeology": {
            "trade_count": len(trades),
            "win_rate": round(len(wins) / len(pnls), 3) if pnls else None,
            "net_pnl": round(sum(pnls), 2) if pnls else 0.0,
            "avg_trade": round(sum(pnls) / len(pnls), 2) if pnls else None,
            "fifo_round_trips": fifo.get("round_trips"),
            "fifo_net_pnl": fifo.get("net_pnl"),
            "fifo_win_rate": fifo.get("win_rate"),
        },
        "fifo_trips": trips[-5:],
        "backtests": bt_rows,
        "backtest_count": len(bt_rows),
        "has_live_history": len(trades) > 0,
        "has_backtest_proof": len(bt_rows) > 0,
    }


def _build_archaeology_summary_from_db(session: Session, *, limit: int = 15) -> dict[str, Any]:
    """Top symbols by archaeology trade count with FIFO win rate and net flow (A11.1)."""
    from collections import defaultdict

    from src.services.archaeology_fifo import fifo_stats, trade_lane

    all_trades = session.query(Trade).filter(Trade.source == "archaeology").all()
    fifo = fifo_stats(all_trades)
    by_symbol: dict[str, list[Trade]] = defaultdict(list)
    for t in all_trades:
        by_symbol[t.symbol.upper()].append(t)

    ranked = sorted(by_symbol.items(), key=lambda x: len(x[1]), reverse=True)
    symbols: list[dict[str, Any]] = []
    total_trades = 0
    total_fifo_pnl = 0.0
    for sym, sym_trades in ranked[: max(1, min(limit, 50))]:
        sym_fifo = fifo_stats(sym_trades)
        net = float(sym_fifo.get("net_pnl") or 0)
        symbols.append(
            {
                "symbol": sym,
                "trade_count": len(sym_trades),
                "win_rate": sym_fifo.get("win_rate"),
                "net_pnl": round(net, 2),
                "fifo_round_trips": sym_fifo.get("round_trips"),
                "fifo_net_pnl": net,
            }
        )
        total_trades += len(sym_trades)
        total_fifo_pnl += net

    lanes = {"futures": 0, "cash": 0, "options": 0}
    for sym, sym_trades in ranked:
        n = len(sym_trades)
        lanes[trade_lane(sym)] = lanes.get(trade_lane(sym), 0) + n

    return {
        "total_trades": total_trades if ranked else len(all_trades),
        "net_pnl": round(total_fifo_pnl, 2),
        "fifo": fifo,
        "symbol_count": len(by_symbol),
        "top_symbols": symbols,
        "lanes": lanes,
    }


def _build_archaeology_summary_from_insights(*, limit: int = 15) -> dict[str, Any] | None:
    data = _load_b3_history_insights()
    summary = data.get("summary") if data else None
    if not summary:
        return None

    core17 = data.get("core17_insights") or {}
    top_raw = (summary.get("top_symbols") or [])[: max(1, min(limit, 50))]
    top_symbols: list[dict[str, Any]] = []
    total_pnl = 0.0
    for item in top_raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            sym, count = str(item[0]), int(item[1])
        elif isinstance(item, dict):
            sym = str(item.get("symbol", ""))
            count = int(item.get("trade_count", 0))
        else:
            continue
        arch = (core17.get(sym) or {}).get("archaeology") or {}
        net = float(arch.get("net_pnl") or 0)
        top_symbols.append(
            {
                "symbol": sym,
                "trade_count": count,
                "win_rate": arch.get("win_rate"),
                "net_pnl": round(net, 2),
            }
        )
        total_pnl += net

    return {
        "total_trades": int(summary.get("archaeology_trade_count") or 0),
        "net_pnl": round(total_pnl, 2),
        "symbol_count": int(summary.get("unique_symbols") or len(top_symbols)),
        "top_symbols": top_symbols,
        "lanes": {
            "futures": int(summary.get("futures_count") or 0),
            "cash": int(summary.get("cash_equity_count") or 0),
            "options": int(summary.get("options_count") or 0),
        },
        "source": "b3_history_insights.json",
    }


def build_archaeology_summary(session: Session, *, limit: int = 15) -> dict[str, Any]:
    """Top symbols, win rate, net flow — DB first, insights JSON fallback (A11.3)."""
    body = _build_archaeology_summary_from_db(session, limit=limit)
    if body["total_trades"] > 0:
        body["source"] = "db"
        return body
    fallback = _build_archaeology_summary_from_insights(limit=limit)
    if fallback:
        return fallback
    body["source"] = "db"
    return body
