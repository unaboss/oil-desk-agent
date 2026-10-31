import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from analysis.fibonacci import (
    find_swing, find_nearest_level, is_price_in_zone,
    FIB_LABELS, FIB_RATIOS,
)


def render_fibonacci_tab(market_data):
    st.subheader("Fibonacci Retracement")

    wti = market_data.get("wti")
    if not wti or not wti.get("dates"):
        st.warning("No WTI price data available.")
        return

    dates = [pd.to_datetime(d) for d in wti["dates"]]
    close = wti["close"]

    lookback = st.slider("Lookback (trading days)", 20, 200, 50, key="fib_lookback")

    swing = find_swing(close, lookback=lookback)
    if not swing:
        st.warning("Not enough data to compute Fibonacci levels.")
        return

    current_price = close[-1]
    nearest_label, nearest_price, nearest_dist = find_nearest_level(current_price, swing["levels"])
    zone = is_price_in_zone(current_price, swing["swing_high"], swing["swing_low"], swing["trend"])

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=close, mode="lines", name="WTI",
        line=dict(color="#FF9800", width=2),
    ))

    major_labels = {"38.2%", "50%", "61.8%"}
    for label, price in swing["levels"].items():
        if label in major_labels:
            color = "#00E5FF" if label == "38.2%" else "#FFEA00" if label == "50%" else "#FF9100"
            width = 2
        elif label in ("0%", "100%"):
            color = "#FFFFFF"
            width = 1
        else:
            color = "#666666"
            width = 1
        fig.add_hline(
            y=price, line_dash="dash", line_color=color,
            opacity=0.6, line_width=width,
            annotation_text=f" {label} ${price:.1f}" if label in major_labels else None,
            annotation_position="right",
        )

    fig.add_hline(
        y=current_price, line_color="white", line_width=1,
        annotation_text=f"  CURRENT ${current_price:.1f}",
        annotation_position="left",
    )

    fig.add_scatter(
        x=[pd.to_datetime(wti["dates"][close.index(swing["swing_high"])])],
        y=[swing["swing_high"]], mode="markers",
        marker=dict(color="#4CAF50", size=10, symbol="triangle-down"),
        name="Swing High",
    )
    fig.add_scatter(
        x=[pd.to_datetime(wti["dates"][close.index(swing["swing_low"])])],
        y=[swing["swing_low"]], mode="markers",
        marker=dict(color="#F44336", size=10, symbol="triangle-up"),
        name="Swing Low",
    )

    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(orientation="h", y=1.08),
        hovermode="x unified",
        template="plotly_dark",
        dragmode="pan",
    )
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.03))

    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True, "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })

    # ── Metrics ────────────────────────────────────────────────────────────────
    trend_icon = "↗️" if swing["trend"] == "uptrend" else "↘️"
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Trend", f"{trend_icon} {swing['trend'].title()}")
    col2.metric("Current", f"${current_price:.2f}")
    col3.metric("Nearest Fib", f"${nearest_price:.2f} ({nearest_label})")
    col4.metric("Distance", f"${nearest_dist:.2f}")
    col5.metric("Swing Range", f"${swing['range']:.2f}")

    st.caption(f"Current price is {zone}. Swing high: ${swing['swing_high']:.2f} | Swing low: ${swing['swing_low']:.2f}")

    # ── Level grid ─────────────────────────────────────────────────────────────
    st.markdown("### Fibonacci Levels")
    cols = st.columns(7)
    for i, label in enumerate(FIB_LABELS):
        price = swing["levels"][label]
        is_nearest = label == nearest_label
        with cols[i]:
            mark = "←" if is_nearest else ""
            st.metric(label, f"${price:.1f}", mark)

    # ── How to Read ────────────────────────────────────────────────────────────
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown(f"""
        **What is Fibonacci retracement?**

        It's based on a mathematical pattern from the Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144…
        The key ratio is **61.8%** (the "golden ratio"), derived by dividing one number by the next (e.g. 55÷89=0.618).
        Other important ratios are **38.2%** (0.382 = 1-0.618) and **23.6%** (derived from square roots).

        **The logic beyond the numbers:**

        Markets don't move in straight lines. After a big up-move, traders who bought late start to take profits, causing the price to fall back — a "retracement." The question is: *how far will it fall before buyers step in again?*

        Fibonacci levels mark the most common stopping points — not because of magic, but because **hundreds of thousands of traders are watching the same levels and placing orders there.** It becomes a self-fulfilling prophecy:
        - A trader who missed the buy at $60 might place a limit order at the 61.8% retracement ($60.80)
        - Another trader who bought at $65 might set their stop-loss just below the 61.8% level
        - An algorithm might add to its position when price touches the 61.8% level with high volume

        Three or four different traders, all acting at the same price, for different reasons — that concentration of orders creates a support or resistance zone.

        **How to use this with the dashboard:**

        1. **In an uptrend (Swing High more recent than Swing Low):** The retracement levels are potential BUY zones. If price pulls back to 61.8% or 38.2%, watch for a bounce. If the Confluence Score (Tab 6) is ALSO bullish at that moment, you have two independent confirmations.

        2. **In a downtrend (Swing Low more recent than Swing High):** The retracement levels are potential SELL zones. A rally to 61.8% or 38.2% with a bearish confluence score = short opportunity.

        3. **The 50% level** is not a Fibonacci number, but it's psychologically the most watched level in any market. It often acts as the strongest support/resistance.

        4. **The "zone"** between 38.2% and 61.8% is the key area. Price entering this zone on declining volume = the trend is healthy and the retracement is just noise. Price crashing through 61.8% on high volume = the trend may be reversing.

        **Important caveat:** Fibonacci levels are probabilities, not guarantees. They work best when CONFIRMED by other signals — volume (Price tab), positioning (COT tab), or the confluence score. A fib level alone is a suggestion; a fib level + a bullish confluence score + COT extreme short is a high-probability trade.
        """)
