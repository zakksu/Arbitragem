"""B3 trade history Excel import — Filipe full history into journal (10.0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from src.integrations.profit_parser import (
    _parse_br_number,
    _rename_trade_columns,
)
from src.logging_config import get_logger
from src.services.trade_archaeology import import_trade_csv

logger = get_logger(__name__)


def _read_excel_df(path: Path) -> pd.DataFrame:
    try:
        return pd.read_excel(path, engine="openpyxl")
    except ImportError as exc:
        raise RuntimeError("openpyxl required for .xlsx — pip install openpyxl") from exc


def _normalize_excel_to_csv(path: Path, dest: Path) -> Path:
    """Convert Excel export to UTF-8 CSV for shared archaeology pipeline."""
    df = _read_excel_df(path)
    df.columns = [str(c).strip() for c in df.columns]
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, sep=";", index=False, encoding="utf-8")
    return dest


def import_b3_history_excel(session: Session, path: Path) -> dict[str, Any]:
    """Import B3 history from .xlsx or .xls via pandas → archaeology CSV pipeline."""
    path = Path(path)
    if not path.exists():
        return {"ok": False, "error": "file_not_found", "path": str(path)}

    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        csv_dest = path.with_suffix(".imported.csv")
        try:
            _normalize_excel_to_csv(path, csv_dest)
        except Exception as exc:
            logger.error("excel_read_failed", path=str(path), error=str(exc))
            return {"ok": False, "error": str(exc), "path": str(path)}
        result = import_trade_csv(session, csv_dest)
        result["source_format"] = "excel"
        result["original_path"] = str(path)
        return result

    if suffix == ".csv":
        result = import_trade_csv(session, path)
        result["source_format"] = "csv"
        return result

    return {"ok": False, "error": "unsupported_type", "path": str(path)}


def preview_excel_rows(path: Path, *, limit: int = 5) -> dict[str, Any]:
    """Lightweight preview without DB write."""
    path = Path(path)
    if path.suffix.lower() not in (".xlsx", ".xls"):
        return {"error": "not_excel"}
    df = _read_excel_df(path)
    trade_df = _rename_trade_columns(df)
    preview = []
    for _, raw in trade_df.head(limit).iterrows():
        preview.append(
            {
                "symbol": str(raw.get("symbol", "")),
                "side": str(raw.get("side", "")),
                "pnl": _parse_br_number(raw.get("pnl")),
            }
        )
    return {"columns": list(trade_df.columns), "preview": preview, "row_count": len(trade_df)}
