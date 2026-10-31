from analysis.fibonacci import (
    get_level_prices, find_swing, find_nearest_level, is_price_in_zone,
    FIB_LABELS,
)


def test_get_level_prices_uptrend():
    levels = get_level_prices(100, 80, "uptrend")
    assert levels["0%"] == 100
    assert levels["100%"] == 80
    assert levels["50%"] == 90
    assert levels["61.8%"] == 87.64


def test_get_level_prices_downtrend():
    levels = get_level_prices(100, 80, "downtrend")
    assert levels["0%"] == 80
    assert levels["100%"] == 100
    assert levels["50%"] == 90
    assert levels["61.8%"] == 92.36


def test_get_level_prices_has_all_labels():
    levels = get_level_prices(100, 80, "uptrend")
    assert set(levels.keys()) == set(FIB_LABELS)


def test_find_swing_uptrend():
    prices = [60, 62, 65, 63, 61, 64, 66, 68, 67, 69, 70, 69, 68]
    swing = find_swing(prices, lookback=10)
    assert swing["trend"] == "uptrend"
    assert swing["swing_low"] == 61
    assert swing["swing_high"] == 70


def test_find_swing_downtrend():
    prices = [70, 68, 66, 64, 62, 60, 65, 63, 61, 59, 57]
    swing = find_swing(prices, lookback=10)
    assert swing["trend"] == "downtrend"


def test_find_swing_insufficient_data():
    assert find_swing([50, 51], 5) is None


def test_find_nearest_level():
    levels = {"38.2%": 92, "50%": 90, "61.8%": 88}
    label, price, dist = find_nearest_level(89.5, levels)
    assert label == "50%"
    assert price == 90
    assert dist == 0.5


def test_is_price_in_zone_uptrend():
    zone = is_price_in_zone(89, 100, 80, "uptrend")
    assert "61.8" in zone or "50" in zone or "38.2" in zone


def test_swing_has_expected_keys():
    prices = [60, 62, 65, 63, 61, 64, 66, 68, 67, 69, 70, 69, 68]
    swing = find_swing(prices, lookback=10)
    assert set(swing.keys()) == {"swing_high", "swing_low", "range", "trend", "levels"}
    assert swing["range"] == 9
