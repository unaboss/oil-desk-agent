"""Fetch public statements by oil-relevant US officials and the military.

Mirror sources (Truth Social has no public post API):
- Google News RSS: one query per watched official / military subject.
- Official agency RSS feeds: DOE, DoD, State press releases.

Every feed is fetched independently and wrapped in try/except — a dead feed
never raises; the result keeps whatever feeds succeeded.
"""

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from data.cache import get, set
from data.statement_store import append_new, load_all, statement_key
from config import (
    AGENCY_FEEDS, GOOGLE_NEWS_RSS, OFFICIAL_KEYWORDS, MILITARY_IRAN_KEYWORDS,
    OFFICIALS_WATCH, MILITARY_WATCH,
    CACHE_TTL_STATEMENTS,
)

CACHE_KEY = "statements_officials"

TIMEOUT_SECONDS = 15
MAX_ITEMS_PER_FEED = 50

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(text):
    """Strip HTML tags and collapse whitespace from an RSS description."""
    if not text:
        return ""
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _parse_date(value):
    """Parse an RFC-2822 pubDate into an ISO UTC string; '' on failure."""
    if not value:
        return ""
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def _fetch_and_parse_rss(url):
    """Return a list of {title, link, source, category, date, description}.

    Returns [] on any failure (network, bad status, malformed XML).
    """
    try:
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception:
        return []

    items = []
    for node in root.iter("item"):
        title = node.findtext("title", default="") or ""
        link = node.findtext("link", default="") or ""
        desc = _strip_html(node.findtext("description", default=""))
        date = _parse_date(node.findtext("pubDate", default=""))
        items.append({"title": title, "link": link, "description": desc, "date": date})
    return items[:MAX_ITEMS_PER_FEED]


def _matches_keywords(text, keywords):
    lowered = text.lower()
    return any(k.lower() in lowered for k in keywords)


def _filter_items(items, category):
    """Apply the category-specific relevance filter.

    Officials / agency non-military items: keep only when an oil keyword matches.
    Military items: keep only when they mention an Iran keyword.
    """
    if category == "military":
        keywords = MILITARY_IRAN_KEYWORDS
    else:
        keywords = OFFICIAL_KEYWORDS
    return [it for it in items if _matches_keywords(
        it["title"] + " " + it["description"], keywords)]


def _fetch_source_items(source_name, category, url):
    """Fetch one feed and return items tagged with source/category, filtered."""
    feed_items = _fetch_and_parse_rss(url)
    for it in feed_items:
        it["source"] = source_name
        it["category"] = category
    return _filter_items(feed_items, category)


def _google_news_url(query):
    return GOOGLE_NEWS_RSS.format(q=requests.utils.quote(query))


def get_officials_statements():
    """Return tracked officials/military statements, newest first.

    On a stale cache the live feeds are fetched, filtered and appended to the
    permanent store (data/officials_statements.csv). The current-window items
    are cached; the accumulated store is always loaded fresh so it stays
    current even on cache hits.
    """
    cached, _, _, stale = get(CACHE_KEY)
    if cached is not None and not stale:
        return {
            "items": cached["items"],
            "store_items": load_all(),
            "available": cached["available"],
            "fetched_at": cached["fetched_at"],
        }

    items = []
    for watch in OFFICIALS_WATCH:
        items.extend(_fetch_source_items(
            watch["name"], watch["category"], _google_news_url(watch["query"])))
    for watch in MILITARY_WATCH:
        items.extend(_fetch_source_items(
            watch["name"], watch["category"], _google_news_url(watch["query"])))
    for feed in AGENCY_FEEDS:
        items.extend(_fetch_source_items(feed["name"], feed["category"], feed["url"]))

    # Dedupe by (title, source) using the store's canonical key, newest first.
    seen = {}
    for it in items:
        key = statement_key(it["title"], it["source"])
        if key not in seen:
            seen[key] = it
    unique = list(seen.values())
    unique.sort(key=lambda it: it["date"], reverse=True)

    append_new(unique)

    fetched_at = datetime.now(timezone.utc).isoformat()
    result = {
        "items": unique,
        "store_items": load_all(),
        "available": len(unique) > 0,
        "fetched_at": fetched_at,
    }
    set(CACHE_KEY, {
        "items": unique,
        "available": len(unique) > 0,
        "fetched_at": fetched_at,
    }, CACHE_TTL_STATEMENTS, last_updated=fetched_at)
    return result
