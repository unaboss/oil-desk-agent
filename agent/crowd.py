"""Crowd view: Polymarket's open oil-price markets (public Gamma API, no key)."""
import json

import requests

GAMMA = "https://gamma-api.polymarket.com"
KEYWORDS = ("crude", "wti", "oil price", "brent")


def _parse_list(v):
    if isinstance(v, list):
        return v
    try:
        return json.loads(v or "[]")
    except (TypeError, ValueError):
        return []


def summarise_markets(events, limit=5):
    """Pure function: pick open oil markets and return question + implied odds."""
    out = []
    for ev in events or []:
        for m in ev.get("markets", []) or []:
            q = (m.get("question") or ev.get("title") or "").strip()
            if not any(k in q.lower() for k in KEYWORDS):
                continue
            if m.get("closed") or m.get("active") is False:
                continue
            outcomes = _parse_list(m.get("outcomes"))
            prices = [float(p) for p in _parse_list(m.get("outcomePrices"))]
            if not outcomes or len(outcomes) != len(prices):
                continue
            out.append({
                "question": q,
                "odds": {o: round(p, 3) for o, p in zip(outcomes, prices)},
                "volume_usd": round(float(m.get("volume") or 0)),
                "ends": m.get("endDate"),
            })
    out.sort(key=lambda x: x["volume_usd"], reverse=True)
    return out[:limit]


def fetch_crowd(timeout=15):
    events = []
    for q in ("crude oil", "WTI"):
        try:
            r = requests.get(f"{GAMMA}/public-search", params={"q": q, "events_status": "active"}, timeout=timeout)
            r.raise_for_status()
            events += r.json().get("events", []) or []
        except Exception:
            continue
    seen, uniq = set(), []
    for e in events:
        if e.get("id") not in seen:
            seen.add(e.get("id"))
            uniq.append(e)
    return summarise_markets(uniq)
