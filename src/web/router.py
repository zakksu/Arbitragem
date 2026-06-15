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


def _list_ideas_sync(limit: int = 20) -> list[dict[str, Any]]:
    from src.services.trade_ideas import TradeIdeaService

    def _load(session):
        svc = TradeIdeaService(session)
        ideas = svc.list_ideas(limit=limit)
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
    return rows


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
    return TEMPLATES.TemplateResponse(request, "board.html", {})


@router.get("/board/partials/status", response_class=HTMLResponse)
async def status_partial(request: Request):
    bootstrap = await _fetch_bootstrap(request)
    risk = await _fetch_risk_summary(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/status_bar.html",
        {"bootstrap": bootstrap, "risk": risk},
    )


@router.get("/board/partials/watchlist", response_class=HTMLResponse)
async def watchlist_partial(request: Request):
    symbols = await _fetch_universe(request)
    sym_list = [s["symbol"] for s in symbols if s.get("symbol")]
    rows = await _to_thread(_watchlist_rows_sync, list(symbols), list(sym_list))
    active = request.query_params.get("active")
    return TEMPLATES.TemplateResponse(
        request,
        "partials/watchlist.html",
        {"symbols": rows, "active_symbol": active},
    )


@router.get("/board/partials/symbol/{symbol}", response_class=HTMLResponse)
async def symbol_partial(request: Request, symbol: str):
    sym = symbol.strip().upper()
    universe = await _fetch_universe(request)
    meta = next((s for s in universe if s.get("symbol") == sym), None)

    def _load_note(session):
        from src.services.board_notes import BoardNotesService

        row = BoardNotesService(session).get(sym)
        if not row:
            return None
        return {"symbol": row.symbol, "content": row.content, "updated_at": row.updated_at.isoformat()}

    note = await _to_thread(_with_db, _load_note)
    quote = await _to_thread(_fast_quote, sym)

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


@router.get("/board/partials/risk-cockpit", response_class=HTMLResponse)
async def risk_cockpit_partial(request: Request):
    cockpit = await _to_thread(_risk_cockpit)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/risk_cockpit.html",
        {"cockpit": cockpit},
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
    ideas = await _fetch_ideas(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_stack.html",
        {"ideas": ideas},
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
            {"idea": idea, "risk": risk, "error": None},
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
        {"idea": idea, "risk": await _fetch_risk_summary(request), "error": None},
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
                        },
                    )
    except httpx.HTTPError as exc:
        error = str(exc)
        idea = await _fetch_idea(request, idea_id)
        if idea:
            return TEMPLATES.TemplateResponse(
                request,
                "partials/idea_execute_step.html",
                {"idea": idea, "risk": await _fetch_risk_summary(request), "error": error},
            )

    ideas = await _fetch_ideas(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_stack.html",
        {"ideas": ideas},
    )


@router.get("/board/partials/ideas/{idea_id}/review", response_class=HTMLResponse)
async def idea_review_partial(request: Request, idea_id: int):
    data = await _fetch_json(request, f"/api/v1/ideas/{idea_id}")
    if not isinstance(data, dict):
        return HTMLResponse("<p>Idea not found</p>", status_code=404)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_review.html",
        {"idea": data},
    )


@router.get("/board/partials/ideas/{idea_id}/confirm-step", response_class=HTMLResponse)
async def idea_confirm_step_partial(request: Request, idea_id: int):
    idea = await _fetch_idea(request, idea_id)
    if not idea:
        return HTMLResponse("<p>Idea not found</p>", status_code=404)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_confirm_step.html",
        {
            "idea": idea,
            "cockpit": _risk_cockpit(),
            "risk": await _fetch_risk_summary(request),
            "error": None,
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
    return TEMPLATES.TemplateResponse(
        request,
        "partials/opportunity_rail.html",
        {"rail": rail},
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
