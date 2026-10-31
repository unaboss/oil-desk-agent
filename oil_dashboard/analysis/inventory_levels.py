"""Inventory level metrics — weeks of supply and SPR depletion projection.

Pure functions over the EIA weekly inventory series (newest-first). No I/O,
fully unit-testable.
"""

import numpy as np

SPR_FLOOR_MBBL = 400.0          # reference "too low" floor (million bbl)
SPR_FULL_MBBL = 714.0           # nominal SPR capacity
DAYS_PER_WEEK = 7.0
WEEKS_PER_YEAR = 52.0


def weeks_of_supply(crude_stocks_mbbl, crude_inputs_mbpd):
    """Weeks of crude cover = stocks / inputs.

    crude_stocks_mbbl: latest commercial crude stocks in million bbl.
    crude_inputs_mbpd: latest refinery crude inputs in million bbl/day.
    Returns None when either input is missing or non-positive.
    """
    if not crude_stocks_mbbl or not crude_inputs_mbpd:
        return None
    if crude_stocks_mbbl <= 0 or crude_inputs_mbpd <= 0:
        return None
    return round(crude_stocks_mbbl / crude_inputs_mbpd / DAYS_PER_WEEK, 1)


def _avg_weekly_change(values):
    """Mean week-over-week change (positive = rising), newest-first input."""
    clean = [v for v in values if v is not None and not np.isnan(v)]
    if len(clean) < 2:
        return None
    return sum(clean[i] - clean[i + 1] for i in range(len(clean) - 1)) / (len(clean) - 1)


def spr_projection(spr_levels_mbbl, floor_mbbl=SPR_FLOOR_MBBL, full_mbbl=SPR_FULL_MBBL):
    """Project SPR depletion or refill timeline.

    spr_levels_mbbl: SPR level series in million bbl (newest-first).
    Returns:
      {"mode": "depleting"|"refilling"|"flat"|"no_data", "rate_mbbl_per_wk",
       "weeks_to_floor": float|None, "weeks_to_full": float|None}
    """
    if not spr_levels_mbbl or len([v for v in spr_levels_mbbl if v is not None]) < 2:
        return {"mode": "no_data", "rate_mbbl_per_wk": None,
                "weeks_to_floor": None, "weeks_to_full": None}

    latest = spr_levels_mbbl[0]
    rate = _avg_weekly_change(spr_levels_mbbl)

    if rate is None:
        return {"mode": "no_data", "rate_mbbl_per_wk": None,
                "weeks_to_floor": None, "weeks_to_full": None}

    tol = 1e-6
    if abs(rate) < tol:
        return {"mode": "flat", "rate_mbbl_per_wk": round(rate, 2),
                "weeks_to_floor": None, "weeks_to_full": None}

    if rate < 0:
        weeks_to_floor = (latest - floor_mbbl) / abs(rate) if latest > floor_mbbl else 0.0
        return {"mode": "depleting", "rate_mbbl_per_wk": round(rate, 2),
                "weeks_to_floor": round(weeks_to_floor, 1), "weeks_to_full": None}

    weeks_to_full = (full_mbbl - latest) / rate if latest < full_mbbl else 0.0
    return {"mode": "refilling", "rate_mbbl_per_wk": round(rate, 2),
            "weeks_to_floor": None, "weeks_to_full": round(weeks_to_full, 1)}


def mbbl_to_million_bbl(values_thousand_bbl):
    """Convert a thousand-bbl series to million bbl, dropping None/NaN."""
    out = []
    for v in values_thousand_bbl:
        if v is None or np.isnan(v):
            continue
        out.append(v / 1000.0)
    return out
