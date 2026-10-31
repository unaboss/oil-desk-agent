"""Officials & Military tracker analysis — pure functions, no I/O.

Derived aggregates over the fetched statement items. Kept offline so the
logic is fully unit-testable.
"""

from collections import Counter

from config import MILITARY_IRAN_KEYWORDS
from analysis.date_utils import day_only


def count_mentions_per_source(items):
    """Return per-category and per-source mention counts.

    {"categories": {category: count}, "sources": {source: count}, "total": int}
    """
    categories = Counter()
    sources = Counter()
    for item in items:
        categories[item.get("category", "unknown")] += 1
        sources[item.get("source", "unknown")] += 1
    return {
        "categories": dict(categories),
        "sources": dict(sources),
        "total": len(items),
    }


def group_mentions_by_date(items):
    """Return a date series per category for the over-time chart.

    {"dates": [iso date], "categories": {category: [counts]}}
    Dates are the item's statement date (date only, no time).
    """
    by_date = {}
    for item in items:
        raw = item.get("date", "")
        day = day_only(raw)
        if day is None:
            continue
        by_date.setdefault(day, Counter())[item.get("category", "unknown")] += 1

    dates = sorted(by_date.keys())
    categories = sorted({item.get("category", "unknown") for item in items})

    series = {}
    for cat in categories:
        series[cat] = [by_date[d].get(cat, 0) for d in dates]

    return {"dates": dates, "categories": series}


def extract_iran_mentions(items):
    """Return military items whose text mentions an Iran keyword, newest first."""
    out = []
    for item in items:
        if item.get("category") != "military":
            continue
        text = f"{item.get('title', '')} {item.get('description', '')}"
        if _matches_keywords(text, MILITARY_IRAN_KEYWORDS):
            out.append(item)
    out.sort(key=lambda it: it.get("date", ""), reverse=True)
    return out


def _matches_keywords(text, keywords):
    lowered = text.lower()
    return any(k.lower() in lowered for k in keywords)
