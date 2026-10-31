"""Shared date helpers for analysis modules."""

from datetime import datetime


def day_only(iso):
    """Return 'YYYY-MM-DD' from an ISO timestamp, or None if unparseable."""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).date().isoformat()
    except ValueError:
        return None
