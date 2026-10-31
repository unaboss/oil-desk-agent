"""Offline demo mode: deterministic SAMPLE data instead of live feeds.

Enabled with OIL_DESK_DEMO=1. Used for screenshots and as a fallback when the live
sources (Yahoo Finance, EIA, CFTC) are unreachable. Never mixes with live data:
the on-disk cache is redirected to a temp folder while demo mode is on.
"""
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ENABLED = os.getenv("OIL_DESK_DEMO") == "1"
SEED = 20261031

# (start level, daily vol, drift) per ticker
_SPECS = {
    "CL=F": (64.0, 0.019, -0.0004),
    "RB=F": (1.98, 0.021, -0.0003),
    "^OVX": (31.0, 0.045, 0.0),
    "DX-Y.NYB": (99.0, 0.003, 0.00005),
}


def _bdays(start, end):
    return pd.bdate_range(start=start, end=end)


def _walk(n, level, vol, drift, rng):
    shocks = rng.normal(drift, vol, n)
    return level * np.exp(np.cumsum(shocks))


def _series(ticker, start, end):
    idx = _bdays(start, end)
    rng = np.random.default_rng(SEED + sum(map(ord, ticker)))
    if ticker == "BZ=F":
        wti = _series("CL=F", start, end)["Close"].values
        spread = 3.6 + np.cumsum(np.random.default_rng(SEED + 7).normal(0, 0.12, len(idx)))
        close = wti + np.clip(spread, -1.5, 6.5)
    else:
        level, vol, drift = _SPECS[ticker]
        close = _walk(len(idx), level, vol, drift, rng)
        if ticker == "^OVX":
            close = np.clip(close, 22, 55)
    df = pd.DataFrame({"Close": close}, index=idx)
    if ticker == "CL=F":
        df["Volume"] = np.random.default_rng(SEED + 3).integers(180_000, 460_000, len(idx)).astype(float)
    return df


def _fake_download(ticker, start=None, end=None, **_):
    return _series(ticker, start or "2025-12-01", end or date.today().isoformat())


_EIA = {  # cache_key -> (level, weekly sd)
    "eia_crude": (421_000.0, 3_200.0),
    "eia_gasoline": (214_000.0, 2_100.0),
    "eia_distillate": (116_000.0, 1_700.0),
    "eia_retail_gas": (3.08, 0.05),
    "eia_spr": (409_000.0, 300.0),
}


def _fake_eia_weekly(route, facets, data_cols, cache_key, start="2025-12-01", end=None, **_):
    end = end or date.today().isoformat()
    weeks = pd.date_range(start=start, end=end, freq="W-FRI")
    level, sd = _EIA.get(cache_key, (100_000.0, 1_000.0))
    rng = np.random.default_rng(SEED + sum(map(ord, cache_key)))
    vals = level + np.cumsum(rng.normal(0, sd, len(weeks)))
    periods = [d.strftime("%Y-%m-%d") for d in weeks][::-1]
    return {"dates": periods, "values": [round(float(v), 2) for v in vals[::-1]]}


def _fake_cot():
    return {"managed_money_long": 212_000, "managed_money_short": 131_000, "net_long": 81_000}


def install():
    """Patch the fetchers. Safe to call more than once."""
    if not ENABLED:
        return False
    import data.cache as cache
    import data.fetcher_yfinance as fy
    import data.fetcher_eia as fe
    import data.fetcher_cot as fc

    tmp = Path(tempfile.gettempdir()) / "oil_desk_demo_cache"
    tmp.mkdir(exist_ok=True)
    cache._cache_file = lambda key: tmp / f"_cache_{key}.json"
    cache._cache.clear()
    fy.yf.download = _fake_download
    fe._eia_weekly = _fake_eia_weekly
    fc.get_cot_data = _fake_cot
    return True


def banner_text():
    return ("SAMPLE DATA: this view uses generated demo prices, not live markets. "
            f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.")
