"""AI symbol report card — Ollama + scan + backtest + sector (A2.9)."""

from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.integrations.ollama_client import get_ollama_client
from src.integrations.profit_bridge import get_profit_client
from src.models import ScanResult, TradeIdea
from src.services.filipe_universe import sector_for

_CACHE_TTL_SEC = 24 * 3600
_cache: dict[str, tuple[float, dict]] = {}


def _latest_scan(session: Session, symbol: str) -> ScanResult | None:
    return (
        session.query(ScanResult)
        .filter(ScanResult.symbol == symbol.upper())
        .order_by(desc(ScanResult.scan_date))
        .first()
    )


def _latest_backtest_proof(session: Session, symbol: str) -> dict | None:
    sym = symbol.upper()
    idea = (
        session.query(TradeIdea)
        .filter(TradeIdea.symbol == sym, TradeIdea.backtest_proof.isnot(None))
        .order_by(desc(TradeIdea.created_at))
        .first()
    )
    return idea.backtest_proof if idea else None


def build_symbol_report(session: Session, symbol: str, *, force: bool = False) -> dict:
    sym = symbol.strip().upper()
    now = time.time()
    cached = _cache.get(sym)
    if cached and not force and now - cached[0] < _CACHE_TTL_SEC:
        out = dict(cached[1])
        out["cached"] = True
        return out

    quote = get_profit_client().get_quote(sym)
    scan = _latest_scan(session, sym)
    proof = _latest_backtest_proof(session, sym)
    sector = sector_for(sym) or ""

    quote_ctx = (
        f"last={quote.last} bid={quote.bid} ask={quote.ask} vol={quote.volume}"
        if quote
        else "no quote"
    )
    scan_ctx = ""
    if scan:
        tags = ", ".join(scan.pattern_tags or [])
        scan_ctx = (
            f"scan spike={scan.spike_score} tags={tags} "
            f"change%={scan.price_change_pct} raw={scan.raw_data or {}}"
        )
    proof_ctx = str(proof) if proof else "no backtest proof on file"

    prompt = (
        f"Symbol report card for {sym} (sector: {sector or 'n/a'}).\n"
        "Sections: Tape read, Strengths/weaknesses, Catalysts, Short-session bias "
        "(not financial advice), Backtest summary, 1-2 suggested structures.\n"
        f"Quote: {quote_ctx}\n"
        f"Latest scan: {scan_ctx or 'none'}\n"
        f"Backtest proof: {proof_ctx}"
    )
    narrative = get_ollama_client().chat(prompt)

    report = {
        "symbol": sym,
        "sector": sector,
        "generated_at": datetime.utcnow().isoformat(),
        "cached": False,
        "quote": (
            {
                "last": quote.last,
                "bid": quote.bid,
                "ask": quote.ask,
                "volume": quote.volume,
            }
            if quote
            else None
        ),
        "scan": (
            {
                "scan_date": scan.scan_date.isoformat() if scan.scan_date else None,
                "spike_score": scan.spike_score,
                "pattern_tags": scan.pattern_tags,
                "price_change_pct": scan.price_change_pct,
            }
            if scan
            else None
        ),
        "backtest_proof": proof,
        "narrative": narrative,
    }
    _cache[sym] = (now, report)
    return report
