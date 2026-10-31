"""Sidebar UI — confluence score, cache status, refresh, date range, mini calendar."""

import streamlit as st
from datetime import datetime, timezone, timedelta

from data.cache import invalidate_all
from config import next_eia_release, next_cot_release
from analysis.confluence import compute_total_score


def render_sidebar(score_placeholder=None):
    st.sidebar.title("Oil Dashboard")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Date Range")
    start_date = st.sidebar.date_input("Start", value=datetime(2025, 12, 1))
    end_date = st.sidebar.date_input("End", value=datetime.now().date())

    st.sidebar.markdown("---")

    if st.sidebar.button("Refresh All Data", use_container_width=True):
        invalidate_all()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Scheduled Releases")

    eia_next = next_eia_release()
    cot_next = next_cot_release()
    now_utc = datetime.now(timezone.utc)

    eia_diff = eia_next - now_utc
    cot_diff = cot_next - now_utc

    eia_label = f"EIA: {eia_next.strftime('%a %b %d %H:%M')} UTC"
    cot_label = f"COT: {cot_next.strftime('%a %b %d %H:%M')} UTC"

    st.sidebar.caption(eia_label)
    st.sidebar.caption(cot_label)

    if eia_diff < timedelta(hours=2):
        st.sidebar.info("EIA releasing soon")
    if cot_diff < timedelta(hours=2):
        st.sidebar.info("COT releasing soon")

    st.sidebar.markdown("---")
    st.sidebar.subheader("This Week")

    today = datetime.now(timezone.utc).date()
    for i in range(7):
        d = today + timedelta(days=i)
        dow = d.strftime("%a")
        label = ""
        if d.weekday() == 2:
            label = "EIA 10:30AM"
        elif d.weekday() == 4:
            label = "COT 3:30PM"
        is_today = "**" if d == today else ""
        st.sidebar.caption(f"{is_today}{dow} {d.strftime('%b %d')}: {label}{is_today}")

    return start_date, end_date


def render_sidebar_score(score_placeholder, market_data, eia_data, cot_data):
    """Fill the top-of-sidebar placeholder with the live confluence score."""
    if score_placeholder is None:
        return
    result = compute_total_score(market_data, eia_data, cot_data)
    total = result["total"]
    direction = result["direction"]
    color = "#4CAF50" if direction == "bullish" else "#F44336" if direction == "bearish" else "#FFC107"
    score_placeholder.markdown(
        f"<div style='text-align:center;padding:6px 0;'>"
        f"<span style='color:{color};font-weight:bold;font-size:20px'>{total}/6</span><br>"
        f"<span style='color:{color};font-weight:bold'>CONFLUENCE — {direction.upper()}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
