"""Optional Streamlit login gate for VPS deployment."""

from __future__ import annotations

import os

import streamlit as st


def _auth_enabled() -> bool:
    return os.getenv("DASHBOARD_AUTH_ENABLED", "false").lower() in ("1", "true", "yes")


def require_login() -> bool:
    """Return True if user may access the dashboard."""
    if not _auth_enabled():
        return True

    if st.session_state.get("authenticated"):
        return True

    st.title("Arbitragem Dashboard")
    st.caption("Sign in to continue")

    with st.form("login"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary")

    if submitted:
        expected_user = os.getenv("DASHBOARD_USERNAME", "filipe")
        expected_pass = os.getenv("DASHBOARD_PASSWORD", "")
        if not expected_pass:
            st.error("Set DASHBOARD_PASSWORD in `.env` before enabling auth.")
        elif user == expected_user and password == expected_pass:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials.")

    st.stop()
    return False
