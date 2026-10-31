"""Trade calendar signals — past signal days, current-day setups, upcoming catalysts."""

import calendar
from datetime import datetime, timezone, timedelta

from analysis.confluence import compute_confluence
from analysis.audit import compute_audit


def get_current_day_setup(market_data, eia_data, cot_data):
    """Build a current-day setup dict with live vs stale flags."""
    score = compute_confluence(market_data, eia_data, cot_data, latest_only=True)

    live_sources = {"volume", "crack", "dxy", "curve"}
    stale_sources = {"cot", "inventories"}

    statuses = {}
    for signal, val in score["signals"].items():
        if signal in live_sources:
            statuses[signal] = {"value": val, "state": "live"}
        elif signal in stale_sources:
            statuses[signal] = {"value": val, "state": "stale"}

    return {
        "date": score["date"],
        "score": score["score"],
        "direction": score["direction"],
        "wti_close": score["wti_close"],
        "statuses": statuses,
    }


def get_calendar_month(year, month, market_data, eia_data, cot_data):
    """Return scores for each day in a month."""
    all_scores = compute_confluence(market_data, eia_data, cot_data, latest_only=False)

    month_days = {}
    cal = calendar.monthcalendar(year, month)

    for week in cal:
        for day in week:
            if day == 0:
                continue
            date_str = f"{year}-{month:02d}-{day:02d}"
            month_days[date_str] = None

    for s in (all_scores or []):
        d = s["date"]
        if d in month_days:
            month_days[d] = {
                "score": s["score"],
                "direction": s["direction"],
                "signals": s["signals"],
            }

    return {
        "year": year,
        "month": month,
        "calendar_weeks": cal,
        "scores": month_days,
    }


def get_upcoming_catalysts():
    """List upcoming scheduled events."""
    now = datetime.now(timezone.utc)
    events = []

    events.append({
        "date": (now + timedelta(days=(2 - now.weekday()) % 7)).strftime("%Y-%m-%d"),
        "label": "EIA Petroleum Status",
        "type": "eia",
    })
    events.append({
        "date": (now + timedelta(days=(4 - now.weekday()) % 7)).strftime("%Y-%m-%d"),
        "label": "COT Report",
        "type": "cot",
    })

    return events


def get_signal_days(market_data, eia_data, cot_data, lookback=30):
    """Return list of past signal days (|confluence| > 2)."""
    all_scores = compute_confluence(market_data, eia_data, cot_data, latest_only=False)
    signal_days = []
    for s in (all_scores or []):
        if abs(s["score"]) >= 2:
            signal_days.append(s)
    signal_days.sort(key=lambda x: x["date"], reverse=True)
    return signal_days[:lookback]
