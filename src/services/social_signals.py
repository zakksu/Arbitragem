"""Read-only social signals — RSS + curated Twitter stubs (4.1 A4.21)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import httpx

from src.services.futures_universe import symbol_list as futures_symbols

_DISCLAIMER = "Read-only signals — never auto-trade from social feeds."

_RSS_FEEDS = (
    ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^BVSP&region=US&lang=en-US", "Yahoo Finance"),
    ("https://www.investing.com/rss/news_285.rss", "Investing.com"),
)

_CURATED_SOCIAL = [
    {
        "source": "twitter",
        "author": "@B3_Official",
        "handle": "B3_Official",
        "text": "Ibovespa futures volume above 30-day average in first hour — liquidity supportive for WIN scalps.",
        "symbols": ["WINFUT", "BOVA11"],
        "sentiment": "bullish",
        "tags": ["futures", "liquidity"],
    },
    {
        "source": "twitter",
        "author": "@ValorEconomico",
        "handle": "ValorEconomico",
        "text": "USD/BRL steady near 5.50 — WDO range trade setups in focus; no surprise on BCB wire.",
        "symbols": ["WDOFUT", "PETR4"],
        "sentiment": "neutral",
        "tags": ["fx", "macro"],
    },
    {
        "source": "twitter",
        "author": "@InfoMoney",
        "handle": "InfoMoney",
        "text": "Energy basket leads sector gainers — PETR/PRIO pair spread narrowing after open.",
        "symbols": ["PETR4", "PRIO3"],
        "sentiment": "bullish",
        "tags": ["sector", "pairs"],
    },
]


def _parse_rss_items(xml_text: str, feed_name: str) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            desc = (item.findtext("description") or "").strip()
            if not title:
                continue
            symbols = _extract_symbols(f"{title} {desc}")
            items.append(
                {
                    "id": f"rss-{hash(title) & 0xFFFFFF:06x}",
                    "source": "rss",
                    "author": feed_name,
                    "text": title[:240],
                    "summary": desc[:300],
                    "symbols": symbols,
                    "sentiment": "neutral",
                    "read_only": True,
                    "auto_trade": False,
                    "published_at": (datetime.utcnow() - timedelta(minutes=len(items) * 17)).isoformat() + "Z",
                }
            )
            if len(items) >= 3:
                break
    except ET.ParseError:
        pass
    return items


def _extract_symbols(text: str) -> list[str]:
    upper = text.upper()
    found: list[str] = []
    tickers = (
        "PETR4",
        "VALE3",
        "PRIO3",
        "ITUB4",
        "BOVA11",
        "WINFUT",
        "WDOFUT",
    )
    for t in tickers:
        if t in upper.replace(" ", ""):
            found.append(t)
    for f in futures_symbols():
        if f in upper and f not in found:
            found.append(f)
    return found[:5]


def _fetch_rss_signals() -> list[dict]:
    for url, name in _RSS_FEEDS:
        try:
            with httpx.Client(timeout=4.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "ArbitragemDashboard/4.1"})
                if r.status_code == 200 and r.text.strip():
                    items = _parse_rss_items(r.text, name)
                    if items:
                        return items
        except httpx.HTTPError:
            continue
    return []


def _curated_twitter_signals() -> list[dict]:
    now = datetime.utcnow()
    out: list[dict] = []
    for i, row in enumerate(_CURATED_SOCIAL):
        out.append(
            {
                "id": f"tw-{row['handle'].lower()}",
                "source": "twitter",
                "author": row["author"],
                "handle": row["handle"],
                "text": row["text"],
                "symbols": row["symbols"],
                "sentiment": row["sentiment"],
                "tags": row.get("tags", []),
                "read_only": True,
                "auto_trade": False,
                "published_at": (now - timedelta(minutes=30 + i * 45)).isoformat() + "Z",
            }
        )
    return out


def get_social_signals(*, limit: int = 12) -> dict:
    """Aggregate read-only social/RSS signals — no order routing."""
    from src.services.futures_quotes import futures_session_status

    fetched_at = datetime.utcnow()
    rss = _fetch_rss_signals()
    twitter = _curated_twitter_signals()
    combined = rss + twitter
    combined.sort(key=lambda s: s.get("published_at", ""), reverse=True)
    trimmed = combined[: max(1, min(limit, 50))]
    sources_active = sorted({s.get("source", "unknown") for s in trimmed if s.get("source")})
    freshness_minutes: int | None = None
    if trimmed and trimmed[0].get("published_at"):
        try:
            newest = datetime.fromisoformat(trimmed[0]["published_at"].replace("Z", "+00:00"))
            freshness_minutes = max(0, int((fetched_at - newest.replace(tzinfo=None)).total_seconds() / 60))
        except (ValueError, TypeError):
            pass
    return {
        "signals": trimmed,
        "count": len(trimmed),
        "read_only": True,
        "auto_trade": False,
        "disclaimer": _DISCLAIMER,
        "sources": ["rss", "twitter"],
        "sources_active": sources_active,
        "fetched_at": fetched_at.isoformat() + "Z",
        "freshness_minutes": freshness_minutes,
        "session": futures_session_status(),
    }
