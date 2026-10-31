import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from analysis.eia_analysis import compute_eia_analysis


SIGNAL_COLORS = {1: "#4CAF50", -1: "#F44336", 0: "#9E9E9E"}
SIGNAL_EMOJI = {1: "✅", -1: "⚠️", 0: "⬜"}
PRODUCT_NAMES = {
    "crude": "Crude Oil",
    "gasoline": "Gasoline",
    "distillate": "Distillate",
    "spr": "SPR",
}


def render_eia_analysis_tab(eia_data):
    st.subheader("EIA Release Analysis")

    if not eia_data or not any(eia_data.get(k) for k in ("crude", "gasoline", "distillate")):
        st.warning("No EIA data available. Requires an EIA API key.")
        return

    analysis = compute_eia_analysis(eia_data)
    if not analysis["by_product"]:
        st.warning("Insufficient EIA data to compute analysis.")
        return

    # ── Composite score gauge ──────────────────────────────────────────────────
    composite = analysis["composite_score"]
    max_score = 4
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=composite,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [-max_score, max_score]},
            "bar": {"color": "#4CAF50" if composite > 0 else "#F44336" if composite < 0 else "#FFC107"},
            "steps": [
                {"range": [-max_score, -1], "color": "rgba(244,67,54,0.3)"},
                {"range": [-1, 1], "color": "rgba(255,193,7,0.3)"},
                {"range": [1, max_score], "color": "rgba(76,175,80,0.3)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": composite,
            },
        },
        title={"text": f"EIA Composite Score (out of {max_score})"},
    ))
    fig.update_layout(height=240, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True, "displaylogo": False,
    })

    # ── Verdict line ───────────────────────────────────────────────────────────
    if composite >= 2:
        verdict = "🟢 BULLISH — Strong fundamental support for higher prices"
        verdict_color = "#4CAF50"
    elif composite >= 1:
        verdict = "🟡 NEUTRAL BULLISH — Moderate support, watch for confirmation"
        verdict_color = "#8BC34A"
    elif composite <= -2:
        verdict = "🔴 BEARISH — Strong fundamental headwinds for prices"
        verdict_color = "#F44336"
    elif composite <= -1:
        verdict = "🟠 NEUTRAL BEARISH — Moderate headwinds, keep cautious"
        verdict_color = "#FF9800"
    else:
        verdict = "⚪ MIXED — Signals cancel out, no clear EIA bias"
        verdict_color = "#9E9E9E"

    st.markdown(f"<h3 style='color:{verdict_color}'>{verdict}</h3>", unsafe_allow_html=True)

    # ── Product cards ─────────────────────────────────────────────────────────
    cols = st.columns(4)
    products_order = ["crude", "gasoline", "distillate", "spr"]
    for i, key in enumerate(products_order):
        p = analysis["by_product"].get(key, {})
        with cols[i]:
            sig = p.get("signal", 0)
            emoji = SIGNAL_EMOJI.get(sig, "⬜")
            color = SIGNAL_COLORS.get(sig, "#9E9E9E")
            st.markdown(f"<span style='font-size:24px'>{emoji}</span> **{PRODUCT_NAMES[key]}**", unsafe_allow_html=True)

            current = p.get("current_change")
            avg_4wk = p.get("four_week_avg")
            trend = p.get("trend_label", "")

            st.metric(
                "This Week",
                f"{current:+.1f} M bbl" if current is not None else "N/A",
                delta=None,
            )
            st.caption(f"4-wk avg: {avg_4wk:+.1f}" if avg_4wk is not None else "4-wk avg: N/A")
            st.caption(f"Deviation: {p['deviation']:+.1f}" if p.get("deviation") is not None else "")
            st.markdown(f"<span style='color:{color}'>{trend}</span>", unsafe_allow_html=True)

    # ── Bar chart: current vs 4-week avg ──────────────────────────────────────
    labels = [PRODUCT_NAMES[k] for k in products_order]
    current_vals = []
    avg_vals = []
    for k in products_order:
        p = analysis["by_product"].get(k, {})
        current_vals.append(p.get("current_change") or 0)
        avg_vals.append(p.get("four_week_avg") or 0)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="This Week", x=labels, y=current_vals, marker_color="#FF9800"))
    fig2.add_trace(go.Bar(name="4-Week Avg", x=labels, y=avg_vals, marker_color="#666666"))
    fig2.add_hline(y=0, line=dict(color="white", width=1, dash="dash"))
    fig2.update_layout(
        title="Current Change vs 4-Week Average",
        height=300,
        barmode="group",
        template="plotly_dark",
        hovermode="x unified",
        dragmode="pan",
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig2, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True, "displaylogo": False,
    })

    # ── Summary bullets ───────────────────────────────────────────────────────
    st.markdown("### Signal Summary")
    if analysis["bullish_products"]:
        st.markdown(f"🟢 **Bullish:** {', '.join(PRODUCT_NAMES[k] for k in analysis['bullish_products'])}")
    if analysis["bearish_products"]:
        st.markdown(f"🔴 **Bearish:** {', '.join(PRODUCT_NAMES[k] for k in analysis['bearish_products'])}")
    if analysis["strongest_reading"]:
        k = analysis["strongest_reading"]
        p = analysis["by_product"].get(k, {})
        st.markdown(f"⚡ **Strongest deviation:** {PRODUCT_NAMES[k]} ({p.get('deviation', 0):+.1f} M bbl deviation)")

    # ── How to Read ───────────────────────────────────────────────────────────
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **What is this?**
        Every Wednesday at 10:30 AM ET, the EIA releases the Weekly Petroleum Status Report. This tab analyzes the report's numbers to tell you whether the data is fundamentally bullish or bearish for oil prices.

        **The four products tracked:**
        1. **Crude Oil** — The raw stuff. A draw (decrease) means more oil is being consumed than produced. Bullish.
        2. **Gasoline** — Made from crude. A draw can signal strong driving demand in summer. Bullish for crude demand.
        3. **Distillate** — Diesel, jet fuel, heating oil. A draw means industrial activity or cold weather is consuming fuel.
        4. **SPR (Strategic Petroleum Reserve)** — Government-owned emergency stockpile. A release (decrease) means the government is adding supply to the market, which is bearish.

        **How each product is scored:**
        - The score compares **this week's change** to the **average of the previous 4 weeks**.
        - If the change is more extreme than the recent trend, it's a signal.
        - **Crude/Gasoline/Distillate:** A bigger draw than the 4-week average = +1 (bullish). A bigger build = -1 (bearish).
        - **SPR:** A release (draw) = -1 (bearish, adds supply). A refill (build) = +1 (bullish, removes supply).

        **Composite Score:**
        - Sum of all four signals. Range: -4 to +4.
        - **+2 to +4:** Strong fundamental support for higher prices.
        - **-2 to -4:** Strong fundamental headwinds, likely lower prices.
        - **-1 to +1:** Mixed — no clear EIA signal.

        **How to use this for trading:**
        - The EIA release can move WTI by 1-3% in minutes. Be cautious trading around 10:30 AM Wednesday.
        - The **deviation** column tells you which product had the biggest surprise versus the recent trend. That's what the market will react to most.
        - A **crude draw** is bullish BUT check gasoline too. If crude is drawing but gasoline is building massively, the draw might be temporary (refinery maintenance, not demand).
        - The **SPR release** signal matters most during a crisis. In normal times, it's usually flat.
        """)
