"""Daily Pattern Scanner — Streamlit page with Plotly charts."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.api_cache import cached_get, invalidate_cache
from dashboard.components.scalp_insights import render_scalp_insights
from dashboard.utils import api_post, scans_to_df

DEFAULT_SCAN_LIMIT = 80

ALERT_COLORS = {
    "info": "#3b82f6",
    "warning": "#f59e0b",
    "critical": "#ef4444",
}

TAG_LABELS = {
    "high_volume": "High Volume",
    "volume_spike": "Volume Spike",
    "price_spike": "Price Spike",
    "iv_skew": "IV Skew",
    "momentum_burst": "Momentum Burst",
    "scalp_long": "Scalp Long",
    "scalp_short": "Scalp Short",
    "spread_compression": "Tight Spread",
    "vwap_reclaim": "VWAP Reclaim",
}


def _format_tags(tags: list[str] | None) -> str:
    if not tags:
        return "—"
    return ", ".join(TAG_LABELS.get(t, t.replace("_", " ").title()) for t in tags)


def _alert_badge(level: str) -> str:
    icons = {"info": "🔵", "warning": "🟠", "critical": "🔴"}
    return f"{icons.get(level, '⚪')} {level.upper()}"


def _chart_height(base: int, rows: int, per_row: int = 48, cap: int = 720) -> int:
    """Responsive chart height — shorter on small symbol sets, capped for mobile scroll."""
    return min(cap, max(base, per_row * rows))


def _volume_bar_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df.sort_values("volume", ascending=True)
    colors = [ALERT_COLORS.get(lvl, "#94a3b8") for lvl in plot_df["alert_level"]]
    fig = go.Figure(
        go.Bar(
            x=plot_df["volume"],
            y=plot_df["symbol"],
            orientation="h",
            marker_color=colors,
            text=plot_df["volume"].map(lambda v: f"{v:,}"),
            textposition="outside",
            hovertemplate="%{y}<br>Volume: %{x:,}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Volume by Symbol (latest scan)",
        xaxis_title="Contracts traded",
        yaxis_title="",
        height=_chart_height(280, len(plot_df), 40),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig


def _spike_scatter(df: pd.DataFrame) -> go.Figure:
    plot_df = df.copy()
    plot_df["alert_label"] = plot_df["alert_level"].str.title()
    fig = px.scatter(
        plot_df,
        x="volume",
        y="spike_score",
        size="spike_score",
        color="alert_label",
        hover_name="symbol",
        color_discrete_map={
            "Info": ALERT_COLORS["info"],
            "Warning": ALERT_COLORS["warning"],
            "Critical": ALERT_COLORS["critical"],
        },
        labels={"volume": "Volume", "spike_score": "Spike Score"},
        title="Volume vs Spike Score",
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="white")))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def _pattern_heatmap(df: pd.DataFrame) -> go.Figure | None:
    all_tags = sorted({t for tags in df["pattern_tags"].dropna() for t in tags})
    if not all_tags:
        return None

    matrix = []
    for symbol in df["symbol"]:
        tags = set(df.loc[df["symbol"] == symbol, "pattern_tags"].iloc[0] or [])
        matrix.append([1 if tag in tags else 0 for tag in all_tags])

    labels = [TAG_LABELS.get(t, t.replace("_", " ").title()) for t in all_tags]
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=labels,
            y=df["symbol"].tolist(),
            colorscale=[[0, "#1e293b"], [1, "#22c55e"]],
            showscale=False,
            hovertemplate="%{y}<br>%{x}: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Detected Patterns",
        height=_chart_height(260, len(df), 36),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_tickangle=-25,
    )
    return fig


def _price_change_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df.sort_values("price_change_pct", ascending=True)
    colors = [
        "#22c55e" if v >= 0 else "#ef4444"
        for v in plot_df["price_change_pct"].fillna(0)
    ]
    fig = go.Figure(
        go.Bar(
            x=plot_df["price_change_pct"],
            y=plot_df["symbol"],
            orientation="h",
            marker_color=colors,
            text=plot_df["price_change_pct"].map(lambda v: f"{v:+.2f}%"),
            textposition="outside",
            hovertemplate="%{y}<br>Change: %{x:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Price Change %",
        xaxis_title="% change",
        height=_chart_height(260, len(plot_df), 40),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig


def _history_chart(history: pd.DataFrame) -> go.Figure | None:
    if history.empty or history["scan_date"].nunique() < 2:
        return None

    history = history.copy()
    history["scan_date"] = pd.to_datetime(history["scan_date"])
    fig = px.line(
        history,
        x="scan_date",
        y="spike_score",
        color="symbol",
        markers=True,
        labels={"scan_date": "Scan time", "spike_score": "Spike Score"},
        title="Spike Score History",
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def _summary_metrics(df: pd.DataFrame) -> None:
    warnings = (df["alert_level"] == "warning").sum()
    critical = (df["alert_level"] == "critical").sum()
    patterned = df["pattern_tags"].apply(lambda t: bool(t)).sum()
    avg_spike = df["spike_score"].mean() if not df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Symbols scanned", len(df))
    c2.metric("Patterns found", int(patterned))
    c3.metric("Warnings", int(warnings + critical))
    c4.metric("Avg spike score", f"{avg_spike:.1f}")


def _results_table(df: pd.DataFrame) -> None:
    display = df.copy()
    display["reliability"] = display["raw_data"].apply(
        lambda r: (r or {}).get("reliability", 0) if isinstance(r, dict) else 0
    )
    display["side"] = display["raw_data"].apply(
        lambda r: (r or {}).get("side_bias", "—") if isinstance(r, dict) else "—"
    )
    display = display.sort_values("reliability", ascending=False)
    display["patterns"] = display["pattern_tags"].apply(_format_tags)
    display["alert"] = display["alert_level"].apply(_alert_badge)
    display["volume"] = display["volume"].fillna(0).astype(int)
    display["spike_score"] = display["spike_score"].round(1)
    display["price_change_pct"] = display["price_change_pct"].map(
        lambda v: f"{v:+.2f}%" if pd.notna(v) else "—"
    )

    cols = [
        "symbol",
        "side",
        "reliability",
        "volume",
        "spike_score",
        "price_change_pct",
        "patterns",
        "alert",
    ]
    st.dataframe(
        display[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol": st.column_config.TextColumn("Symbol", width="small"),
            "side": "Bias",
            "reliability": st.column_config.ProgressColumn(
                "Reliability", min_value=0, max_value=100, format="%.0f"
            ),
            "volume": st.column_config.NumberColumn("Volume", format="%d"),
            "spike_score": st.column_config.ProgressColumn(
                "Spike Score", min_value=0, max_value=100, format="%.0f"
            ),
            "price_change_pct": "Price Δ",
            "patterns": st.column_config.TextColumn("Patterns", width="medium"),
            "alert": "Alert",
        },
    )


def _ai_insights(df: pd.DataFrame) -> None:
    with_ai = df[df["ai_summary"].notna() & (df["ai_summary"] != "")]
    if with_ai.empty:
        return

    st.subheader("Ollama Insights")
    for _, row in with_ai.iterrows():
        with st.expander(f"💡 {row['symbol']} — {_format_tags(row['pattern_tags'])}"):
            st.markdown(row["ai_summary"])


@st.fragment(run_every=timedelta(seconds=60))
def _render_live_scanner(
    view: str,
    symbol_filter: str,
    run_clicked: bool,
) -> None:
    _render_scanner_body(view, symbol_filter, run_clicked)


def _scalp_insights_panel() -> None:
    render_scalp_insights(limit=8, show_ollama_button=True)


def _universe_panel() -> None:
    try:
        data = cached_get("/universe/ibov-top20", ttl=60)
        symbols = data.get("symbols") or []
        if not symbols:
            return
        df = pd.DataFrame(symbols)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "avg_volume_30d": st.column_config.NumberColumn("Avg vol 30d", format="%d"),
            },
        )
    except Exception as exc:
        st.caption(f"Universe: {exc}")


def _render_scanner_body(view: str, symbol_filter: str, run_clicked: bool) -> None:
    if run_clicked:
        with st.spinner("Scanning symbols via Profit bridge..."):
            try:
                results = api_post("/scanner/run")
                invalidate_cache()
                st.success(f"Scan complete — {len(results)} symbol(s) analyzed.")
            except Exception as exc:
                st.error(f"Scan failed: {exc}")

    params: dict = {"limit": DEFAULT_SCAN_LIMIT}
    if symbol_filter.strip():
        params["symbol"] = symbol_filter.strip().upper()
    if view == "Latest scan":
        params["latest_batch"] = True

    metrics_slot = st.empty()
    charts_slot = st.empty()
    table_slot = st.empty()

    try:
        with st.spinner("Loading scan results..."):
            scans = cached_get("/scanner/results", params=params, ttl=30)
    except Exception as exc:
        st.error(f"Could not load scan results: {exc}")
        st.info("Make sure the API is running (`uvicorn src.main:app`) and run a scan first.")
        return

    if not scans:
        st.info("No scan results yet. Click **Run Scan Now** to scan IBOV Top 20 + BOVA watchlist.")
        return

    df = scans_to_df(scans)
    df["scan_date"] = pd.to_datetime(df["scan_date"])
    latest_time = df["scan_date"].max()

    with metrics_slot.container():
        st.caption(f"Last scan: {latest_time.strftime('%Y-%m-%d %H:%M UTC')}")
        _summary_metrics(df)

    with charts_slot.container():
        if view == "Latest scan":
            with st.spinner("Rendering charts..."):
                left, right = st.columns(2)
                with left:
                    st.plotly_chart(_volume_bar_chart(df), use_container_width=True)
                with right:
                    st.plotly_chart(_spike_scatter(df), use_container_width=True)

                heatmap = _pattern_heatmap(df)
                if heatmap:
                    st.plotly_chart(heatmap, use_container_width=True)
                else:
                    st.info("No pattern tags detected in the latest scan.")

                st.plotly_chart(_price_change_chart(df), use_container_width=True)
        else:
            with st.spinner("Loading scan history..."):
                history = scans_to_df(
                    cached_get(
                        "/scanner/results",
                        params={"limit": DEFAULT_SCAN_LIMIT},
                        ttl=30,
                    )
                )
            history["scan_date"] = pd.to_datetime(history["scan_date"])
            hist_fig = _history_chart(history)
            if hist_fig:
                st.plotly_chart(hist_fig, use_container_width=True)
            else:
                st.info("Run more scans over time to see spike score trends.")

            symbol_pick = st.selectbox(
                "Compare symbol over time",
                sorted(history["symbol"].unique()),
            )
            sym_df = history[history["symbol"] == symbol_pick].sort_values("scan_date")
            if len(sym_df) > 1:
                fig = px.area(
                    sym_df,
                    x="scan_date",
                    y="volume",
                    title=f"{symbol_pick} — Volume over scans",
                    labels={"scan_date": "Scan time", "volume": "Volume"},
                )
                fig.update_layout(height=320)
                st.plotly_chart(fig, use_container_width=True)

    with table_slot.container():
        st.subheader("Top Scalp Candidates")
        with st.spinner("Loading scalp insights..."):
            _scalp_insights_panel()

        st.subheader("Scan Results")
        _results_table(df)
        _ai_insights(df)


def render_scanner_page() -> None:
    st.title("Daily Pattern Scanner")
    st.caption("IBOV Top 20 · volume spikes · scalp patterns · Ollama NTSL hints")

    uni_tab, scan_tab = st.tabs(["IBOV Universe", "Scanner"])
    with uni_tab:
        st.subheader("IBOV Top 20 (30d volume)")
        _universe_panel()

    with scan_tab:
        _render_scanner_tabs()


def _render_scanner_tabs() -> None:
    toolbar = st.columns([2, 1, 1])
    with toolbar[0]:
        view = st.radio(
            "View",
            ["Latest scan", "All history"],
            horizontal=True,
            label_visibility="collapsed",
        )
    with toolbar[1]:
        symbol_filter = st.text_input("Filter symbol", placeholder="e.g. BOVA11")
    with toolbar[2]:
        auto_refresh = st.toggle("Auto-refresh (60s)", value=False, key="scanner_auto_refresh")

    action_cols = st.columns([1, 3])
    with action_cols[0]:
        run_clicked = st.button("Run Scan Now", type="primary", use_container_width=True)
    with action_cols[1]:
        st.caption("Scheduled scan runs daily via API scheduler (SCANNER_CRON_* in `.env`)")

    if auto_refresh:
        _render_live_scanner(view, symbol_filter, run_clicked)
    else:
        _render_scanner_body(view, symbol_filter, run_clicked)
