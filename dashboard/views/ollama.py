"""Ollama Insights — chat with presets for IBOV scalping."""

import json

import streamlit as st

from dashboard.api_cache import cached_get, get_health
from dashboard.utils import api_post

PRESETS = {
    "Top scalp pick today": "Based on today's scanner, which IBOV symbol has the best risk/reward for a 2-minute scalp right now?",
    "Scalp plan (30 sec)": "Give entry trigger, stop ticks, target ticks, and max size for a quick scalp. No overnight.",
    "Optimize NTSL": "Review and optimize the NTSL code in context. Return improved code with comments.",
    "Post-market review": "Analyze my trading day: what went well, what to improve tomorrow, and one risk rule to add.",
    "Risk check": "Given my active strategies and today's P&L, am I within safe risk limits for intraday scalping?",
}


def render() -> None:
    st.title("Ollama Insights")
    st.caption("IBOV Top 20 scalping · seconds to minutes · tight stops")

    try:
        health = get_health(ttl=45)
        if not health.get("ollama"):
            st.warning("Ollama offline — run `ollama serve` and `ollama pull llama3.2`.")
    except Exception:
        pass

    if "ollama_history" not in st.session_state:
        st.session_state.ollama_history = []

    # Prefill from scanner "Ask Ollama" or other pages
    default_context = st.session_state.pop("ollama_prefill_context", "")
    default_message = st.session_state.pop("ollama_prefill_message", "")

    st.subheader("Quick prompts")
    cols = st.columns(2)
    preset_msg = default_message
    for i, (label, prompt) in enumerate(PRESETS.items()):
        if cols[i % 2].button(label, use_container_width=True, key=f"preset_{i}"):
            preset_msg = prompt

    if st.button("Load top scalp pick from scanner"):
        try:
            data = cached_get("/scanner/insights", params={"limit": 1}, ttl=30)
            picks = data.get("insights") or []
            if picks:
                pick = picks[0]
                preset_msg = (
                    f"30-second scalp plan for {pick['symbol']} "
                    f"({pick.get('side_bias', 'neutral')} bias, reliability {pick.get('reliability', 0):.0f}%)"
                )
                default_context = json.dumps(pick, indent=2, default=str)
                st.session_state["_ollama_ctx"] = default_context
        except Exception as exc:
            st.error(str(exc))

    context = st.text_area(
        "Context (scan JSON, NTSL, journal)",
        value=st.session_state.pop("_ollama_ctx", default_context),
        height=120,
    )

    user_msg = st.text_area("Your question", value=preset_msg or "", height=80)

    if st.button("Send to Ollama", type="primary"):
        if not user_msg.strip():
            st.warning("Enter a question.")
        else:
            with st.spinner("Thinking..."):
                try:
                    reply = api_post(
                        "/ollama/chat",
                        {"message": user_msg, "context": context or None},
                    )
                    st.session_state.ollama_history.insert(
                        0,
                        {"q": user_msg, "a": reply.get("reply", "")},
                    )
                except Exception as exc:
                    st.error(str(exc))

    for item in st.session_state.ollama_history[:10]:
        with st.chat_message("user"):
            st.markdown(item["q"][:500])
        with st.chat_message("assistant"):
            st.markdown(item["a"])
