"""Tab 6: Confluence Score Dashboard — live 6-signal board."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from analysis.confluence import compute_total_score
from config import BULLISH_THRESHOLD, BEARISH_THRESHOLD


def render_confluence_tab(market_data, eia_data, cot_data):
    st.subheader("Confluence Score — Fake Move Detection")

    total_result = compute_total_score(market_data, eia_data, cot_data)
    total = total_result["total"]
    signals = total_result["signals"]

    st.markdown(f"### Score: **{total}/6** — Direction: **{total_result['direction'].upper()}**")

    cols = st.columns(3)
    signal_config = [
        ("Volume", "volume", "WTI volume > 20d avg"),
        ("COT", "cot", "MM not at extreme"),
        ("Inventories", "inventories", "Crude drawing"),
        ("Crack", "crack", "RBOB-WTI widening"),
        ("DXY", "dxy", "Dollar weakening"),
        ("Curve", "curve", "Backwardation"),
    ]

    for i, (label, key, desc) in enumerate(signal_config):
        col_idx = i % 3
        val = signals.get(key, 0)
        if val == 1:
            icon = "✅"
            color = "#4CAF50"
        elif val == -1:
            icon = "⚠️"
            color = "#F44336"
        else:
            icon = "⬜"
            color = "#9E9E9E"

        with cols[col_idx]:
            st.markdown(f"<span style='color:{color};font-size:20px'>{icon}</span> **{label}**",
                        unsafe_allow_html=True)
            st.caption(desc)

    # Confluence gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+delta",
        value=total,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [-6, 6]},
            "bar": {"color": "#4CAF50" if total >= BULLISH_THRESHOLD else "#F44336" if total <= BEARISH_THRESHOLD else "#FFC107"},
            "steps": [
                {"range": [-6, BEARISH_THRESHOLD], "color": "rgba(244,67,54,0.3)"},
                {"range": [BEARISH_THRESHOLD, BULLISH_THRESHOLD], "color": "rgba(255,193,7,0.3)"},
                {"range": [BULLISH_THRESHOLD, 6], "color": "rgba(76,175,80,0.3)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": total,
            },
        },
        title={"text": "Confluence Score"},
    ))
    fig.update_layout(height=250, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
    })

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown(f"""
        **What is the Confluence Score?**

        Imagine you're a detective. One witness saying something is interesting, but not enough to act on. But if six independent witnesses all point to the same conclusion, you can be much more confident.

        That's what this tab does for oil trading. Instead of looking at just one data point (like "price went up today"), it checks **six different sources** of information and asks: *Do they all agree?*

        **The six signals:**
        1. **Volume** — Is there real money behind the move, or is it quiet?
        2. **COT** — Are hedge funds positioned for more upside, or are they already all-in?
        3. **Inventories** — Is crude oil actually being used up, or piling up in storage?
        4. **Crack Spread** — Are refineries making money? (If yes, they'll buy more crude.)
        5. **DXY (Dollar)** — Is the dollar helping or hurting oil prices?
        6. **Curve (Brent-WTI spread)** — Is the physical market tight or loose?

        Each signal gets +1 (bullish), -1 (bearish), or 0 (neutral/no data). The gauge adds them all up.

        **How to use the score:**
        - **Score >= {BULLISH_THRESHOLD} (Bullish)** — Multiple signals confirm that rising prices have real support. The move is likely genuine, not a fake-out.
        - **Score <= {BEARISH_THRESHOLD} (Bearish)** — Multiple signals confirm falling prices are justified. The downtrend has legs.
        - **Score in between** — The signals disagree. The market is confused. If price is moving but fundamentals don't agree, you might be looking at a **fake move** — a price swing that could reverse soon.

        **The main idea:** The dashboard is designed to protect you from getting "sucked in" to a price move that has no fundamental backing. If price is rising but the score is neutral or bearish, ask yourself: "Is this move real, or am I about to get trapped?"
        """)

    # Scoring rules
    with st.expander("Scoring Rules", expanded=False):
        st.markdown(f"""
        | Signal | +1 (Bullish) | -1 (Bearish) | 0 (Neutral) |
        |---|---|---|---|
        | Volume | WTI volume > 20d avg | Below avg | No data |
        | COT | MM not at extreme | MM extreme long/short | No data |
        | Inventories | Crude drawing | Crude building | No data |
        | Crack | Crack > 5d MA | Crack < 5d MA | No data |
        | DXY | Dollar weakening | Dollar strengthening | No data |
        | Curve | Backwardation (B-W > 0) | Contango | No data |

        **Score >= {BULLISH_THRESHOLD}**: Bullish setup — move likely real
        **Score <= {BEARISH_THRESHOLD}**: Bearish setup — move likely real
        **Score between**: Mixed signals — stay neutral
        """)
