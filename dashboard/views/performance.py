"""Performance dashboard — P&L, drawdown, win rate."""

import streamlit as st

from dashboard.components.charts import (
    cumulative_pnl_chart,
    daily_pnl_bars,
    drawdown_chart,
    prepare_trades_df,
    symbol_pnl_bar,
    win_loss_pie,
)
from dashboard.api_cache import cached_get, invalidate_cache
from dashboard.components.empty_state import render_empty_state
from dashboard.utils import api_post


def render() -> None:
    st.title("Performance")
    st.caption("P&L analytics from Clear / Profit journal sync")

    limit = st.slider("Trades to load", 50, 500, 200, step=50)
    try:
        trades = cached_get("/trades", params={"limit": limit}, ttl=45)
    except Exception as exc:
        st.error(f"Could not load trades: {exc}")
        return

    df = prepare_trades_df(trades)
    if df.empty:
        render_empty_state(
            "No performance data yet",
            "Sync trades from Clear or Profit to see P&L, drawdown, and win rate charts.",
            actions=[
                ("Open Journal", "Journal"),
                ("Run Scanner", "Daily Scanner"),
            ],
            link_url="http://localhost:8000/board",
            link_label="Open Structure Deck",
        )
        if st.button("Sync journal now", type="primary", key="perf_empty_sync"):
            with st.spinner("Syncing trades…"):
                try:
                    api_post("/journal/sync")
                    invalidate_cache()
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        return

    total_pnl = df["pnl"].sum() if "pnl" in df.columns else 0
    wins = (df["pnl"] > 0).sum() if "pnl" in df.columns else 0
    total = len(df)
    max_dd = df["drawdown"].max() if "drawdown" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net P&L", f"R$ {total_pnl:,.2f}")
    c2.metric("Win rate", f"{100 * wins / total:.1f}%")
    c3.metric("Trades", total)
    c4.metric("Max drawdown", f"R$ {max_dd:,.2f}")

    st.plotly_chart(cumulative_pnl_chart(df), use_container_width=True)

    row2_l, row2_r = st.columns(2)
    with row2_l:
        st.plotly_chart(drawdown_chart(df), use_container_width=True)
    with row2_r:
        st.plotly_chart(win_loss_pie(df), use_container_width=True)

    row3_l, row3_r = st.columns(2)
    with row3_l:
        st.plotly_chart(daily_pnl_bars(df), use_container_width=True)
    with row3_r:
        st.plotly_chart(symbol_pnl_bar(df), use_container_width=True)

    with st.expander("Raw trade log"):
        st.dataframe(df, use_container_width=True, hide_index=True)
