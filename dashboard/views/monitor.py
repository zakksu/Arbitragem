"""Live Monitor — strategy control with auto-refresh."""

from datetime import timedelta

import streamlit as st

from dashboard.api_cache import cached_get
from dashboard.components.theme import status_class
from dashboard.utils import api_get, api_post


def _strategy_card(s: dict) -> None:
    status = s["status"]
    css = status_class(status)
    with st.container(border=True):
        head_l, head_r = st.columns([3, 1])
        head_l.markdown(f"### {s['name']}")
        head_r.markdown(f'<span class="{css}">{status.upper()}</span>', unsafe_allow_html=True)

        if s.get("description"):
            st.caption(s["description"])

        m1, m2, m3 = st.columns(3)
        m1.metric("Loss limit", f"R$ {s['daily_loss_limit_brl']:.0f}")
        m2.metric("Max contratos", s["max_contracts"])
        m3.metric("Max posições", s["max_open_positions"])

        params = s.get("parameters") or {}
        if params:
            st.caption("Params: " + ", ".join(f"{k}={v}" for k, v in params.items()))

        b1, b2, b3 = st.columns(3)
        if b1.button("▶ Start", key=f"start_{s['id']}", type="primary", use_container_width=True):
            try:
                api_post(f"/strategies/{s['id']}/start")
                st.toast(f"Started {s['name']}")
                st.rerun()
            except Exception as exc:
                st.error(f"Cannot start: {exc}")
        if b2.button("⏸ Pause", key=f"pause_{s['id']}", use_container_width=True):
            try:
                api_post(f"/strategies/{s['id']}/pause")
                st.toast(f"Paused {s['name']}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if b3.button("📤 Export NTSL", key=f"exp_{s['id']}", use_container_width=True):
            out = api_post(f"/strategies/{s['id']}/export-profit")
            st.success(out.get("exported_path", "Exported"))


@st.fragment(run_every=timedelta(seconds=15))
def _live_refresh() -> None:
    _render_body()


def _render_body() -> None:
    try:
        strategies = cached_get("/strategies", ttl=15)
    except Exception as exc:
        st.error(f"API error: {exc}")
        return

    if not strategies:
        st.info("No strategies yet. Agent A seeds a sample on first API start.")
        return

    active = sum(1 for s in strategies if s["status"] == "active")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total strategies", len(strategies))
    c2.metric("Active", active)
    c3.metric("Stopped", len(strategies) - active)

    st.divider()

    try:
        risk = cached_get("/risk/summary", ttl=20)
        st.subheader("Risk snapshot")
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Day P&L", f"R$ {risk.get('day_pnl', 0):,.2f}")
        rc2.metric("Loss limit used", f"{risk.get('loss_limit_used_pct', 0):.0f}%")
        rc3.metric("Trades today", risk.get("trades_today", 0))
        status = risk.get("status", "ok")
        status_label = {"ok": "🟢 OK", "warning": "🟠 Warning", "blocked": "🔴 Blocked"}.get(
            status, status
        )
        rc4.metric("Risk status", status_label)
        if risk.get("kill_switch_active"):
            st.error(f"Kill switch ON — {risk.get('kill_switch_reason') or 'all confirms blocked'}")
        if not risk.get("can_confirm_ideas", True):
            st.warning("Idea confirms are blocked.")
        if status == "blocked":
            st.error("Daily loss limit reached — strategies should stay stopped.")
        elif status == "warning":
            st.warning("Approaching daily loss limit — reduce size or pause.")
    except Exception:
        st.caption("Risk summary unavailable.")

    st.divider()

    try:
        risk_ks = cached_get("/risk/summary", ttl=10)
        ks_col1, ks_col2 = st.columns([1, 3])
        if ks_col1.button(
            "KILL SWITCH",
            type="primary",
            use_container_width=True,
            disabled=bool(risk_ks.get("kill_switch_active")),
            help="Blocks all confirms and executes; pauses active strategies",
        ):
            try:
                out = api_post("/risk/kill-switch", json={"active": True, "reason": "monitor stop"})
                st.toast(
                    f"Kill switch ON — paused {out.get('paused_strategies', 0)} strategies"
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if risk_ks.get("kill_switch_active"):
            ks_col2.error(
                f"Kill switch active: {risk_ks.get('kill_switch_reason') or 'manual stop'}"
            )
    except Exception:
        pass

    st.divider()

    try:
        account = cached_get("/account/summary", ttl=20)
        positions = cached_get("/positions", ttl=20)
        st.subheader("Account & Positions")
        if account.get("mock"):
            st.caption("📄 Paper mode — positions from mock Clear client")
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Day P&L", f"R$ {account.get('day_pnl', 0):,.2f}")
        pc2.metric("Open positions", len(positions))
        pc3.metric("Mode", "Paper" if account.get("mock") else "Live")
        if positions:
            st.dataframe(positions, use_container_width=True, hide_index=True)
    except Exception:
        st.caption("Positions require API `/positions` endpoint.")

    st.subheader("Strategy Control")
    for s in strategies:
        _strategy_card(s)


def render() -> None:
    st.title("Live Monitor")
    st.caption("Start/stop strategies · risk limits · real-time status")

    st.link_button(
        "Open Structure Deck (blackboard)",
        "http://localhost:8000/board",
        use_container_width=False,
    )

    auto = st.toggle("Auto-refresh (15s)", value=True, key="monitor_auto_refresh")
    if auto:
        _live_refresh()
    else:
        _render_body()
