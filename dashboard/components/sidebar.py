"""Shared sidebar with navigation and system status."""

from __future__ import annotations

import streamlit as st

from dashboard.api_cache import get_sidebar_context, invalidate_cache, refresh_integrations
from dashboard.components.alerts import render_alerts_sidebar
from dashboard.utils import api_post

PAGES = [
    "Home",
    "Live Monitor",
    "Performance",
    "Daily Scanner",
    "Strategies",
    "Backtest & Optimize",
    "Journal",
    "Ollama Insights",
    "Settings",
]


def _integration_dots(health: dict) -> str:
    ollama = health.get("ollama")
    profit = health.get("profit_bridge")
    clear = health.get("clear_api")

    def dot(ok: bool | None) -> str:
        if ok is None:
            return "⚪"
        return "🟢" if ok else "🔴"

    clear_dot = "🟢" if clear else "🟡"
    return f"{dot(ollama)} AI · {dot(profit)} Profit · {clear_dot} Clear"


def render_sidebar() -> str:
    st.sidebar.markdown(
        '<div class="arb-logo">📈 <span>Arbitragem</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("IBOV Top 20 · Profit + Clear + Ollama")

    ctx = get_sidebar_context()
    health = ctx.get("health") or {}

    if health.get("status") == "ok" or health.get("version"):
        st.sidebar.success(f"API online · v{health.get('version', '?')}")
        if health.get("paper_trading_mode"):
            st.sidebar.warning("📄 Paper mode")
        mode = health.get("scanner_mode", "ibov_top20")
        count = health.get("scanner_symbol_count", "?")
        st.sidebar.caption(f"Scan: {count} sym · `{mode}`")
        st.sidebar.caption(_integration_dots(health))
    else:
        st.sidebar.error("API offline")
        st.sidebar.caption("Run: python scripts/dev.py start")

    st.sidebar.divider()
    nav_override = st.session_state.pop("nav_page", None)
    if nav_override in PAGES:
        page = st.sidebar.radio(
            "Navigate",
            PAGES,
            index=PAGES.index(nav_override),
            label_visibility="collapsed",
            key="main_nav",
        )
    else:
        page = st.sidebar.radio(
            "Navigate",
            PAGES,
            label_visibility="collapsed",
            key="main_nav",
        )
    st.sidebar.divider()
    render_alerts_sidebar()

    st.sidebar.divider()
    with st.sidebar.expander("Quick actions"):
        if st.button("Sync journal", use_container_width=True, key="sidebar_sync"):
            try:
                r = api_post("/journal/sync")
                invalidate_cache()
                st.sidebar.success(
                    f"C{r.get('imported_clear', 0)} P{r.get('imported_profit', 0)}"
                )
            except Exception as e:
                st.sidebar.error(str(e)[:60])
        if st.button("Refresh connectors", use_container_width=True, key="sidebar_refresh"):
            with st.spinner("Probing..."):
                refresh_integrations()
            st.rerun()

    if not health.get("paper_trading_mode"):
        st.sidebar.caption("Live trading — Clear API connected")
    else:
        st.sidebar.caption("Add Clear keys in `.env` for live execution")

    st.sidebar.markdown("[**Open Blackboard (2.0)**](http://localhost:8000/board)")
    return page
