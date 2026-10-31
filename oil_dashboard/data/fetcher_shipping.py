"""Shipping/tanker tracking data placeholder — plug-in for future vessel AIS data.

When you source shipping data (Vortexa, Kpler, MarineTraffic, etc.),
drop a CSV at data/shipping_input.csv with columns:
    date, volume_mbbl, origin, destination, eta, vessel_count
"""

import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from data.cache import get, set
from config import DATA_DIR, CACHE_TTL_YFINANCE_MARKET

CACHE_KEY = "shipping"
SHIPPING_FILE = DATA_DIR / "shipping_input.csv"


def get_shipping_data():
    """Load shipping data from CSV if available. Returns None if no file."""
    data, _, _, stale = get(CACHE_KEY)
    if data is not None and not stale:
        return data

    if not SHIPPING_FILE.exists():
        result = {"available": False, "message": "No shipping_input.csv found"}
        last_upd = datetime.now(timezone.utc).isoformat()
        set(CACHE_KEY, result, CACHE_TTL_YFINANCE_MARKET, last_updated=last_upd)
        return result

    try:
        df = pd.read_csv(SHIPPING_FILE)
        df["date"] = pd.to_datetime(df["date"])

        result = {
            "available": True,
            "dates": [str(d.date()) for d in df["date"]],
            "volumes": df["volume_mbbl"].tolist() if "volume_mbbl" in df.columns else [],
            "vessel_count": df["vessel_count"].tolist() if "vessel_count" in df.columns else [],
            "origins": df["origin"].tolist() if "origin" in df.columns else [],
            "destinations": df["destination"].tolist() if "destination" in df.columns else [],
            "etas": [str(d) for d in df["eta"].tolist()] if "eta" in df.columns else [],
            "total_in_transit": df["volume_mbbl"].sum() if "volume_mbbl" in df.columns else 0,
        }
    except Exception:
        result = {"available": False, "message": "Error reading shipping_input.csv"}

    last_upd = datetime.now(timezone.utc).isoformat()
    set(CACHE_KEY, result, CACHE_TTL_YFINANCE_MARKET * 6, last_updated=last_upd)
    return result
