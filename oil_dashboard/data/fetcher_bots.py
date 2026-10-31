"""Fetch Google Trends bot-mention proxy for oil trading bots/platforms.

Reuses the pytrends + cache pattern from fetcher_trends.py. This is a
NARRATIVE proxy (search interest in bot/platform terms), not a headcount of
bots actually trading oil.
"""

from datetime import datetime, timezone

from data.cache import get, set
from config import CACHE_TTL_TRENDS, BOT_KEYWORDS


def get_bot_mentions(keywords=None, start="2025-12-01", end=None):
    """Return Google Trends interest over time for bot/platform keywords."""
    cache_key = "bot_mentions"
    data, _, _, stale = get(cache_key)
    if data is not None and not stale:
        return data

    if keywords is None:
        keywords = BOT_KEYWORDS

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
    set(cache_key, result, CACHE_TTL_TRENDS, last_updated=last_upd)
    return result
