"""Client-side alert panel — uses cached sidebar context when available."""

from __future__ import annotations

import streamlit as st

from dashboard.api_cache import get_sidebar_context


def _banner(level: str, message: str) -> None:
    css = f"arb-alert-{level}"
    st.markdown(
        f'<div class="arb-alert-banner {css}">{message}</div>',
        unsafe_allow_html=True,
    )


def collect_alerts() -> list[tuple[str, str]]:
    return get_sidebar_context().get("alerts", [])


def render_alerts_sidebar() -> None:
    alerts = collect_alerts()
    if not alerts:
        st.sidebar.caption("No active alerts")
        return
    st.sidebar.subheader("Alerts")
    for level, msg in alerts[:8]:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "•")
        st.sidebar.markdown(f"{icon} {msg}")


def render_alerts_banner(max_show: int = 2) -> None:
    alerts = collect_alerts()
    critical = [a for a in alerts if a[0] == "critical"]
    warnings = [a for a in alerts if a[0] == "warning"]
    shown = 0
    for level, msg in critical + warnings:
        if shown >= max_show:
            break
        _banner(level, msg)
        shown += 1
