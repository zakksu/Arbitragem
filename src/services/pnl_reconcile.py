"""PETR4 P&L reconciliation — journal vs Profit DLL / export (Release 7.0)."""

from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT, get_settings
from src.integrations.profit_bridge import get_profit_client
from src.models import MotorJournal, Trade
from src.services.pnl_truth import resolve_day_pnl

HISTORY_PATH = PROJECT_ROOT / "data" / "pnl_reconcile_history.json"
_last: dict[str, Any] | None = None


def _load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return list(data.get("entries") or []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(entries: list[dict[str, Any]]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": entries[-60:], "updated_at": datetime.utcnow().isoformat()}
    HISTORY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _symbol_journal_pnl(session: Session, symbol: str) -> tuple[float, int]:
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    pnl = (
        session.query(func.coalesce(func.sum(Trade.pnl), 0.0))
        .filter(Trade.executed_at >= today_start, Trade.symbol == symbol, Trade.pnl.isnot(None))
        .scalar()
    )
    count = (
        session.query(func.count(Trade.id))
        .filter(Trade.executed_at >= today_start, Trade.symbol == symbol)
        .scalar()
    )
    return float(pnl or 0), int(count or 0)


def _profit_position_qty(symbol: str) -> int | None:
    client = get_profit_client()
    if not client.is_available():
        return None
    try:
        for pos in client.get_positions() or []:
            sym = str(getattr(pos, "symbol", "") or pos.get("symbol", "")).upper()
            if sym == symbol:
                return int(getattr(pos, "quantity", 0) or pos.get("quantity", 0) or 0)
    except Exception:
        return None
    return 0


def reconcile_symbol_pnl(session: Session, symbol: str | None = None) -> dict[str, Any]:
    """Compare journal P&L and fills vs Profit bridge for one symbol."""
    global _last
    settings = get_settings()
    sym = (symbol or settings.golden_path_symbol).upper()
    truth = resolve_day_pnl(session)
    journal_sym_pnl, sym_trades = _symbol_journal_pnl(session, sym)
    profit_day = truth.get("profit_day_pnl")
    journal_day = float(truth.get("journal_pnl") or 0)

    journal_fills = (
        session.query(func.count(MotorJournal.id))
        .filter(
            MotorJournal.phase == "FILL",
            MotorJournal.symbol == sym,
            MotorJournal.created_at >= datetime.combine(datetime.utcnow().date(), time.min),
        )
        .scalar()
    )
    profit_qty = _profit_position_qty(sym)

    reference = profit_day if profit_day is not None else journal_day
    if reference is not None and abs(float(reference)) > 0.01:
        diff_pct = abs(journal_sym_pnl - float(reference)) / max(abs(float(reference)), 1.0) * 100.0
    elif sym_trades == 0 and journal_fills == 0:
        diff_pct = 0.0
    else:
        diff_pct = 0.0 if journal_sym_pnl == 0 else 100.0

    within = diff_pct <= 2.0
    entry = {
        "symbol": sym,
        "journal_symbol_pnl": round(journal_sym_pnl, 2),
        "journal_day_pnl": journal_day,
        "profit_day_pnl": profit_day,
        "diff_pct": round(diff_pct, 2),
        "within_tolerance": within,
        "journal_fills_today": int(journal_fills or 0),
        "symbol_trades_today": sym_trades,
        "profit_position_qty": profit_qty,
        "pnl_source": truth.get("pnl_source"),
        "reconciled_at": datetime.utcnow().isoformat(),
    }
    _last = entry

    history = _load_history()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    history = [h for h in history if h.get("date") != today or h.get("symbol") != sym]
    history.append({**entry, "date": today})
    _save_history(history)
    return entry


def last_reconcile(session: Session | None = None) -> dict[str, Any]:
    if _last:
        return _last
    if session is not None:
        return reconcile_symbol_pnl(session)
    history = _load_history()
    if history:
        return history[-1]
    return {"within_tolerance": True, "diff_pct": 0.0, "symbol": get_settings().golden_path_symbol}
