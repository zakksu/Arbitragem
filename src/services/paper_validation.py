"""Paper week validation gate — 4.0.0 GA checklist (A4.18)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT, get_settings
from src.models import JournalEntry, Trade, TradeIdea

_JOURNAL_DIR = PROJECT_ROOT / "exports" / "journal"

_TARGETS = {
    "structure_confirms": 10,
    "journal_trades": 5,
    "trade_products_journaled": 3,
    "distinct_structures": 2,
}


def _structure_confirms(session: Session) -> int:
    return (
        session.query(TradeIdea)
        .filter(TradeIdea.status.in_(["confirmed", "executed"]))
        .count()
    )


def _journal_trades(session: Session) -> int:
    return session.query(Trade).count()


def _trade_products_journaled(session: Session) -> int:
    return (
        session.query(TradeIdea)
        .filter(
            TradeIdea.status.in_(["confirmed", "executed"]),
            TradeIdea.rationale.isnot(None),
            TradeIdea.rationale != "",
        )
        .count()
    )


def _distinct_structures(session: Session) -> int:
    rows = (
        session.query(TradeIdea.structure_type)
        .filter(TradeIdea.status.in_(["confirmed", "executed"]))
        .distinct()
        .all()
    )
    return len(rows)


def build_paper_validation(session: Session) -> dict[str, Any]:
    """Checklist for paper week #3 — gate before live."""
    counts = {
        "structure_confirms": _structure_confirms(session),
        "journal_trades": _journal_trades(session),
        "trade_products_journaled": _trade_products_journaled(session),
        "distinct_structures": _distinct_structures(session),
    }
    checklist = [
        {
            "id": key,
            "label": _label_for(key),
            "current": counts[key],
            "target": target,
            "ok": counts[key] >= target,
        }
        for key, target in _TARGETS.items()
    ]
    gate_pass = counts["structure_confirms"] >= _TARGETS["structure_confirms"] and counts[
        "trade_products_journaled"
    ] >= _TARGETS["trade_products_journaled"]
    settings = get_settings()
    return {
        "week": "paper_week_3",
        "gate_pass": gate_pass,
        "paper_trading_mode": settings.paper_trading_mode,
        "checklist": checklist,
        "counts": counts,
        "targets": dict(_TARGETS),
        "note": "Run 10+ structure confirms and journal 3+ Trade Products before live.",
        "cli": "python scripts/paper_validation.py",
    }


def _label_for(key: str) -> str:
    labels = {
        "structure_confirms": "Structure confirms (confirmed + executed)",
        "journal_trades": "Paper trades in journal",
        "trade_products_journaled": "Trade Products with rationale",
        "distinct_structures": "Distinct structure types used",
    }
    return labels.get(key, key)


def _trade_row(trade: Trade) -> dict[str, Any]:
    return {
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "quantity": trade.quantity,
        "price": trade.price,
        "pnl": trade.pnl,
        "fees": trade.fees,
        "source": trade.source,
        "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
        "journal_note": trade.journal_note,
        "slippage_model": (trade.raw_payload or {}).get("slippage_model"),
    }


def _idea_row(idea: TradeIdea) -> dict[str, Any]:
    return {
        "idea_id": idea.id,
        "symbol": idea.symbol,
        "structure_type": idea.structure_type,
        "status": idea.status,
        "side": idea.side,
        "reliability": idea.reliability,
        "rationale": idea.rationale,
        "confirmed_at": idea.confirmed_at.isoformat() if idea.confirmed_at else None,
        "executed_at": idea.executed_at.isoformat() if idea.executed_at else None,
    }


def build_journal_export(session: Session) -> dict[str, Any]:
    """In-memory journal bundle for API / CLI export."""
    trades = session.query(Trade).order_by(Trade.executed_at.desc()).all()
    ideas = (
        session.query(TradeIdea)
        .filter(TradeIdea.status.in_(["confirmed", "executed", "rejected"]))
        .order_by(TradeIdea.created_at.desc())
        .all()
    )
    entries = session.query(JournalEntry).order_by(JournalEntry.created_at.desc()).all()
    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "trades": [_trade_row(t) for t in trades],
        "ideas": [_idea_row(i) for i in ideas],
        "journal_entries": [
            {
                "id": e.id,
                "trade_id": e.trade_id,
                "title": e.title,
                "content": e.content,
                "tags": e.tags,
                "mood": e.mood,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "validation": build_paper_validation(session),
    }


def write_journal_csv(session: Session) -> dict[str, Any]:
    """Write trades CSV to exports/journal/ for offline review."""
    _JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = _JOURNAL_DIR / f"paper_journal_{stamp}.csv"
    trades = session.query(Trade).order_by(Trade.executed_at.desc()).all()
    fieldnames = [
        "trade_id",
        "symbol",
        "side",
        "quantity",
        "price",
        "pnl",
        "fees",
        "source",
        "executed_at",
        "journal_note",
        "slippage_model",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            row = _trade_row(trade)
            writer.writerow({k: row.get(k) for k in fieldnames})
    return {
        "path": str(path),
        "format": "csv",
        "rows": len(trades),
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }


def journal_csv_text(session: Session) -> str:
    """CSV string for download responses."""
    buf = io.StringIO()
    fieldnames = [
        "trade_id",
        "symbol",
        "side",
        "quantity",
        "price",
        "pnl",
        "fees",
        "source",
        "executed_at",
        "journal_note",
        "slippage_model",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for trade in session.query(Trade).order_by(Trade.executed_at.desc()).all():
        row = _trade_row(trade)
        writer.writerow({k: row.get(k) for k in fieldnames})
    return buf.getvalue()
