"""Weekly strategy simulation report — tick replay on session candles + paper book."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import ReplaySession, Trade
from src.services.filipe_universe import CORE5_STOCKS
from src.services.futures_universe import symbol_list as futures_symbols
from src.services.replay_batch import strategies_for_symbol
from src.services.structure_types import STRUCTURE_CATALOG, STRUCTURE_TO_REPLAY_STRATEGY

REPLAY_TO_STRUCTURE = {v: k for k, v in STRUCTURE_TO_REPLAY_STRATEGY.items()}

STRATEGY_LABELS: dict[str, str] = {
    row["id"]: row["label"]
    for row in STRUCTURE_CATALOG
    if row["id"] in STRUCTURE_TO_REPLAY_STRATEGY
    or row["id"].startswith("futures_")
}
for replay_id, struct_id in REPLAY_TO_STRUCTURE.items():
    for row in STRUCTURE_CATALOG:
        if row["id"] == struct_id:
            STRATEGY_LABELS[replay_id] = row["label"]
            break


def _week_window(days: int = 7) -> tuple[datetime, datetime]:
    end = datetime.utcnow()
    start = end - timedelta(days=max(1, days))
    return start, end


REPLAY_LABELS: dict[str, str] = {
    "s1_vwap_reclaim": "VWAP reclaim (S1)",
    "s2_orb_break": "Opening range (S2)",
    "s3_bb_fade": "Mean reversion (S3)",
    "s4_arch_bias": "Archaeology bias (S4)",
    "s5_pulse": "Pulse scalp (S5)",
    "f1_open_drive": "Open drive (F1)",
    "f2_vwap_reclaim": "Futures VWAP (F2)",
    "f3_lunch_fade": "Lunch fade (F3)",
    "f4_afternoon_trend": "Afternoon trend (F4)",
    "f5_failed_breakout": "Failed breakout (F5)",
    "scalp_default": "Core14 scalp",
}


def _label(strategy_id: str) -> str:
    key = strategy_id.strip().lower()
    return REPLAY_LABELS.get(key) or STRATEGY_LABELS.get(key, strategy_id.replace("_", " ").title())


def _pf_from_metrics(metrics: dict[str, Any]) -> float | None:
    wins = int(metrics.get("wins") or 0)
    losses = int(metrics.get("losses") or 0)
    if wins + losses == 0:
        return None
    total = float(metrics.get("total_pnl") or 0)
    if total == 0:
        return 1.0
    if wins > 0 and losses == 0:
        return round(2.0 + wins * 0.1, 2)
    if losses > 0 and wins == 0:
        return 0.5
    avg = total / max(wins + losses, 1)
    gross_win = max(avg * wins, 0.01)
    gross_loss = max(abs(avg * losses), 0.01)
    return round(gross_win / gross_loss, 2)


def _gate_pass(metrics: dict[str, Any]) -> bool:
    pf = _pf_from_metrics(metrics)
    pnl = float(metrics.get("total_pnl") or 0)
    wr = float(metrics.get("win_rate_pct") or 0)
    trips = int(metrics.get("round_trips") or metrics.get("fills") or 0)
    if trips < 2:
        return False
    if pf is not None and pf < 1.2:
        return False
    if pnl < 0 and wr < 45:
        return False
    return pnl >= 0 or wr >= 50


def _aggregate_paper_trades(session: Session, start: datetime) -> list[dict[str, Any]]:
    rows = (
        session.query(
            Trade.symbol,
            func.count(Trade.id).label("trades"),
            func.coalesce(func.sum(Trade.pnl), 0.0).label("net_pnl"),
        )
        .filter(Trade.executed_at >= start, Trade.source.in_(("paper", "replay", "motor")))
        .group_by(Trade.symbol)
        .all()
    )
    out = []
    for sym, trades, net in rows:
        out.append(
            {
                "symbol": sym,
                "trades": int(trades),
                "net_pnl_brl": round(float(net or 0), 2),
            }
        )
    out.sort(key=lambda x: x["net_pnl_brl"], reverse=True)
    return out


def _load_replay_rows(session: Session, start: datetime) -> list[ReplaySession]:
    return (
        session.query(ReplaySession)
        .filter(
            ReplaySession.started_at >= start,
            ReplaySession.status == "completed",
        )
        .order_by(ReplaySession.started_at.desc())
        .all()
    )


def _run_fresh_sims(
    session: Session,
    *,
    symbols: list[str],
    max_pairs: int = 25,
) -> list[dict[str, Any]]:
    """Fast tick sim on session candles — no WFO/Ollama hooks."""
    from src.services.replay_engine import _run_tick_simulation

    fresh: list[dict[str, Any]] = []
    count = 0
    for sym in symbols:
        for strat in strategies_for_symbol(sym):
            if count >= max_pairs:
                break
            try:
                _fills, metrics = _run_tick_simulation(sym, strat, speed=50.0)
                row = ReplaySession(
                    job_id=f"wk-{sym}-{strat}-{count}",
                    symbol=sym,
                    strategy_name=strat,
                    status="completed",
                    speed=50.0,
                    mode="weekly_sim",
                    source="tick_sim",
                    progress_pct=100.0,
                    fill_count=int(metrics.get("fills") or 0),
                    metrics=metrics,
                    message="Weekly sim (lightweight)",
                    completed_at=datetime.utcnow(),
                )
                session.add(row)
                fresh.append(
                    {
                        "symbol": sym,
                        "strategy": strat,
                        "label": _label(strat),
                        "source": "tick_sim",
                        "metrics": metrics,
                        "fresh": True,
                    }
                )
                count += 1
            except Exception as exc:
                fresh.append(
                    {
                        "symbol": sym,
                        "strategy": strat,
                        "label": _label(strat),
                        "error": str(exc)[:200],
                        "fresh": True,
                    }
                )
                count += 1
        if count >= max_pairs:
            break
    session.commit()
    return fresh


def build_weekly_strategy_report(
    session: Session,
    *,
    days: int = 7,
    run_sim: bool = False,
    max_fresh: int = 25,
) -> dict[str, Any]:
    """Aggregate replay + paper performance for the trailing week."""
    start, end = _week_window(days)
    symbols = list(CORE5_STOCKS) + list(futures_symbols())[:2]

    if run_sim:
        _run_fresh_sims(session, symbols=symbols, max_pairs=max_fresh)

    replay_rows = _load_replay_rows(session, start)
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for row in replay_rows:
        key = (row.symbol.upper(), row.strategy_name)
        metrics = row.metrics or {}
        if key in by_key:
            continue
        by_key[key] = {
            "symbol": row.symbol.upper(),
            "strategy": row.strategy_name,
            "label": _label(row.strategy_name),
            "source": row.source,
            "metrics": metrics,
            "fill_count": row.fill_count,
            "simulated_at": row.completed_at.isoformat() if row.completed_at else None,
            "gate_pass": _gate_pass(metrics),
            "profit_factor": _pf_from_metrics(metrics),
            "net_pnl_brl": round(float(metrics.get("total_pnl") or 0), 2),
            "win_rate_pct": metrics.get("win_rate_pct"),
            "round_trips": metrics.get("round_trips"),
        }

    strategies = sorted(by_key.values(), key=lambda x: x.get("net_pnl_brl", 0), reverse=True)
    paper_book = _aggregate_paper_trades(session, start)
    total_sim_pnl = sum(s.get("net_pnl_brl", 0) for s in strategies)
    total_paper_pnl = sum(p["net_pnl_brl"] for p in paper_book)
    passed = [s for s in strategies if s.get("gate_pass")]
    failed = [s for s in strategies if not s.get("gate_pass") and s.get("round_trips")]

    return {
        "period_days": days,
        "week_start": start.date().isoformat(),
        "week_end": end.date().isoformat(),
        "generated_at": end.isoformat() + "Z",
        "disclaimer": (
            "Tick replay on Profit session candles (VWAP reclaim logic). "
            "Not a guarantee of live results — validate in Profit NTSL."
        ),
        "summary": {
            "strategy_pairs_simulated": len(strategies),
            "gate_pass_count": len(passed),
            "gate_fail_count": len(failed),
            "total_sim_pnl_brl": round(total_sim_pnl, 2),
            "total_paper_pnl_brl": round(total_paper_pnl, 2),
            "best_strategy": strategies[0] if strategies else None,
            "worst_strategy": strategies[-1] if strategies else None,
        },
        "strategies": strategies,
        "paper_book_by_symbol": paper_book,
        "ranked_pass": sorted(passed, key=lambda x: x.get("profit_factor") or 0, reverse=True)[:5],
    }


def format_weekly_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Weekly strategy simulation ({report['week_start']} to {report['week_end']})",
        "",
        f"_{report.get('disclaimer', '')}_",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Pairs simulated | {report['summary']['strategy_pairs_simulated']} |",
        f"| Gate pass | {report['summary']['gate_pass_count']} |",
        f"| Sim P&L (week) | R$ {report['summary']['total_sim_pnl_brl']:.2f} |",
        f"| Paper P&L (week) | R$ {report['summary']['total_paper_pnl_brl']:.2f} |",
        "",
        "## Top strategies (sim)",
        "",
        "| Rank | Strategy | Symbol | P&L | PF | Win% | Gate |",
        "|------|----------|--------|-----|----|----- |------|",
    ]
    for i, s in enumerate(report.get("strategies", [])[:12], 1):
        gate = "PASS" if s.get("gate_pass") else "fail"
        pf = s.get("profit_factor")
        pf_s = f"{pf:.2f}" if pf is not None else "-"
        wr = s.get("win_rate_pct")
        wr_s = f"{wr:.1f}" if wr is not None else "-"
        lines.append(
            f"| {i} | {s.get('label', s.get('strategy'))} | {s.get('symbol')} | "
            f"R$ {s.get('net_pnl_brl', 0):.2f} | {pf_s} | {wr_s}% | {gate} |"
        )
    if report.get("paper_book_by_symbol"):
        lines.extend(["", "## Paper book by symbol", "", "| Symbol | Trades | Net P&L |", "|--------|--------|---------|"])
        for p in report["paper_book_by_symbol"][:10]:
            lines.append(f"| {p['symbol']} | {p['trades']} | R$ {p['net_pnl_brl']:.2f} |")
    return "\n".join(lines) + "\n"
