"""Settings — alerts, integrations, system log."""

import streamlit as st

from dashboard.api_cache import cached_get, get_health
from dashboard.utils import api_get, api_post


def render() -> None:
    st.title("Settings & Integrations")
    st.caption("Connection status · alerts · Profit bridge · system log")

    try:
        health = get_health(ttl=45)
    except Exception as exc:
        st.error(f"API offline: {exc}")
        return

    if not health:
        st.error("API offline — run `python scripts/dev.py start`")
        return

    if health.get("paper_trading_mode"):
        st.info("**Paper trading mode** — Clear API uses mock data until credentials are set.")

    st.subheader("System status")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("API", health.get("status", "?").upper())
    c2.metric("Ollama", "On" if health.get("ollama") else "Off")
    c3.metric("Profit", "On" if health.get("profit_bridge") else "Off")
    c4.metric("Clear", "Live" if health.get("clear_api") else "Mock")
    c5.metric("Scanner", f"{health.get('scanner_symbol_count', 0)} sym")

    st.caption(f"Scanner mode: `{health.get('scanner_mode', 'custom')}` · set `SCANNER_MODE=ibov_top20` in `.env`")

    st.divider()
    st.subheader("Clear API setup")
    with st.expander("How to connect Clear Smart Trader"):
        st.markdown(
            """
            Add to `.env` and restart (`python scripts/dev.py restart --wait`):
            ```
            CLEAR_API_KEY=your-key
            CLEAR_API_SECRET=your-secret
            CLEAR_ACCOUNT_ID=your-account
            PAPER_TRADING_MODE=false
            ```
            Until then the dashboard uses **mock** account data (safe for learning).
            """
        )

    if st.button("Test Clear connection"):
        try:
            result = api_get("/integrations/clear/test")
            if result.get("configured"):
                st.success("Clear API credentials configured.")
            else:
                st.info("Clear in mock mode — paper trading.")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Profit bridge setup")
    with st.expander("How to connect ProfitChart (Windows)"):
        st.markdown(
            """
            1. Open **ProfitChart / ProfitPro** on your trading PC.
            2. Start the bridge (auto-started by `dev.py` when enabled):
               ```powershell
               python scripts/profit_bridge_stub.py
               ```
               Or for DLL path (when ready):
               ```powershell
               set PROFIT_DLL_PATH=C:\\Nelogica\\Profit\\ProfitDLL.dll
               python scripts/profit_dll_bridge.py
               ```
            3. In `.env`:
               ```
               PROFIT_BRIDGE_ENABLED=true
               PROFIT_BRIDGE_AUTO_DETECT=true
               PROFIT_BRIDGE_URL=http://localhost:9100
               ```
            4. Click **Test Profit connection** below — expect sample PETR4/GGBR4 quotes.
            """
        )

    if st.button("Test Profit connection"):
        try:
            result = api_get("/integrations/profit/test")
            if result.get("available"):
                st.success("Profit bridge is reachable.")
            else:
                st.warning("Bridge not reachable — using mock quotes.")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Alerts (Telegram / Discord)")

    try:
        alerts = cached_get("/alerts/status", ttl=45)
        a1, a2, a3 = st.columns(3)
        a1.metric("Enabled", "Yes" if alerts.get("enabled") else "No")
        a2.metric("Configured", "Yes" if alerts.get("configured") else "No")
        a3.metric("Channels", f"TG:{'✓' if alerts.get('telegram') else '—'} DC:{'✓' if alerts.get('discord') else '—'}")

        if not alerts.get("configured"):
            st.markdown(
                """
                Add to `.env` and restart API:
                ```
                ALERTS_ENABLED=true
                TELEGRAM_BOT_TOKEN=...
                TELEGRAM_CHAT_ID=...
                ```
                """
            )

        if st.button("Send test alert", type="primary"):
            try:
                api_post("/alerts/test")
                st.success("Test alert sent.")
            except Exception as exc:
                st.error(str(exc))
    except Exception as exc:
        st.warning(f"Alerts: {exc}")

    st.divider()
    st.subheader("Recent system events")
    try:
        events = cached_get("/system/events", params={"limit": 15}, ttl=30)
        if not events:
            st.caption("No events logged yet.")
        for ev in events:
            icon = {"error": "🔴", "warning": "🟠", "info": "🔵"}.get(ev.get("level"), "•")
            st.text(f"{icon} [{ev.get('component')}] {ev.get('message', '')[:120]}")
    except Exception as exc:
        st.caption(f"Events API: {exc}")

    st.divider()
    st.subheader("Dashboard auth (VPS)")
    st.markdown(
        """
        ```
        DASHBOARD_AUTH_ENABLED=true
        DASHBOARD_USERNAME=filipe
        DASHBOARD_PASSWORD=your-strong-password
        ```
        """
    )
