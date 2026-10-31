"""Fetch EIA weekly petroleum data via API v2."""

import time

import requests
from datetime import datetime, timezone

from data.cache import get, set
from config import (
    EIA_API_KEY, EIA_BASE,
    DEFAULT_START, DEFAULT_END,
    CACHE_TTL_EIA,
    next_eia_release,
)

CACHE_KEY_CRUDE = "eia_crude"
CACHE_KEY_GASOLINE = "eia_gasoline"
CACHE_KEY_DISTILLATE = "eia_distillate"
CACHE_KEY_RETAIL = "eia_retail_gas"
CACHE_KEY_SPR = "eia_spr"


def _eia_weekly(route, facets, data_cols, cache_key, start=DEFAULT_START, end=DEFAULT_END):
    data, _, _, stale = get(cache_key)
    if data is not None and not stale:
        return data

    url = f"{EIA_BASE}{route}/data"
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "weekly",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 5000,
    }
    for i, col in enumerate(data_cols):
        params[f"data[{i}]"] = col
    for k, v in facets.items():
        params[f"facets[{k}][]"] = v

    try:
        resp = None
        for attempt in range(3):
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                break
            # EIA rate-limits with 403/429 and occasional 5xx; retry briefly.
            time.sleep(0.5 * (attempt + 1))
        if resp is None or resp.status_code != 200:
            return None
        js = resp.json()
    except Exception:
        return None

    if "response" not in js or "data" not in js["response"]:
        return None

    rows = js["response"]["data"]

    seen = {}
    for r in rows:
        period = r["period"]
        if period not in seen:
            seen[period] = float(r["value"]) if r.get("value") else None

    periods = sorted(seen.keys(), reverse=True)
    values = [seen[p] for p in periods]

    result = {"dates": periods, "values": values}

    next_upd = next_eia_release().isoformat()
    last_upd = datetime.now(timezone.utc).isoformat()
    set(cache_key, result, CACHE_TTL_EIA, last_updated=last_upd, next_update=next_upd)
    return result


def get_crude_stocks(start=DEFAULT_START, end=DEFAULT_END):
    """Weekly U.S. crude oil commercial ending stocks excl SPR (thousand barrels).
    Series WCESTUS1 = Ending Stocks excl SPR of Crude Oil."""
    return _eia_weekly(
        route="/petroleum/stoc/wstk",
        facets={"duoarea": "NUS", "product": "EPC0", "series": "WCESTUS1"},
        data_cols=["value"],
        cache_key=CACHE_KEY_CRUDE,
        start=start, end=end,
    )


def get_gasoline_stocks(start=DEFAULT_START, end=DEFAULT_END):
    """Weekly total gasoline ending stocks (thousand barrels).
    Series WGTSTUS1 = Ending Stocks of Total Gasoline."""
    return _eia_weekly(
        route="/petroleum/stoc/wstk",
        facets={"duoarea": "NUS", "product": "EPM0", "series": "WGTSTUS1"},
        data_cols=["value"],
        cache_key=CACHE_KEY_GASOLINE,
        start=start, end=end,
    )


def get_distillate_stocks(start=DEFAULT_START, end=DEFAULT_END):
    """Weekly distillate fuel oil ending stocks (thousand barrels).
    Series WDISTUS1 = Ending Stocks of Distillate Fuel Oil."""
    return _eia_weekly(
        route="/petroleum/stoc/wstk",
        facets={"duoarea": "NUS", "product": "EPD0", "series": "WDISTUS1"},
        data_cols=["value"],
        cache_key=CACHE_KEY_DISTILLATE,
        start=start, end=end,
    )


def get_retail_gas_price(start=DEFAULT_START, end=DEFAULT_END):
    """Weekly U.S. regular all formulations retail gasoline price ($/gal)."""
    return _eia_weekly(
        route="/petroleum/pri/gnd",
        facets={"duoarea": "NUS", "product": "EPMR"},
        data_cols=["value"],
        cache_key=CACHE_KEY_RETAIL,
        start=start, end=end,
    )


def get_spr_stocks(start=DEFAULT_START, end=DEFAULT_END):
    """Weekly U.S. Strategic Petroleum Reserve crude oil ending stocks (thousand barrels).
    Series WCRSTUS1 = Ending Stocks of Crude Oil in SPR."""
    return _eia_weekly(
        route="/petroleum/stoc/wstk",
        facets={"duoarea": "NUS", "product": "EPC0", "series": "WCRSTUS1"},
        data_cols=["value"],
        cache_key=CACHE_KEY_SPR,
        start=start, end=end,
    )


def get_weekly_changes(data_dict):
    """Compute week-over-week changes for inventory data (newest-first).

    The series is sorted newest-first (periods descending), so change[i] =
    values[i] - values[i+1]. The oldest row has no prior week -> NaN.
    """
    if data_dict is None:
        return None
    vals = data_dict["values"]
    changes = []
    for i in range(len(vals) - 1):
        cur, prev = vals[i], vals[i + 1]
        if cur is None or prev is None:
            changes.append(float("nan"))
        else:
            changes.append(cur - prev)
    changes.append(float("nan"))
    return {
        "dates": data_dict["dates"],
        "values": vals,
        "changes": changes,
    }


def get_all_eia_data(start=DEFAULT_START, end=DEFAULT_END):
    spr_raw = get_spr_stocks(start, end)
    return {
        "crude": get_weekly_changes(get_crude_stocks(start, end)),
        "gasoline": get_weekly_changes(get_gasoline_stocks(start, end)),
        "distillate": get_weekly_changes(get_distillate_stocks(start, end)),
        "retail_gas": get_retail_gas_price(start, end),
        "spr": get_weekly_changes(spr_raw),
        "spr_level": spr_raw,
    }
