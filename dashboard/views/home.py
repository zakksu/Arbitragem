"""Home — IBOV top 20 command center."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.alerts import render_alerts_banner
from dashboard.api_cache import cached_get, get_sidebar_context, invalidate_cache
from dashboard.utils import api_post

def _render_status_bar(account: dict, health: dict, universe_count: int) -> None:
    """Compact ProfitChart-style top strip — balance, P&L, connectors, universe."""
    paper = account.get("mock", False)
    mode_label = "PAPER" if paper else "LIVE"
    mode_color = "#f59e0b" if paper else "#22c55e"
    profit_dot = "🟢" if health.get("profit_bridge") else "🔴"
    ollama_dot = "🟢" if health.get("ollama") else "🔴"
    clear_dot = "🟢" if health.get("clear_api") else "🟡"
    version = health.get("version", "?")
    scanner_mode = health.get("scanner_mode", "ibov_top20")

    st.markdown(
        f"""
        <div style="
            display:flex; flex-wrap:wrap; align-items:center; gap:0.75rem 1.5rem;
            background:linear-gradient(90deg,#0f172a 0%,#1e293b 100%);
            border:1px solid #334155; border-radius:10px;
            padding:0.65rem 1rem; margin-bottom:0.75rem;
            font-family:'JetBrains Mono',monospace; font-size:0.8rem;
        ">
            <span style="color:{mode_color};font-weight:700;">{mode_label}</span>
            <span style="color:#94a3b8;">|</span>
            <span style="color:#94a3b8;">Saldo</span>
            <span style="color:#f8fafc;font-weight:600;">
                R$ {account.get('balance_brl', 0):,.2f}
            </span>
            <span style="color:#94a3b8;">P&L</span>
            <span style="color:{'#22c55e' if account.get('day_pnl', 0) >= 0 else '#ef4444'};font-weight:600;">
                R$ {account.get('day_pnl', 0):+,.2f}
            </span>
            <span style="color:#94a3b8;">Margem</span>
            <span style="color:#f8fafc;">R$ {account.get('available_margin', 0):,.2f}</span>
            <span style="color:#94a3b8;">|</span>
            <span style="color:#94a3b8;">IBOV</span>
            <span style="color:#f8fafc;">{universe_count}</span>
            <span style="color:#94a3b8;">|</span>
            <span>{profit_dot} Profit</span>
            <span>{ollama_dot} AI</span>
            <span>{clear_dot} Clear</span>
            <span style="color:#94a3b8;">|</span>
            <span style="color:#64748b;">v{version} · {scanner_mode}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if paper:
        st.caption("Paper mode — add Clear API keys in `.env` for live trading.")


def _render_scalp_watchlist(limit: int = 8) -> None:
    """Watchlist-style table with long/short/neutral row tinting."""
    try:
        data = cached_get("/scanner/insights", params={"limit": limit}, ttl=30)
    except Exception as exc:
        st.caption(f"Scalp picks unavailable: {exc}")
        return

    insights = data.get("insights") or []
    if not insights:
        st.info("No scalp picks yet — open **Daily Scanner** and click **Run Scan Now**.")
        return

    rows = []
    for i, item in enumerate(insights, 1):
        side = str(item.get("side_bias", "neutral")).lower()
        bias_icon = {"long": "🟢", "short": "🔴", "neutral": "⚪"}.get(side, "⚪")
        tags = ", ".join(item.get("pattern_tags") or []) or "—"
        stop = item.get("stop_ticks")
        target = item.get("target_ticks")
        rows.append(
            {
                "rank": i,
                "symbol": item["symbol"],
                "bias": f"{bias_icon} {side.upper()}",
                "reliability": float(item.get("reliability", 0)),
                "spike_score": float(item.get("spike_score", 0)),
                "volume": int(item.get("volume", 0)),
                "patterns": tags,
                "stop_target": f"{stop}/{target}" if stop is not None else "—",
            }
        )

    df = pd.DataFrame(rows)
    display_cols = [
        "rank",
        "symbol",
        "bias",
        "reliability",
        "spike_score",
        "volume",
        "patterns",
        "stop_target",
    ]

    st.caption(f"Top {len(insights)} by reliability")

    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        key="home_scalp_watchlist",
        column_config={
            "rank": st.column_config.NumberColumn("#", width="small"),
            "symbol": st.column_config.TextColumn("Symbol", width="small"),
            "bias": st.column_config.TextColumn("Bias", width="small"),
            "reliability": st.column_config.ProgressColumn(
                "Reliability", min_value=0, max_value=100, format="%.0f"
            ),
            "spike_score": st.column_config.ProgressColumn(
                "Spike", min_value=0, max_value=100, format="%.0f"
            ),
            "volume": st.column_config.NumberColumn("Volume", format="%d"),
            "patterns": st.column_config.TextColumn("Patterns", width="medium"),
            "stop_target": st.column_config.TextColumn("Stop/Target", width="small"),
        },
    )

    for item in insights:
        if item.get("ai_summary"):
            with st.expander(f"Ollama — {item['symbol']}"):
                st.markdown(item["ai_summary"])


def render() -> None:
    st.title("Trading Command Center")
    st.caption("IBOV Top 20 · 30d volume leaders · Scalping (seconds to minutes)")

    st.link_button(
        "Open Structure Deck (blackboard)",
        "http://localhost:8000/board",
        use_container_width=False,
    )

    render_alerts_banner()

    ctx = get_sidebar_context()
    account = ctx.get("account") or {}
    health = ctx.get("health") or {}
    universe_count = health.get("scanner_symbol_count", 20)

    if account or health:
        _render_status_bar(account, health, universe_count)
    else:
        st.warning("Account data unavailable — check API is running.")

    action1, action2, action3 = st.columns(3)
    with action1:
        if st.button("Run IBOV Scan", type="primary", use_container_width=True):
            with st.spinner("Scanning top 20..."):
                try:
                    r = api_post("/scanner/run")
                    invalidate_cache()
                    st.success(f"Scanned {len(r)} symbols.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with action2:
        if st.button("Sync Journal", use_container_width=True):
            with st.spinner("Syncing trades..."):
                try:
                    r = api_post("/journal/sync")
                    invalidate_cache()
                    st.success(
                        f"Clear {r.get('imported_clear', 0)} · Profit {r.get('imported_profit', 0)}"
                    )
                except Exception as exc:
                    st.error(str(exc))
    with action3:
        if st.button("Refresh", use_container_width=True):
            invalidate_cache()
            st.rerun()

    st.divider()
    st.subheader("Today's Scalp Picks")
    _render_scalp_watchlist(limit=8)

    st.divider()
    st.markdown(
        """
        ### Workflow
        1. **Run IBOV Scan** — volume + momentum on top 20
        2. **Scalp Picks** — reliability-ranked long/short bias
        3. **Ollama Insights** — refine entry/stop for a symbol
        4. **Backtest** — validate in ProfitChart before live
        """
    )
