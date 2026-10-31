"""Fetch market data via yfinance (WTI, Brent, RBOB, OVX, DXY, volume, curve spread)."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

from data.cache import get, set
from config import (
    DEFAULT_START, DEFAULT_END,
    TICKER_WTI, TICKER_BRENT, TICKER_RBOB, TICKER_OVX, TICKER_DXY,
    CACHE_TTL_YFINANCE_MARKET,
    VOLUME_MA_DAYS,
)

CACHE_KEY_WTI = "yf_wti"
CACHE_KEY_BRENT = "yf_brent"
CACHE_KEY_RBOB = "yf_rbob"
CACHE_KEY_OVX = "yf_ovx"
CACHE_KEY_DXY = "yf_dxy"
CACHE_KEY_VOLUME = "yf_volume"

def _is_market_hours():
    now = datetime.now(timezone.utc)
    h = now.hour
    w = now.weekday()
    if w >= 5:
        return False
    return 14 <= h < 21  # roughly NYMEX hours UTC

def _fetch_ticker(ticker, cache_key, start, end):
    cache_key_with_range = f"{cache_key}_{start}_{end}"
    data, _, _, stale = get(cache_key_with_range)
    if data is not None and not stale:
        return data

    ttl = CACHE_TTL_YFINANCE_MARKET if _is_market_hours() else CACHE_TTL_YFINANCE_MARKET * 6

    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty:
        return None

    dates = [str(d.date()) for d in df.index]

    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns:
            close_series = df["Close"]
        else:
            col_names = [c[0] for c in df.columns]
            idx = col_names.index("Close") if "Close" in col_names else 0
            close_series = df.iloc[:, idx]
    else:
        close_series = df["Close"] if "Close" in df.columns else df.iloc[:, 3]

    close = [float(x) if not pd.isna(float(x)) else None for x in close_series.values.flatten()]

    result = {"dates": dates, "close": close}

    if "Volume" in df.columns:
        vol_vals = df["Volume"].values.flatten()
        result["volume"] = [float(x) if not pd.isna(float(x)) else None for x in vol_vals]

    last_upd = datetime.now(timezone.utc).isoformat()
    set(cache_key_with_range, result, ttl, last_updated=last_upd)
    return result


def get_wti(start=DEFAULT_START, end=DEFAULT_END):
    """Return dict: {dates, close, volume}."""
    return _fetch_ticker(TICKER_WTI, CACHE_KEY_WTI, start, end)


def get_brent(start=DEFAULT_START, end=DEFAULT_END):
    """Return dict: {dates, close}."""
    return _fetch_ticker(TICKER_BRENT, CACHE_KEY_BRENT, start, end)


def get_rbob(start=DEFAULT_START, end=DEFAULT_END):
    """Return dict: {dates, close}."""
    return _fetch_ticker(TICKER_RBOB, CACHE_KEY_RBOB, start, end)


def get_ovx(start=DEFAULT_START, end=DEFAULT_END):
    """Return dict: {dates, close}."""
    return _fetch_ticker(TICKER_OVX, CACHE_KEY_OVX, start, end)


def get_dxy(start=DEFAULT_START, end=DEFAULT_END):
    """Return dict: {dates, close}."""
    return _fetch_ticker(TICKER_DXY, CACHE_KEY_DXY, start, end)


def get_crack_spread(start=DEFAULT_START, end=DEFAULT_END):
    """RBOB-WTI crack spread: RBOB $/gal * 42 - WTI $/bbl."""
    wti = get_wti(start, end)
    rbob = get_rbob(start, end)
    if not wti or not rbob:
        return None

    import pandas as pd
    df_wti = pd.DataFrame({"date": pd.to_datetime(wti["dates"]), "wti": wti["close"]})
    df_rbob = pd.DataFrame({"date": pd.to_datetime(rbob["dates"]), "rbob": rbob["close"]})

    merged = pd.merge(df_wti, df_rbob, on="date", how="inner")
    merged["crack"] = merged["rbob"] * 42 - merged["wti"]
    merged["crack_5ma"] = merged["crack"].rolling(5).mean()

    return {
        "dates": [str(d.date()) for d in merged["date"]],
        "crack": merged["crack"].tolist(),
        "crack_5ma": merged["crack_5ma"].tolist(),
    }


def get_curve_spread(start=DEFAULT_START, end=DEFAULT_END):
    """Brent 1mo vs 6mo spread as CFD proxy.
    Falls back to Brent-WTI spread if deferred contract unavailable."""
    cache_key = f"yf_curve_{start}_{end}"

    data, _, _, stale = get(cache_key)
    if data is not None and not stale:
        return data

    brent_front = yf.download(TICKER_BRENT, start=start, end=end, progress=False, auto_adjust=True)
    if brent_front.empty:
        return None

    try:
        brent_back = yf.download("BZ=F", start=start, end=end, progress=False, auto_adjust=True)
        if brent_back is not brent_front:
            pass
    except Exception:
        brent_back = None

    ttl = CACHE_TTL_YFINANCE_MARKET if _is_market_hours() else CACHE_TTL_YFINANCE_MARKET * 6

    dates = [str(d.date()) for d in brent_front.index]
    front_close = brent_front["Close"].values.tolist()

    result = {"dates": dates, "front": front_close}

    try:
        wti = yf.download(TICKER_WTI, start=start, end=end, progress=False, auto_adjust=True)
        if not wti.empty:
            pd_brent = pd.DataFrame({"date": pd.to_datetime(dates), "brent": front_close})
            pd_wti = pd.DataFrame({"date": pd.to_datetime([str(d.date()) for d in wti.index]), "wti": wti["Close"].values.tolist()})
            merged = pd.merge(pd_brent, pd_wti, on="date", how="inner")
            result["brent_wti_spread"] = (merged["brent"] - merged["wti"]).tolist()
            result["spread_dates"] = [str(d.date()) for d in merged["date"]]
    except Exception:
        result["brent_wti_spread"] = []

    result["is_curve_proxy"] = True

    last_upd = datetime.now(timezone.utc).isoformat()
    set(cache_key, result, ttl, last_updated=last_upd)
    return result


def get_volume_anomaly(start=DEFAULT_START, end=DEFAULT_END):
    """Return volume vs 20-day moving average."""
    wti = get_wti(start, end)
    if not wti or "volume" not in wti:
        return None

    vols = pd.Series(wti["volume"])
    ma = vols.rolling(VOLUME_MA_DAYS).mean()
    ratio = vols / ma

    return {
        "dates": wti["dates"],
        "volume": wti["volume"],
        "volume_ma": ma.tolist(),
        "volume_ratio": ratio.tolist(),
    }


def get_all_market_data(start=DEFAULT_START, end=DEFAULT_END):
    """Fetch all yfinance data in one call. Returns combined dict."""
    return {
        "wti": get_wti(start, end),
        "brent": get_brent(start, end),
        "rbob": get_rbob(start, end),
        "ovx": get_ovx(start, end),
        "dxy": get_dxy(start, end),
        "crack": get_crack_spread(start, end),
        "curve": get_curve_spread(start, end),
        "volume_anomaly": get_volume_anomaly(start, end),
    }
