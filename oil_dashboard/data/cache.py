"""Unified cache layer with staleness tracking per source."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from config import DATA_DIR

_cache = {}

def _cache_file(key):
    return DATA_DIR / f"_cache_{key}.json"

def get(key):
    """Return (data, last_updated_dt, next_update_dt, is_stale) or (None, None, None, True)."""
    if key in _cache:
        entry = _cache[key]
        age = time.time() - entry["fetched_at"]
        is_stale = age > entry["ttl"]
        return entry["data"], entry["last_updated"], entry["next_update"], is_stale

    cf = _cache_file(key)
    if cf.exists():
        try:
            entry = json.loads(cf.read_text())
            _cache[key] = entry
            age = time.time() - entry["fetched_at"]
            is_stale = age > entry["ttl"]
            return entry["data"], entry["last_updated"], entry["next_update"], is_stale
        except Exception:
            pass
    return None, None, None, True

def set(key, data, ttl, last_updated=None, next_update=None):
    """Store data with TTL in seconds."""
    now = time.time()
    entry = {
        "data": data,
        "fetched_at": now,
        "ttl": ttl,
        "last_updated": last_updated or datetime.now(timezone.utc).isoformat(),
        "next_update": next_update or "",
    }
    _cache[key] = entry
    try:
        _cache_file(key).write_text(json.dumps(entry, default=str))
    except Exception:
        pass

def invalidate(key):
    _cache.pop(key, None)
    cf = _cache_file(key)
    if cf.exists():
        cf.unlink()

def invalidate_all():
    _cache.clear()
    for f in DATA_DIR.glob("_cache_*.json"):
        f.unlink()

def status_text(key, label=""):
    """Return a human-readable cache status line."""
    data, last_upd, next_upd, stale = get(key)
    if last_upd is None:
        return f"{label}: No data" if label else "No data"
    status = "STALE" if stale else "fresh"
    line = f"{label}: {status} ({last_upd[:16]})" if label else f"{status} ({last_upd[:16]})"
    if next_upd:
        line += f" | next update: {next_upd[:16]}"
    return line
