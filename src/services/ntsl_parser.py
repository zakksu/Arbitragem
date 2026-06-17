"""Extract structured logic from ProfitChart NTSL strategy files (10.0)."""

from __future__ import annotations

import hashlib
import re
from typing import Any


_INPUT_RE = re.compile(r"^\s*(\w+)\s*\(([^)]*)\)\s*;", re.MULTILINE | re.IGNORECASE)
_VAR_RE = re.compile(r"^\s*var\s*\n((?:\s*\w+\s*:\s*\w+\s*;\s*\n?)*)", re.MULTILINE | re.IGNORECASE)
_SYMBOL_RE = re.compile(r'"([A-Z]{4}\d{1,2})"')
_BUY_SELL_RE = re.compile(r"\b(Buy|Sell|BuyAtMarket|SellAtMarket|BuyLimit|SellLimit)\b", re.IGNORECASE)
_STOP_RE = re.compile(r"(SetStopLoss|StopLoss|Stop)\s*\(([^)]*)\)", re.IGNORECASE)
_TARGET_RE = re.compile(r"(SetProfitTarget|ProfitTarget|Target)\s*\(([^)]*)\)", re.IGNORECASE)
_STRUCTURE_HINTS = (
    "covered call",
    "vertical",
    "collar",
    "scalp",
    "pair",
    "hedge",
    "spread",
)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def extract_ntsl_features(code: str) -> dict[str, Any]:
    """Parse NTSL source into tags usable by strategy store + RAG."""
    lines = code.splitlines()
    inputs = [
        {"name": m.group(1), "default": m.group(2).strip()}
        for m in _INPUT_RE.finditer(code)
    ]
    symbols = sorted(set(_SYMBOL_RE.findall(code)))
    buy_sell = sorted({m.group(1).lower() for m in _BUY_SELL_RE.finditer(code)})
    stops = [m.group(2).strip() for m in _STOP_RE.finditer(code)]
    targets = [m.group(2).strip() for m in _TARGET_RE.finditer(code)]
    comments = [
        ln.strip().lstrip("/").strip()
        for ln in lines
        if ln.strip().startswith("//") and len(ln.strip()) > 4
    ]
    lower = code.lower()
    structure_hints = [h for h in _STRUCTURE_HINTS if h in lower]
    leg_comments = [c for c in comments if c.lower().startswith("leg ")]
    return {
        "inputs": inputs[:20],
        "symbols": symbols[:12],
        "order_ops": buy_sell[:8],
        "stop_exprs": stops[:6],
        "target_exprs": targets[:6],
        "structure_hints": structure_hints,
        "leg_count": len(leg_comments) or (2 if "covered" in lower else 1),
        "summary": _summarize(code, symbols, structure_hints, buy_sell),
        "line_count": len(lines),
    }


def _summarize(
    code: str,
    symbols: list[str],
    structure_hints: list[str],
    buy_sell: list[str],
) -> str:
    sym = symbols[0] if symbols else "?"
    st = structure_hints[0] if structure_hints else "custom"
    ops = "/".join(buy_sell[:2]) if buy_sell else "no_orders"
    return f"{st} on {sym} — ops: {ops} ({len(code)} chars)"
