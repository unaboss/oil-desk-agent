"""Technical signal computations: moving averages, volume spikes, trend."""

import pandas as pd
import numpy as np


def compute_sma(data, window):
    """Simple moving average on a list/tuple of values."""
    s = pd.Series(data)
    return s.rolling(window, min_periods=window).mean().tolist()


def compute_ema(data, span):
    """Exponential moving average."""
    s = pd.Series(data)
    return s.ewm(span=span, adjust=False).mean().tolist()


def wti_trend(wti_dict):
    """Determine WTI short/medium trend from price vs MA."""
    if not wti_dict:
        return {"trend": "neutral", "vs_sma20": None, "vs_sma50": None}

    close = wti_dict.get("close", [])
    if len(close) < 50:
        return {"trend": "neutral", "vs_sma20": None, "vs_sma50": None}

    sma20 = compute_sma(close, 20)
    sma50 = compute_sma(close, 50)
    last = close[-1]
    vs20 = 1 if last > sma20[-1] else -1 if last < sma20[-1] else 0
    vs50 = 1 if last > sma50[-1] else -1 if last < sma50[-1] else 0

    if vs20 > 0 and vs50 > 0:
        trend = "bullish"
    elif vs20 < 0 and vs50 < 0:
        trend = "bearish"
    else:
        trend = "mixed"

    return {"trend": trend, "vs_sma20": vs20, "vs_sma50": vs50}


def daily_returns(close_prices):
    """Compute daily % returns."""
    s = pd.Series(close_prices)
    return (s.pct_change() * 100).tolist()


def forward_returns(close_prices, days=3):
    """N-day forward % return."""
    s = pd.Series(close_prices)
    return ((s.shift(-days) - s) / s * 100).tolist()
