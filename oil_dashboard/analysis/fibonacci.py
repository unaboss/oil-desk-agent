import pandas as pd


FIB_RATIOS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIB_LABELS = ["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"]


def get_level_prices(swing_high, swing_low, trend):
    span = swing_high - swing_low
    levels = {}
    for label, ratio in zip(FIB_LABELS, FIB_RATIOS):
        if trend == "uptrend":
            levels[label] = round(swing_high - span * ratio, 2)
        else:
            levels[label] = round(swing_low + span * ratio, 2)
    return levels


def find_swing(wti_close, lookback=50):
    if not wti_close or len(wti_close) < 5:
        return None
    n = min(lookback, len(wti_close))
    recent = wti_close[-n:]
    swing_high = max(recent)
    swing_low = min(recent)
    high_idx = recent.index(swing_high)
    low_idx = recent.index(swing_low)
    trend = "uptrend" if high_idx > low_idx else "downtrend"
    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "range": round(swing_high - swing_low, 2),
        "trend": trend,
        "levels": get_level_prices(swing_high, swing_low, trend),
    }


def find_nearest_level(current_price, levels):
    nearest = None
    nearest_label = None
    min_dist = None
    for label, price in levels.items():
        dist = abs(current_price - price)
        if min_dist is None or dist < min_dist:
            min_dist = dist
            nearest = price
            nearest_label = label
    return nearest_label, nearest, round(min_dist, 2)


def is_price_in_zone(current_price, swing_high, swing_low, trend):
    """Return which fib-ratio-range price sits in (e.g. 'between 38.2% and 50%')."""
    levels = get_level_prices(swing_high, swing_low, trend)
    sorted_levels = list(levels.items())
    for i in range(len(sorted_levels) - 1):
        label_lo, price_lo = sorted_levels[i]
        label_hi, price_hi = sorted_levels[i + 1]
        lo = min(price_lo, price_hi)
        hi = max(price_lo, price_hi)
        if lo <= current_price <= hi:
            if trend == "uptrend":
                return f"between {label_hi} and {label_lo}"
            else:
                return f"between {label_lo} and {label_hi}"
    return "outside extreme levels"
