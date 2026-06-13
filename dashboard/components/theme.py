"""Inject global Streamlit theme — ProfitChart-inspired dark terminal."""

import streamlit as st

THEME_CSS = """
<style>
    /* ProfitChart-like: near-black bg, amber accents, green/red P&L */
    :root {
        --arb-bg: #0c0c0c;
        --arb-panel: #161616;
        --arb-border: #2a2a2a;
        --arb-accent: #f59e0b;
        --arb-text: #e8e8e8;
        --arb-muted: #8a8a8a;
        --arb-green: #00c853;
        --arb-red: #ff5252;
    }

    .stApp {
        background-color: var(--arb-bg);
    }

    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .main .block-container {
        padding-top: 1rem;
        max-width: 1480px;
    }

    h1, h2, h3 {
        font-weight: 600 !important;
        color: var(--arb-text) !important;
        letter-spacing: -0.01em;
    }

    .arb-logo {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--arb-accent);
        padding: 0.25rem 0;
    }
    .arb-logo span { color: var(--arb-text); }

    .arb-metric-card {
        background: var(--arb-panel);
        border: 1px solid var(--arb-border);
        border-top: 2px solid var(--arb-accent);
        border-radius: 4px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }

    .arb-metric-label {
        color: var(--arb-muted);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .arb-metric-value {
        color: var(--arb-text);
        font-size: 1.35rem;
        font-weight: 600;
        font-family: 'Consolas', 'Courier New', monospace;
    }

    .arb-status-active { color: var(--arb-green); font-weight: 600; }
    .arb-status-stopped { color: var(--arb-red); font-weight: 600; }
    .arb-status-paused { color: var(--arb-accent); font-weight: 600; }

    .arb-alert-banner {
        border-radius: 4px;
        padding: 0.6rem 0.9rem;
        margin: 0.4rem 0;
        border-left: 3px solid;
        font-size: 0.9rem;
    }
    .arb-alert-warning { background: #2a1f0a; border-color: var(--arb-accent); color: #fcd34d; }
    .arb-alert-critical { background: #2a0f0f; border-color: var(--arb-red); color: #fca5a5; }
    .arb-alert-info { background: #0f1a2a; border-color: #3b82f6; color: #93c5fd; }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #080808 0%, #121212 100%);
        border-right: 1px solid var(--arb-border);
    }

    div[data-testid="stSidebar"] .stRadio label {
        font-size: 0.9rem;
    }

    .stButton > button {
        border-radius: 4px;
        font-weight: 600;
        border: 1px solid var(--arb-border);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #d97706 0%, #b45309 100%);
        color: #0c0c0c;
        border: 1px solid #92400e;
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
    }

    .arb-side-long { color: var(--arb-green); font-weight: 600; }
    .arb-side-short { color: var(--arb-red); font-weight: 600; }
    .arb-side-neutral { color: var(--arb-muted); font-weight: 600; }

    /* Dataframes — tighter like a watchlist */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--arb-border);
        border-radius: 4px;
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        .arb-metric-value { font-size: 1.1rem; }
        .main div[data-testid="stDataFrame"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            max-width: 100%;
        }
        .main div[data-testid="stDataFrame"] > div {
            min-width: 32rem;
        }
        div[data-testid="stPlotlyChart"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
    }
</style>
"""


def apply_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str | None = None) -> None:
    delta_html = f'<div style="color:var(--arb-green);font-size:0.8rem;">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="arb-metric-card">
            <div class="arb-metric-label">{label}</div>
            <div class="arb-metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_class(status: str) -> str:
    return {
        "active": "arb-status-active",
        "stopped": "arb-status-stopped",
        "paused": "arb-status-paused",
        "draft": "arb-status-paused",
    }.get(status.lower(), "")
