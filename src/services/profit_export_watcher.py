"""Watch Profit export folder — auto-ingest CSV backtests and attach proof to ideas."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.models import BacktestRun, TradeIdea
from src.services.trade_ideas import TradeIdeaService

logger = get_logger(__name__)
_PROCESSED: set[str] = set()


def scan_profit_exports(session: Session) -> dict:
    """Ingest new CSV files from profit export dir; update matching TradeIdeas."""
    export_dir = get_settings().profit_export_path
    export_dir.mkdir(parents=True, exist_ok=True)
    client = get_profit_client()
    svc = TradeIdeaService(session)
    imported = 0
    promoted = 0

    for path in sorted(export_dir.glob("*.csv")):
        key = f"{path.name}:{path.stat().st_mtime_ns}"
        if key in _PROCESSED:
            continue
        metrics = client.import_backtest_results(path)
        if metrics.get("error"):
            continue
        _PROCESSED.add(key)
        imported += 1

        symbol = str(metrics.get("symbol") or path.stem.split("_")[0]).upper()
        session.add(
            BacktestRun(
                engine="profit",
                symbol=symbol,
                metrics=metrics,
                profit_export_path=str(path),
                notes="auto-import watcher",
            )
        )

        if not svc.passes_backtest_gate(metrics):
            continue

        idea = svc.attach_backtest_proof(symbol, metrics)
        if idea:
            promoted += 1

    session.commit()
    logger.info("profit_export_scan", imported=imported, promoted=promoted)
    return {"imported": imported, "promoted": promoted}
