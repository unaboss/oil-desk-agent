"""Trump oil-statement event study.

Tests the hypothesis that oil-related statements arrive *after* the price move
is already done (lagging) or *before* a direction change (pre-reversal).

Reuses the WTI series already loaded by the dashboard (market_data["wti"]).
"""

import pandas as pd
from datetime import datetime, timezone

from config import (
    RESEARCH_TRUMP_CSV,
    TRUMP_PRE_LOOKBACK,
    TRUMP_FWD_LOOKBACK,
    TRUMP_MOVE_THRESHOLD,
)


def _load_statements():
    if not RESEARCH_TRUMP_CSV.exists():
        return []
    df = pd.read_csv(RESEARCH_TRUMP_CSV)
    out = []
    for _, row in df.iterrows():
        try:
            out.append({
                "date": pd.to_datetime(str(row["date"])).strftime("%Y-%m-%d"),
                "statement": str(row.get("statement", "")),
                "claim_type": str(row.get("claim_type", "")),
                "source_url": str(row.get("source_url", "")),
            })
        except Exception:
            continue
    return out


def compute_trump_event_study(market_data, start=None, end=None):
    """Return per-statement returns + aggregate lag statistics.

    Each statement is classified as:
      - "Lagging"      : big move BEFORE he spoke, little/opposite AFTER
      - "Pre-reversal" : move AFTER reverses the prior direction
      - "Confirmation" : move continues in same direction after
      - "No signal"    : neither window met the move threshold
    """
    wti = market_data.get("wti", {})
    dates = wti.get("dates", [])
    close = wti.get("close", [])
    if not dates or not close:
        return {"events": [], "lag_rate": 0.0, "total": 0, "classified": 0,
                "summary": {}}

    date_to_idx = {d: i for i, d in enumerate(dates)}
    statements = _load_statements()

    start_s = pd.to_datetime(start).strftime("%Y-%m-%d") if start else None
    end_s = pd.to_datetime(end).strftime("%Y-%m-%d") if end else None

    events = []
    for s in statements:
        d = s["date"]
        if start_s and d < start_s:
            continue
        if end_s and d > end_s:
            continue
        if d not in date_to_idx:
            continue
        idx = date_to_idx[d]

        pre_idx = max(0, idx - TRUMP_PRE_LOOKBACK)
        fwd_idx = min(len(close) - 1, idx + TRUMP_FWD_LOOKBACK)
        if pre_idx == idx or fwd_idx == idx:
            continue

        p0 = close[pre_idx]
        p1 = close[idx]
        p2 = close[fwd_idx]
        if p0 in (None, 0) or p1 in (None, 0) or p2 in (None, 0):
            continue

        pre_return = p1 / p0 - 1.0
        fwd_return = p2 / p1 - 1.0

        pre_sig = abs(pre_return) >= TRUMP_MOVE_THRESHOLD
        fwd_sig = abs(fwd_return) >= TRUMP_MOVE_THRESHOLD

        if pre_sig and not fwd_sig:
            klass = "Lagging"
        elif fwd_sig and (pre_return * fwd_return < 0):
            klass = "Pre-reversal"
        elif pre_sig and fwd_sig and (pre_return * fwd_return > 0):
            klass = "Confirmation"
        else:
            klass = "No signal"

        events.append({
            "date": d,
            "statement": s["statement"],
            "claim_type": s["claim_type"],
            "source_url": s["source_url"],
            "pre_return_pct": round(pre_return * 100, 2),
            "fwd_return_pct": round(fwd_return * 100, 2),
            "classification": klass,
        })

    events.sort(key=lambda x: abs(x["pre_return_pct"]), reverse=True)

    classified = [e for e in events if e["classification"] != "No signal"]
    lagging = [e for e in classified if e["classification"] == "Lagging"]
    lag_rate = round(100.0 * len(lagging) / len(classified), 1) if classified else 0.0

    summary = {
        "Lagging": len(lagging),
        "Pre-reversal": len([e for e in classified if e["classification"] == "Pre-reversal"]),
        "Confirmation": len([e for e in classified if e["classification"] == "Confirmation"]),
        "No signal": len([e for e in events if e["classification"] == "No signal"]),
    }

    return {
        "events": events,
        "lag_rate": lag_rate,
        "total": len(events),
        "classified": len(classified),
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
