"""Backtest & Optimize — hybrid Profit + Python with charts."""

import streamlit as st

from dashboard.components.charts import backtest_compare_chart
from dashboard.api_cache import cached_get, invalidate_cache
from dashboard.utils import api_post, api_upload_csv


def _show_profit_metrics(m: dict) -> None:
    if m.get("error"):
        st.error(m.get("message", m["error"]))
        return
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Net P&L", f"R$ {m.get('net_pnl', 0):,.2f}")
    c2.metric("Trades", m.get("total_trades", 0))
    c3.metric("Win rate", f"{100 * m.get('win_rate', 0):.1f}%")
    c4.metric("Max DD", f"R$ {m.get('max_drawdown', 0):,.2f}")
    c5.metric("Profit Factor", f"{m.get('profit_factor', 0):.2f}")
    if m.get("format"):
        st.caption(f"Format: `{m['format']}` · Source: ProfitChart CSV")
    if m.get("parse_warnings"):
        with st.expander("Parse notes"):
            for w in m["parse_warnings"]:
                st.caption(w)
    if m.get("trades_preview"):
        with st.expander("Trade preview (first 20 rows)"):
            st.dataframe(m["trades_preview"], use_container_width=True)


def render() -> None:
    st.title("Backtest & Optimize")
    st.caption("ProfitChart Tick-a-Tick (primary) + Python grid/genetic (supplement)")

    try:
        strategies = cached_get("/strategies", ttl=30)
    except Exception as exc:
        st.error(str(exc))
        return

    if not strategies:
        st.warning("Create a strategy first.")
        return

    sid = st.selectbox("Strategy", strategies, format_func=lambda x: x["name"])["id"]

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", "BOVAX125")
    with col2:
        engine = st.selectbox("Engine", ["python", "profit", "compare"])

    st.subheader("ProfitChart CSV")
    st.caption(
        "Export from Profit: Backtest → Operações or Relatório → Exportar CSV. "
        "Use **Aplicar formatação dos dados** when exporting."
    )

    upload_col, path_col = st.columns([1, 1])
    with upload_col:
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="profit_csv_upload")
        if uploaded is not None:
            if st.button("Upload & Preview", use_container_width=True):
                with st.spinner("Parsing CSV..."):
                    try:
                        resp = api_upload_csv(
                            "/backtest/upload",
                            uploaded.name,
                            uploaded.getvalue(),
                        )
                        st.session_state["profit_csv_path"] = resp["path"]
                        st.session_state["profit_csv_preview"] = resp["preview"]
                        st.success("CSV parsed successfully.")
                    except Exception as exc:
                        st.error(str(exc))

    with path_col:
        csv_path = st.text_input(
            "Or enter file path",
            value=st.session_state.get("profit_csv_path", ""),
            placeholder="exports/profit/20250101_backtest.csv",
        )

    if "profit_csv_preview" in st.session_state:
        with st.expander("Uploaded CSV preview", expanded=True):
            _show_profit_metrics(st.session_state["profit_csv_preview"])

    if st.button("Run Backtest", type="primary"):
        with st.spinner("Running backtest..."):
            try:
                result = api_post(
                    "/backtest",
                    {
                        "strategy_id": sid,
                        "symbol": symbol,
                        "engine": engine,
                        "profit_csv_path": csv_path or None,
                    },
                )
                st.session_state["last_backtest"] = result
                invalidate_cache()
            except Exception as exc:
                st.error(str(exc))

    if "last_backtest" in st.session_state:
        result = st.session_state["last_backtest"]
        st.subheader("Results")
        if engine == "compare" and "profit" in result and "python" in result:
            _show_profit_metrics(result["profit"])
            st.plotly_chart(
                backtest_compare_chart(result["profit"], result["python"]),
                use_container_width=True,
            )
            st.info(result.get("recommendation", ""))
        elif "metrics" in result:
            _show_profit_metrics(result["metrics"])
        else:
            st.json(result)

    st.divider()
    st.subheader("Parameter Optimization (Python)")

    opt_method = st.radio("Method", ["grid", "genetic", "walk_forward"], horizontal=True)
    wf_folds = 3
    if opt_method == "walk_forward":
        wf_folds = st.slider("Walk-forward folds", 2, 6, 3)

    if st.button("Run Optimization"):
        with st.spinner("Optimizing — may take a minute..."):
            try:
                if opt_method == "genetic":
                    space = {"stop_ticks": [2.0, 10.0], "target_ticks": [4.0, 15.0]}
                else:
                    space = {"stop_ticks": [3, 5, 7], "target_ticks": [6, 8, 10]}
                result = api_post(
                    "/optimize",
                    {
                        "strategy_id": sid,
                        "symbol": symbol,
                        "method": opt_method,
                        "folds": wf_folds,
                        "parameter_space": space,
                    },
                )
                st.session_state["last_optimize"] = result
                invalidate_cache()
            except Exception as exc:
                st.error(str(exc))

    if "last_optimize" in st.session_state:
        opt = st.session_state["last_optimize"]
        st.success(f"Status: {opt.get('status')} · method: {opt.get('method', opt_method)}")
        if opt.get("best_parameters"):
            st.markdown("**Best parameters**")
            st.json(opt["best_parameters"])
        if opt.get("best_metrics"):
            st.markdown("**Best metrics**")
            st.json(opt["best_metrics"])
        run_id = opt.get("run_id")
        if run_id and opt.get("best_parameters"):
            if st.button("Apply best parameters to strategy", type="secondary"):
                try:
                    updated = api_post(f"/optimizations/{run_id}/apply")
                    invalidate_cache()
                    st.success(f"Applied to **{updated.get('name')}**")
                    st.json(updated.get("parameters"))
                except Exception as exc:
                    st.error(str(exc))
        folds = (opt.get("results") or {}).get("folds")
        if folds:
            import pandas as pd
            import plotly.express as px

            st.markdown("**Walk-forward folds**")
            fold_df = pd.DataFrame(folds)
            fig = px.bar(
                fold_df,
                x="fold",
                y=["train_pnl", "test_pnl"],
                barmode="group",
                title="Train vs test P&L per fold",
                labels={"value": "P&L", "fold": "Fold"},
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(fold_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Run history")
    try:
        backtests = cached_get(
            "/backtests", params={"limit": 10, "strategy_id": sid}, ttl=45
        )
        opts = cached_get(
            "/optimizations", params={"limit": 10, "strategy_id": sid}, ttl=45
        )
        h1, h2 = st.columns(2)
        with h1:
            st.caption("Recent backtests")
            if backtests:
                for b in backtests:
                    m = b.get("metrics") or {}
                    pnl = m.get("net_pnl", "—")
                    st.text(f"#{b['id']} {b['engine']} {b['symbol']} P&L={pnl}")
            else:
                st.caption("No backtests yet.")
        with h2:
            st.caption("Recent optimizations")
            if opts:
                for o in opts:
                    st.text(f"#{o['id']} {o['method']} {o['status']}")
            else:
                st.caption("No optimizations yet.")
    except Exception:
        st.caption("History requires API `/backtests` and `/optimizations`.")
