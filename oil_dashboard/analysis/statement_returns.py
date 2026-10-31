"""Statement vs price analysis.

Maps captured officials/military statement dates onto the WTI series and
measures what the price did 1, 3 and 5 trading days after each statement,
grouped by category. Pure functions — no I/O, fully unit-testable.
"""

from datetime import datetime, timezone

from analysis.date_utils import day_only

FORWARD_HORIZONS = (1, 3, 5)

DIRECTION_THRESHOLD = 0.005  # 0.5% move to count as up/down (else flat)


def map_statement_dates(items, wti):
    """Return every statement that falls on a WTI trading day.

    Unlike compute_statement_returns this does not require forward prices, so
    statements near the end of the series (no forward window yet) still appear.
    Used for the price-chart markers.

    Each entry: {date, category, source, title, close}
    """
    dates = wti.get("dates", [])
    close = wti.get("close", [])
    if not dates or not close:
        return {"markers": [], "available": False}

    date_to_idx = {d: i for i, d in enumerate(dates)}
    markers = []
    for item in items:
        date = day_only(item.get("date", ""))
        if date is None or date not in date_to_idx:
            continue
        idx = date_to_idx[date]
        markers.append({
            "date": date,
            "category": item.get("category", "unknown"),
            "source": item.get("source", "unknown"),
            "title": item.get("title", ""),
            "close": close[idx],
        })

    markers.sort(key=lambda m: m["date"])
    return {"markers": markers, "available": len(markers) > 0}


def compute_statement_returns(items, wti):
    """Return per-statement forward returns aligned to the WTI series.

    Each event: {date, category, source, title, fwd_1d, fwd_3d, fwd_5d}
    Statements whose date is missing from the WTI dates, or that sit too close
    to the end of the series to have a full forward window, are skipped.
    """
    dates = wti.get("dates", [])
    close = wti.get("close", [])
    if not dates or not close:
        return {"events": [], "available": False, "generated_at": _now()}

    date_to_idx = {d: i for i, d in enumerate(dates)}
    events = []
    for item in items:
        date = day_only(item.get("date", ""))
        if date is None or date not in date_to_idx:
            continue
        idx = date_to_idx[date]

        fwd = {}
        complete = True
        for horizon in FORWARD_HORIZONS:
            fwd_idx = idx + horizon
            if fwd_idx >= len(close):
                complete = False
                break
            base, target = close[idx], close[fwd_idx]
            if base in (None, 0) or target is None:
                complete = False
                break
            fwd[f"fwd_{horizon}d"] = round((target / base - 1.0) * 100, 2)
        if not complete:
            continue

        events.append({
            "date": date,
            "category": item.get("category", "unknown"),
            "source": item.get("source", "unknown"),
            "title": item.get("title", ""),
            "fwd_1d": fwd["fwd_1d"],
            "fwd_3d": fwd["fwd_3d"],
            "fwd_5d": fwd["fwd_5d"],
        })

    events.sort(key=lambda e: e["date"])
    return {"events": events, "available": len(events) > 0, "generated_at": _now()}


def aggregate_returns(events):
    """Mean/count of each forward return, grouped by category.

    {"categories": {cat: {"fwd_1d": {"mean": x, "count": n}, ...}}, "overall": {...}}
    """
    out = {"categories": {}, "overall": _agg_for(events)}
    for cat in sorted({e["category"] for e in events}):
        cat_events = [e for e in events if e["category"] == cat]
        out["categories"][cat] = _agg_for(cat_events)
    return out


def _agg_for(events):
    agg = {}
    for horizon in FORWARD_HORIZONS:
        key = f"fwd_{horizon}d"
        vals = [e[key] for e in events if e.get(key) is not None]
        if not vals:
            agg[key] = {"mean": None, "count": 0}
            continue
        agg[key] = {
            "mean": round(sum(vals) / len(vals), 2),
            "count": len(vals),
        }
    return agg


def classify_direction(events, horizon=3):
    """Tag each event up/down/flat at a horizon + per-category hit rates.

    {"events": [{...same event, "direction": "up"|"down"|"flat"}],
     "hit_rates": {cat: {"up": pct, "down": pct, "flat": pct, "count": n}}, "overall": {...}}
    """
    key = f"fwd_{horizon}d"
    tagged = []
    for e in events:
        value = e.get(key)
        if value is None:
            direction = "flat"
        elif value > DIRECTION_THRESHOLD:
            direction = "up"
        elif value < -DIRECTION_THRESHOLD:
            direction = "down"
        else:
            direction = "flat"
        tagged.append({**e, "direction": direction, "horizon": horizon})

    rates = {}
    for cat in sorted({e["category"] for e in tagged}):
        rates[cat] = _rate_for([e for e in tagged if e["category"] == cat])
    return {"events": tagged, "hit_rates": rates, "overall": _rate_for(tagged)}


def _rate_for(events):
    total = len(events)
    if total == 0:
        return {"up": 0.0, "down": 0.0, "flat": 0.0, "count": 0}
    up = sum(1 for e in events if e["direction"] == "up")
    down = sum(1 for e in events if e["direction"] == "down")
    flat = sum(1 for e in events if e["direction"] == "flat")
    return {
        "up": round(100.0 * up / total, 1),
        "down": round(100.0 * down / total, 1),
        "flat": round(100.0 * flat / total, 1),
        "count": total,
    }


def _now():
    return datetime.now(timezone.utc).isoformat()
