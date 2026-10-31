"""Centralized configuration for Oil Dashboard."""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

EIA_API_KEY = os.getenv("EIA_API_KEY", "PLACEHOLDER")

# ── Date Range ──────────────────────────────────────────────────────────────────
DEFAULT_START = "2025-12-01"
DEFAULT_END = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── yfinance Tickers ────────────────────────────────────────────────────────────
TICKER_WTI = "CL=F"
TICKER_BRENT = "BZ=F"
TICKER_RBOB = "RB=F"
TICKER_OVX = "^OVX"
TICKER_DXY = "DX-Y.NYB"

# ── EIA API v2 Routes ───────────────────────────────────────────────────────────
EIA_BASE = "https://api.eia.gov/v2"

EIA_ROUTES = {
    "crude_stocks": "/petroleum/stoc/wstk",
    "gasoline_stocks": "/petroleum/stoc/wstk",
    "distillate_stocks": "/petroleum/stoc/wstk",
    "cushing_stocks": "/petroleum/stoc/wstk",
    "retail_gas_price": "/petroleum/pri/gnd",
    "gasoline_stocks_change": "/petroleum/stoc/wstk",
    "distillate_stocks_change": "/petroleum/stoc/wstk",
}

# ── Refinery Capacity & Utilization ──────────────────────────────────────────────
# EIA Refinery Capacity Report (annual XLSX) + weekly inputs & utilization API.
# The report uses a 2-digit year in the filename (refcap26.xlsx).
REFINERY_CAP_URL = "https://www.eia.gov/petroleum/refinerycapacity/refcap{yy}.xlsx"
REFINERY_CAP_PRODUCT = "TOTAL OPERABLE CAPACITY"
REFINERY_CAP_SERIES = "Atmospheric Crude Distillation Capacity (barrels per calendar day)"
REFINERY_UTIL_ROUTE = "/petroleum/pnp/wiup"
# Weekly series: percent utilization, crude inputs (Mbbl/d), operable capacity (Mbbl/d)
REFINERY_UTIL_SERIES = {
    "utilization_pct": "WPULEUS3",
    "crude_inputs": "WCRRIUS2",
    "operable_capacity": "WOCLEUS2",
}
CACHE_TTL_REFINERY_CAP = 60 * 60 * 24 * 30   # annual report, refresh monthly
CACHE_TTL_REFINERY_UTIL = 60 * 60 * 6        # weekly data, refresh every 6h
# On a failed fetch, retry after a short delay instead of caching the failure
# under the long capacity TTL (a transient outage would otherwise blank the
# table for 30 days).
CACHE_TTL_REFINERY_CAP_FAILURE = 60 * 60

# ── CFTC COT Report ─────────────────────────────────────────────────────────────
COT_URL = "https://www.cftc.gov/dea/futures/deacmesf.htm"
COT_CACHE_FILE = DATA_DIR / "cot_cache.csv"

# ── Cache TTLs (seconds) ────────────────────────────────────────────────────────
# yfinance: 3600 market hours, 21600 otherwise
CACHE_TTL_YFINANCE_MARKET = 60 * 60
CACHE_TTL_YFINANCE_OFFHOURS = 60 * 60 * 6
CACHE_TTL_EIA = 60 * 60 * 24 * 3  # until next Wednesday
CACHE_TTL_COT = 60 * 60 * 24 * 3  # until next Friday
CACHE_TTL_AAA = 60 * 60 * 24
CACHE_TTL_TRENDS = 60 * 60 * 24
CACHE_TTL_CALENDAR = 60 * 60 * 6

# ── EIA Weekly Release Schedule ─────────────────────────────────────────────────
# EIA Petroleum Status: Wednesdays at 10:30 AM ET (15:30 UTC daylight, 14:30 UTC standard)
def next_eia_release():
    now = datetime.now(timezone.utc)
    release_hour = 15  # 10:30 AM ET = 14:30/15:30 UTC depending on DST
    days_until_wed = (2 - now.weekday()) % 7
    if days_until_wed == 0 and now.hour >= release_hour:
        days_until_wed = 7
    next_wed = now.replace(hour=release_hour, minute=30, second=0, microsecond=0) + timedelta(days=days_until_wed)
    return next_wed

# COT Report: Fridays at 3:30 PM ET
def next_cot_release():
    now = datetime.now(timezone.utc)
    release_hour = 20  # 3:30 PM ET
    days_until_fri = (4 - now.weekday()) % 7
    if days_until_fri == 0 and now.hour >= release_hour:
        days_until_fri = 7
    next_fri = now.replace(hour=release_hour, minute=30, second=0, microsecond=0) + timedelta(days=days_until_fri)
    return next_fri

# ── Confluence Score Thresholds ─────────────────────────────────────────────────
CONFLUENCE_SIGNALS = [
    "volume",      # WTI volume > 20d avg
    "cot",         # COT managed money extreme long/short
    "inventories", # EIA crude draw/build
    "crack",       # RBOB-WTI crack widening/narrowing
    "dxy",         # Dollar weakening/strengthening
    "curve",       # Futures curve backwardation/contango
]

SIGNAL_WEIGHTS = {
    "volume": 1,
    "cot": 1,
    "inventories": 1,
    "crack": 1,
    "dxy": 1,
    "curve": 1,
}

BULLISH_THRESHOLD = 2
BEARISH_THRESHOLD = -2

# ── Volume Anomaly ──────────────────────────────────────────────────────────────
VOLUME_MA_DAYS = 20

# ── COT Extreme Thresholds ──────────────────────────────────────────────────────
COT_EXTREME_LONG_PCT = 80
COT_EXTREME_SHORT_PCT = 20

# ── Returns thresholds for audit ────────────────────────────────────────────────
AUDIT_RETURN_THRESHOLD = 0.03  # 3% move to flag as significant
AUDIT_LOOKBACK_DAYS = 30
AUDIT_FORWARD_DAYS = 3  # check 3-day forward return

# ── Research & Narrative Tab ─────────────────────────────────────────────────────
RESEARCH_TRUMP_CSV = DATA_DIR / "trump_oil_statements.csv"
RESEARCH_TRADERS_CSV = DATA_DIR / "losing_traders.csv"

# ── Officials & Military Tracker ─────────────────────────────────────────────────
# Google News RSS query per watched official (broad news coverage).
OFFICIALS_WATCH = [
    {"name": "Secretary of Energy", "query": '"Secretary of Energy"', "category": "officials"},
    {"name": "Secretary of the Interior", "query": '"Secretary of the Interior"', "category": "officials"},
    {"name": "Secretary of State", "query": '"Secretary of State"', "category": "officials"},
    {"name": "Secretary of Defense", "query": '"Secretary of Defense"', "category": "officials"},
    {"name": "EPA Administrator", "query": '"EPA Administrator"', "category": "officials"},
    {"name": "FERC Chair", "query": '"FERC"', "category": "officials"},
    {"name": "EIA Administrator", "query": '"EIA"', "category": "officials"},
]

# Google News RSS queries for military / Iran tracking. Military items are
# kept only when they mention a MILITARY_IRAN_KEYWORDS term.
MILITARY_WATCH = [
    {"name": "Pentagon", "query": "Pentagon Iran", "category": "military"},
    {"name": "CENTCOM", "query": "CENTCOM Iran", "category": "military"},
    {"name": "Department of Defense", "query": '"Department of Defense" Iran', "category": "military"},
    {"name": "Military & Oil", "query": "military oil", "category": "military"},
]

# Official agency press-release feeds (primary source).
AGENCY_FEEDS = [
    {"name": "DOE", "url": "https://www.energy.gov/rss/press-releases.xml", "category": "energy"},
    {"name": "DoD", "url": "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=20&ContentType=1&Site=945", "category": "military"},
    {"name": "State", "url": "https://www.state.gov/rss-feed/press-releases/feed/", "category": "state"},
]

# Oil-relevance keywords: officials/agency items are kept only when one matches.
OFFICIAL_KEYWORDS = [
    "oil", "crude", "gasoline", "refinery", "pipeline", "sanction",
    "energy", "Iran", "OPEC", "petroleum",
]

# Military items are kept only when they mention one of these (Iran tracking).
MILITARY_IRAN_KEYWORDS = ["Iran"]

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
CACHE_TTL_STATEMENTS = 3 * 60 * 60      # single cache TTL for the tracker feed


# Trump event-study windows (trading days)
TRUMP_PRE_LOOKBACK = 5    # move already done before he spoke
TRUMP_FWD_LOOKBACK = 3    # move after he spoke
TRUMP_MOVE_THRESHOLD = 0.02  # 2% to count as a "significant" move

# Bot-mention proxy keywords (Google Trends)
BOT_KEYWORDS = [
    "MetaTrader oil EA",
    "TradingView oil bot",
    "Pine Script oil",
    "3Commas oil",
    "oil trading bot",
]
