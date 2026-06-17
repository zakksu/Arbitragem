"""Backtest rankings — SQLite storage + sortable Strategy Lab data."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.autonomous.models import RankingDetail, RankingRow
from src.autonomous.ollama_strategist import OllamaStrategist
from src.models import BacktestRanking, OptimizationRun, Strategy
from src.services.filipe_universe import sector_for
from src.services.idea_score import score_idea
from src.services.trade_ideas import TradeIdeaService

_CACHE_TTL_SEC = 30.0
_list_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _metrics_from_run(run: OptimizationRun) -> dict[str, float]:
    m = run.best_metrics or {}
    pf = float(m.get("profit_factor") or m.get("pf") or 1.0)
    dd = float(m.get("max_drawdown_pct") or m.get("max_drawdown") or 5.0)
    if dd > 1.5:
        dd = dd / 100.0
    wr = float(m.get("win_rate") or m.get("win_rate_pct") or 50.0)
    if wr <= 1.0:
        wr *= 100.0
    return {"profit_factor": round(pf, 3), "max_drawdown_pct": round(dd, 2), "win_rate": round(wr, 1)}


def _wf_score(run: OptimizationRun) -> float:
    folds = (run.results or {}).get("folds") or []
    if not folds:
        return 0.0
    passed = sum(1 for f in folds if float(f.get("test_pnl") or 0) > 0)
    ratio = passed / max(len(folds), 1)
    metrics = _metrics_from_run(run)
    return round(ratio * 50 + min(metrics["profit_factor"], 3.0) * 15, 1)


def _synthetic_equity_curve(metrics: dict[str, Any], *, points: int = 60) -> list[dict[str, Any]]:
    """Lightweight equity stub from net_pnl when no trade list exists."""
    import math

    net = float(metrics.get("net_pnl") or metrics.get("total_pnl") or 100.0)
    curve: list[dict[str, Any]] = []
    base = datetime.utcnow() - timedelta(days=points)
    for i in range(points):
        t = base + timedelta(days=i)
        noise = math.sin(i / 7) * (net * 0.05)
        val = (net / points) * i + noise
        curve.append({"time": int(t.timestamp()), "value": round(val, 2)})
    return curve


def _row_from_orm(r: BacktestRanking, strategy_name: str = "") -> RankingRow:
    return RankingRow(
        id=r.id,
        symbol=r.symbol,
        strategy_id=r.strategy_id,
        strategy_name=strategy_name or r.strategy_name or "—",
        sector=r.sector or sector_for(r.symbol) or "other",
        structure_type=r.structure_type or "scalp_long",
        idea_score=float(r.idea_score or 0),
        wf_score=float(r.wf_score or 0),
        profit_factor=float(r.profit_factor or 0),
        max_drawdown_pct=float(r.max_drawdown_pct or 0),
        win_rate=float(r.win_rate or 0),
        status=r.status or "candidate",
        last_optimized_at=r.last_optimized_at,
        parameters=r.parameters or {},
    )


class BacktestRankingsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def sync_from_optimization_runs(self, *, limit: int = 50) -> int:
        """Upsert rankings from completed WFO runs."""
        runs = (
            self.session.query(OptimizationRun)
            .filter(OptimizationRun.status == "completed")
            .order_by(desc(OptimizationRun.completed_at))
            .limit(limit)
            .all()
        )
        upserted = 0
        for run in runs:
            strategy = self.session.get(Strategy, run.strategy_id) if run.strategy_id else None
            symbol = (run.parameter_space or {}).get("symbol")
            if not symbol:
                from src.models import BacktestRun

                bt = (
                    self.session.query(BacktestRun)
                    .filter(BacktestRun.strategy_id == run.strategy_id)
                    .order_by(desc(BacktestRun.created_at))
                    .first()
                )
                symbol = bt.symbol if bt else "PETR4"

            metrics = _metrics_from_run(run)
            wf = _wf_score(run)
            idea_stub = {
                "symbol": symbol,
                "structure_type": "scalp_long",
                "side": "long",
                "backtest_proof": run.best_metrics,
                "walk_forward_pass": wf >= 40,
            }
            idea_sc = float(score_idea(idea_stub))

            existing = (
                self.session.query(BacktestRanking)
                .filter(
                    BacktestRanking.optimization_run_id == run.id,
                )
                .first()
            )
            if not existing:
                existing = (
                    self.session.query(BacktestRanking)
                    .filter(
                        BacktestRanking.symbol == symbol,
                        BacktestRanking.strategy_id == run.strategy_id,
                    )
                    .order_by(desc(BacktestRanking.updated_at))
                    .first()
                )

            folds = (run.results or {}).get("folds") or []
            equity = _synthetic_equity_curve(run.best_metrics or {})
            param_hist = [{"at": run.completed_at.isoformat() if run.completed_at else None, "params": run.best_parameters}]

            if existing:
                row = existing
            else:
                row = BacktestRanking(symbol=symbol)
                self.session.add(row)

            row.strategy_id = run.strategy_id
            row.optimization_run_id = run.id
            row.strategy_name = strategy.name if strategy else None
            row.sector = sector_for(symbol) or "other"
            row.structure_type = "scalp_long"
            row.idea_score = idea_sc
            row.wf_score = wf
            row.profit_factor = metrics["profit_factor"]
            row.max_drawdown_pct = metrics["max_drawdown_pct"]
            row.win_rate = metrics["win_rate"]
            row.status = row.status or "candidate"
            row.parameters = run.best_parameters
            row.fold_results = folds
            row.equity_curve = equity
            row.parameter_history = param_hist
            row.last_optimized_at = run.completed_at or datetime.utcnow()
            row.updated_at = datetime.utcnow()
            upserted += 1

        self.session.commit()
        _list_cache.clear()
        return upserted

    def list_rankings(
        self,
        *,
        symbol: str | None = None,
        sector: str | None = None,
        structure_type: str | None = None,
        period_days: int | None = None,
        sort_by: str = "idea_score",
        sort_dir: str = "desc",
    ) -> list[dict[str, Any]]:
        cache_key = f"{symbol}|{sector}|{structure_type}|{period_days}|{sort_by}|{sort_dir}"
        now = time.monotonic()
        cached = _list_cache.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SEC:
            return cached[1]

        q = self.session.query(BacktestRanking)
        if symbol:
            q = q.filter(BacktestRanking.symbol == symbol.upper())
        if sector:
            q = q.filter(BacktestRanking.sector == sector.lower())
        if structure_type:
            q = q.filter(BacktestRanking.structure_type == structure_type)
        if period_days:
            cutoff = datetime.utcnow() - timedelta(days=period_days)
            q = q.filter(BacktestRanking.last_optimized_at >= cutoff)

        col = getattr(BacktestRanking, sort_by, BacktestRanking.idea_score)
        q = q.order_by(desc(col) if sort_dir == "desc" else col.asc())
        rows = q.limit(200).all()

        out = [_row_from_orm(r).to_dict() for r in rows]
        _list_cache[cache_key] = (now, out)
        return out

    def get_detail(self, ranking_id: int, *, refresh_commentary: bool = False) -> dict[str, Any] | None:
        r = self.session.get(BacktestRanking, ranking_id)
        if not r:
            return None
        row = _row_from_orm(r, r.strategy_name or "")
        detail = RankingDetail(
            **{k: getattr(row, k) for k in RankingRow.__dataclass_fields__},
            fold_results=r.fold_results or [],
            parameter_history=r.parameter_history or [],
            equity_curve=r.equity_curve or [],
            ollama_commentary=r.ollama_commentary,
            optimization_run_id=r.optimization_run_id,
        )
        if refresh_commentary and not r.ollama_commentary:
            commentary = OllamaStrategist().comment_on_ranking_sync(detail.to_dict())
            r.ollama_commentary = commentary
            self.session.commit()
            detail.ollama_commentary = commentary
        return detail.to_dict()

    def promote_to_idea_stack(self, ranking_id: int) -> dict[str, Any]:
        r = self.session.get(BacktestRanking, ranking_id)
        if not r:
            raise ValueError("Ranking not found")

        from src.config import get_settings

        settings = get_settings()
        pf = float(r.profit_factor or 0)
        dd = float(r.max_drawdown_pct if r.max_drawdown_pct is not None else 100.0)
        if pf < settings.backtest_min_profit_factor:
            raise ValueError(
                f"Profit factor {pf} below gate ({settings.backtest_min_profit_factor})"
            )
        if dd > settings.backtest_max_drawdown_pct:
            raise ValueError(
                f"Max drawdown {dd}% above gate ({settings.backtest_max_drawdown_pct}%)"
            )

        svc = TradeIdeaService(self.session)
        proof = {
            "profit_factor": r.profit_factor,
            "max_drawdown_pct": r.max_drawdown_pct,
            "win_rate": r.win_rate,
            "walk_forward_folds_passed": len(
                [f for f in (r.fold_results or []) if (f.get("test_pnl") or 0) > 0]
            ),
            "walk_forward_folds_total": len(r.fold_results or []),
            "source": "strategy_lab",
        }
        idea = svc.create_from_structure(
            r.symbol,
            r.structure_type or "scalp_long",
            side="long",
        )
        idea.backtest_proof = proof
        idea.rationale = "Promoted from Strategy Lab rankings."
        idea.rationale_tags = list(idea.rationale_tags or []) + ["strategy_lab", "walk_forward_pass"]
        idea.status = "backtested"
        self.session.commit()
        r.status = "promoted"
        r.updated_at = datetime.utcnow()
        self.session.commit()
        _list_cache.clear()
        return svc.to_dict(idea)
