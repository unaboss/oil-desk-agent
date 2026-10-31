"""Bot-mention narrative analysis.

Builds a normalized bot-mention index from Google Trends and correlates it
with WTI realized volatility. This is a narrative proxy, not a measured
count of bots trading oil.
"""

import numpy as np
import pandas as pd

from config import BOT_KEYWORDS


def compute_bot_narrative(trends_data, market_data):
    """Return bot-mention index series + correlation with WTI volatility."""
    out = {
        "available": False,
        "dates": [],
        "index": [],
        "keywords": [],
        "corr_vol": None,
        "latest_index": None,
        "peak_date": None,
    }

    if not trends_data or not trends_data.get("available"):
        return out

    dates = trends_data["dates"]
    kw_values = trends_data["values"]
    out["keywords"] = list(kw_values.keys())

    matrix = pd.DataFrame({kw: kw_values[kw] for kw in kw_values})
    if matrix.empty:
        return out

    # Normalize each keyword to 0-100 (Trends is already 0-100), then average.
    index = matrix.mean(axis=1)
    out["dates"] = dates
    out["index"] = index.round(2).tolist()
    out["available"] = True
    out["latest_index"] = round(float(index.iloc[-1]), 2) if len(index) else None

    if len(index):
        peak_idx = int(index.idxmax())
        out["peak_date"] = dates[peak_idx]

    # Correlate with WTI realized volatility (5-day rolling stdev of returns).
    wti = market_data.get("wti", {})
    wti_dates = wti.get("dates", [])
    wti_close = wti.get("close", [])
    if wti_dates and wti_close:
        wdf = pd.DataFrame({"date": wti_dates, "close": wti_close}).dropna()
        wdf["date"] = pd.to_datetime(wdf["date"])
        wdf = wdf.sort_values("date")
        rets = wdf["close"].pct_change()
        vol = rets.rolling(5).std() * np.sqrt(252) * 100  # annualized %
        wdf["vol"] = vol

        bdf = pd.DataFrame({"date": pd.to_datetime(dates), "idx": index.values})
        merged = pd.merge_asof(
            bdf.sort_values("date"), wdf[["date", "vol"]].sort_values("date"),
            on="date", direction="nearest", tolerance=pd.Timedelta(days=3),
        ).dropna()
        if len(merged) > 5:
            corr = merged["idx"].corr(merged["vol"])
            out["corr_vol"] = round(float(corr), 2) if pd.notna(corr) else None

    return out
