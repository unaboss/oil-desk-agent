"""Oil Dashboard — WTI CFD Swing Trader Dashboard.

Streamlit app. 8 tabs, sidebar with refresh and schedule.
"""

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# Load .env from this app's directory (the server may run from the repo root).
load_dotenv(Path(__file__).parent / ".env")

st.set_page_config(
    page_title="Oil Dashboard",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config import ROOT_DIR
from data import demo_mode
_DEMO = demo_mode.install()
from ui.sidebar import render_sidebar, render_sidebar_score
from ui.charts_price import render_price_tab
from ui.charts_curve import render_curve_tab
from ui.charts_cot import render_cot_tab
from ui.charts_inventory import render_inventory_tab
from ui.charts_sentiment import render_sentiment_tab
from ui.charts_confluence import render_confluence_tab
from ui.calendar_view import render_calendar_tab
from ui.charts_audit import render_audit_tab
from ui.charts_research import render_research_tab
from ui.charts_fibonacci import render_fibonacci_tab
from ui.charts_eia_analysis import render_eia_analysis_tab
from ui.charts_agent import render_agent_tab

from data.fetcher_yfinance import get_all_market_data
from data.fetcher_eia import get_all_eia_data
import data.fetcher_cot as _fetcher_cot
from data.fetcher_aaa import get_aaa_gas_price
from data.fetcher_trends import get_google_trends
from data.fetcher_bots import get_bot_mentions
from data.fetcher_statements import get_officials_statements


@st.cache_data(ttl=3600)
def load_market_data(start, end, _version="2"):  # bump _version to invalidate stale cache
    return get_all_market_data(start=str(start), end=str(end))


@st.cache_data(ttl=86400)
def load_eia_data(start, end):
    return get_all_eia_data(start=str(start), end=str(end))


@st.cache_data(ttl=86400)
def load_cot_data():
    return _fetcher_cot.get_cot_data()  # module lookup so demo mode can swap it


@st.cache_data(ttl=86400)
def load_trends_data(start, end):
    return get_google_trends(start=str(start), end=str(end))


@st.cache_data(ttl=86400)
def load_bot_trends_data(start, end):
    return get_bot_mentions(start=str(start), end=str(end))


@st.cache_data(ttl=1800)
def load_statements_data():
    return get_officials_statements()


@st.cache_data(ttl=86400)
def load_aaa_data():
    return get_aaa_gas_price()


def load_events():
    events_path = ROOT_DIR / "data" / "events.csv"
    if events_path.exists():
        events_df = pd.read_csv(events_path)
        events_df["date"] = pd.to_datetime(events_df["date"].astype(str), format="%Y%m%d")
        return events_df
    return None


def main():
    col_title, col_ref = st.columns([5, 1])
    with col_title:
        st.title("Oil Dashboard")
    with col_ref:
        st.caption("")

    if _DEMO:
        st.warning(demo_mode.banner_text())

    score_placeholder = st.sidebar.empty()
    start_date, end_date = render_sidebar()
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    with st.spinner("Loading market data..."):
        market_data = load_market_data(start_str, end_str)

    with st.spinner("Loading EIA data..."):
        eia_data = load_eia_data(start_str, end_str)

    with st.spinner("Loading COT data..."):
        cot_data = load_cot_data()

    render_sidebar_score(score_placeholder, market_data, eia_data, cot_data)

    with st.spinner("Loading sentiment data..."):
        trends_data = load_trends_data(start_str, end_str)

    with st.spinner("Loading bot-mention data..."):
        bot_trends_data = load_bot_trends_data(start_str, end_str)

    with st.spinner("Loading officials & military statements..."):
        statements_data = load_statements_data()

    events_df = load_events()

    tabs = st.tabs([
        "0. Oil Desk Agent",
        "1. Price & Flows",
        "2. Curve & Divergence",
        "3. Inventories",
        "4. Positioning & COT",
        "5. Retail & Sentiment",
        "6. Confluence Score",
        "7. Trade Calendar",
        "8. Signal Audit",
        "9. Research & Narrative",
        "10. Fibonacci Retracement",
        "11. EIA Release Analysis",
    ])

    with tabs[0]:
        render_agent_tab(market_data)

    with tabs[1]:
        render_price_tab(market_data, events_df)

    with tabs[2]:
        render_curve_tab(market_data)

    with tabs[3]:
        render_inventory_tab(eia_data)

    with tabs[4]:
        render_cot_tab(cot_data, market_data)

    with tabs[5]:
        render_sentiment_tab(market_data, eia_data, trends_data)

    with tabs[6]:
        render_confluence_tab(market_data, eia_data, cot_data)

    with tabs[7]:
        render_calendar_tab(market_data, eia_data, cot_data)

    with tabs[8]:
        render_audit_tab(market_data, eia_data, cot_data)

    with tabs[9]:
        render_research_tab(market_data, bot_trends_data, start_str, end_str, statements_data)

    with tabs[10]:
        render_fibonacci_tab(market_data)

    with tabs[11]:
        render_eia_analysis_tab(eia_data)


if __name__ == "__main__":
    main()
