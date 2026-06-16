"""Backtest metric normalization — drawdown % without bogus 100% defaults."""

from __future__ import annotations

from typing import Any

import numpy as np


def equity_drawdown(pnls: np.ndarray | list[float]) -> tuple[float, float | None]:
    """Return (max_drawdown_abs, max_drawdown_pct) from a PnL series."""
    arr = np.asarray(pnls, dtype=float)
    if arr.size == 0:
        return 0.0, None
    equity = np.cumsum(arr)
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_dd = float(drawdown.max()) if drawdown.size else 0.0
    if max_dd <= 0:
        return 0.0, 0.0
    idx = int(drawdown.argmax())
    peak_at = float(peak[idx])
    if peak_at <= 0:
        return max_dd, None
    return max_dd, round(max_dd / peak_at * 100.0, 4)


def normalize_drawdown_pct(
    value: float | int | None,
    *,
    equity_peak: float | None = None,
) -> float | None:
    """Normalize mixed Profit/Clear DD inputs to a percentage, or None if unknown."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v < 0:
        v = abs(v)
    if v == 0:
        return 0.0
    if 0 < v <= 1.0:
        return round(v * 100.0, 4)
    if equity_peak and equity_peak > 0 and v > 1.0:
        if v > equity_peak * 0.15:
            return round(v / equity_peak * 100.0, 4)
    if v <= 100.0:
        return round(v, 4)
    if equity_peak and equity_peak > 0:
        return round(v / equity_peak * 100.0, 4)
    return round(v, 4)


def backtest_proof_drawdown_pct(metrics: dict[str, Any] | None) -> float | None:
    """Extract display/gate drawdown % from heterogeneous backtest dicts."""
    if not metrics:
        return None
    if metrics.get("max_drawdown_pct") is not None:
        return normalize_drawdown_pct(
            metrics["max_drawdown_pct"],
            equity_peak=_equity_peak_hint(metrics),
        )
    raw = metrics.get("max_drawdown") or metrics.get("maxDrawdown")
    if raw is None:
        return None
    return normalize_drawdown_pct(raw, equity_peak=_equity_peak_hint(metrics))


def metrics_with_drawdown_pct(metrics: dict[str, Any]) -> dict[str, Any]:
    """Ensure backtest metrics include max_drawdown_pct when computable."""
    out = dict(metrics)
    dd_pct = backtest_proof_drawdown_pct(out)
    if dd_pct is not None:
        out["max_drawdown_pct"] = dd_pct
    elif "max_drawdown_pct" in out:
        out.pop("max_drawdown_pct", None)
    return out


def _equity_peak_hint(metrics: dict[str, Any]) -> float | None:
    for key in ("equity_peak", "peak_equity", "initial_balance", "saldo_inicial"):
        if metrics.get(key) is not None:
            try:
                return float(metrics[key])
            except (TypeError, ValueError):
                continue
    net = metrics.get("net_pnl")
    if net is not None:
        try:
            base = 10_000.0
            return max(base, base + float(net))
        except (TypeError, ValueError):
            pass
    return None
