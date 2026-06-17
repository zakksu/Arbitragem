"""Arbitragem Dashboard — Streamlit entry point."""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.auth import require_login
from dashboard.components.sidebar import render_sidebar
from dashboard.components.theme import apply_theme
from dashboard.views import backtest, home, journal, monitor, ollama, performance, settings, strategies
from dashboard.scanner_ui import render_scanner_page
from src.config import get_settings

SLIM_PAGES = ("Home", "Performance", "Journal", "Settings")

st.set_page_config(
    page_title="Arbitragem Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
require_login()
page = render_sidebar()

ROUTES = {
    "Home": home.render,
    "Live Monitor": monitor.render,
    "Performance": performance.render,
    "Daily Scanner": render_scanner_page,
    "Strategies": strategies.render,
    "Backtest & Optimize": backtest.render,
    "Journal": journal.render,
    "Ollama Insights": ollama.render,
    "Settings": settings.render,
}

if get_settings().streamlit_slim_enabled:
    ROUTES = {k: v for k, v in ROUTES.items() if k in SLIM_PAGES}

ROUTES.get(page, home.render)()
