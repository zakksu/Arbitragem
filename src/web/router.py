"""HTMX blackboard routes — partials wired to /api/v1 universe + ideas."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, TypeVar

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.config import get_settings
from src.integrations.profit_bridge import ProfitBridgeClient, get_profit_client
from src.services.bootstrap_context import build_bootstrap
from src.services.filipe_universe import load_filipe_core14, SECTOR_BASKETS
from src.services.risk_cockpit import build_risk_cockpit
from src.services.risk_summary import build_risk_summary
from src.web.deps import TEMPLATES

T = TypeVar("T")

router = APIRouter(tags=["blackboard"])

# Frozen Core14 — matches RELEASE_2.0.0 when API not yet mounted
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

def _pulse_rail_with_social_sync() -> dict[str, Any]:
    from src.config import get_settings
    from src.services.pulse_rail import get_pulse_rail
    from src.services.social_signals import get_social_signals

    pulse = get_pulse_rail()
    if not get_settings().social_signals_runtime_enabled:
        return pulse
    social = get_social_signals(limit=8)
    out = dict(pulse)
    out["social_signals"] = social.get("signals") or []
    out["social_disclaimer"] = social.get("disclaimer")
    return out


def _api_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


async def _to_thread(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await asyncio.to_thread(fn, *args, **kwargs)


def _with_db(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    from src.models import get_session_factory

    session = get_session_factory()()
    try:
        return fn(session, *args, **kwargs)
    finally:
        session.close()


def _idea_gates_sync(idea_id: int) -> dict[str, Any] | None:
    from src.services.idea_gates import build_idea_gates

    try:
        return _with_db(build_idea_gates, idea_id)
    except ValueError:
        return None


def _clear_status_sync() -> dict[str, Any]:
    from src.services.clear_router import clear_router_status

    return clear_router_status()


async def _fetch_json(request: Request, path: str, *, timeout: float = 2.0) -> dict[str, Any] | list[Any] | None:
    """Loopback GET for rare cases — prefer direct service calls."""
    url = f"{_api_base(request)}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except httpx.HTTPError:
        pass
    return None


def _universe_payload_sync() -> dict[str, Any]:
    symbols = load_filipe_core14()
    if symbols:
        return {
            "symbols": [s.to_dict() for s in symbols],
            "sector_baskets": SECTOR_BASKETS,
        }
    return {"symbols": [dict(s) for s in _CORE14_FALLBACK], "sector_baskets": SECTOR_BASKETS}


async def _fetch_universe_payload(request: Request) -> dict[str, Any]:
    return await _to_thread(_universe_payload_sync)


async def _fetch_universe(request: Request) -> list[dict[str, Any]]:
    payload = await _fetch_universe_payload(request)
    return list(payload.get("symbols") or [])


def _list_ideas_sync(limit: int = 20, symbol: str | None = None) -> list[dict[str, Any]]:
    from src.services.trade_ideas import TradeIdeaService

    def _load(session):
        svc = TradeIdeaService(session)
        ideas = svc.list_ideas_for_stack(limit=limit, symbol=symbol)
        return [svc.to_dict(i) for i in ideas]

    return _with_db(_load)


async def _fetch_ideas(request: Request) -> list[dict[str, Any]]:
    return await _to_thread(_list_ideas_sync)


async def _fetch_bootstrap(request: Request) -> dict[str, Any] | None:
    try:
        return await _to_thread(_with_db, build_bootstrap)
    except Exception:
        return None


def _quote_map(symbols: list[str]) -> dict[str, Any]:
    client = get_profit_client()
    batch = client.get_quotes_batch(symbols)
    return {sym: batch[sym] for sym in symbols if sym in batch}


def _fast_quote(symbol: str):
    """Instant quote for first paint — SSE stream enriches live prices."""
    return ProfitBridgeClient._synthetic_quote(symbol.strip().upper())


def _watchlist_rows_sync(symbols: list[dict[str, Any]], sym_list: list[str]) -> list[dict[str, Any]]:
    from src.services.risk_profile import get_or_create_profile
    from src.services.trade_ideas import TradeIdeaService
    from src.services.watchlist_enrich import enrich_watchlist_rows

    settings = get_settings()
    profit = get_profit_client()
    if settings.scanner_include_bova_options:
        try:
            chain = profit.get_bova_option_chain()
            for leg in (chain.get("calls") or [])[:4] + (chain.get("puts") or [])[:4]:
                sym = leg.get("symbol")
                if sym and sym not in sym_list:
                    sym_list.append(sym)
                    symbols.append(
                        {"symbol": sym, "name": sym, "sector": "BOVA opt", "strike": leg.get("strike")}
                    )
        except Exception:
            pass
    quotes = _quote_map(sym_list)
    rows: list[dict[str, Any]] = []
    for row in symbols:
        sym = row.get("symbol", "")
        enriched = dict(row)
        q = quotes.get(sym)
        if q:
            enriched["last"] = q.last
            enriched["bid"] = q.bid
            enriched["ask"] = q.ask
        rows.append(enriched)

    def _ideas(session):
        svc = TradeIdeaService(session)
        return [svc.to_dict(i) for i in svc.list_ideas(limit=50)]

    ideas = _with_db(_ideas)

    def _profile(session):
        return get_or_create_profile(session)

    profile = _with_db(_profile)
    return enrich_watchlist_rows(rows, ideas, cost_per_trade_brl=profile.cost_per_trade_brl)


def _fetch_idea_sync(idea_id: int) -> dict[str, Any] | None:
    from src.models import TradeIdea
    from src.services.trade_ideas import TradeIdeaService

    def _load(session):
        idea = session.get(TradeIdea, idea_id)
        if not idea:
            return None
        return TradeIdeaService(session).to_dict(idea)

    return _with_db(_load)


def _option_enrichment(sym: str) -> tuple[Any, Any, Any]:
    client = get_profit_client()
    und = "BOVA11" if sym.startswith("BOVA") or sym == "BOVA11" else sym
    option_chain = client.get_option_chain(und)
    max_pain = (option_chain or {}).get("max_pain")
    if not max_pain and option_chain:
        from src.services.structure_signals import compute_max_pain

        max_pain = compute_max_pain(option_chain)
    iv_data = client.get_iv_rank(und)
    iv_rank_val = iv_data.get("iv_rank") if iv_data else None
    return option_chain, max_pain, iv_rank_val


async def _fetch_risk_summary(request: Request) -> dict[str, Any] | None:
    try:
        return await _to_thread(_with_db, build_risk_summary)
    except Exception:
        return None


async def _fetch_idea(request: Request, idea_id: int) -> dict[str, Any] | None:
    return await _to_thread(_fetch_idea_sync, idea_id)


def _risk_cockpit():
    from src.models import get_session_factory

    session = get_session_factory()()
    try:
        return build_risk_cockpit(session)
    finally:
        session.close()


def _api_error_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
            if isinstance(detail, list):
                return "; ".join(str(d) for d in detail)
            return str(detail)
        return str(body)
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"


@router.get("/board", response_class=HTMLResponse)
async def board_page(request: Request):
    settings = get_settings()
    return TEMPLATES.TemplateResponse(
        request,
        "board.html",
        {"golden_path_mode": settings.golden_path_mode, "low_ram_mode": settings.low_ram_enabled},
    )


@router.get("/board/partials/status", response_class=HTMLResponse)
async def status_partial(request: Request):
    bootstrap = await _fetch_bootstrap(request)
    risk = await _fetch_risk_summary(request)
    cockpit = await _to_thread(_risk_cockpit)

    def _validation(session):
        from src.services.paper_validation import build_paper_validation

        return build_paper_validation(session)

    validation = await _to_thread(_with_db, _validation)
    from src.services.self_healing.health_registry import health_snapshot

    health = await _to_thread(health_snapshot)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/status_bar.html",
        {"bootstrap": bootstrap, "risk": risk, "cockpit": cockpit, "validation": validation, "health": health},
    )


@router.get("/board/partials/watchlist", response_class=HTMLResponse)
async def watchlist_partial(request: Request):
    from src.services.enriched_watchlist import build_enriched_watchlist

    payload = await _to_thread(_with_db, build_enriched_watchlist)
    rows = payload["symbols"]
    active = request.query_params.get("active")
    equity_rows = [r for r in rows if r.get("asset_class") not in ("future", "crypto")]
    return TEMPLATES.TemplateResponse(
        request,
        "partials/watchlist.html",
        {
            "symbols": rows,
            "equity_rows": equity_rows,
            "futures_rows": payload.get("futures") or [],
            "crypto_rows": payload.get("crypto") or [],
            "crypto_count": payload.get("crypto_count") or 0,
            "active_symbol": active,
        },
    )


@router.get("/board/partials/symbol/{symbol}", response_class=HTMLResponse)
async def symbol_partial(request: Request, symbol: str):
    from src.services.crypto_quotes import get_crypto_quotes
    from src.services.crypto_universe import is_crypto, load_crypto_universe

    sym = symbol.strip().upper()
    crypto_sym = is_crypto(sym)
    universe = await _fetch_universe(request)
    meta = next((s for s in universe if s.get("symbol") == sym), None)
    if crypto_sym:
        meta = next((c.to_dict() for c in load_crypto_universe() if c.symbol == sym), meta)

    def _load_note(session):
        from src.services.board_notes import BoardNotesService

        row = BoardNotesService(session).get(sym)
        if not row:
            return None
        return {"symbol": row.symbol, "content": row.content, "updated_at": row.updated_at.isoformat()}

    def _top_idea(session):
        from src.services.trade_ideas import TradeIdeaService

        ideas = TradeIdeaService(session).list_ideas(limit=1, symbol=sym)
        if not ideas:
            return None
        return TradeIdeaService(session).to_dict(ideas[0])

    note = await _to_thread(_with_db, _load_note)
    top_idea = await _to_thread(_with_db, _top_idea)
    if crypto_sym:
        quote = get_crypto_quotes([sym]).get(sym)
        candles = []
        session_vwap = None
    else:
        quote = await _to_thread(_fast_quote, sym)
        candles = await _to_thread(get_profit_client().get_session_candles, sym)
        from src.services.vwap import build_session_vwap_payload

        session_vwap = await _to_thread(build_session_vwap_payload, sym)

    option_chain = None
    max_pain = None
    iv_rank_val = None
    if sym.startswith("BOVA") or sym in ("BOVA11",):
        try:
            option_chain, max_pain, iv_rank_val = await asyncio.wait_for(
                _to_thread(_option_enrichment, sym),
                timeout=1.5,
            )
        except (asyncio.TimeoutError, Exception):
            pass

    theory_cards: list = []
    if top_idea:
        from src.services.theory_cards import build_theory_cards

        idea_meta = top_idea.get("meta") or {}
        pattern_tags = idea_meta.get("pattern_tags") or idea_meta.get("patterns") or []
        theory_cards = await _to_thread(
            build_theory_cards,
            symbol=sym,
            structure_type=top_idea.get("structure_type"),
            tags=pattern_tags if isinstance(pattern_tags, list) else [],
        )

    return TEMPLATES.TemplateResponse(
        request,
        "partials/symbol_panel.html",
        {
            "symbol": sym,
            "meta": meta,
            "quote": quote,
            "note": note,
            "option_chain": option_chain,
            "max_pain": max_pain,
            "iv_rank": iv_rank_val,
            "preview_legs": None,
            "candles": candles,
            "is_crypto": crypto_sym,
            "top_idea": top_idea,
            "session_vwap": session_vwap,
            "theory_cards": theory_cards,
        },
    )


@router.get("/board/partials/symbol/{symbol}/report", response_class=HTMLResponse)
async def symbol_report_partial(request: Request, symbol: str):
    sym = symbol.strip().upper()
    force = request.query_params.get("force", "false").lower() in ("1", "true", "yes")
    base = _api_base(request)
    report: dict[str, Any] | None = None
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.get(
                f"{base}/api/v1/symbols/{sym}/report",
                params={"force": str(force).lower()},
            )
            if resp.status_code == 200:
                report = resp.json()
            else:
                error = _api_error_detail(resp)
    except httpx.HTTPError as exc:
        error = str(exc)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/symbol_report.html",
        {"report": report, "error": error},
    )


@router.get("/board/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request):
    from src.services.strategy_report import build_strategy_report

    report = await _to_thread(_with_db, build_strategy_report)
    return TEMPLATES.TemplateResponse(request, "strategies.html", {"report": report})


@router.get("/board/strategy-lab", response_class=HTMLResponse)
async def strategy_lab_page(request: Request):
    return TEMPLATES.TemplateResponse(request, "strategy_lab.html", {})


@router.get("/board/partials/rankings-table", response_class=HTMLResponse)
async def rankings_table_partial(request: Request):
    from src.autonomous.backtest_rankings import BacktestRankingsService

    params = dict(request.query_params)
    symbol = params.get("symbol") or None
    sector = params.get("sector") or None
    structure_type = params.get("type") or None
    period_raw = params.get("period")
    period_days = int(period_raw) if period_raw else None
    sort_by = params.get("sort_by") or "idea_score"

    def _load(session):
        return BacktestRankingsService(session).list_rankings(
            symbol=symbol,
            sector=sector,
            structure_type=structure_type,
            period_days=period_days,
            sort_by=sort_by,
        )

    rankings = await _to_thread(_with_db, _load)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/rankings_table.html",
        {"rankings": rankings},
    )


@router.get("/board/strategy-lab/{ranking_id}", response_class=HTMLResponse)
async def strategy_lab_detail(request: Request, ranking_id: int):
    from src.autonomous.backtest_rankings import BacktestRankingsService

    commentary = request.query_params.get("commentary") == "1"

    def _load(session):
        return BacktestRankingsService(session).get_detail(
            ranking_id, refresh_commentary=commentary
        )

    detail = await _to_thread(_with_db, _load)
    if not detail:
        return HTMLResponse("<p class='bb-muted'>Ranking not found.</p>", status_code=404)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/rankings_detail.html",
        {"detail": detail},
    )


@router.post("/board/strategy-lab/{ranking_id}/promote", response_class=HTMLResponse)
async def strategy_lab_promote(request: Request, ranking_id: int):
    from src.autonomous.backtest_rankings import BacktestRankingsService

    def _promote(session):
        return BacktestRankingsService(session).promote_to_idea_stack(ranking_id)

    try:
        idea = await _to_thread(_with_db, _promote)
    except ValueError as exc:
        return HTMLResponse(f"<p class='bb-pnl-neg'>{exc}</p>", status_code=404)
    return HTMLResponse(
        f"<p class='bb-pnl-pos'>Promoted <strong>{idea.get('symbol')}</strong> "
        f"→ Idea #{idea.get('id')}. <a href='/board'>Open board</a></p>"
    )


@router.get("/board/partials/risk-cockpit", response_class=HTMLResponse)
async def risk_cockpit_partial(request: Request):
    cockpit = await _to_thread(_risk_cockpit)
    risk = await _fetch_risk_summary(request)
    sleeves = (risk or {}).get("sleeves")
    return TEMPLATES.TemplateResponse(
        request,
        "partials/risk_cockpit.html",
        {"cockpit": cockpit, "sleeves": sleeves},
    )


@router.post("/board/partials/symbol/{symbol}/structure-preview", response_class=HTMLResponse)
async def structure_preview_partial(request: Request, symbol: str):
    from src.services.trade_ideas import TradeIdeaService

    sym = symbol.strip().upper()
    form = await request.form()
    structure_type = str(form.get("structure_type", "covered_call"))
    side = str(form.get("side", "long"))
    session = __import__("src.models", fromlist=["get_session_factory"]).get_session_factory()()
    hedge_info = None
    try:
        svc = TradeIdeaService(session)
        legs = svc._legs_for_structure(structure_type, sym, side, get_profit_client().get_quote(sym))
        notional = sum(int(l.get("quantity", 100)) * 10.0 for l in legs)
        if structure_type == "bova_hedge":
            from src.services.bova_hedge import suggest_bova_hedge

            hedge_info = suggest_bova_hedge(sym, 100)
    finally:
        session.close()
    return TEMPLATES.TemplateResponse(
        request,
        "partials/structure_preview.html",
        {"legs": legs, "notional": notional, "hedge_info": hedge_info},
    )


@router.post("/board/partials/symbol/{symbol}/structure-create", response_class=HTMLResponse)
async def structure_create_partial(request: Request, symbol: str):
    sym = symbol.strip().upper()
    form = await request.form()
    structure_type = str(form.get("structure_type", "covered_call"))
    side = str(form.get("side", "long"))
    base = _api_base(request)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{base}/api/v1/ideas/from-structure",
                json={"symbol": sym, "structure_type": structure_type, "side": side},
            )
    except httpx.HTTPError:
        pass
    ideas = await _fetch_ideas(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_stack.html",
        {"ideas": ideas},
    )


@router.get("/board/partials/ideas", response_class=HTMLResponse)
async def ideas_partial(request: Request):
    symbol = request.query_params.get("symbol")
    ideas = await _to_thread(_list_ideas_sync, 20, symbol)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_stack.html",
        {"ideas": ideas, "filter_symbol": symbol},
    )


@router.post("/board/partials/ideas/{idea_id}/confirm", response_class=HTMLResponse)
async def confirm_idea_partial(request: Request, idea_id: int):
    base = _api_base(request)
    form = await request.form()
    paper_override = str(form.get("paper_override", "")).lower() in ("true", "1", "on", "yes")
    idea: dict[str, Any] | None = None
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base}/api/v1/ideas/{idea_id}/confirm",
                params={"paper_override": str(paper_override).lower()},
            )
            if resp.status_code == 200:
                idea = resp.json()
            else:
                error = _api_error_detail(resp)
    except httpx.HTTPError as exc:
        error = str(exc)

    if idea and idea.get("status") == "confirmed":
        risk = await _fetch_risk_summary(request)
        return TEMPLATES.TemplateResponse(
            request,
            "partials/idea_execute_step.html",
            {
                "idea": idea,
                "risk": risk,
                "error": None,
                "gates": await _to_thread(_idea_gates_sync, idea_id),
                "clear": await _to_thread(_clear_status_sync),
            },
        )

    if idea is None:
        idea = await _fetch_idea(request, idea_id) or {"id": idea_id, "symbol": "?", "side": ""}

    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_confirm_step.html",
        {
            "idea": idea,
            "cockpit": _risk_cockpit(),
            "risk": await _fetch_risk_summary(request),
            "error": error,
            "gates": await _to_thread(_idea_gates_sync, idea_id),
            "clear": await _to_thread(_clear_status_sync),
        },
    )


@router.get("/board/partials/ideas/{idea_id}/execute-step", response_class=HTMLResponse)
async def idea_execute_step_partial(request: Request, idea_id: int):
    idea = await _fetch_idea(request, idea_id)
    if not idea:
        return HTMLResponse("<p>Idea not found</p>", status_code=404)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_execute_step.html",
        {
            "idea": idea,
            "risk": await _fetch_risk_summary(request),
            "error": None,
            "gates": await _to_thread(_idea_gates_sync, idea_id),
            "clear": await _to_thread(_clear_status_sync),
        },
    )


@router.post("/board/partials/ideas/{idea_id}/execute", response_class=HTMLResponse)
async def execute_idea_partial(request: Request, idea_id: int):
    base = _api_base(request)
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base}/api/v1/ideas/{idea_id}/execute")
            if resp.status_code != 200:
                error = _api_error_detail(resp)
                idea = await _fetch_idea(request, idea_id)
                if idea:
                    return TEMPLATES.TemplateResponse(
                        request,
                        "partials/idea_execute_step.html",
                        {
                            "idea": idea,
                            "risk": await _fetch_risk_summary(request),
                            "error": error,
                            "gates": await _to_thread(_idea_gates_sync, idea_id),
                            "clear": await _to_thread(_clear_status_sync),
                        },
                    )
    except httpx.HTTPError as exc:
        error = str(exc)
        idea = await _fetch_idea(request, idea_id)
        if idea:
            return TEMPLATES.TemplateResponse(
                request,
                "partials/idea_execute_step.html",
                {
                    "idea": idea,
                    "risk": await _fetch_risk_summary(request),
                    "error": error,
                    "gates": await _to_thread(_idea_gates_sync, idea_id),
                    "clear": await _to_thread(_clear_status_sync),
                },
            )

    ideas = await _fetch_ideas(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_stack.html",
        {"ideas": ideas},
    )


@router.get("/board/partials/ideas/{idea_id}/review", response_class=HTMLResponse)
async def idea_review_partial(request: Request, idea_id: int):
    idea = await _fetch_idea(request, idea_id)
    if not idea:
        return HTMLResponse("<p>Idea not found</p>", status_code=404)
    from src.services.idea_levels import enrich_idea_levels, idea_risk_summary

    idea = enrich_idea_levels(idea)
    risk_box = idea_risk_summary(idea)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_review.html",
        {
            "idea": idea,
            "risk_box": risk_box,
            "gates": await _to_thread(_idea_gates_sync, idea_id),
            "clear": await _to_thread(_clear_status_sync),
        },
    )


@router.get("/board/partials/ideas/{idea_id}/confirm-step", response_class=HTMLResponse)
async def idea_confirm_step_partial(request: Request, idea_id: int):
    idea = await _fetch_idea(request, idea_id)
    if not idea:
        return HTMLResponse("<p>Idea not found</p>", status_code=404)
    from src.services.idea_levels import enrich_idea_levels, idea_risk_summary
    from src.services.paper_execution import estimate_paper_fills

    idea = enrich_idea_levels(dict(idea))
    idea["fill_preview"] = estimate_paper_fills(idea)
    risk_box = idea_risk_summary(idea)

    def _brief(session):
        from src.services.decision_brief import build_decision_brief

        try:
            return build_decision_brief(session, idea_id)
        except ValueError:
            return None

    brief = await _to_thread(_with_db, _brief)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_confirm_step.html",
        {
            "idea": idea,
            "risk_box": risk_box,
            "brief": brief,
            "cockpit": _risk_cockpit(),
            "risk": await _fetch_risk_summary(request),
            "error": None,
            "gates": await _to_thread(_idea_gates_sync, idea_id),
            "clear": await _to_thread(_clear_status_sync),
        },
    )


@router.post("/board/scan", response_class=HTMLResponse)
async def board_scan(request: Request):
    base = _api_base(request)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{base}/api/v1/scanner/run")
    except httpx.HTTPError:
        pass
    ideas = await _fetch_ideas(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_stack.html",
        {"ideas": ideas},
    )


@router.get("/board/partials/setup", response_class=HTMLResponse)
async def setup_partial(request: Request):
    data = await _fetch_json(request, "/api/v1/setup/status")
    setup = data if isinstance(data, dict) else {"steps": [], "release": "2.0.0"}
    return TEMPLATES.TemplateResponse(
        request,
        "partials/setup_wizard.html",
        {"setup": setup, "test_result": None},
    )


@router.post("/board/partials/setup/test", response_class=HTMLResponse)
async def setup_test_partial(request: Request):
    base = _api_base(request)
    test_result: dict[str, Any] | None = None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{base}/api/v1/setup/test")
            if resp.status_code == 200:
                test_result = resp.json()
    except httpx.HTTPError:
        pass
    data = await _fetch_json(request, "/api/v1/setup/status")
    setup = data if isinstance(data, dict) else {"steps": [], "release": "2.0.0"}
    return TEMPLATES.TemplateResponse(
        request,
        "partials/setup_wizard.html",
        {"setup": setup, "test_result": test_result},
    )


_SECTOR_LABELS: dict[str, str] = {
    "banks": "Bancos",
    "steel": "Siderurgia",
    "energy": "Energia",
    "defensive": "Defensivo",
}

_FALLBACK_BASKETS: dict[str, list[str]] = {
    "banks": ["ITUB4", "BBAS3", "BBDC4", "BBSE3", "B3SA3"],
    "steel": ["GGBR4", "CSNA3", "USIM5"],
    "energy": ["PETR4", "PRIO3"],
    "defensive": ["ABEV3", "SUZB3", "WEGE3"],
}


@router.get("/board/partials/sector-strip", response_class=HTMLResponse)
async def sector_strip_partial(request: Request):
    payload = await _fetch_universe_payload(request)
    baskets = payload.get("sector_baskets") or _FALLBACK_BASKETS
    return TEMPLATES.TemplateResponse(
        request,
        "partials/sector_strip.html",
        {"baskets": baskets, "labels": _SECTOR_LABELS},
    )


@router.get("/board/partials/opportunity-rail", response_class=HTMLResponse)
async def opportunity_rail_partial(request: Request):
    data = await _fetch_json(request, "/api/v1/signals/opportunity-rail")
    rail = data if isinstance(data, dict) else {"signals": [], "sector_heat": {}}
    pattern_theory_cards: list = []
    try:
        insights_data = await _fetch_json(request, "/api/v1/scanner/insights?limit=3")
        insights = (insights_data or {}).get("insights") or []
        if insights:
            from src.services.theory_cards import build_theory_cards

            top = insights[0]
            sym = (top.get("symbol") or "PETR4").strip().upper()
            tags = top.get("pattern_tags") or []
            pattern_theory_cards = await _to_thread(
                build_theory_cards,
                symbol=sym,
                structure_type=tags[0] if tags else None,
                tags=tags[:3] if isinstance(tags, list) else [],
            )
    except Exception:
        pass
    return TEMPLATES.TemplateResponse(
        request,
        "partials/opportunity_rail.html",
        {"rail": rail, "pattern_theory_cards": pattern_theory_cards},
    )


@router.get("/board/partials/layout-presets", response_class=HTMLResponse)
async def layout_presets_partial(request: Request):
    data = await _fetch_json(request, "/api/v1/board/layouts")
    layouts = []
    if isinstance(data, dict):
        layouts = list(data.get("layouts") or [])
    return TEMPLATES.TemplateResponse(
        request,
        "partials/layout_presets.html",
        {"layouts": layouts},
    )


@router.post("/board/partials/layout/{preset}", response_class=HTMLResponse)
async def apply_layout_partial(request: Request, preset: str):
    base = _api_base(request)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{base}/api/v1/board/layout/{preset}")
    except httpx.HTTPError:
        pass
    return HTMLResponse("", status_code=204)


@router.get("/board/partials/portfolio-backtest", response_class=HTMLResponse)
async def portfolio_backtest_partial(request: Request):
    from src.models import get_session_factory
    from src.services.portfolio_backtest import run_portfolio_backtest

    session = get_session_factory()()
    try:
        report = run_portfolio_backtest(session)
    finally:
        session.close()
    return TEMPLATES.TemplateResponse(
        request,
        "partials/portfolio_backtest.html",
        {"report": report},
    )


@router.post("/board/partials/symbol/{symbol}/notes", response_class=HTMLResponse)
async def save_notes_partial(request: Request, symbol: str):
    form = await request.form()
    content = str(form.get("content", ""))
    from src.models import get_session_factory
    from src.services.board_notes import BoardNotesService

    session = get_session_factory()()
    try:
        BoardNotesService(session).save(symbol, content)
    finally:
        session.close()
    return HTMLResponse("")


@router.post("/board/partials/symbol/{symbol}/analyze", response_class=HTMLResponse)
async def analyze_symbol_partial(request: Request, symbol: str):
    sym = symbol.strip().upper()
    base = _api_base(request)
    report = ""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{base}/api/v1/board/{sym}/analyze")
            if resp.status_code == 200:
                data = resp.json()
                report = data.get("report") or ""
    except httpx.HTTPError:
        pass
    return TEMPLATES.TemplateResponse(
        request,
        "partials/ai_report.html",
        {"report": report},
    )


@router.get("/board/partials/world-clocks", response_class=HTMLResponse)
async def world_clocks_partial(request: Request):
    from src.services.market_clocks import get_market_clocks

    clocks = await _to_thread(get_market_clocks)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/world_clocks.html",
        {"clocks": clocks},
    )


@router.get("/board/partials/risk-profile", response_class=HTMLResponse)
async def risk_profile_partial(request: Request):
    from src.services.risk_profile import get_or_create_profile, profile_to_dict

    profile = await _to_thread(_with_db, lambda s: profile_to_dict(get_or_create_profile(s)))
    return TEMPLATES.TemplateResponse(
        request,
        "partials/risk_profile.html",
        {"profile": profile},
    )


@router.post("/board/partials/risk-profile/save", response_class=HTMLResponse)
async def risk_profile_save(request: Request):
    from src.services.risk_profile import update_profile

    form = await request.form()
    payload = {}
    for key in ("max_daily_loss_brl", "max_open_positions", "cost_per_trade_brl", "max_net_delta"):
        if key in form and form.get(key):
            val = form.get(key)
            payload[key] = float(val) if "brl" in key or key == "max_net_delta" else int(val)

    def _save(session):
        update_profile(session, payload)

    await _to_thread(_with_db, _save)
    return HTMLResponse('<span class="bb-muted">Saved</span>')


@router.get("/board/partials/mobile-banner", response_class=HTMLResponse)
async def mobile_banner_partial(request: Request):
    bootstrap = await _fetch_bootstrap(request)
    risk = await _fetch_risk_summary(request)
    cockpit = await _to_thread(_risk_cockpit)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/mobile_banner.html",
        {"bootstrap": bootstrap, "risk": risk, "cockpit": cockpit},
    )


@router.get("/board/partials/pulse-rail", response_class=HTMLResponse)
async def pulse_rail_partial(request: Request):
    """Legacy alias — redirects to trader desk."""
    return await trader_desk_partial(request)


@router.get("/board/partials/trader-desk", response_class=HTMLResponse)
async def trader_desk_partial(request: Request):
    from src.services.trader_desk import build_trader_desk

    data = await _to_thread(_with_db, build_trader_desk)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/trader_desk.html",
        data,
    )


@router.get("/board/partials/golden-path", response_class=HTMLResponse)
async def golden_path_partial(request: Request):
    from src.services.golden_path import evaluate_golden_path

    data = await _to_thread(_with_db, evaluate_golden_path)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/golden_path.html",
        {"golden_path": data},
    )


@router.get("/board/partials/ops-panel", response_class=HTMLResponse)
async def ops_panel_partial(request: Request):
    from src.services.ops_panel import build_ops_panel

    data = await _to_thread(build_ops_panel)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/ops_panel.html",
        {"ops": data},
    )


async def _symbol_factory_context(message: str = "", message_ok: bool = True) -> dict[str, Any]:
    from src.services.golden_path import evaluate_golden_path
    from src.services.symbol_factory import factory_status

    def _load(session):
        return {
            "factory": factory_status(session),
            "golden_path": evaluate_golden_path(session),
            "message": message,
            "message_ok": message_ok,
        }

    return await _to_thread(_with_db, _load)


@router.get("/board/partials/symbol-factory", response_class=HTMLResponse)
async def symbol_factory_partial(request: Request):
    ctx = await _symbol_factory_context()
    return TEMPLATES.TemplateResponse(request, "partials/symbol_factory.html", ctx)


@router.post("/board/partials/symbol-factory/shadow", response_class=HTMLResponse)
async def symbol_factory_shadow(request: Request):
    from src.services.symbol_factory import add_shadow_symbol

    form = await request.form()
    symbol = str(form.get("symbol", "")).strip()

    def _add(session):
        return add_shadow_symbol(session, symbol)

    result = await _to_thread(_with_db, _add)
    if result.get("ok"):
        msg = f"{symbol} added to shadow mode"
        ctx = await _symbol_factory_context(msg, True)
    else:
        msg = result.get("error") or "Shadow add failed"
        ctx = await _symbol_factory_context(msg, False)
    return TEMPLATES.TemplateResponse(request, "partials/symbol_factory.html", ctx)


@router.post("/board/partials/symbol-factory/promote", response_class=HTMLResponse)
async def symbol_factory_promote(request: Request):
    from src.services.symbol_factory import promote_shadow_symbol

    form = await request.form()
    symbol = str(form.get("symbol", "")).strip()

    def _promote(session):
        return promote_shadow_symbol(session, symbol)

    result = await _to_thread(_with_db, _promote)
    if result.get("ok"):
        msg = f"{symbol} promoted to motor universe"
        ctx = await _symbol_factory_context(msg, True)
    else:
        msg = result.get("error") or "Promote failed"
        ctx = await _symbol_factory_context(msg, False)
    return TEMPLATES.TemplateResponse(request, "partials/symbol_factory.html", ctx)


@router.get("/board/partials/market-context", response_class=HTMLResponse)
async def market_context_partial(request: Request):
    pulse = await _to_thread(_pulse_rail_with_social_sync)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/market_context.html",
        {"pulse": pulse},
    )


@router.get("/board/stream/trader-desk")
async def trader_desk_stream(request: Request):
    """SSE — push trader desk HTML every 10s (Phase A)."""
    import asyncio
    import json

    from starlette.responses import StreamingResponse

    async def event_generator():
        settings = get_settings()
        interval = settings.desk_sse_interval_sec
        while True:
            if await request.is_disconnected():
                break
            from src.services.trader_desk import build_trader_desk

            data = await _to_thread(_with_db, build_trader_desk)
            template = TEMPLATES.env.get_template("partials/trader_desk.html")
            html = template.render(request=request, **data)
            payload = json.dumps({"html": html})
            yield f"event: desk\ndata: {payload}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/board/partials/pulse-rail-legacy", response_class=HTMLResponse)
async def pulse_rail_legacy_partial(request: Request):
    from src.services.trading_desk import build_trading_desk
    from src.services.trading_orchestrator import orchestrator_status

    pulse = await _to_thread(_pulse_rail_with_social_sync)
    cockpit = await _to_thread(_risk_cockpit)
    risk = await _fetch_risk_summary(request)
    desk = await _to_thread(_with_db, build_trading_desk)
    orchestrator = await _to_thread(orchestrator_status)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/pulse_rail.html",
        {
            "pulse": pulse,
            "cockpit": cockpit,
            "desk": desk,
            "orchestrator": orchestrator,
            "sleeves": (risk or {}).get("sleeves"),
            "autonomy_enabled": (risk or {}).get("autonomy_enabled", False),
        },
    )


@router.get("/board/partials/symbol/{symbol}/trade-product", response_class=HTMLResponse)
async def trade_product_partial(request: Request, symbol: str):
    sym = symbol.strip().upper()
    product = None
    theory_cards: list = []
    try:
        data = await _fetch_json(request, f"/api/v1/symbols/{sym}/trade-product")
        if isinstance(data, dict):
            product = data
            from src.services.theory_cards import build_theory_cards

            st = product.get("structure_type") or ""
            tags = product.get("economics_tags") or []
            theory_cards = await _to_thread(
                build_theory_cards,
                symbol=sym,
                structure_type=st,
                tags=tags if isinstance(tags, list) else [],
            )
    except Exception:
        pass
    return TEMPLATES.TemplateResponse(
        request,
        "partials/trade_product.html",
        {"product": product, "theory_cards": theory_cards},
    )


@router.get("/board/partials/learning-rail", response_class=HTMLResponse)
async def learning_rail_partial(request: Request):
    from src.services.outcome_ranker import rank_outcomes
    from src.services.patch_proposals import list_proposals

    def _load(session):
        return {
            "patches": list_proposals(session, status="pending"),
            "outcomes": rank_outcomes(session, limit=5),
        }

    rail = await _to_thread(_with_db, _load)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/learning_rail.html",
        {"rail": rail},
    )


@router.post("/board/partials/learning-rail/generate", response_class=HTMLResponse)
async def learning_rail_generate(request: Request):
    from src.services.outcome_ranker import rank_outcomes
    from src.services.patch_proposals import generate_patch_proposals, list_proposals

    def _gen(session):
        generate_patch_proposals(session)
        return {
            "patches": list_proposals(session, status="pending"),
            "outcomes": rank_outcomes(session, limit=5),
        }

    rail = await _to_thread(_with_db, _gen)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/learning_rail.html",
        {"rail": rail},
    )


@router.get("/board/partials/patches/{proposal_id}", response_class=HTMLResponse)
async def patch_review_partial(request: Request, proposal_id: int):
    from src.models import PatchProposal

    def _load(session):
        row = session.get(PatchProposal, proposal_id)
        if not row:
            return None
        from src.services.patch_proposals import proposal_to_dict

        return proposal_to_dict(row)

    patch = await _to_thread(_with_db, _load)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/patch_review.html",
        {"patch": patch},
    )


@router.post("/board/partials/patches/{proposal_id}/approve", response_class=HTMLResponse)
async def patch_approve_partial(request: Request, proposal_id: int):
    from src.services.outcome_ranker import rank_outcomes
    from src.services.patch_proposals import approve_proposal, list_proposals

    def _approve(session):
        approve_proposal(session, proposal_id)
        return {
            "patches": list_proposals(session, status="pending"),
            "outcomes": rank_outcomes(session, limit=5),
        }

    rail = await _to_thread(_with_db, _approve)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/learning_rail.html",
        {"rail": rail},
    )


@router.post("/board/partials/patches/{proposal_id}/reject", response_class=HTMLResponse)
async def patch_reject_partial(request: Request, proposal_id: int):
    from src.services.outcome_ranker import rank_outcomes
    from src.services.patch_proposals import list_proposals, reject_proposal

    def _reject(session):
        reject_proposal(session, proposal_id, reason="board reject")
        return {
            "patches": list_proposals(session, status="pending"),
            "outcomes": rank_outcomes(session, limit=5),
        }

    rail = await _to_thread(_with_db, _reject)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/learning_rail.html",
        {"rail": rail},
    )


@router.get("/board/partials/decision-queue", response_class=HTMLResponse)
async def decision_queue_partial(request: Request):
    def _queue(session):
        from src.services.trade_ideas import TradeIdeaService

        svc = TradeIdeaService(session)
        ideas = svc.list_ideas(limit=12)
        out = []
        for idea in ideas:
            d = svc.to_dict(idea)
            meta = d.get("meta") or {}
            d["theory_card_count"] = meta.get("theory_card_count", 0)
            out.append(d)
        out.sort(key=lambda x: x.get("idea_score") or 0, reverse=True)
        return out[:8]

    queue = await _to_thread(_with_db, _queue)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/decision_queue.html",
        {"queue": queue or []},
    )


@router.get("/board/partials/profitchart-companion", response_class=HTMLResponse)
async def profitchart_companion_partial(request: Request):
    from src.web.profitchart_companion import build_profitchart_companion

    sym = (request.query_params.get("symbol") or "PETR4").strip().upper()

    def _ctx(session):
        from src.services.trade_ideas import TradeIdeaService
        from src.services.vwap import build_session_vwap_payload

        ideas = TradeIdeaService(session).list_ideas(limit=1, symbol=sym)
        top = TradeIdeaService(session).to_dict(ideas[0]) if ideas else None
        vwap = build_session_vwap_payload(sym)
        quote = _fast_quote(sym)
        return build_profitchart_companion(sym, quote=quote, top_idea=top, session_vwap=vwap)

    companion = await _to_thread(_with_db, _ctx)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/profitchart_companion.html",
        {"companion": companion},
    )


@router.get("/board/partials/strategy-store", response_class=HTMLResponse)
async def strategy_store_partial(request: Request):
    from src.services.strategy_store import list_stored_strategies

    def _load(session):
        return {
            "strategies": list_stored_strategies(session, limit=40),
            "scan_result": None,
        }

    store = await _to_thread(_with_db, _load)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/strategy_store.html",
        {"store": store},
    )


@router.post("/board/partials/strategy-store/scan", response_class=HTMLResponse)
async def strategy_store_scan_partial(request: Request):
    from src.services.strategy_store import list_stored_strategies, scan_strategy_directories

    def _scan(session):
        result = scan_strategy_directories(session)
        return {
            "strategies": list_stored_strategies(session, limit=40),
            "scan_result": result,
        }

    store = await _to_thread(_with_db, _scan)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/strategy_store.html",
        {"store": store},
    )


@router.get("/board/partials/strategy-store/{stored_id}", response_class=HTMLResponse)
async def strategy_store_detail_partial(request: Request, stored_id: int):
    from src.services.strategy_store import get_stored_strategy

    detail = await _to_thread(_with_db, get_stored_strategy, stored_id)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/strategy_store_detail.html",
        {"detail": detail},
    )


@router.get("/board/partials/engine-mind", response_class=HTMLResponse)
async def engine_mind_partial(request: Request):
    from src.web.engine_mind import build_engine_mind

    mind = await _to_thread(_with_db, build_engine_mind)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/engine_mind.html",
        {"mind": mind},
    )


@router.get("/board/partials/daily-briefing", response_class=HTMLResponse)
async def daily_briefing_partial(request: Request):
    from src.services.daily_briefing import build_daily_briefing

    briefing = await _to_thread(_with_db, build_daily_briefing)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/daily_briefing.html",
        {"briefing": briefing},
    )


@router.get("/board/partials/knowledge-library", response_class=HTMLResponse)
async def knowledge_library_partial(request: Request):
    from src.services.knowledge.store import knowledge_status, search_chunks

    q = (request.query_params.get("q") or "").strip()
    sym = (request.query_params.get("symbol") or "PETR4").strip().upper()
    status = await _to_thread(knowledge_status)
    results = await _to_thread(search_chunks, q, symbol=sym, limit=8) if q else []
    return TEMPLATES.TemplateResponse(
        request,
        "partials/knowledge_library.html",
        {"status": status, "results": results, "query": q, "symbol": sym},
    )


@router.get("/board/partials/replay-player", response_class=HTMLResponse)
async def replay_player_partial(request: Request):
    from src.web.replay_player import build_replay_player_context

    sym = (request.query_params.get("symbol") or "PETR4").strip().upper()
    speed = int(request.query_params.get("speed", "8") or 8)
    job_id = (request.query_params.get("job_id") or "").strip() or None

    def _load(session):
        return build_replay_player_context(session, sym, speed=speed, job_id=job_id)

    ctx = await _to_thread(_with_db, _load)
    return TEMPLATES.TemplateResponse(request, "partials/replay_player.html", ctx)


@router.post("/board/partials/replay-player/run", response_class=HTMLResponse)
async def replay_player_run(request: Request):
    from src.services.replay_engine import start_replay
    from src.web.replay_player import build_replay_player_context

    form = await request.form()
    sym = str(form.get("symbol", "PETR4")).strip().upper()
    strategy = str(form.get("strategy", "scalp_default")).strip()
    speed = int(form.get("speed", 8) or 8)

    def _run(session):
        run = start_replay(
            strategy=strategy,
            symbol=sym,
            speed=float(speed),
            mode="sandbox",
            session=session,
        )
        return build_replay_player_context(
            session,
            sym,
            speed=speed,
            job_id=run.get("job_id"),
            last_run=run,
        )

    ctx = await _to_thread(_with_db, _run)
    return TEMPLATES.TemplateResponse(request, "partials/replay_player.html", ctx)


@router.get("/board/partials/replay-lab", response_class=HTMLResponse)
async def replay_lab_partial(request: Request):
    sym = (request.query_params.get("symbol") or "PETR4").strip().upper()
    speed = request.query_params.get("speed", "10")
    return TEMPLATES.TemplateResponse(
        request,
        "partials/replay_lab.html",
        {"symbol": sym, "speed": speed, "last_run": None},
    )


@router.post("/board/partials/replay-lab/run", response_class=HTMLResponse)
async def replay_lab_run(request: Request):
    from src.services.replay_lab import start_replay

    form = await request.form()
    sym = str(form.get("symbol", "PETR4")).strip().upper()
    speed = float(form.get("speed", 10) or 10)
    run = await _to_thread(
        start_replay,
        strategy="scalp_default",
        symbol=sym,
        speed=speed,
        mode="sandbox",
    )
    return TEMPLATES.TemplateResponse(
        request,
        "partials/replay_lab_log.html",
        {"run": run},
    )


@router.get("/board/partials/archaeology", response_class=HTMLResponse)
async def archaeology_partial(request: Request):
    from src.services.trade_archaeology import build_timeline

    symbol = request.query_params.get("symbol")
    limit = int(request.query_params.get("limit", "100") or 100)

    def _load(session):
        return build_timeline(session, limit=limit, symbol=symbol)

    timeline = await _to_thread(_with_db, _load)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/archaeology_timeline.html",
        {"timeline": timeline, "symbol_filter": symbol},
    )


@router.post("/board/partials/archaeology/import", response_class=HTMLResponse)
async def archaeology_import_partial(request: Request):
    from src.services.trade_archaeology import build_timeline, import_trade_csv

    form = await request.form()
    upload = form.get("file")
    if not upload or not hasattr(upload, "read"):
        return TEMPLATES.TemplateResponse(
            request,
            "partials/archaeology_status.html",
            {"status": "error", "message": "Choose a Profit trade-list CSV file."},
        )

    content = await upload.read()
    settings = get_settings()
    import_dir = settings.archaeology_import_path
    import_dir.mkdir(parents=True, exist_ok=True)
    safe_name = str(getattr(upload, "filename", "import.csv") or "import.csv").replace("\\", "_").replace("/", "_")
    path = import_dir / safe_name
    path.write_bytes(content)

    def _import(session):
        result = import_trade_csv(session, path)
        result["timeline"] = build_timeline(session, limit=100)
        return result

    result = await _to_thread(_with_db, _import)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/archaeology_status.html",
        {
            "status": "ok",
            "message": f"Imported {result.get('imported', 0)} rows (skipped {result.get('skipped', 0)}).",
            "timeline": result.get("timeline"),
        },
    )


@router.post("/board/partials/archaeology/scan", response_class=HTMLResponse)
async def archaeology_scan_partial(request: Request):
    from src.services.trade_archaeology import build_timeline, scan_archaeology_dir

    def _scan(session):
        scan = scan_archaeology_dir(session)
        scan["timeline"] = build_timeline(session, limit=100)
        return scan

    result = await _to_thread(_with_db, _scan)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/archaeology_status.html",
        {
            "status": "ok",
            "message": (
                f"Scanned {result.get('files_scanned', 0)} file(s); "
                f"imported {result.get('imported', 0)} new row(s)."
            ),
            "timeline": result.get("timeline"),
        },
    )


@router.get("/board/partials/symbol/{symbol}/crypto-paper", response_class=HTMLResponse)
async def crypto_paper_partial(request: Request, symbol: str):
    from src.services.crypto_paper import preview_crypto_fill
    from src.services.crypto_universe import is_crypto, load_crypto_universe

    sym = symbol.strip().upper()
    if not is_crypto(sym):
        return HTMLResponse("", status_code=404)

    meta = next((c.to_dict() for c in load_crypto_universe() if c.symbol == sym), {})
    preview = None
    error = None
    try:
        preview = await _to_thread(
            preview_crypto_fill,
            symbol=sym,
            side="buy",
            quantity=0.01,
        )
    except Exception as exc:
        error = str(exc)

    return TEMPLATES.TemplateResponse(
        request,
        "partials/crypto_paper.html",
        {"symbol": sym, "meta": meta, "preview": preview, "error": error},
    )


@router.post("/board/partials/symbol/{symbol}/crypto-paper/execute", response_class=HTMLResponse)
async def crypto_paper_execute_partial(request: Request, symbol: str):
    from src.services.crypto_paper import execute_crypto_paper
    from src.services.crypto_universe import is_crypto

    sym = symbol.strip().upper()
    if not is_crypto(sym):
        return HTMLResponse("", status_code=404)

    form = await request.form()
    side = str(form.get("side", "buy"))
    try:
        quantity = float(form.get("quantity", 0.01) or 0.01)
    except (TypeError, ValueError):
        quantity = 0.01

    def _execute(session):
        return execute_crypto_paper(session, symbol=sym, side=side, quantity=quantity)

    try:
        result = await _to_thread(_with_db, _execute)
        return TEMPLATES.TemplateResponse(
            request,
            "partials/crypto_paper_result.html",
            {"symbol": sym, "result": result, "error": None},
        )
    except Exception as exc:
        return TEMPLATES.TemplateResponse(
            request,
            "partials/crypto_paper_result.html",
            {"symbol": sym, "result": None, "error": str(exc)},
        )


@router.get("/board/partials/ntsl-arm-confirm", response_class=HTMLResponse)
async def ntsl_arm_confirm(request: Request):
    sym = request.query_params.get("symbol", "").strip().upper()
    structure_type = request.query_params.get("structure_type", "scalp")
    side = request.query_params.get("side", "long")
    return TEMPLATES.TemplateResponse(
        request,
        "partials/ntsl_arm_confirm.html",
        {"symbol": sym, "structure_type": structure_type, "side": side},
    )
