"""Fetch US retail gasoline national average via AAA or fallback sources."""

import requests
from datetime import datetime, timezone

from data.cache import get, set
from config import CACHE_TTL_AAA

CACHE_KEY = "aaa_gas_price"


def get_aaa_gas_price():
    """Return current US national average gas price. Falls back to known EIA weekly if scrape fails."""
    data, _, _, stale = get(CACHE_KEY)
    if data is not None and not stale:
        return data

    price = None
    try:
        url = "https://gasprices.aaa.com/"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        import re
        match = re.search(r'\$?(\d+\.\d{2,3})', resp.text)
        if match:
            candidates = []
            for m in re.finditer(r'\$(\d+\.\d{3})', resp.text):
                val = float(m.group(1))
                if 2.0 < val < 8.0:
                    candidates.append(val)
            if candidates:
                price = candidates[0]
    except Exception:
        pass

    result = {
        "price": price,
        "source": "AAA" if price else "UNAVAILABLE",
        "date": datetime.now(timezone.utc).isoformat()[:10],
    }

    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY, result, CACHE_TTL_AAA, last_updated=last_upd)
    return result
