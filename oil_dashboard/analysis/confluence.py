"""Confluence scoring engine — 6-signal composite score for WTI directional bias.

Signals:
  1. Volume: WTI volume above 20d MA (+1) or below (-1)
  2. COT: Managed Money positioning NOT at extreme (+1) or at extreme (-1)
  3. Inventories: EIA crude drawing (+1) or building (-1)
  4. Crack: RBOB-WTI crack widening (+1) or narrowing (-1)
  5. DXY: Dollar weakening (+1 for oil) or strengthening (-1)
  6. Curve: Backwardation (+1) or contango (-1)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone

from config import (
    CONFLUENCE_SIGNALS, SIGNAL_WEIGHTS,
    BULLISH_THRESHOLD, BEARISH_THRESHOLD,
    VOLUME_MA_DAYS,
)


def compute_confluence(market_data, eia_data, cot_data, latest_only=True):
    """
    Compute confluence score per day.

    market_data: dict from fetcher_yfinance.get_all_market_data()
    eia_data: dict from fetcher_eia.get_all_eia_data()
    cot_data: dict from fetcher_cot.get_cot_data()

    Returns:
        If latest_only=True: a single score dict for most recent day.
        If latest_only=False: list of score dicts per day.
    """
    scores = []

    wti = market_data.get("wti") or {}
    vol = market_data.get("volume_anomaly") or {}
    crack = market_data.get("crack") or {}
    curve = market_data.get("curve") or {}
    dxy = market_data.get("dxy") or {}
    crude_inv = (eia_data.get("crude") or {}) if eia_data else {}

    wti_dates = wti.get("dates", [])
    wti_close = wti.get("close", [])

    if not wti_dates:
        empty = _empty_score(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        return [empty] if not latest_only else empty

    for i in range(len(wti_dates)):
        day_score = {
            "date": wti_dates[i],
            "signals": {},
            "score": 0,
            "direction": "neutral",
            "wti_close": wti_close[i] if i < len(wti_close) else None,
        }

        # 1. Volume
        vol_ratio = (vol.get("volume_ratio") or [None])[i] if i < len(vol.get("volume_ratio", [])) else None
        if vol_ratio is not None and not np.isnan(vol_ratio):
            day_score["signals"]["volume"] = 1 if vol_ratio > 1.0 else -1
        else:
            day_score["signals"]["volume"] = 0

        # 2. COT — same value for all days (weekly snapshot)
        if cot_data and cot_data.get("net_long") is not None:
            day_score["signals"]["cot"] = 0  # Neutral by default; extreme flag set by caller
        else:
            day_score["signals"]["cot"] = 0

        # 3. Inventories — map closest EIA week
        eia_dates = crude_inv.get("dates", [])
        eia_changes = crude_inv.get("changes", [])
        day_score["signals"]["inventories"] = 0
        if eia_dates and eia_changes:
            pd_date = pd.to_datetime(wti_dates[i])
            best_j = None
            best_diff = None
            for j, ed in enumerate(eia_dates):
                ed_dt = pd.to_datetime(ed)
                diff = abs((pd_date - ed_dt).days)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_j = j
            if best_j is not None and best_diff < 10 and best_j < len(eia_changes):
                ch = eia_changes[best_j]
                if ch is not None and not np.isnan(ch):
                    day_score["signals"]["inventories"] = 1 if ch < 0 else -1

        # 4. Crack spread
        crack_dates = crack.get("dates", [])
        crack_vals = crack.get("crack", [])
        crack_ma = crack.get("crack_5ma", [])
        day_score["signals"]["crack"] = 0
        if crack_dates and crack_vals:
            for k, cd in enumerate(crack_dates):
                if cd == wti_dates[i] and k < len(crack_vals) and k < len(crack_ma):
                    if not np.isnan(crack_vals[k]) and not np.isnan(crack_ma[k]):
                        day_score["signals"]["crack"] = 1 if crack_vals[k] > crack_ma[k] else -1
                    break

        # 5. DXY
        dxy_dates = dxy.get("dates", [])
        dxy_close = dxy.get("close", [])
        day_score["signals"]["dxy"] = 0
        if dxy_dates and dxy_close and i > 0:
            pd_date = pd.to_datetime(wti_dates[i])
            prev_idx = None
            for k, dd in enumerate(dxy_dates):
                if pd.to_datetime(dd) <= pd_date:
                    prev_idx = k
                else:
                    break
            if prev_idx is not None and prev_idx > 0 and prev_idx < len(dxy_close):
                prev_val = dxy_close[prev_idx - 1]
                curr_val = dxy_close[prev_idx]
                if prev_val and curr_val:
                    dxy_pct = (curr_val - prev_val) / prev_val
                    day_score["signals"]["dxy"] = 1 if dxy_pct < 0 else -1  # DXY down = oil up

        # 6. Curve
        curve_dates = curve.get("spread_dates", curve.get("dates", []))
        spread_vals = curve.get("brent_wti_spread", [])
        day_score["signals"]["curve"] = 0
        if curve_dates and spread_vals:
            for k, cd in enumerate(curve_dates):
                if cd == wti_dates[i] and k < len(spread_vals):
                    val = spread_vals[k]
                    if val is not None and not np.isnan(val):
                        day_score["signals"]["curve"] = 1 if val > 0 else -1
                    break

        # Composite
        total = sum(day_score["signals"].get(s, 0) * SIGNAL_WEIGHTS.get(s, 1) for s in CONFLUENCE_SIGNALS)
        day_score["score"] = total
        if total >= BULLISH_THRESHOLD:
            day_score["direction"] = "bullish"
        elif total <= BEARISH_THRESHOLD:
            day_score["direction"] = "bearish"
        else:
            day_score["direction"] = "neutral"

        scores.append(day_score)

    if latest_only and scores:
        return scores[-1]
    return scores


def _empty_score(date_str):
    return {
        "date": date_str,
        "signals": {s: 0 for s in CONFLUENCE_SIGNALS},
        "score": 0,
        "direction": "neutral",
        "wti_close": None,
    }


def compute_cot_extreme(cot_data, historical_pct=50):
    """Determine if current COT positioning is at extreme.
    Since we only have latest snapshot, use a heuristic:
    net_long > large positive or < large negative = extreme."""
    if not cot_data or cot_data.get("net_long") is None:
        return {"is_extreme": False, "side": "", "net_long": None}

    nl = cot_data["net_long"]
    is_extreme = abs(nl) > 100000  # heuristic threshold
    side = "long" if nl > 0 else "short"
    return {"is_extreme": is_extreme, "side": side, "net_long": nl}


def compute_total_score(market_data, eia_data, cot_data):
    """Return the latest confluence total + direction, COT extreme included.

    Single source of truth for the composite score so the sidebar and the
    Confluence tab always agree. Uses the latest daily score then applies the
    COT extreme override (extreme = -1, non-extreme = +1 when data exists).
    """
    score = compute_confluence(market_data, eia_data, cot_data, latest_only=True)
    if cot_data and cot_data.get("net_long") is not None:
        extreme = compute_cot_extreme(cot_data)
        score["signals"]["cot"] = -1 if extreme.get("is_extreme") else 1
    total = sum(score["signals"].get(s, 0) for s in CONFLUENCE_SIGNALS)
    if total >= BULLISH_THRESHOLD:
        direction = "bullish"
    elif total <= BEARISH_THRESHOLD:
        direction = "bearish"
    else:
        direction = "neutral"
    return {"total": total, "direction": direction, "signals": score["signals"]}
