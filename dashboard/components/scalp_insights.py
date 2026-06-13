"""Scalp insights panel — top IBOV picks with reliability and Ollama."""

from __future__ import annotations

import streamlit as st

from dashboard.api_cache import cached_get
from dashboard.utils import api_post


def _side_chip(side: str) -> str:
    return {"long": "🟢 LONG", "short": "🔴 SHORT", "neutral": "⚪ NEUTRAL"}.get(side, side)


def render_scalp_insights(limit: int = 5, show_ollama_button: bool = True) -> None:
    try:
        data = cached_get("/scanner/insights", params={"limit": limit}, ttl=30)
    except Exception as exc:
        st.caption(f"Insights unavailable: {exc}")
        return

    insights = data.get("insights") or []
    if not insights:
        st.info("No scalp insights yet — run **Daily Scanner** → **Run Scan Now**.")
        return

    st.caption(f"Mode: `{data.get('scanner_mode', 'ibov_top20')}` · Top {len(insights)} by reliability")

    for i, item in enumerate(insights, 1):
        rel = item.get("reliability", 0)
        with st.container(border=True):
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.markdown(f"**#{i} {item['symbol']}** · {_side_chip(item.get('side_bias', 'neutral'))}")
            h2.metric("Reliability", f"{rel:.0f}%")
            h3.metric("Spike", f"{item.get('spike_score', 0):.0f}")

            tags = ", ".join(item.get("pattern_tags") or []) or "—"
            st.caption(
                f"Patterns: {tags} · Vol {item.get('volume', 0):,} · "
                f"Stop {item.get('stop_ticks')} / Target {item.get('target_ticks')} ticks"
            )

            if item.get("ai_summary"):
                with st.expander("Ollama insight"):
                    st.markdown(item["ai_summary"])

            if show_ollama_button:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Ask Ollama", key=f"ollama_insight_{item['symbol']}_{i}"):
                        with st.spinner("Analyzing..."):
                            try:
                                reply = api_post(
                                    "/ollama/chat",
                                    {
                                        "message": (
                                            f"Give a 30-second scalp plan for {item['symbol']} "
                                            f"bias {item.get('side_bias')}. Entry, stop, target, size."
                                        ),
                                        "context": str(item),
                                    },
                                )
                                st.markdown(reply.get("reply", ""))
                            except Exception as exc:
                                st.error(str(exc))
                with b2:
                    if st.button("Open in Ollama", key=f"ollama_open_{item['symbol']}_{i}"):
                        st.session_state["ollama_prefill_message"] = (
                            f"30-second scalp plan for {item['symbol']} "
                            f"({item.get('side_bias', 'neutral')} bias)"
                        )
                        st.session_state["ollama_prefill_context"] = str(item)
                        st.session_state["nav_page"] = "Ollama Insights"
                        st.rerun()
