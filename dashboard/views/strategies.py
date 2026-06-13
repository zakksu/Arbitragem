"""Strategy Control — NTSL editor, risk limits, Profit export."""

import streamlit as st

from dashboard.api_cache import cached_get, invalidate_cache
from dashboard.utils import api_patch, api_post


def render() -> None:
    st.title("Strategy Control")
    st.caption("Manage NTSL strategies · risk limits · one-click ProfitChart export")

    try:
        strategies = cached_get("/strategies", ttl=30)
    except Exception as exc:
        st.error(f"API error: {exc}")
        return

    if not strategies:
        st.warning("No strategies found.")
        return

    names = {s["name"]: s for s in strategies}
    selected_name = st.selectbox("Select strategy", list(names.keys()))
    s = names[selected_name]

    tab_view, tab_edit, tab_create = st.tabs(["Overview", "Edit Risk / Params", "New Strategy"])

    with tab_view:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"**Status:** `{s['status']}`")
            st.markdown(s.get("description") or "_No description_")
            if s.get("ntsl_code"):
                st.code(s["ntsl_code"], language="cpp")
        with c2:
            st.json(s.get("parameters") or {})
            if st.button("📤 Export to ProfitChart", type="primary", use_container_width=True):
                out = api_post(f"/strategies/{s['id']}/export-profit")
                st.success(f"Saved: `{out.get('exported_path')}`")
                st.caption("ProfitChart → Editor de Estratégias → Importar")

    with tab_edit:
        st.subheader("NTSL & description")
        with st.form("strategy_edit"):
            desc = st.text_area("Description", value=s.get("description") or "", height=80)
            ntsl = st.text_area("NTSL code", value=s.get("ntsl_code") or "", height=220)
            if st.form_submit_button("Save NTSL / description"):
                try:
                    api_patch(
                        f"/strategies/{s['id']}",
                        {"description": desc, "ntsl_code": ntsl},
                    )
                    invalidate_cache()
                    st.success("Strategy updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.subheader("Risk limits")
        with st.form("risk_form"):
            loss_limit = st.number_input(
                "Daily loss limit (R$)",
                value=float(s["daily_loss_limit_brl"]),
                min_value=50.0,
                step=50.0,
            )
            max_contracts = st.number_input(
                "Max contracts",
                value=int(s["max_contracts"]),
                min_value=1,
                max_value=100,
            )
            max_positions = st.number_input(
                "Max open positions",
                value=int(s["max_open_positions"]),
                min_value=1,
                max_value=20,
            )
            stop_ticks = st.number_input(
                "Stop ticks (param)",
                value=float((s.get("parameters") or {}).get("stop_ticks", 5)),
            )
            target_ticks = st.number_input(
                "Target ticks (param)",
                value=float((s.get("parameters") or {}).get("target_ticks", 8)),
            )
            if st.form_submit_button("Save", type="primary"):
                try:
                    api_post(
                        f"/strategies/{s['id']}/risk",
                        {
                            "daily_loss_limit_brl": loss_limit,
                            "max_contracts": max_contracts,
                            "max_open_positions": max_positions,
                            "parameters": {
                                **(s.get("parameters") or {}),
                                "stop_ticks": stop_ticks,
                                "target_ticks": target_ticks,
                            },
                        },
                    )
                    invalidate_cache()
                    st.success("Risk limits updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with tab_create:
        with st.form("create_strategy"):
            name = st.text_input("Name", "BOVA Scalp v2")
            desc = st.text_area("Description", "Intraday BOVA options scalp")
            ntsl = st.text_area("NTSL code", height=200, placeholder="// Paste NTSL here...")
            if st.form_submit_button("Create strategy"):
                try:
                    api_post(
                        "/strategies",
                        {
                            "name": name,
                            "description": desc,
                            "ntsl_code": ntsl or None,
                            "parameters": {"stop_ticks": 5, "target_ticks": 8},
                        },
                    )
                    invalidate_cache()
                    st.success(f"Created **{name}**")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
