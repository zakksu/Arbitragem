"""Reusable Plotly charts for performance and monitoring."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8"),
    margin=dict(l=40, r=20, t=50, b=40),
)


def cumulative_pnl_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["executed_at"],
            y=df["cum_pnl"],
            mode="lines",
            fill="tozeroy",
            line=dict(color="#22c55e", width=2),
            fillcolor="rgba(34,197,94,0.15)",
            name="P&L",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#475569", line_width=1)
    fig.update_layout(
        title="Cumulative P&L",
        xaxis_title="",
        yaxis_title="R$",
        height=380,
        **CHART_LAYOUT,
    )
    return fig


def drawdown_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=df["executed_at"],
            y=df["drawdown"],
            fill="tozeroy",
            line=dict(color="#ef4444", width=2),
            fillcolor="rgba(239,68,68,0.2)",
            name="Drawdown",
        )
    )
    fig.update_layout(
        title="Drawdown",
        xaxis_title="",
        yaxis_title="R$",
        height=280,
        **CHART_LAYOUT,
    )
    return fig


def daily_pnl_bars(df: pd.DataFrame) -> go.Figure:
    daily = df.groupby(df["executed_at"].dt.date)["pnl"].sum().reset_index()
    daily.columns = ["date", "pnl"]
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in daily["pnl"]]
    fig = go.Figure(go.Bar(x=daily["date"], y=daily["pnl"], marker_color=colors))
    fig.update_layout(title="Daily P&L", height=300, **CHART_LAYOUT)
    return fig


def win_loss_pie(df: pd.DataFrame) -> go.Figure:
    if "pnl" not in df.columns or df["pnl"].isna().all():
        return go.Figure()
    wins = (df["pnl"] > 0).sum()
    losses = (df["pnl"] <= 0).sum()
    fig = go.Figure(
        go.Pie(
            labels=["Wins", "Losses"],
            values=[wins, losses],
            hole=0.55,
            marker_colors=["#22c55e", "#ef4444"],
            textinfo="label+percent",
        )
    )
    fig.update_layout(title="Win / Loss", height=280, **CHART_LAYOUT)
    return fig


def symbol_pnl_bar(df: pd.DataFrame) -> go.Figure:
    if "pnl" not in df.columns:
        return go.Figure()
    sym = df.groupby("symbol")["pnl"].sum().sort_values()
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in sym]
    fig = go.Figure(go.Bar(x=sym.values, y=sym.index, orientation="h", marker_color=colors))
    fig.update_layout(title="P&L by Symbol", height=max(260, 40 * len(sym)), **CHART_LAYOUT)
    return fig


def backtest_compare_chart(profit_metrics: dict, python_metrics: dict) -> go.Figure:
    keys = ["net_pnl", "win_rate", "max_drawdown", "sharpe"]
    labels = ["Net P&L", "Win Rate", "Max DD", "Sharpe"]
    profit_vals = [profit_metrics.get(k, 0) or 0 for k in keys]
    python_vals = [python_metrics.get(k, 0) or 0 for k in keys]

    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(go.Bar(name="ProfitChart", x=labels, y=profit_vals, marker_color="#3b82f6"))
    fig.add_trace(go.Bar(name="Python", x=labels, y=python_vals, marker_color="#a855f7"))
    fig.update_layout(barmode="group", title="Backtest Engine Comparison", height=360, **CHART_LAYOUT)
    return fig


def prepare_trades_df(trades: list) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["executed_at"] = pd.to_datetime(df["executed_at"])
    df = df.sort_values("executed_at")
    if "pnl" in df.columns:
        df["pnl"] = df["pnl"].fillna(0)
        df["cum_pnl"] = df["pnl"].cumsum()
        peak = df["cum_pnl"].cummax()
        df["drawdown"] = peak - df["cum_pnl"]
    return df
