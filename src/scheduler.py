"""Background scheduler for daily scans, journal sync, and optimization hooks."""

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import get_settings
from src.logging_config import get_logger
from src.models import get_session_factory
from src.services.journal import JournalService
from src.services.profit_export_watcher import scan_profit_exports
from src.services.profit_pnl_sync import sync_profit_pnl
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
        if settings.autonomous_rankings_sync:
            from src.autonomous.backtest_rankings import BacktestRankingsService

            synced = BacktestRankingsService(session).sync_from_optimization_runs()
            result["rankings_synced"] = synced
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


def _run_profit_pnl_sync() -> None:
    session = get_session_factory()()
    try:
        sync_profit_pnl(session)
    except Exception as exc:
        logger.error("profit_pnl_sync_failed", error=str(exc))
    finally:
        session.close()


def _run_pnl_reconcile() -> None:
    settings = get_settings()
    if not settings.golden_path_mode:
        return
    session = get_session_factory()()
    try:
        from src.services.pnl_reconcile import reconcile_symbol_pnl

        reconcile_symbol_pnl(session, settings.golden_path_symbol)
    except Exception as exc:
        logger.error("pnl_reconcile_failed", error=str(exc))
    finally:
        session.close()


def _run_journal_maintenance() -> None:
    session = get_session_factory()()
    try:
        from src.services.journal_maintenance import ensure_journal_indexes, prune_motor_journal

        ensure_journal_indexes()
        result = prune_motor_journal(session)
        if result.get("deleted"):
            logger.info("motor_journal_pruned", **result)
    except Exception as exc:
        logger.error("journal_maintenance_failed", error=str(exc))
    finally:
        session.close()


def _run_orchestrator_tick() -> None:
    settings = get_settings()
    if not settings.orchestrator_scheduler_enabled:
        return
    if not settings.paper_trading_mode and not settings.autonomy_enabled:
        return
    session = get_session_factory()()
    try:
        from src.services.trader_agent import run_trader_cycle

        run_trader_cycle(session)
    except Exception as exc:
        logger.error("orchestrator_tick_failed", error=str(exc))
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
        _run_profit_pnl_sync,
        "interval",
        minutes=2,
        id="profit_pnl_sync",
    )
    _scheduler.add_job(
        _run_export_watcher,
        "interval",
        minutes=10,
        id="export_watcher",
    )
    _scheduler.add_job(
        _run_pnl_reconcile,
        "interval",
        minutes=5,
        id="pnl_reconcile",
    )
    _scheduler.add_job(
        _run_journal_maintenance,
        "cron",
        hour=3,
        minute=0,
        id="journal_maintenance",
    )
    if settings.walk_forward_auto_promote:
        _scheduler.add_job(
            _run_walk_forward_promotion,
            "interval",
            hours=settings.walk_forward_interval_hours,
            id="walk_forward_promotion",
        )
    from src.autonomous.scheduler import register_autonomous_jobs

    register_autonomous_jobs(_scheduler)
    if settings.orchestrator_scheduler_enabled and (
        settings.autonomy_enabled or (settings.paper_trading_mode and settings.auto_trading_on_sleeves)
    ):
        interval = max(30, int(settings.orchestrator_interval_sec))
        _scheduler.add_job(
            _run_orchestrator_tick,
            "interval",
            seconds=interval,
            id="orchestrator_tick",
            replace_existing=True,
        )
    _scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
