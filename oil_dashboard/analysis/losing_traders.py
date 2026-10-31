"""Losing oil traders — anonymous/aggregate proxy.

Sources: public CTA databases (NilssonHedge/BarclayHedge/SocGen CTA index)
and social-copy-trading energy leaderboards. Kept aggregate/anonymous where
possible to avoid attributing poor performance to named individuals.
"""

import pandas as pd
from datetime import datetime, timezone

from config import RESEARCH_TRADERS_CSV


def compute_losing_traders():
    """Load curated losing-traders CSV and return aggregate stats + rows."""
    if not RESEARCH_TRADERS_CSV.exists():
        return {"available": False, "rows": [], "stats": {}}

    df = pd.read_csv(RESEARCH_TRADERS_CSV)
    if df.empty:
        return {"available": False, "rows": [], "stats": {}}

    df["ytd_return_pct"] = pd.to_numeric(df["ytd_return_pct"], errors="coerce")
    df["max_drawdown_pct"] = pd.to_numeric(df["max_drawdown_pct"], errors="coerce")

    df = df.sort_values("ytd_return_pct")

    stats = {
        "total": int(len(df)),
        "negative": int((df["ytd_return_pct"] < 0).sum()),
        "median_ytd": round(float(df["ytd_return_pct"].median()), 2),
        "worst_ytd": round(float(df["ytd_return_pct"].min()), 2),
        "median_drawdown": round(float(df["max_drawdown_pct"].median()), 2),
        "by_type": {
            t: int((df["type"] == t).sum())
            for t in df["type"].unique()
        },
    }

    return {
        "available": True,
        "rows": df.to_dict(orient="records"),
        "stats": stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
