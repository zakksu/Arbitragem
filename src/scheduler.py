"""Background scheduler for daily scans, journal sync, and optimization hooks."""

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import get_settings
from src.logging_config import get_logger
from src.models import get_session_factory
from src.services.journal import JournalService
from src.services.profit_export_watcher import scan_profit_exports
from src.services.scanner import PatternScanner
from src.services.trade_ideas import TradeIdeaService
from src.services.walk_forward_promotion import run_walk_forward_promotion

logger = get_logger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_daily_scan() -> None:
    session = get_session_factory()()
    try:
        from src.services.system_audit import log_event

        results = PatternScanner(session).run_daily_scan()
        if results:
            from src.services.alerting import get_alert_service

            get_alert_service().notify_scan_alerts(results)
            TradeIdeaService(session).generate_from_latest_scan(limit=12)
            log_event(
                session,
                level="info",
                component="scanner",
                message=f"Daily scan complete — {len(results)} symbols",
                details={"count": len(results)},
            )
            session.commit()
    except Exception as exc:
        logger.error("scheduled_scan_failed", error=str(exc))
    finally:
        session.close()


def _run_journal_sync() -> None:
    session = get_session_factory()()
    try:
        JournalService(session).sync_all_sources()
    except Exception as exc:
        logger.error("scheduled_journal_failed", error=str(exc))
    finally:
        session.close()


def _run_export_watcher() -> None:
    session = get_session_factory()()
    try:
        scan_profit_exports(session)
    except Exception as exc:
        logger.error("export_watcher_failed", error=str(exc))
    finally:
        session.close()


def _run_walk_forward_promotion() -> None:
    settings = get_settings()
    if not settings.walk_forward_auto_promote:
        return
    session = get_session_factory()()
    try:
        from src.services.system_audit import log_event

        result = run_walk_forward_promotion(session, folds=settings.walk_forward_promote_folds)
        log_event(
            session,
            level="info",
            component="walk_forward",
            message=f"Walk-forward promotion — {result.get('promoted', 0)} ideas",
            details=result,
        )
        session.commit()
    except Exception as exc:
        logger.error("walk_forward_promotion_failed", error=str(exc))
    finally:
        session.close()


def start_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    if not settings.enable_scheduler:
        logger.info("scheduler_disabled")
        return
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone=settings.timezone)
    _scheduler.add_job(
        _run_daily_scan,
        "cron",
        hour=settings.scanner_cron_hour,
        minute=settings.scanner_cron_minute,
        id="daily_scan",
    )
    _scheduler.add_job(
        _run_journal_sync,
        "interval",
        minutes=5,
        id="journal_sync",
    )
    _scheduler.add_job(
        _run_export_watcher,
        "interval",
        minutes=10,
        id="export_watcher",
    )
    if settings.walk_forward_auto_promote:
        _scheduler.add_job(
            _run_walk_forward_promotion,
            "interval",
            hours=settings.walk_forward_interval_hours,
            id="walk_forward_promotion",
        )
    _scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
