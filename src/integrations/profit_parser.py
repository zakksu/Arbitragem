"""Parse ProfitChart backtest CSV exports (Portuguese / Brazilian format).

Supports two common export shapes from Profit Editor / Backtest:

1. **Trade list** — one row per operation (export from trades/operations grid)
2. **Summary report** — metric name + value rows, or wide single-row summary

Profit CSV conventions (B3 / Nelogica):
  - Separator: ``;`` (sometimes ``,``)
  - Encoding: ``latin-1`` or ``utf-8``
  - Decimal: ``,`` · Thousands: ``.``

Export from Profit:
  Backtest → Relatório / Operações → Exportar CSV (or Excel → save as CSV)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.logging_config import get_logger
from src.services.metrics_utils import equity_drawdown, normalize_drawdown_pct

logger = get_logger(__name__)

# --- Column aliases (normalized key → accepted header variants) ---
TRADE_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "datetime": (
        "data",
        "date",
        "data/hora",
        "data hora",
        "datetime",
        "entrada",
        "abertura",
        "horario",
        "horário",
        "data do negocio",
        "data do negócio",
    ),
    "symbol": (
        "ativo",
        "symbol",
        "ticker",
        "papel",
        "instrumento",
        "codigo de negociacao",
        "código de negociação",
    ),
    "side": (
        "tipo",
        "side",
        "operacao",
        "operação",
        "oper",
        "c/v",
        "cv",
        "direcao",
        "direção",
        "tipo de movimentacao",
        "tipo de movimentação",
    ),
    "quantity": ("quantidade", "qtd", "qty", "quantity", "contratos", "volume"),
    "price": ("preco", "preço", "price", "preco medio", "preço médio", "preco de entrada"),
    "pnl": (
        "resultado",
        "result",
        "pnl",
        "pl",
        "p/l",
        "lucro",
        "ganho",
        "profit",
        "res",
        "resultado liquido",
        "resultado líquido",
        "resultado bruto",
    ),
    "fees": ("custos", "custo", "taxa", "taxas", "fees", "corretagem", "emolumentos"),
    "gross_value": ("valor", "value", "financeiro", "total"),
}

SUMMARY_METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "total_trades": (
        "total de trades",
        "total de operações",
        "total de operacoes",
        "total operacoes",
        "total trades",
        "numero de trades",
        "número de trades",
        "qtd trades",
        "trades",
    ),
    "win_rate": (
        "taxa de acerto",
        "taxa acerto",
        "win rate",
        "percentual de acerto",
        "% acerto",
        "acerto",
    ),
    "net_pnl": (
        "resultado liquido",
        "resultado líquido",
        "lucro liquido",
        "lucro líquido",
        "net profit",
        "lucro total",
        "resultado total",
        "saldo final",
        "pl total",
        "p/l total",
    ),
    "max_drawdown": (
        "drawdown maximo",
        "drawdown máximo",
        "max drawdown",
        "maior drawdown",
        "dd maximo",
        "dd máximo",
    ),
    "profit_factor": (
        "profit factor",
        "fator de lucro",
        "fator lucro",
        "fator de profit",
    ),
    "gross_profit": ("lucro bruto", "ganho bruto", "gross profit"),
    "gross_loss": ("perda bruta", "prejuizo bruto", "prejuízo bruto", "gross loss"),
    "avg_trade": (
        "media por trade",
        "média por trade",
        "resultado medio",
        "resultado médio",
        "avg trade",
    ),
    "sharpe": ("sharpe", "sharpe ratio", "indice sharpe", "índice sharpe"),
}


@dataclass
class ProfitBacktestResult:
    """Normalized backtest metrics from a ProfitChart CSV."""

    source: str = "profit_chart"
    path: str = ""
    format: str = "unknown"  # trades | summary | hybrid
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    net_pnl: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    sharpe: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    avg_trade: float = 0.0
    start_date: str | None = None
    end_date: str | None = None
    symbols: list[str] = field(default_factory=list)
    trades_preview: list[dict[str, Any]] = field(default_factory=list)
    raw_columns: list[str] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)

    def drawdown_pct(self) -> float | None:
        if self.max_drawdown <= 0:
            return 0.0 if self.total_trades else None
        peak_hint = max(10_000.0, 10_000.0 + self.net_pnl) if self.net_pnl else 10_000.0
        return normalize_drawdown_pct(self.max_drawdown, equity_peak=peak_hint)

    def to_dict(self) -> dict[str, Any]:
        dd_pct = self.drawdown_pct()
        payload: dict[str, Any] = {
            "source": self.source,
            "path": self.path,
            "format": self.format,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "net_pnl": round(self.net_pnl, 4),
            "win_rate": round(self.win_rate, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "profit_factor": round(self.profit_factor, 4),
            "sharpe": round(self.sharpe, 4),
            "gross_profit": round(self.gross_profit, 4),
            "gross_loss": round(self.gross_loss, 4),
            "avg_trade": round(self.avg_trade, 4),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "symbols": self.symbols,
            "symbol": self.symbols[0] if self.symbols else None,
            "trades_preview": self.trades_preview,
            "raw_columns": self.raw_columns,
            "parse_warnings": self.parse_warnings,
        }
        if dd_pct is not None:
            payload["max_drawdown_pct"] = dd_pct
        return payload


def _normalize_header(name: str) -> str:
    text = str(name).strip().lower()
    text = text.replace("\ufeff", "")  # BOM
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text


def _parse_br_number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "—", "nan", "None"}:
        return None
    # Percent e.g. "58,5%" or "58.5%"
    is_pct = text.endswith("%")
    if is_pct:
        text = text[:-1].strip()
    text = text.replace("R$", "").replace("r$", "").strip()
    text = text.replace(" ", "")
    # Brazilian: 1.234,56 → 1234.56
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        num = float(text)
        return num / 100.0 if is_pct and num > 1 else num
    except ValueError:
        return None


def _label_matches_metric(label: str, aliases: tuple[str, ...]) -> bool:
    if label in aliases:
        return True
    normalized_aliases = {_normalize_header(a) for a in aliases}
    if label in normalized_aliases:
        return True
    return any(a in label or label in a for a in normalized_aliases)


def _match_alias(column: str, aliases: dict[str, tuple[str, ...]]) -> str | None:
    col = _normalize_header(column)
    for key, variants in aliases.items():
        if _label_matches_metric(col, variants):
            return key
    return None


def _has_mojibake(text: str) -> bool:
    """Detect latin-1 misread of UTF-8 Portuguese text."""
    return any(c in text for c in "§μ¡©\ufffd") or "\xad" in text


def _read_csv_flexible(path: Path) -> tuple[pd.DataFrame, str]:
    """Try common Profit export encodings and separators."""
    attempts = [
        {"sep": ";", "encoding": "utf-8", "decimal": ",", "thousands": "."},
        {"sep": ";", "encoding": "latin-1", "decimal": ",", "thousands": "."},
        {"sep": ";", "encoding": "utf-8-sig", "decimal": ",", "thousands": "."},
        {"sep": ",", "encoding": "utf-8"},
        {"sep": ",", "encoding": "latin-1"},
    ]
    best: tuple[pd.DataFrame, str] | None = None
    last_error: Exception | None = None
    for opts in attempts:
        try:
            df = pd.read_csv(path, **opts, engine="python", on_bad_lines="skip")
            if df.shape[1] < 1 or len(df) < 1:
                continue
            header_blob = " ".join(str(c) for c in df.columns)
            if _has_mojibake(header_blob) or any(
                _has_mojibake(str(v)) for v in df.iloc[:3, 0].astype(str)
            ):
                continue
            return df, f"sep={opts['sep']} enc={opts['encoding']}"
        except Exception as exc:
            last_error = exc
    if best:
        return best
    raise ValueError(f"Could not read CSV: {path} ({last_error})")


def _rename_trade_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping: dict[str, str] = {}
    for col in df.columns:
        key = _match_alias(col, TRADE_COLUMN_ALIASES)
        if key and key not in mapping.values():
            mapping[col] = key
    return df.rename(columns=mapping)


def _is_trade_list(df: pd.DataFrame) -> bool:
    cols = {_normalize_header(c) for c in df.columns}
    has_pnl = any(_match_alias(c, {"pnl": TRADE_COLUMN_ALIASES["pnl"]}) for c in df.columns)
    has_symbol = any(_match_alias(c, {"symbol": TRADE_COLUMN_ALIASES["symbol"]}) for c in df.columns)
    # At least 2 rows and a result column
    return len(df) >= 2 and has_pnl and (has_symbol or len(cols) >= 3)


def _is_summary_kv(df: pd.DataFrame) -> bool:
    """Two-column metric / value layout."""
    if df.shape[1] != 2:
        return False
    c0 = _normalize_header(df.columns[0])
    c1 = _normalize_header(df.columns[1])
    kv_headers = (
        ("métrica", "valor"),
        ("metrica", "valor"),
        ("indicador", "valor"),
        ("metric", "value"),
        ("campo", "valor"),
    )
    if (c0, c1) in kv_headers:
        return True
    # Heuristic: first column strings look like metric names
    sample = df.iloc[:5, 0].astype(str).str.lower()
    hits = sample.apply(
        lambda s: any(alias in s for aliases in SUMMARY_METRIC_ALIASES.values() for alias in aliases)
    ).sum()
    return hits >= 2


def _extract_summary_kv(df: pd.DataFrame) -> dict[str, float]:
    metrics: dict[str, float] = {}
    col_key, col_val = df.columns[0], df.columns[1]
    for _, row in df.iterrows():
        label = _normalize_header(row[col_key])
        value = _parse_br_number(row[col_val])
        if value is None:
            continue
        for metric_key, aliases in SUMMARY_METRIC_ALIASES.items():
            if _label_matches_metric(label, aliases):
                metrics[metric_key] = value
                break
    return metrics


def _extract_summary_wide(df: pd.DataFrame) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if len(df) == 0:
        return metrics
    row = df.iloc[0]
    for col in df.columns:
        label = _normalize_header(col)
        value = _parse_br_number(row[col])
        if value is None:
            continue
        for metric_key, aliases in SUMMARY_METRIC_ALIASES.items():
            if _label_matches_metric(label, aliases):
                metrics[metric_key] = value
                break
    return metrics


def _compute_from_trades(df: pd.DataFrame) -> ProfitBacktestResult:
    result = ProfitBacktestResult(format="trades")
    result.raw_columns = list(df.columns)

    if "pnl" not in df.columns:
        raise ValueError("Trade list CSV missing result/PnL column")

    pnls = df["pnl"].apply(_parse_br_number)
    valid = pnls.notna()
    pnls = pnls[valid].astype(float)

    # Profit often exports entry legs with Resultado=0; count only closed legs
    closed = pnls[pnls != 0]
    if len(closed) < len(pnls):
        result.parse_warnings.append(
            f"ignored {len(pnls) - len(closed)} zero-PnL rows (entry legs)"
        )
    pnls = closed if len(closed) > 0 else pnls

    if pnls.empty:
        raise ValueError("No parseable PnL values in trade list")

    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    result.total_trades = int(len(pnls))
    result.winning_trades = int(len(wins))
    result.losing_trades = int(len(losses))
    result.net_pnl = float(pnls.sum())
    result.win_rate = float(len(wins) / len(pnls)) if len(pnls) else 0.0
    result.gross_profit = float(wins.sum()) if len(wins) else 0.0
    result.gross_loss = float(abs(losses.sum())) if len(losses) else 0.0
    result.profit_factor = (
        result.gross_profit / result.gross_loss if result.gross_loss > 0 else 0.0
    )
    result.avg_trade = float(pnls.mean())

    max_dd, _ = equity_drawdown(pnls.to_numpy())
    result.max_drawdown = max_dd

    if len(pnls) > 1 and pnls.std() > 0:
        result.sharpe = float((pnls.mean() / pnls.std()) * (252**0.5))

    if "symbol" in df.columns:
        result.symbols = sorted(df["symbol"].dropna().astype(str).unique().tolist())

    if "datetime" in df.columns:
        dates = pd.to_datetime(df["datetime"], dayfirst=True, errors="coerce").dropna()
        if not dates.empty:
            result.start_date = dates.min().isoformat()
            result.end_date = dates.max().isoformat()

    preview_cols = [c for c in ("datetime", "symbol", "side", "quantity", "price", "pnl") if c in df.columns]
    preview = df[preview_cols].head(20) if preview_cols else df.head(20)
    result.trades_preview = preview.to_dict(orient="records")

    return result


def _apply_summary_metrics(result: ProfitBacktestResult, summary: dict[str, float]) -> None:
    if "total_trades" in summary:
        result.total_trades = int(summary["total_trades"])
    if "win_rate" in summary:
        wr = summary["win_rate"]
        result.win_rate = wr / 100.0 if wr > 1 else wr
    if "net_pnl" in summary:
        result.net_pnl = summary["net_pnl"]
    if "max_drawdown" in summary:
        dd = summary["max_drawdown"]
        result.max_drawdown = abs(dd)
    if "profit_factor" in summary:
        result.profit_factor = summary["profit_factor"]
    if "sharpe" in summary:
        result.sharpe = summary["sharpe"]
    if "gross_profit" in summary:
        result.gross_profit = summary["gross_profit"]
    if "gross_loss" in summary:
        result.gross_loss = summary["gross_loss"]
    if "avg_trade" in summary:
        result.avg_trade = summary["avg_trade"]


def parse_profit_backtest_csv(path: Path | str) -> ProfitBacktestResult:
    """Parse a ProfitChart backtest CSV and return normalized metrics."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    result = ProfitBacktestResult(path=str(csv_path.resolve()))
    df, read_info = _read_csv_flexible(csv_path)
    result.parse_warnings.append(f"read with {read_info}")

    logger.info("profit_csv_loaded", path=str(csv_path), rows=len(df), cols=list(df.columns))

    # Summary key-value (2 columns)
    if _is_summary_kv(df):
        result.format = "summary"
        summary = _extract_summary_kv(df)
        _apply_summary_metrics(result, summary)
        result.raw_columns = list(df.columns)
        return result

    # Trade list
    trade_df = _rename_trade_columns(df)
    if _is_trade_list(trade_df):
        trade_result = _compute_from_trades(trade_df)
        trade_result.path = result.path
        trade_result.parse_warnings.extend(result.parse_warnings)
        return trade_result

    # Wide summary (single row, metric names as headers)
    wide = _extract_summary_wide(df)
    if wide:
        result.format = "summary_wide"
        result.raw_columns = list(df.columns)
        _apply_summary_metrics(result, wide)
        return result

    # Last resort: if any column looks like pnl, try trades
    trade_df = _rename_trade_columns(df)
    if "pnl" in trade_df.columns:
        result.parse_warnings.append("fallback: parsed as trades via pnl column only")
        trade_result = _compute_from_trades(trade_df)
        trade_result.path = result.path
        trade_result.parse_warnings.extend(result.parse_warnings)
        return trade_result

    raise ValueError(
        f"Unrecognized Profit CSV format. Columns: {list(df.columns)}. "
        "Export trades (Operações) or summary report from Profit backtest."
    )


def _side_is_sell(raw_side: str | None) -> bool:
    val = (raw_side or "").strip().lower()
    return val in ("v", "venda", "sell", "s", "short")


def _infer_row_pnl(raw: Any, trade_df: pd.DataFrame) -> float | None:
    """PnL column, or signed cash flow from B3 CEI ``valor`` column."""
    pnl = _parse_br_number(raw.get("pnl"))
    if pnl is not None:
        return float(pnl)
    if "gross_value" not in trade_df.columns:
        return None
    gross = _parse_br_number(raw.get("gross_value"))
    if gross is None:
        return 0.0
    side_raw = str(raw.get("side") or "buy")
    return float(gross) if _side_is_sell(side_raw) else -float(gross)


def _iter_trade_df_rows(trade_df: pd.DataFrame):
    if "pnl" not in trade_df.columns and "gross_value" not in trade_df.columns:
        raise ValueError("Trade list CSV missing result/PnL or valor column")

    for _, raw in trade_df.iterrows():
        pnl = _infer_row_pnl(raw, trade_df)
        if pnl is None:
            continue
        symbol = str(raw.get("symbol") or "UNKNOWN").strip().upper()
        side = str(raw.get("side") or "buy")
        qty = raw.get("quantity")
        try:
            quantity = int(float(qty)) if qty is not None and str(qty).strip() else 0
        except (TypeError, ValueError):
            quantity = 0
        price_val = _parse_br_number(raw.get("price"))
        price = float(price_val) if price_val is not None else 0.0
        fees_val = _parse_br_number(raw.get("fees")) if "fees" in trade_df.columns else None
        fees = float(fees_val) if fees_val is not None else 0.0

        executed_at: datetime | None = None
        if "datetime" in trade_df.columns:
            dt = pd.to_datetime(raw.get("datetime"), dayfirst=True, errors="coerce")
            if pd.notna(dt):
                executed_at = dt.to_pydatetime()

        if executed_at is None:
            executed_at = datetime.utcnow()

        yield {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "fees": fees,
            "pnl": float(pnl),
            "executed_at": executed_at,
        }


def parse_profit_trade_rows(path: Path | str) -> list[dict[str, Any]]:
    """Parse Profit trade-list CSV into rows for archaeology import."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df, _ = _read_csv_flexible(csv_path)
    trade_df = _rename_trade_columns(df)
    rows = list(_iter_trade_df_rows(trade_df))
    if not rows:
        raise ValueError("No parseable trade rows in CSV")
    return rows


def iter_profit_trade_rows(path: Path | str):
    """Yield trade rows one at a time — same parse rules as parse_profit_trade_rows."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df, _ = _read_csv_flexible(csv_path)
    trade_df = _rename_trade_columns(df)
    yield from _iter_trade_df_rows(trade_df)


def save_uploaded_csv(content: bytes, filename: str, export_dir: Path) -> Path:
    """Save uploaded CSV bytes to exports/profit and return path."""
    export_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]", "_", filename) or "upload.csv"
    if not safe.lower().endswith(".csv"):
        safe += ".csv"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = export_dir / f"{stamp}_{safe}"
    dest.write_bytes(content)
    return dest
