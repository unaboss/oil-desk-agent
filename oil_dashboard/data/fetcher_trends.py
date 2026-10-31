"""Fetch Google Trends data for sentiment overlay."""

from datetime import datetime, timezone

from data.cache import get, set
from config import CACHE_TTL_TRENDS

CACHE_KEY = "google_trends"


def get_google_trends(keywords=None, start="2025-12-01", end=None):
    """Return Google Trends interest over time for given keywords.
    Falls back gracefully if pytrends is rate-limited or unavailable."""
    data, _, _, stale = get(CACHE_KEY)
    if data is not None and not stale:
        return data

    if keywords is None:
        keywords = ["oil price", "gas prices"]

    result = {"dates": [], "keywords": keywords, "values": {}, "available": False}

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=360, retries=1, backoff_factor=0.1)
        pytrends.build_payload(keywords, timeframe=f"{start} {end or ''}", geo="US")
        df = pytrends.interest_over_time()
        if not df.empty:
            result["dates"] = [str(d.date()) for d in df.index]
            for kw in keywords:
                if kw in df.columns:
                    result["values"][kw] = df[kw].tolist()
            result["available"] = True
    except Exception:
        pass

    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY, result, CACHE_TTL_TRENDS, last_updated=last_upd)
    return result
