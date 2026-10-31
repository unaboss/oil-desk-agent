"""Statistical analysis: lag correlation, win-rate backtesting."""

import pandas as pd
import numpy as np


def cross_correlation(series_a, series_b, max_lag=14):
    """Compute cross-correlation between two series at various lags.
    Returns dict: {lag_days: correlation}."""
    sa = pd.Series(series_a).pct_change().dropna()
    sb = pd.Series(series_b).pct_change().dropna()
    results = {}
    for lag in range(max_lag + 1):
        if lag == 0:
            corr = sa.corr(sb)
        else:
            shifted = sb.shift(lag).dropna()
            aligned = sa.iloc[-len(shifted):] if len(shifted) < len(sa) else sa
            c = aligned.corr(shifted)
            results[lag] = round(c, 4) if not np.isnan(c) else 0.0
    return results


def optimal_lag(series_a, series_b, max_lag=14):
    """Find the lag with highest absolute correlation."""
    cc = cross_correlation(series_a, series_b, max_lag)
    best = max(cc.items(), key=lambda x: abs(x[1]))
    return {"lag": best[0], "correlation": best[1]}


def signal_win_rate(scores_df, returns, threshold=2, forward_days=3):
    """Given a DataFrame with date and score columns, compute signal accuracy."""
    if scores_df.empty:
        return 0.0
    signals = scores_df[abs(scores_df["score"]) >= threshold]
    if len(signals) == 0:
        return 0.0
    wins = 0
    for _, row in signals.iterrows():
        direction = "bullish" if row["score"] > 0 else "bearish"
        idx = scores_df.index.get_loc(row.name)
        if idx + forward_days >= len(returns):
            continue
        fwd = returns[idx + forward_days] - returns[idx]
        if (direction == "bullish" and fwd > 0) or (direction == "bearish" and fwd < 0):
            wins += 1
    return wins / len(signals) if len(signals) > 0 else 0.0
