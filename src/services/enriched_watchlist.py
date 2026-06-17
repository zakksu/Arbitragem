"""Single pipeline for GET /watchlist/enriched — Core14 + futures + crypto (4.x)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.services.resource_profile import get_resource_profile
from src.integrations.profit_bridge import get_profit_client
from src.services.crypto_quotes import build_crypto_watchlist_rows
from src.services.filipe_universe import load_filipe_core14
from src.services.futures_quotes import build_futures_watchlist_rows
from src.services.risk_profile import get_or_create_profile
from src.services.trade_ideas import TradeIdeaService
from src.services.watchlist_enrich import enrich_watchlist_rows

_CORE14_FALLBACK: list[dict[str, str]] = [
    {"symbol": "PETR4", "name": "Petrobras PN", "sector": "Energia"},
    {"symbol": "VALE3", "name": "Vale ON", "sector": "Mineração"},
    {"symbol": "PRIO3", "name": "PetroRio ON", "sector": "Energia"},
    {"symbol": "ITUB4", "name": "Itaú PN", "sector": "Financeiro"},
    {"symbol": "BBAS3", "name": "Banco do Brasil ON", "sector": "Financeiro"},
    {"symbol": "BBDC4", "name": "Bradesco PN", "sector": "Financeiro"},
    {"symbol": "BBSE3", "name": "BB Seguridade ON", "sector": "Financeiro"},
    {"symbol": "B3SA3", "name": "B3 ON", "sector": "Financeiro"},
    {"symbol": "ABEV3", "name": "Ambev ON", "sector": "Consumo"},
    {"symbol": "GGBR4", "name": "Gerdau PN", "sector": "Siderurgia"},
    {"symbol": "CSNA3", "name": "CSN ON", "sector": "Siderurgia"},
    {"symbol": "USIM5", "name": "Usiminas PN", "sector": "Siderurgia"},
    {"symbol": "SUZB3", "name": "Suzano ON", "sector": "Papel"},
    {"symbol": "WEGE3", "name": "WEG ON", "sector": "Industrial"},
]


def build_enriched_watchlist(session: Session) -> dict[str, Any]:
    """Return enriched watchlist payload — shared by API and board partials."""
    settings = get_settings()
    res_profile = get_resource_profile(settings)
    if settings.golden_path_mode:
        sym = settings.golden_path_symbol
        rows: list[dict[str, Any]] = [
            {"symbol": sym, "name": "Petrobras PN", "sector": "Energia", "asset_class": "equity"}
        ]
    else:
        symbols = load_filipe_core14()
        rows = (
            [s.to_dict() for s in symbols] if symbols else [dict(s) for s in _CORE14_FALLBACK]
        )
        for row in rows:
            row.setdefault("asset_class", "equity")
        if settings.futures_watchlist_enabled and res_profile.watchlist_extra_universes:
            rows.extend(build_futures_watchlist_rows())
        if settings.crypto_watchlist_enabled and res_profile.watchlist_extra_universes:
            rows.extend(build_crypto_watchlist_rows())

    eq_syms = [
        r["symbol"]
        for r in rows
        if r.get("asset_class") not in ("future", "crypto") and r.get("symbol")
    ]
    batch = get_profit_client().get_quotes_batch(eq_syms)
    for row in rows:
        if row.get("asset_class") in ("future", "crypto"):
            continue
        q = batch.get(row["symbol"])
        if q:
            row["last"] = q.last
            row["bid"] = q.bid
            row["ask"] = q.ask

    svc = TradeIdeaService(session)
    ideas = [svc.to_dict(i) for i in svc.list_ideas(limit=res_profile.watchlist_ideas_limit)]
    risk_profile = get_or_create_profile(session)
    enriched = enrich_watchlist_rows(rows, ideas, cost_per_trade_brl=risk_profile.cost_per_trade_brl)
    from src.services.paper_graduation import graduation_status

    for row in enriched:
        if row.get("asset_class") in ("future", "crypto", "futures"):
            continue
        g = graduation_status(session, row["symbol"])
        row["graduated"] = g.get("graduated", False)
        gates = g.get("gates") or {}
        row["graduation_gates_ok"] = sum(1 for v in gates.values() if v)
        row["graduation_gates_total"] = len(gates) or 4
    futures = [r for r in enriched if r.get("asset_class") == "future"]
    crypto = [r for r in enriched if r.get("asset_class") == "crypto"]
    return {
        "symbols": enriched,
        "count": len(enriched),
        "futures": futures,
        "futures_count": len(futures),
        "crypto": crypto,
        "crypto_count": len(crypto),
    }
