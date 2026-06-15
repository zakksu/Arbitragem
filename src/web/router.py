"""HTMX blackboard routes — partials wired to /api/v1 universe + ideas."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.config import get_settings
from src.integrations.profit_bridge import get_profit_client
from src.web.deps import TEMPLATES

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


async def _fetch_json(request: Request, path: str) -> dict[str, Any] | list[Any] | None:
    url = f"{_api_base(request)}{path}"
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except httpx.HTTPError:
        pass
    return None


async def _fetch_universe_payload(request: Request) -> dict[str, Any]:
    data = await _fetch_json(request, "/api/v1/universe/filipe-core14")
    if isinstance(data, dict) and data.get("symbols"):
        return data
    return {"symbols": [dict(s) for s in _CORE14_FALLBACK], "sector_baskets": {}}


async def _fetch_universe(request: Request) -> list[dict[str, Any]]:
    payload = await _fetch_universe_payload(request)
    return list(payload.get("symbols") or [])


async def _fetch_ideas(request: Request) -> list[dict[str, Any]]:
    data = await _fetch_json(request, "/api/v1/ideas")
    if isinstance(data, dict):
        if "ideas" in data:
            return list(data["ideas"])
        if "items" in data:
            return list(data["items"])
    if isinstance(data, list):
        return data
    return []


async def _fetch_bootstrap(request: Request) -> dict[str, Any] | None:
    data = await _fetch_json(request, "/api/v1/bootstrap")
    return data if isinstance(data, dict) else None


def _coerce_quote(raw: Any):
    if raw is None:
        return None
    if hasattr(raw, "last"):
        return raw
    if isinstance(raw, dict):
        return SimpleNamespace(**raw)
    return None


def _quote_map(symbols: list[str]) -> dict[str, Any]:
    client = get_profit_client()
    batch = client.get_quotes_batch(symbols)
    return {sym: batch[sym] for sym in symbols if sym in batch}


@router.get("/board", response_class=HTMLResponse)
async def board_page(request: Request):
    return TEMPLATES.TemplateResponse(request, "board.html", {})


@router.get("/board/partials/status", response_class=HTMLResponse)
async def status_partial(request: Request):
    bootstrap = await _fetch_bootstrap(request)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/status_bar.html",
        {"bootstrap": bootstrap},
    )


@router.get("/board/partials/watchlist", response_class=HTMLResponse)
async def watchlist_partial(request: Request):
    symbols = await _fetch_universe(request)
    sym_list = [s["symbol"] for s in symbols if s.get("symbol")]
    settings = get_settings()
    if settings.scanner_include_bova_options:
        chain = get_profit_client().get_bova_option_chain()
        for leg in (chain.get("calls") or [])[:4] + (chain.get("puts") or [])[:4]:
            sym = leg.get("symbol")
            if sym and sym not in sym_list:
                sym_list.append(sym)
                symbols.append(
                    {"symbol": sym, "name": sym, "sector": "BOVA opt", "strike": leg.get("strike")}
                )
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

    note: dict[str, Any] | None = None
    note_data = await _fetch_json(request, f"/api/v1/board/{sym}/notes")
    if isinstance(note_data, dict):
        note = note_data

    quote = None
    bootstrap = await _fetch_bootstrap(request)
    if bootstrap:
        quotes = bootstrap.get("quotes") or {}
        quote = _coerce_quote(quotes.get(sym))

    if quote is None:
        quote = get_profit_client().get_quote(sym)

    client = get_profit_client()
    option_chain = None
    max_pain = None
    iv_rank_val = None
    und = sym if len(sym) <= 6 and not sym.startswith("BOVAX") and not sym.startswith("BOVAY") else sym[:4] + "4"
    if sym == "BOVA11" or sym.startswith("BOVA"):
        und = "BOVA11"
    try:
        option_chain = client.get_option_chain(und)
        max_pain = (option_chain or {}).get("max_pain")
        if not max_pain and option_chain:
            from src.services.structure_signals import compute_max_pain

            max_pain = compute_max_pain(option_chain)
        iv_data = client.get_iv_rank(und)
        iv_rank_val = iv_data.get("iv_rank") if iv_data else None
    except Exception:
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
        },
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
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(f"{base}/api/v1/ideas/{idea_id}/confirm")
    except httpx.HTTPError:
        pass
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
    data = await _fetch_json(request, f"/api/v1/ideas/{idea_id}")
    if not isinstance(data, dict):
        return HTMLResponse("<p>Idea not found</p>", status_code=404)
    return TEMPLATES.TemplateResponse(
        request,
        "partials/idea_confirm_step.html",
        {"idea": data},
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
