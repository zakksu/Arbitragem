"""Profit CSV history import — trade archaeology timeline (4.2 A4.22)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.profit_parser import iter_profit_trade_rows
from src.logging_config import get_logger
from src.models import Trade

logger = get_logger(__name__)
_PROCESSED: set[str] = set()
_IMPORT_BATCH_SIZE = 100


def _normalize_side(raw: str | None) -> str:
    val = (raw or "buy").strip().lower()
    if val in ("c", "compra", "buy", "b", "long"):
        return "buy"
    if val in ("v", "venda", "sell", "s", "short"):
        return "sell"
    return "buy"


def _external_id(path: Path, row: dict[str, Any], idx: int) -> str:
    key = "|".join(
        str(row.get(k, ""))
        for k in ("datetime", "symbol", "side", "quantity", "price", "pnl", idx)
    )
    digest = hashlib.sha256(key.encode()).hexdigest()[:24]
    return f"arch-{path.stem}-{digest}"


def import_trade_csv(session: Session, path: Path) -> dict[str, Any]:
    """Import Profit trade-list CSV rows into `trades` with source=archaeology."""
    imported = 0
    skipped = 0
    errors: list[str] = []
    pending = 0

    for idx, row in enumerate(iter_profit_trade_rows(path)):
        ext_id = _external_id(path, row, idx)
        exists = session.query(Trade).filter(Trade.external_id == ext_id).first()
        if exists:
            skipped += 1
            continue
        executed_at = row.get("executed_at")
        if not isinstance(executed_at, datetime):
            errors.append(f"row {idx}: missing executed_at")
            continue
        try:
            payload_row = {
                k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()
            }
            session.add(
                Trade(
                    external_id=ext_id,
                    source="archaeology",
                    symbol=str(row.get("symbol") or "UNKNOWN").upper(),
                    side=_normalize_side(row.get("side")),
                    quantity=int(row.get("quantity") or 0),
                    price=float(row.get("price") or 0.0),
                    fees=float(row.get("fees") or 0.0),
                    pnl=float(row["pnl"]) if row.get("pnl") is not None else None,
                    executed_at=executed_at,
                    raw_payload={"import_path": str(path), **payload_row},
                )
            )
            imported += 1
            pending += 1
            if pending >= _IMPORT_BATCH_SIZE:
                session.commit()
                session.expire_all()
                pending = 0
        except (TypeError, ValueError) as exc:
            errors.append(f"row {idx}: {exc}")
        if len(errors) >= 20:
            break

    session.commit()
    logger.info("archaeology_import", path=str(path), imported=imported, skipped=skipped)
    return {
        "path": str(path),
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:20],
    }


def scan_archaeology_dir(session: Session) -> dict[str, Any]:
    """Scan archaeology import folder for new CSV files."""
    import_dir = get_settings().archaeology_import_path
    import_dir.mkdir(parents=True, exist_ok=True)
    total_imported = 0
    files_scanned = 0

    for path in sorted(import_dir.glob("*.csv")):
        key = f"{path.name}:{path.stat().st_mtime_ns}"
        if key in _PROCESSED:
            continue
        result = import_trade_csv(session, path)
        _PROCESSED.add(key)
        files_scanned += 1
        total_imported += int(result.get("imported") or 0)

    return {"files_scanned": files_scanned, "imported": total_imported}


def build_timeline(
    session: Session,
    *,
    limit: int = 100,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Chronological trade events from archaeology imports."""
    q = session.query(Trade).filter(Trade.source == "archaeology")
    if symbol:
        q = q.filter(Trade.symbol == symbol.strip().upper())
    rows = q.order_by(Trade.executed_at.desc()).limit(max(1, min(limit, 500))).all()
    events = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side,
            "quantity": t.quantity,
            "price": t.price,
            "pnl": t.pnl,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            "source": t.source,
        }
        for t in rows
    ]
    return {
        "events": events,
        "count": len(events),
        "symbol_filter": symbol.upper() if symbol else None,
    }
