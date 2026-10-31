"""Tab 7: Trade Calendar — monthly heatmap + today's setup + upcoming catalysts."""

import calendar
import streamlit as st
from datetime import datetime, timezone

from analysis.calendar_signals import (
    get_current_day_setup,
    get_calendar_month,
    get_upcoming_catalysts,
    get_signal_days,
)
from analysis.confluence import CONFLUENCE_SIGNALS


def render_calendar_tab(market_data, eia_data, cot_data):
    st.subheader("Trade Calendar")

    col_day, col_cal = st.columns([1, 2])

    with col_day:
        _render_today_setup(market_data, eia_data, cot_data)
        _render_upcoming_catalysts()

    with col_cal:
        _render_monthly_calendar(market_data, eia_data, cot_data)

    st.markdown("---")
    with st.expander("How to Read This Tab", expanded=False):
        st.markdown("""
        **Today's Setup (left panel):**
        - Shows the live confluence score for today. Green = bullish, Red = bearish, Yellow = neutral.
        - Each signal shows whether it's bullish (checkmark), bearish (warning), or neutral (grey square).
        - `[stale]` means the data hasn't been updated recently (COT is only released Fridays, EIA only on Wednesdays). Treat stale signals with less confidence.
        - WTI Last shows the most recent closing price.

        **Upcoming Catalysts:**
        - Shows what's coming this week that might move oil prices. EIA report on Wednesday, COT report on Friday.

        **Monthly Calendar (right panel):**
        - Each day gets a color based on the confluence score for that date.
        - 🟢 Green = that day had a bullish signal setup.
        - 🔴 Red = that day had a bearish signal setup.
        - 🟡 Yellow = signals were mixed or neutral.
        - Today is highlighted with a gold border.

        **How to use the calendar:**
        - Look for clusters — several green days in a row suggests a sustained bullish environment. Isolated green days in a red week might be false signals.
        - Cross-check with the Signal Audit tab to see how reliable the signals have been.
        """)


def _render_today_setup(market_data, eia_data, cot_data):
    st.markdown("### Today's Setup")
    setup = get_current_day_setup(market_data, eia_data, cot_data)

    score = setup["score"]
    direction = setup["direction"]
    color = "#4CAF50" if direction == "bullish" else "#F44336" if direction == "bearish" else "#FFC107"

    st.markdown(f"**Live Score: <span style='color:{color}'>{score}/6 {direction.upper()}</span>**",
                unsafe_allow_html=True)

    for signal, info in setup["statuses"].items():
        val = info["value"]
        state = info["state"]
        icon = "✅" if val == 1 else "⚠️" if val == -1 else "⬜"
        stale_label = " [stale]" if state == "stale" else ""
        st.caption(f"{icon} {signal.capitalize()}: {'Bullish' if val==1 else 'Bearish' if val==-1 else 'Neutral'}{stale_label}")

    if setup["wti_close"]:
        st.metric("WTI Last", f"${setup['wti_close']:.2f}")


def _render_upcoming_catalysts():
    st.markdown("### Upcoming")
    cats = get_upcoming_catalysts()
    for c in cats:
        st.caption(f"🔶 {c['date']}: {c['label']}")


def _render_monthly_calendar(market_data, eia_data, cot_data):
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    cal_data = get_calendar_month(year, month, market_data, eia_data, cot_data)

    st.markdown(f"### {calendar.month_name[month]} {year}")

    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    rows_html = "<tr>"
    for d in days_of_week:
        rows_html += f"<th style='padding:6px;text-align:center;color:#888'>{d}</th>"
    rows_html += "</tr>"

    today = now.day
    scores = cal_data.get("scores", {})

    for week in cal_data["calendar_weeks"]:
        rows_html += "<tr>"
        for day in week:
            if day == 0:
                rows_html += "<td></td>"
                continue
            date_str = f"{year}-{month:02d}-{day:02d}"
            s = scores.get(date_str)
            bg = "#1e1e1e"
            emoji = ""
            if s is not None:
                if s["direction"] == "bullish":
                    bg = "rgba(76,175,80,0.3)"
                    emoji = "🟢"
                elif s["direction"] == "bearish":
                    bg = "rgba(244,67,54,0.3)"
                    emoji = "🔴"
                else:
                    emoji = "🟡"

            border = "2px solid #FFC107" if day == today else "1px solid #333"
            rows_html += (
                f"<td style='padding:6px;text-align:center;border:{border};"
                f"background:{bg};border-radius:4px'>"
                f"{emoji}<br><span style='font-size:14px'>{day}</span></td>"
            )
        rows_html += "</tr>"

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;color:#e0e0e0">
    {rows_html}
    </table>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:12px;color:#888;margin-top:8px">
    🟢 Bullish setup &nbsp; 🔴 Bearish setup &nbsp; 🟡 Neutral &nbsp; 
    <span style="border:2px solid #FFC107;padding:0 4px;border-radius:2px">Today</span>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Click a day to see signal details (feature in development).")
