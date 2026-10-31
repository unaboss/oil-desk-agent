"""Market view from the Oil Dashboard's confluence engine and signal audit."""
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DASH = Path(__file__).resolve().parent.parent / "oil_dashboard"
if str(DASH) not in sys.path:
    sys.path.insert(0, str(DASH))


def _clean(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _hit_fraction(x):
    """The dashboard's audit reports hit rate in percent (0-100); the agent uses 0-1."""
    v = _clean(x)
    if v is None:
        return None
    return v / 100 if v > 1 else v


def build_view(market_data, eia_data, cot_data):
    """Pure function: turn raw dashboard data into the agent's view (testable offline)."""
    from analysis.confluence import compute_total_score
    from analysis.audit import compute_audit

    score = compute_total_score(market_data, eia_data, cot_data)
    try:
        audit = compute_audit(market_data, eia_data, cot_data)
    except Exception:  # audit needs enough history; never block a decision on it
        audit = {"hit_rate": None, "total_signals": 0}

    wti = market_data.get("wti") or {}
    closes = [c for c in (_clean(v) for v in wti.get("close", [])) if c is not None]
    price = closes[-1] if closes else None
    chg_5d = (closes[-1] / closes[-6] - 1) if len(closes) >= 6 else None
    ovx = market_data.get("ovx") or {}
    ovx_close = [c for c in (_clean(v) for v in ovx.get("close", [])) if c is not None]

    return {
        "asof": (wti.get("dates") or [None])[-1],
        "wti_price": price,
        "wti_change_5d": chg_5d,
        "oil_volatility_ovx": ovx_close[-1] if ovx_close else None,
        "confluence_total": score["total"],
        "confluence_direction": score["direction"],
        "signals": score["signals"],
        "audit_hit_rate": _hit_fraction(audit.get("hit_rate")),
        "audit_signals": audit.get("total_signals", 0),
    }


def fetch_view(lookback_days=200):
    """Fetch live data with the dashboard's own fetchers (yfinance, EIA, CFTC)."""
    from data.fetcher_yfinance import get_all_market_data
    from data.fetcher_eia import get_all_eia_data
    from data.fetcher_cot import get_cot_data

    end = datetime.now(timezone.utc)
    start = (end - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")
    market = get_all_market_data(start=start, end=end_s)
    try:
        eia = get_all_eia_data(start=start, end=end_s)
    except Exception:
        eia = {}
    try:
        cot = get_cot_data()
    except Exception:
        cot = {}
    return build_view(market, eia, cot)
