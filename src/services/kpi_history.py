"""KPI history rollups — today / 5d / 20d / 3mo (4.0-rc)."""

from __future__ import annotations

from datetime import datetime, timedelta, time

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import Trade
from src.services.pnl_truth import resolve_day_pnl


def _pnl_since(session: Session, since: datetime) -> tuple[float, int, float]:
    rows = session.query(Trade).filter(Trade.executed_at >= since, Trade.pnl.isnot(None)).all()
    if not rows:
        return 0.0, 0, 0.0
    pnls = [float(t.pnl or 0) for t in rows]
    total = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / len(pnls) * 100 if pnls else 0.0
    return round(total, 2), len(pnls), round(win_rate, 1)


def _profit_factor_last_n(session: Session, n: int = 20) -> float | None:
    rows = (
        session.query(Trade)
        .filter(Trade.pnl.isnot(None))
        .order_by(Trade.executed_at.desc())
        .limit(n)
        .all()
    )
    if not rows:
        return None
    gains = sum(float(t.pnl) for t in rows if (t.pnl or 0) > 0)
    losses = abs(sum(float(t.pnl) for t in rows if (t.pnl or 0) < 0))
    if losses <= 0:
        return round(gains, 2) if gains else None
    return round(gains / losses, 2)


def build_kpi_history(session: Session, range_key: str = "today") -> dict:
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), time.min)
    ranges = {
        "today": today_start,
        "5d": now - timedelta(days=5),
        "20d": now - timedelta(days=20),
        "3mo": now - timedelta(days=90),
        "ytd": datetime(now.year, 1, 1),
    }
    since = ranges.get(range_key, today_start)
    pnl, trades, win_rate = _pnl_since(session, since)
    day = resolve_day_pnl(session)
    return {
        "range": range_key,
        "pnl_brl": pnl if range_key != "today" else day["day_pnl"],
        "trades": trades if range_key != "today" else day["trades_today"],
        "win_rate_pct": win_rate,
        "profit_factor_20": _profit_factor_last_n(session, 20),
        "pnl_source": day["pnl_source"],
    }
