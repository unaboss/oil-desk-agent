import numpy as np


def _four_week_avg(values):
    clean = [v for v in values if v is not None and not np.isnan(v)]
    if len(clean) < 2:
        return None
    n = min(5, len(clean))
    recent = clean[:n]
    return sum(recent[1:]) / len(recent[1:])


def _product_analysis(data, product_label, is_spr=False):
    if not data or not data.get("changes"):
        return _empty_product()
    ch = data["changes"]
    if not ch:
        return _empty_product()
    current = ch[0]
    avg_4wk = _four_week_avg(ch)
    if current is None or np.isnan(current) or avg_4wk is None:
        return _empty_product()
    deviation = round(current - avg_4wk, 2)
    if abs(deviation) < 0.1:
        signal = 0
        trend_label = "In line with trend"
    else:
        is_draw = current < 0
        bigger = abs(current) > abs(avg_4wk)
        if is_spr:
            signal = -1 if current < 0 else 1
            if current < 0:
                trend_label = "Accelerating release" if bigger else "Decelerating release"
            else:
                trend_label = "Accelerating refill" if bigger else "Decelerating refill"
        elif is_draw:
            signal = -1 if current > avg_4wk else 1  # bigger draw = more bullish
            trend_label = "Accelerating draw" if bigger else "Decelerating draw"
        else:
            signal = -1 if current > avg_4wk else 1
            trend_label = "Accelerating build" if bigger else "Decelerating build"
    return {
        "current_change": round(current, 2),
        "four_week_avg": round(avg_4wk, 2),
        "deviation": deviation,
        "signal": signal,
        "trend_label": trend_label,
    }


def _empty_product():
    return {"current_change": None, "four_week_avg": None, "deviation": None, "signal": 0, "trend_label": "Insufficient data"}


def compute_eia_analysis(eia_data):
    if not eia_data:
        return {"by_product": {}, "composite_score": 0, "bullish_products": [], "bearish_products": [], "strongest_reading": None}
    crude = _product_analysis(eia_data.get("crude"), "crude")
    gasoline = _product_analysis(eia_data.get("gasoline"), "gasoline")
    distillate = _product_analysis(eia_data.get("distillate"), "distillate")
    spr = _product_analysis(eia_data.get("spr"), "spr", is_spr=True)
    products = {"crude": crude, "gasoline": gasoline, "distillate": distillate, "spr": spr}
    composite = sum(p["signal"] for p in products.values())
    bullish = [k for k, v in products.items() if v["signal"] == 1]
    bearish = [k for k, v in products.items() if v["signal"] == -1]
    strongest = None
    best_dev = 0
    for k, v in products.items():
        if v["deviation"] is not None and abs(v["deviation"]) > best_dev:
            best_dev = abs(v["deviation"])
            strongest = k
    return {
        "by_product": products,
        "composite_score": composite,
        "bullish_products": bullish,
        "bearish_products": bearish,
        "strongest_reading": strongest,
    }
