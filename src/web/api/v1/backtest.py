"""Strategy Lab — backtest rankings API (v1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.autonomous.backtest_rankings import BacktestRankingsService
from src.models import get_session_factory

router = APIRouter()


def get_db():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@router.get("/rankings")
def list_rankings(
    symbol: str | None = None,
    sector: str | None = None,
    structure_type: str | None = Query(None, alias="type"),
    period_days: int | None = Query(None, alias="period"),
    sort_by: str = Query("idea_score", pattern="^(idea_score|wf_score|profit_factor|max_drawdown_pct|win_rate|last_optimized_at)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    svc = BacktestRankingsService(db)
    rows = svc.list_rankings(
        symbol=symbol,
        sector=sector,
        structure_type=structure_type,
        period_days=period_days,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return {"count": len(rows), "rankings": rows}


@router.get("/rankings/{ranking_id}")
def get_ranking(
    ranking_id: int,
    commentary: bool = False,
    db: Session = Depends(get_db),
):
    svc = BacktestRankingsService(db)
    detail = svc.get_detail(ranking_id, refresh_commentary=commentary)
    if not detail:
        raise HTTPException(404, "Ranking not found")
    return detail


@router.post("/rankings/sync")
def sync_rankings(db: Session = Depends(get_db)):
    svc = BacktestRankingsService(db)
    n = svc.sync_from_optimization_runs()
    return {"synced": n}


@router.post("/rankings/{ranking_id}/promote")
def promote_ranking(ranking_id: int, db: Session = Depends(get_db)):
    svc = BacktestRankingsService(db)
    try:
        idea = svc.promote_to_idea_stack(ranking_id)
    except ValueError as exc:
        msg = str(exc)
        if "gate" in msg.lower():
            raise HTTPException(400, msg) from exc
        raise HTTPException(404, msg) from exc
    return {"promoted": True, "idea": idea}
