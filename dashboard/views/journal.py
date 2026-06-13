"""Trade Journal — auto-sync + Ollama analysis."""

import pandas as pd
import streamlit as st

from dashboard.api_cache import cached_get, invalidate_cache
from dashboard.utils import api_post


def render() -> None:
    st.title("Trade Journal")
    st.caption("Auto-import from **Clear + Profit** · AI analysis via Ollama")

    action = st.columns([1, 2])
    with action[0]:
        if st.button("🔄 Sync + Analyze", type="primary", use_container_width=True):
            with st.spinner("Syncing trades and running Ollama analysis..."):
                try:
                    result = api_post("/journal/sync")
                    invalidate_cache()
                    st.success(
                        f"Clear **{result.get('imported_clear', 0)}** · "
                        f"Profit **{result.get('imported_profit', 0)}** · "
                        f"Analyzed **{result.get('analyzed', 0)}**"
                    )
                except Exception as exc:
                    st.error(str(exc))

    with action[1]:
        filter_side = st.selectbox("Filter", ["All", "buy", "sell"], label_visibility="collapsed")

    try:
        trades = cached_get("/trades", params={"limit": 100}, ttl=45)
    except Exception as exc:
        st.error(f"Could not load journal: {exc}")
        return

    if filter_side != "All":
        trades = [t for t in trades if t.get("side") == filter_side]

    if not trades:
        st.info("Journal empty. Click **Sync + Analyze** above.")
        return

    df = pd.DataFrame(trades)
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "journal_trades.csv",
        "text/csv",
        use_container_width=True,
    )

    for t in trades:
        pnl = t.get("pnl")
        pnl_str = f" · P&L R$ {pnl:,.2f}" if pnl is not None else ""
        side_icon = "🟢" if t.get("side") == "buy" else "🔴"
        title = f"{side_icon} {t['symbol']} {t['side'].upper()} {t['quantity']} @ R$ {t['price']:.4f}{pnl_str}"

        with st.expander(title, expanded=bool(t.get("ai_analysis"))):
            meta = st.columns(4)
            meta[0].caption(f"ID: {t.get('id')}")
            meta[1].caption(f"Time: {t.get('executed_at', '')[:19]}")
            meta[2].caption(f"Source: {t.get('source', 'clear')}")
            meta[3].caption(f"Fees: R$ {t.get('fees', 0):.2f}")

            if t.get("ai_analysis"):
                st.markdown("#### AI Analysis")
                st.markdown(t["ai_analysis"])
            else:
                st.caption("No AI analysis — run Sync + Analyze (requires Ollama).")
