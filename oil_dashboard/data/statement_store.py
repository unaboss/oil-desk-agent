"""Persistent store for captured officials & military statements.

Statements are appended to a CSV on each fetch and never overwritten, so the
store accumulates a permanent record of every statement ever captured. Dedupe
is by (title, source) — the same key the fetcher uses.
"""

import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR

STORAGE_CSV = DATA_DIR / "officials_statements.csv"

COLUMNS = ["date", "category", "source", "title", "link", "description", "first_seen_at"]


def load_all():
    """Return all captured statements as a list of dicts (newest first)."""
    rows = _read_rows()
    rows.sort(key=lambda it: it.get("date", ""), reverse=True)
    return rows


def append_new(items):
    """Persist any items not already stored (dedupe by title+source).

    Returns the number of new statements appended. Atomic write (temp file +
    rename) so a crash never corrupts the store.
    """
    existing = _read_rows()
    seen = {statement_key(row["title"], row["source"]) for row in existing}

    now = datetime.now(timezone.utc).isoformat()
    new_rows = []
    for item in items:
        key = statement_key(item.get("title", ""), item.get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        new_rows.append({
            "date": item.get("date", ""),
            "category": item.get("category", ""),
            "source": item.get("source", ""),
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "description": item.get("description", ""),
            "first_seen_at": now,
        })

    if not new_rows:
        return 0

    all_rows = existing + new_rows
    _write_atomic(all_rows)
    return len(new_rows)


def statement_key(title, source):
    """Stable dedupe key for a statement (shared by fetcher and store)."""
    return title.lower().strip(), source.lower().strip()


def _read_rows():
    if not STORAGE_CSV.exists():
        return []
    with STORAGE_CSV.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _write_atomic(rows):
    STORAGE_CSV.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(STORAGE_CSV.parent), prefix="_statements_tmp_", suffix=".csv")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, STORAGE_CSV)
    except Exception:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        raise
