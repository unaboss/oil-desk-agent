"""Signal audit — confirmed vs missed moves, hit rate."""

import numpy as np
from datetime import datetime, timezone
from analysis.confluence import compute_confluence
from config import AUDIT_RETURN_THRESHOLD, AUDIT_LOOKBACK_DAYS, AUDIT_FORWARD_DAYS


def compute_audit(market_data, eia_data, cot_data):
    """Compare confluence signals against actual 3-day forward returns.

    Returns:
        dict with confirmed, missed, false_signals lists, and hit_rate.
    """
    all_scores = compute_confluence(market_data, eia_data, cot_data, latest_only=False)
    if not all_scores:
        return {"confirmed": [], "missed": [], "false_signals": [], "hit_rate": 0.0, "total_signals": 0}

    wti = market_data.get("wti", {})
    close = wti.get("close", [])
    dates = wti.get("dates", [])

    confirmed = []
    missed = []
    false_signals = []

    for s in all_scores:
        date_str = s["date"]
        if date_str not in dates:
            continue
        idx = dates.index(date_str)
        if idx + AUDIT_FORWARD_DAYS >= len(close):
            continue

        fwd_return = (close[idx + AUDIT_FORWARD_DAYS] / close[idx] - 1)
        abs_return = abs(fwd_return)
        signal_abs = abs(s["score"])

        if signal_abs >= 2:
            direction_correct = (
                (s["direction"] == "bullish" and fwd_return > 0) or
                (s["direction"] == "bearish" and fwd_return < 0)
            )
            if direction_correct and abs_return >= AUDIT_RETURN_THRESHOLD:
                confirmed.append({
                    "date": date_str,
                    "score": s["score"],
                    "direction": s["direction"],
                    "fwd_return_pct": round(fwd_return * 100, 2),
                    "signals": s["signals"],
                })
            elif not direction_correct:
                false_signals.append({
                    "date": date_str,
                    "score": s["score"],
                    "direction": s["direction"],
                    "fwd_return_pct": round(fwd_return * 100, 2),
                    "signals": s["signals"],
                })

        elif abs_return >= AUDIT_RETURN_THRESHOLD and signal_abs < 2:
            missed.append({
                "date": date_str,
                "fwd_return_pct": round(fwd_return * 100, 2),
                "move_direction": "up" if fwd_return > 0 else "down",
                "score": s["score"],
            })

    confirmed.sort(key=lambda x: abs(x["fwd_return_pct"]), reverse=True)
    missed.sort(key=lambda x: abs(x["fwd_return_pct"]), reverse=True)
    false_signals.sort(key=lambda x: abs(x["fwd_return_pct"]), reverse=True)

    total_signals = len(confirmed) + len(false_signals)
    hit_rate = len(confirmed) / total_signals if total_signals > 0 else 0.0

    return {
        "confirmed": confirmed[:3],
        "missed": missed[:3],
        "false_signals": false_signals[:3],
        "hit_rate": round(hit_rate * 100, 1),
        "total_signals": total_signals,
        "missed_count": len(missed),
        "lookback_days": AUDIT_LOOKBACK_DAYS,
    }
