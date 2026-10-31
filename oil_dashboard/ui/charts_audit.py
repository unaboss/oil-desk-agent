"""Tab 8: Signal Audit — confirmed vs missed moves, hit rate."""

import streamlit as st
import plotly.graph_objects as go

from analysis.audit import compute_audit


def render_audit_tab(market_data, eia_data, cot_data):
    st.subheader("Signal Audit")

    audit = compute_audit(market_data, eia_data, cot_data)

    col_rate, _ = st.columns([1, 2])
    with col_rate:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=audit["hit_rate"],
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#4CAF50" if audit["hit_rate"] >= 50 else "#FFC107" if audit["hit_rate"] >= 30 else "#F44336"},
                "steps": [
                    {"range": [0, 30], "color": "rgba(244,67,54,0.3)"},
                    {"range": [30, 70], "color": "rgba(255,193,7,0.3)"},
                    {"range": [70, 100], "color": "rgba(76,175,80,0.3)"},
                ],
            },
            title={"text": "Hit Rate"},
        ))
        fig.update_layout(height=200, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True, config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
        })
        st.caption(f"{audit['total_signals']} signals, {audit['missed_count']} missed moves")

    tab_conf, tab_missed, tab_false = st.tabs(["Confirmed", "Missed", "False Signals"])

    with tab_conf:
        st.markdown("#### Top 3 Confirmed Signals")
        if not audit["confirmed"]:
            st.caption("No confirmed signals in lookback period.")
        for c in audit["confirmed"]:
            color = "#4CAF50" if c["direction"] == "bullish" else "#F44336"
            st.markdown(
                f"**{c['date']}** — <span style='color:{color}'>{c['direction'].upper()} "
                f"(Score: {c['score']})</span> → {c['fwd_return_pct']:+.1f}% in 3 days",
                unsafe_allow_html=True,
            )
            signals_display = " | ".join(
                f"{k}: {'+' if v==1 else '-' if v==-1 else '0'}" for k, v in c["signals"].items()
            )
            st.caption(signals_display)

    with tab_missed:
        st.markdown("#### Top 3 Missed Moves")
        if not audit["missed"]:
            st.caption("No missed moves in lookback period.")
        for m in audit["missed"]:
            direction_emoji = "↑" if m["move_direction"] == "up" else "↓"
            st.markdown(
                f"**{m['date']}** — WTI {direction_emoji} {m['fwd_return_pct']:+.1f}% "
                f"— Model score: {m['score']} (no signal)",
                unsafe_allow_html=True,
            )
            st.caption("Possible: shipping disruption, geopolitics, surprise news")

    with tab_false:
        st.markdown("#### Top 3 False Signals")
        if not audit["false_signals"]:
            st.caption("No false signals in lookback period.")
        for f in audit["false_signals"]:
            color = "#4CAF50" if f["direction"] == "bullish" else "#F44336"
            st.markdown(
                f"**{f['date']}** — <span style='color:{color}'>{f['direction'].upper()} "
                f"(Score: {f['score']})</span> → {f['fwd_return_pct']:+.1f}% (moved opposite)",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption("Audit uses 3-day forward return to evaluate if confluence signals correctly predicted direction.")

    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **What is the Signal Audit?**

        This tab checks how good the confluence score actually is at predicting price moves. Think of it as a "report card" for the dashboard's signals. It looks at every day where the score was 2 or higher (bullish) or -2 or lower (bearish), then checks what WTI actually did over the next 3 trading days.

        **The Gauge:**
        - Shows the **hit rate** — what percentage of signals called the direction correctly.
        - 70%+ = excellent. 50-70% = useful. Below 50% = signals are no better than a coin flip, be cautious.

        **Confirmed tab:**
        - Best examples where the signal was RIGHT. A bullish score + price went up 3%+ = confirmed.
        - These are what you want to see — the dashboard doing its job.

        **Missed tab:**
        - Big price moves that the dashboard did NOT signal. Price moved 3%+ but the confluence score was below 2.
        - These are usually caused by sudden news — geopolitics, surprise OPEC announcements, etc. The dashboard can't predict those.

        **False Signals tab:**
        - The dashboard said "bullish" but price went down, or said "bearish" but price went up.
        - Every system has false signals. The goal is to have more confirmed than false.

        **How to use the audit:**
        1. Check the hit rate regularly. If it drops below 50% for weeks, the market may be in a news-driven phase where fundamentals matter less.
        2. When you see a confluence signal today, look back at the audit. Are signals working right now, or is the market ignoring fundamentals?
        3. Don't trade every signal — only trade when the audit shows the dashboard is "in sync" with the market.
        """)
