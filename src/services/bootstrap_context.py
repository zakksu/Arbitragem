"""Fast bootstrap payload for dashboard shell and blackboard status bar."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src import __version__
from src.config import get_settings
from src.integrations.clear_api import get_clear_client
from src.models import ScanResult, Strategy


def build_bootstrap(session: Session) -> dict:
    settings = get_settings()
    clear = get_clear_client()
    account = clear.get_account_summary()

    alerts: list[dict[str, str]] = []
    if not clear.is_configured():
        alerts.append({"level": "warning", "message": "Clear API in mock mode — add credentials in `.env`."})

    strategies = session.query(Strategy).all()
    for s in strategies:
        if s.status == "active":
            alerts.append(
                {
                    "level": "info",
                    "message": f"Strategy **{s.name}** LIVE — loss limit R$ {s.daily_loss_limit_brl:.0f}",
                }
            )

    latest = session.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
    if latest:
        rows = (
            session.query(ScanResult)
            .filter(
                ScanResult.scan_date == latest[0],
                ScanResult.alert_level.in_(["warning", "critical"]),
            )
            .limit(8)
            .all()
        )
        for s in rows:
            tags = ", ".join(s.pattern_tags or [])
            alerts.append(
                {
                    "level": s.alert_level,
                    "message": f"Scanner: **{s.symbol}** spike={s.spike_score:.0f} — {tags or 'pattern'}",
                }
            )
            if len([a for a in alerts if "Scanner" in a.get("message", "")]) >= 3:
                break

    return {
        "status": "ok",
        "version": __version__,
        "paper_trading_mode": settings.paper_trading_mode,
        "scanner_mode": settings.scanner_mode,
        "scanner_symbol_count": len(settings.scanner_symbol_list),
        "clear_api": clear.is_configured(),
        "account": account,
        "alerts": alerts,
        "strategies_count": len(strategies),
        "active_strategies": sum(1 for s in strategies if s.status == "active"),
    }
