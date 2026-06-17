"""Bottom pulse rail feeds — news RSS, calendar, lessons (4.0 GA)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from src.services.education import daily_axiom, list_axioms

_RSS_FEEDS = (
    "https://www.investing.com/rss/news_285.rss",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^BVSP&region=US&lang=en-US",
)
_CURATED_NEWS = [
    {
        "headline": "B3 session — Core14 liquidity normal",
        "summary": "No major macro surprise in last hour; sector pairs active.",
    },
    {
        "headline": "Ibovespa futures steady ahead of open",
        "summary": "Pre-market volumes within 30-day average.",
    },
]


def _parse_rss(xml_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title = item.findtext("title") or ""
            desc = item.findtext("description") or ""
            if title:
                items.append({"headline": title.strip()[:120], "summary": desc.strip()[:200]})
            if len(items) >= 3:
                break
    except ET.ParseError:
        pass
    return items


def _fetch_headlines() -> dict:
    from src.config import get_settings

    if get_settings().low_ram_enabled:
        idx = datetime.utcnow().day % len(_CURATED_NEWS)
        return dict(_CURATED_NEWS[idx])
    for url in _RSS_FEEDS:
        try:
            with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "ArbitragemDashboard/4.0"})
                if r.status_code == 200 and r.text.strip():
                    items = _parse_rss(r.text)
                    if items:
                        return items[0]
        except httpx.HTTPError:
            continue
    idx = datetime.utcnow().day % len(_CURATED_NEWS)
    return dict(_CURATED_NEWS[idx])


def _calendar_events() -> list[dict[str, str]]:
    now = datetime.utcnow()
    return [
        {"time": "10:00", "label": "B3 cash open", "impact": "high"},
        {"time": "14:30", "label": "US economic data (watch USD/BRL)", "impact": "medium"},
        {"time": "17:55", "label": "B3 closing auction", "impact": "high"},
        {"time": "18:00", "label": "After-market", "impact": "low"},
    ]


def get_pulse_rail() -> dict:
    lesson = daily_axiom()
    return {
        "news": _fetch_headlines(),
        "calendar": {"events": _calendar_events()},
        "lesson": lesson,
        "axioms_count": len(list_axioms()),
    }
