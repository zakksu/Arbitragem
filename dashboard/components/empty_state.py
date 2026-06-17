"""Reusable empty-state blocks for Streamlit views (4.0 GA W4.18)."""

from __future__ import annotations

import streamlit as st


def render_empty_state(
    title: str,
    body: str,
    *,
    actions: list[tuple[str, str]] | None = None,
    link_url: str | None = None,
    link_label: str | None = None,
) -> None:
    """Centered empty state with optional nav buttons (page name → sidebar radio)."""
    st.markdown(
        f"""
        <div style="
            text-align:center; padding:2rem 1rem; margin:1rem 0;
            border:1px dashed #334155; border-radius:12px;
            background:rgba(15,23,42,0.5);
        ">
            <div style="font-size:2rem; opacity:0.4; margin-bottom:0.5rem;">◇</div>
            <h3 style="margin:0 0 0.5rem; color:#e2e8f0; font-size:1.1rem;">{title}</h3>
            <p style="margin:0; color:#94a3b8; font-size:0.9rem; max-width:28rem; margin-inline:auto;">
                {body}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if actions:
        cols = st.columns(len(actions))
        for col, (label, page) in zip(cols, actions, strict=False):
            with col:
                if st.button(label, use_container_width=True, key=f"empty_nav_{page}"):
                    st.session_state.nav_page = page
                    st.rerun()
    if link_url and link_label:
        st.link_button(link_label, link_url, use_container_width=False)
