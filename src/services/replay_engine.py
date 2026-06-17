"""Replay Training Engine — tick-by-tick replay, fills → journal + WFO + Ollama (10.0)."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Generator

from sqlalchemy.orm import Session

from src.config import get_settings
from src.logging_config import get_logger
from src.models import BacktestRun, JournalEntry, ReplayFill, ReplaySession, Trade
from src.services.self_healing import get_breaker
from src.services.vwap import session_vwap

logger = get_logger(__name__)

# In-memory active job index for fast polling (DB is source of truth)
_ACTIVE: dict[str, int] = {}


def start_replay(
    *,
    strategy: str,
    symbol: str,
    speed: float = 10.0,
    mode: str = "sandbox",
    session: Session | None = None,
) -> dict[str, Any]:
    """Start replay — backward compatible with replay_lab API."""
    from src.models import get_session_factory

    own_session = session is None
    db = session or get_session_factory()()
    breaker = get_breaker("replay_training")
    if breaker.is_open():
        return {
            "job_id": "",
            "status": "circuit_open",
            "message": "Replay circuit breaker open — cooling down",
            "symbol": symbol.strip().upper(),
        }
    try:
        speed = max(1.0, min(50.0, float(speed)))
        sym = symbol.strip().upper()
        job_id = str(uuid.uuid4())[:8]
        row = ReplaySession(
            job_id=job_id,
            symbol=sym,
            strategy_name=strategy,
            status="queued",
            speed=speed,
            mode=mode,
            source="pending",
            message="Starting replay training cycle",
        )
        db.add(row)
        db.flush()
        _ACTIVE[job_id] = row.id

        bridge_result = _try_bridge_replay(sym, strategy, speed)
        if bridge_result and bridge_result.get("status") not in ("error", "not_found"):
            bridge_job = bridge_result.get("job_id") or job_id
            row.job_id = bridge_job
            _ACTIVE[bridge_job] = row.id
            polled = _poll_bridge_replay(bridge_job, bridge_result)
            fills = polled.get("fills") or []
            metrics = polled.get("metrics") or bridge_result
            row.source = "profit_bridge"
            row.status = "completed"
            row.progress_pct = 100.0
            row.fill_count = len(fills)
            row.metrics = metrics
            row.message = polled.get("message", "Bridge replay complete")
            row.completed_at = datetime.utcnow()
            _persist_fills(db, row, sym, fills)
            db.flush()
            _post_session_hooks(db, row, fills)
            db.commit()
            breaker.record_success()
            return _session_to_dict(row)

        fills, metrics = _run_tick_simulation(sym, strategy, speed=speed)
        row.source = "tick_sim"
        row.status = "completed"
        row.progress_pct = 100.0
        row.fill_count = len(fills)
        row.metrics = metrics
        row.message = f"Tick sim complete — {len(fills)} fills"
        row.completed_at = datetime.utcnow()

        for f in fills:
            db.add(
                ReplayFill(
                    session_id=row.id,
                    symbol=sym,
                    side=f["side"],
                    quantity=f.get("quantity", 100),
                    price=f["price"],
                    pnl=f.get("pnl"),
                    tick_index=f.get("tick_index"),
                    executed_at=f.get("executed_at", datetime.utcnow()),
                    raw_payload=f,
                )
            )
        db.flush()
        _post_session_hooks(db, row, fills)
        db.commit()
        breaker.record_success()
        return _session_to_dict(row)
    except Exception as exc:
        breaker.record_failure()
        logger.exception("replay_start_failed", symbol=symbol, error=str(exc))
        raise
    finally:
        if own_session:
            db.close()


def _poll_bridge_replay(job_id: str, initial: dict[str, Any]) -> dict[str, Any]:
    """Poll bridge until completed or timeout — keeps hot path off motor."""
    if initial.get("status") == "completed" and initial.get("fills"):
        return initial
    for _ in range(15):
        status = _fetch_bridge_replay(job_id)
        if not status:
            break
        if status.get("status") == "completed":
            return status
        time.sleep(0.15)
    return initial


def _fetch_bridge_replay(job_id: str) -> dict[str, Any] | None:
    from src.integrations.profit_bridge import get_profit_client

    client = get_profit_client()
    if not client.is_available():
        return None
    try:
        import httpx

        with httpx.Client(base_url=client.base_url, timeout=10.0) as http:
            r = http.get(f"/replay/{job_id}")
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        logger.debug("bridge_replay_poll_failed", job_id=job_id, error=str(exc))
    return None


def _persist_fills(db: Session, row: ReplaySession, sym: str, fills: list[dict]) -> None:
    for f in fills:
        db.add(
            ReplayFill(
                session_id=row.id,
                symbol=sym,
                side=f.get("side", "buy"),
                quantity=int(f.get("quantity", 100)),
                price=float(f["price"]),
                pnl=f.get("pnl"),
                tick_index=f.get("tick_index"),
                executed_at=datetime.utcnow(),
                raw_payload=f,
            )
        )


def _try_bridge_replay(symbol: str, strategy: str, speed: float) -> dict[str, Any] | None:
    from src.integrations.profit_bridge import get_profit_client

    client = get_profit_client()
    if not client.is_available():
        return None
    try:
        import httpx

        with httpx.Client(base_url=client.base_url, timeout=30.0) as http:
            r = http.post(
                "/replay/run",
                json={"symbol": symbol, "strategy": strategy, "speed": speed},
            )
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        logger.debug("bridge_replay_unavailable", error=str(exc))
    return None


def _iter_ticks(candles: list[dict[str, Any]]) -> Generator[tuple[int, float, dict], None, None]:
    """Yield (tick_index, price, bar) — 4 ticks per bar keeps RAM flat vs full tick DB."""
    idx = 0
    for bar in candles:
        for key in ("open", "high", "low", "close"):
            raw = bar.get(key) or bar.get(key[0])
            if raw is None:
                continue
            try:
                price = float(raw)
            except (TypeError, ValueError):
                continue
            if price > 0:
                yield idx, price, bar
                idx += 1


def _run_tick_simulation(
    symbol: str,
    strategy: str,
    *,
    speed: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Scalp replay on session candles — VWAP reclaim long/short logic."""
    from src.integrations.profit_bridge import get_profit_client

    settings = get_settings()
    client = get_profit_client()
    max_bars = min(settings.replay_max_bars_per_session, 390)
    candles = client.get_session_candles(symbol, bars=max_bars)
    if not candles:
        return [], {"error": "no_candles", "bars": 0}

    vwap = session_vwap(candles)
    fills: list[dict[str, Any]] = []
    position: str | None = None
    entry_price = 0.0
    prev_price: float | None = None
    wins = 0
    losses = 0
    total_pnl = 0.0
    tick_index = 0
    stop_pct = 0.004
    target_pct = 0.006

    for tick_index, price, _bar in _iter_ticks(candles):
        if vwap and prev_price is not None:
            reclaim_long = prev_price < vwap <= price
            reclaim_short = prev_price > vwap >= price
            if position is None and reclaim_long and strategy != "scalp_short":
                position = "long"
                entry_price = price
                fills.append(
                    {
                        "side": "buy",
                        "price": price,
                        "quantity": 100,
                        "tick_index": tick_index,
                        "executed_at": datetime.utcnow(),
                        "event": "entry_long",
                    }
                )
            elif position is None and reclaim_short and strategy not in ("scalp_long", "scalp_default"):
                position = "short"
                entry_price = price
                fills.append(
                    {
                        "side": "sell",
                        "price": price,
                        "quantity": 100,
                        "tick_index": tick_index,
                        "executed_at": datetime.utcnow(),
                        "event": "entry_short",
                    }
                )
            elif position == "long":
                pnl_pct = (price - entry_price) / entry_price
                if pnl_pct <= -stop_pct or pnl_pct >= target_pct or reclaim_short:
                    pnl = round((price - entry_price) * 100, 2)
                    total_pnl += pnl
                    if pnl >= 0:
                        wins += 1
                    else:
                        losses += 1
                    fills.append(
                        {
                            "side": "sell",
                            "price": price,
                            "quantity": 100,
                            "pnl": pnl,
                            "tick_index": tick_index,
                            "executed_at": datetime.utcnow(),
                            "event": "exit_long",
                        }
                    )
                    position = None
            elif position == "short":
                pnl_pct = (entry_price - price) / entry_price
                if pnl_pct <= -stop_pct or pnl_pct >= target_pct or reclaim_long:
                    pnl = round((entry_price - price) * 100, 2)
                    total_pnl += pnl
                    if pnl >= 0:
                        wins += 1
                    else:
                        losses += 1
                    fills.append(
                        {
                            "side": "buy",
                            "price": price,
                            "quantity": 100,
                            "pnl": pnl,
                            "tick_index": tick_index,
                            "executed_at": datetime.utcnow(),
                            "event": "exit_short",
                        }
                    )
                    position = None
        prev_price = price
        if speed > 1 and tick_index % int(speed) == 0:
            time.sleep(0.001)

    closed = wins + losses
    ticks_simulated = tick_index + 1 if prev_price is not None else 0
    metrics = {
        "bars": len(candles),
        "ticks_simulated": ticks_simulated,
        "session_vwap": vwap,
        "fills": len(fills),
        "round_trips": closed,
        "wins": wins,
        "losses": losses,
        "total_pnl": round(total_pnl, 2),
        "win_rate_pct": round(wins / closed * 100, 1) if closed else 0.0,
        "strategy": strategy,
        "engine": "tick_sim",
    }
    return fills, metrics


def _post_session_hooks(db: Session, row: ReplaySession, fills: list[dict[str, Any]]) -> None:
    """Feed journal, backtest row, optional Ollama — runs after sim completes."""
    settings = get_settings()
    metrics = row.metrics or {}
    sym = row.symbol

    if settings.replay_feed_journal:
        for i, f in enumerate(fills):
            if f.get("event", "").startswith("exit"):
                ext_id = f"replay-{row.job_id}-{i}"
                existing = db.query(Trade).filter(Trade.external_id == ext_id).first()
                if existing:
                    continue
                db.add(
                    Trade(
                        external_id=ext_id,
                        source="replay",
                        symbol=sym,
                        side=f["side"],
                        quantity=int(f.get("quantity", 100)),
                        price=float(f["price"]),
                        pnl=f.get("pnl"),
                        executed_at=f.get("executed_at", datetime.utcnow()),
                        raw_payload={"job_id": row.job_id, **f},
                    )
                )
        note = (
            f"Replay {row.job_id} on {sym}: {metrics.get('round_trips', 0)} RT, "
            f"PnL {metrics.get('total_pnl', 0)}, WR {metrics.get('win_rate_pct', 0)}%"
        )
        db.add(
            JournalEntry(
                title=f"Replay training {sym}",
                content=note,
                tags=["replay", "training", sym.lower(), row.strategy_name],
                ai_generated=False,
            )
        )

    db.add(
        BacktestRun(
            engine="replay",
            symbol=sym,
            parameters={"strategy": row.strategy_name, "job_id": row.job_id},
            metrics=metrics,
            notes=f"Replay training session {row.job_id}",
        )
    )

    if settings.replay_feed_wfo:
        try:
            from src.services.walk_forward_promotion import run_walk_forward_promotion

            run_walk_forward_promotion(db, folds=2)
        except Exception as exc:
            logger.warning("replay_wfo_hook_failed", error=str(exc))

    if settings.replay_ollama_summary and settings.ollama_runtime_enabled:
        try:
            from src.integrations.ollama_client import get_ollama_client

            client = get_ollama_client()
            if client.is_available():
                summary = client.chat(
                    f"Summarize this replay in 3 bullets for a B3 scalper:\n{metrics}\n"
                    f"Fills count: {len(fills)}",
                )
                if summary and not summary.startswith("[Ollama offline"):
                    db.add(
                        JournalEntry(
                            title=f"Ollama replay insight {sym}",
                            content=summary,
                            tags=["replay", "ollama", sym.lower()],
                            ai_generated=True,
                        )
                    )
        except Exception as exc:
            logger.debug("replay_ollama_skip", error=str(exc))

    from src.autonomous.engine_mind import get_engine_mind

    get_engine_mind().record_cycle(
        "replay_complete",
        symbol=sym,
        meta={"job_id": row.job_id, "fills": len(fills), **metrics},
    )

    if get_settings().knowledge_runtime_enabled:
        try:
            from src.services.knowledge.replay_ingest import ingest_replay_session

            ingest_replay_session(db, row.job_id)
        except Exception as exc:
            logger.debug("replay_knowledge_ingest_skip", error=str(exc))


def get_replay(job_id: str, session: Session | None = None) -> dict[str, Any] | None:
    from src.models import get_session_factory

    own = session is None
    db = session or get_session_factory()()
    try:
        row = db.query(ReplaySession).filter(ReplaySession.job_id == job_id).first()
        if not row:
            return None
        payload = _session_to_dict(row)
        fills = (
            db.query(ReplayFill)
            .filter(ReplayFill.session_id == row.id)
            .order_by(ReplayFill.tick_index)
            .limit(200)
            .all()
        )
        payload["fills"] = [
            {
                "side": f.side,
                "price": f.price,
                "pnl": f.pnl,
                "tick_index": f.tick_index,
            }
            for f in fills
        ]
        return payload
    finally:
        if own:
            db.close()


def run_training_cycle(session: Session) -> dict[str, Any]:
    """Scheduler entry — parallel replays per effective_replay_workers."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from src.autonomous.engine_mind import get_engine_mind
    from src.models import get_session_factory

    settings = get_settings()
    if not settings.replay_training_enabled:
        return {"skipped": True, "reason": "disabled"}

    breaker = get_breaker("replay_training")
    if breaker.is_open():
        return {"skipped": True, "reason": "circuit_open"}

    mind = get_engine_mind()
    mind.record_cycle("replay_cycle_start", meta={})

    sym = settings.golden_path_symbol if settings.golden_path_mode else "PETR4"
    workers = settings.effective_replay_workers
    symbols = list(dict.fromkeys([sym] + settings.scanner_symbol_list[:workers]))[:workers]

    if settings.strategy_store_enabled:
        from src.services.strategy_store import scan_strategy_directories

        scan_strategy_directories(session)
        if settings.knowledge_runtime_enabled:
            from src.services.knowledge.replay_ingest import ingest_all_stored_strategies

            ingest_all_stored_strategies(session, limit=20)

    from src.models import StoredStrategy

    default_strat = "scalp_default"
    latest_stored = (
        session.query(StoredStrategy)
        .order_by(StoredStrategy.last_scanned_at.desc())
        .first()
    )
    if latest_stored:
        default_strat = latest_stored.name

    def _one(symbol: str) -> dict[str, Any]:
        s = get_session_factory()()
        try:
            return start_replay(
                strategy=default_strat,
                symbol=symbol,
                speed=20.0,
                mode="training",
                session=s,
            )
        finally:
            s.close()

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, symbol): symbol for symbol in symbols}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                logger.warning("parallel_replay_failed", symbol=futures[fut], error=str(exc))
                breaker.record_failure()

    mind.record_cycle("replay_cycle_done", meta={"runs": len(results)})
    return {"runs": len(results), "sessions": results, "parallel_workers": workers}


def list_recent_sessions(session: Session, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        session.query(ReplaySession)
        .order_by(ReplaySession.started_at.desc())
        .limit(limit)
        .all()
    )
    return [_session_to_dict(r) for r in rows]


def _session_to_dict(row: ReplaySession) -> dict[str, Any]:
    return {
        "job_id": row.job_id,
        "id": row.id,
        "strategy": row.strategy_name,
        "symbol": row.symbol,
        "speed": row.speed,
        "mode": row.mode,
        "status": row.status,
        "source": row.source,
        "progress_pct": row.progress_pct,
        "fill_count": row.fill_count,
        "message": row.message,
        "metrics": row.metrics,
        "started_at": row.started_at.isoformat() + "Z" if row.started_at else None,
        "completed_at": row.completed_at.isoformat() + "Z" if row.completed_at else None,
        "fills": [],
    }


def purge_old_sessions(session: Session, *, days: int = 14) -> int:
    """Keep replay DB lean — deletes old sessions + fills."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    old = session.query(ReplaySession).filter(ReplaySession.started_at < cutoff).all()
    n = 0
    for row in old:
        session.query(ReplayFill).filter(ReplayFill.session_id == row.id).delete()
        session.delete(row)
        n += 1
    session.commit()
    return n
