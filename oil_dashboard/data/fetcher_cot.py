"""Scrape CFTC Commitment of Traders report for Managed Money positioning."""

import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timezone

from data.cache import get, set
from config import CACHE_TTL_COT, next_cot_release

CACHE_KEY = "cot_positioning"


def _parse_cot_html(html):
    """Extract Managed Money long/short from CFTC legacy COT futures-only report."""
    try:
        dfs = pd.read_html(StringIO(html))
    except Exception:
        return None

    for df in dfs:
        if df.shape[1] < 10:
            continue
        cols = [str(c).strip() for c in df.iloc[0].tolist()]
        for i, row in df.iterrows():
            vals = row.astype(str).tolist()
            row_str = " ".join(vals).lower()
            if "managed money" in row_str and "long" in row_str:
                try:
                    long_idx = next(i for i, c in enumerate(cols) if "long" in c.lower() and "pos" in c.lower())
                    short_idx = long_idx + 1
                    long_val = float(str(row.iloc[long_idx]).replace(",", ""))
                    short_val = float(str(row.iloc[short_idx]).replace(",", ""))
                    return {"managed_money_long": long_val, "managed_money_short": short_val}
                except Exception:
                    continue
    return None


def get_cot_data():
    """Return {managed_money_long, managed_money_short, net_long}."""
    data, _, _, stale = get(CACHE_KEY)
    if data is not None and not stale:
        return data

    try:
        resp = requests.get(
            "https://www.cftc.gov/dea/futures/deacmesf.htm",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        parsed = _parse_cot_html(resp.text)
    except Exception:
        parsed = None

    result = {
        "managed_money_long": parsed["managed_money_long"] if parsed else None,
        "managed_money_short": parsed["managed_money_short"] if parsed else None,
        "net_long": (parsed["managed_money_long"] - parsed["managed_money_short"]) if parsed else None,
    }

    next_upd = next_cot_release().isoformat()
    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY, result, CACHE_TTL_COT, last_updated=last_upd, next_update=next_upd)
    return result
