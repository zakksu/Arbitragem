"""B3 CEI export parser spike (4.3 research import)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.integrations.profit_parser import _parse_br_number, _read_csv_flexible, _rename_trade_columns


def parse_cei_export(path: Path | str) -> dict[str, Any]:
    """Parse CEI/B3-style trade export CSV into normalized preview rows."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CEI file not found: {csv_path}")

    df, read_info = _read_csv_flexible(csv_path)
    trade_df = _rename_trade_columns(df)
    if "symbol" not in trade_df.columns:
        raise ValueError(f"CEI export missing symbol column. Columns: {list(df.columns)}")

    rows: list[dict[str, Any]] = []
    for _, raw in trade_df.iterrows():
        sym = str(raw.get("symbol") or "").strip().upper()
        if not sym:
            continue
        pnl = _parse_br_number(raw.get("pnl")) if "pnl" in trade_df.columns else None
        rows.append(
            {
                "symbol": sym,
                "side": str(raw.get("side") or ""),
                "quantity": raw.get("quantity"),
                "price": _parse_br_number(raw.get("price")) if "price" in trade_df.columns else None,
                "pnl": float(pnl) if pnl is not None else None,
                "datetime": str(raw.get("datetime") or ""),
            }
        )

    if not rows:
        raise ValueError("No parseable CEI rows")

    symbols = sorted({r["symbol"] for r in rows})
    pnls = [r["pnl"] for r in rows if r.get("pnl") is not None]
    return {
        "format": "cei_csv",
        "path": str(csv_path.resolve()),
        "read_info": read_info,
        "row_count": len(rows),
        "symbols": symbols,
        "preview": rows[:25],
        "net_pnl": round(sum(pnls), 2) if pnls else None,
    }
