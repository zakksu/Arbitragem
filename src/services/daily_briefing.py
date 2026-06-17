"""Daily briefing — transparent PETR4 session summary (10.0)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.services.golden_path import evaluate_golden_path
from src.services.knowledge.store import knowledge_status
from src.services.motor_journal import list_recent
from src.services.replay_engine import list_recent_sessions
from src.services.risk_summary import build_risk_summary
from src.services.strategy_store import list_stored_strategies
from src.services.trading_orchestrator import orchestrator_status


def build_daily_briefing(session: Session) -> dict[str, Any]:
    settings = get_settings()
    sym = settings.golden_path_symbol if settings.golden_path_mode else "PETR4"
    risk = build_risk_summary(session)
    gp = evaluate_golden_path(session)
    orch = orchestrator_status()
    journal = list_recent(session, limit=8)
    replays = list_recent_sessions(session, limit=5)
    strategies = list_stored_strategies(session, limit=20)
    know = knowledge_status()

    bullets: list[dict[str, str]] = []

    bullets.append(
        {
            "level": "info",
            "text": f"Symbol focus: {sym} — motor {'ON' if orch.get('active') else 'idle'}, "
            f"sleeves {'open' if risk.get('sleeves_all_open') else 'paused'}.",
        }
    )
    bullets.append(
        {
            "level": "pnl",
            "text": f"Day P&L R$ {risk.get('day_pnl', 0):.2f} ({risk.get('pnl_source', 'journal')}) · "
            f"{risk.get('trades_today', 0)} trades today.",
        }
    )
    gp_ok = gp.get("items_ok", 0)
    gp_total = gp.get("items_total", 7)
    bullets.append(
        {
            "level": "golden" if gp.get("all_green") else "warn",
            "text": f"Golden path {gp_ok}/{gp_total} · {gp.get('sessions_green_count', 0)} green sessions recorded.",
        }
    )
    if replays:
        last = replays[0]
        bullets.append(
            {
                "level": "replay",
                "text": f"Last replay {last.get('symbol')} — {last.get('status')} "
                f"({last.get('fill_count', 0)} fills, source {last.get('source', '—')}).",
            }
        )
    else:
        bullets.append(
            {
                "level": "replay",
                "text": "No replay sessions yet — background training will seed PETR4 sandboxes.",
            }
        )
    bullets.append(
        {
            "level": "strategy",
            "text": f"Strategy store: {len(strategies)} NTSL files indexed "
            f"({len(settings.strategy_store_scan_paths)} scan dirs).",
        }
    )
    bullets.append(
        {
            "level": "knowledge",
            "text": f"Knowledge corpus: {know.get('chunks', 0)} chunks from {know.get('sources', 0)} sources "
            f"({know.get('db_mb', 0)} MB).",
        }
    )
    if journal:
        j = journal[0]
        bullets.append(
            {
                "level": "motor",
                "text": f"Latest motor: {j.get('phase')} — {j.get('message', '')[:120]}",
            }
        )

    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    charts = _briefing_charts(session, gp, replays, risk, today_start)

    return {
        "symbol": sym,
        "generated_at": datetime.utcnow().isoformat(),
        "bullets": bullets[:7],
        "golden_path": {
            "all_green": gp.get("all_green"),
            "trust_score_pct": gp.get("trust_score_pct"),
        },
        "risk_status": risk.get("status"),
        "replay_count": len(replays),
        "knowledge": know,
        "charts": charts,
    }


def _briefing_charts(
    session: Session,
    gp: dict[str, Any],
    replays: list[dict[str, Any]],
    risk: dict[str, Any],
    today_start: datetime,
) -> dict[str, Any]:
    from collections import Counter

    from src.models import Trade

    gp_ok = int(gp.get("items_ok") or 0)
    gp_total = int(gp.get("items_total") or 7) or 7
    golden_pct = round(100.0 * gp_ok / gp_total, 1)

    rows = (
        session.query(Trade)
        .filter(Trade.executed_at >= today_start, Trade.pnl.isnot(None))
        .order_by(Trade.executed_at.asc())
        .all()
    )
    spark: list[float] = []
    cum = 0.0
    for row in rows:
        cum += float(row.pnl or 0)
        spark.append(round(cum, 2))
    if not spark:
        spark = [float(risk.get("day_pnl") or 0)]

    lo, hi = min(spark), max(spark)
    span = hi - lo or 1.0
    points: list[str] = []
    for i, val in enumerate(spark):
        x = (i / max(len(spark) - 1, 1)) * 118 + 1
        y = 30 - ((val - lo) / span) * 26
        points.append(f"{x:.1f},{y:.1f}")

    status_counts = Counter(r.get("status") or "unknown" for r in replays)
    max_c = max(status_counts.values()) if status_counts else 1
    replay_bars = [
        {
            "label": label,
            "count": count,
            "pct": max(12, round(100 * count / max_c)),
        }
        for label, count in status_counts.items()
    ]
    if not replay_bars:
        replay_bars = [{"label": "none", "count": 0, "pct": 12}]

    return {
        "golden_pct": golden_pct,
        "pnl_spark": len(spark) > 1,
        "pnl_spark_points": " ".join(points),
        "pnl_end": spark[-1],
        "replay_bars": replay_bars[:5],
    }
