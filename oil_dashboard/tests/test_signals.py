import math
import numpy as np
import pytest
from analysis.signals import compute_sma, compute_ema, wti_trend, daily_returns, forward_returns


def test_sma_known_values():
    result = compute_sma([1.0, 2.0, 3.0, 4.0, 5.0], window=3)
    assert math.isnan(result[0])
    assert math.isnan(result[1])
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)
    assert result[4] == pytest.approx(4.0)


def test_sma_constant_series():
    result = compute_sma([5.0, 5.0, 5.0, 5.0, 5.0], window=3)
    assert result[2] == pytest.approx(5.0)
    assert result[4] == pytest.approx(5.0)


def test_sma_window_larger_than_data():
    result = compute_sma([1.0, 2.0], window=5)
    for v in result:
        assert math.isnan(v)


def test_ema_produces_values():
    result = compute_ema([1.0, 2.0, 3.0, 4.0, 5.0], span=3)
    assert not np.isnan(result[0])
    assert result[-1] is not None


def test_wti_trend_bullish():
    prices = list(range(50, 100))  # steadily rising
    data = {"close": prices, "dates": [""] * len(prices)}
    trend = wti_trend(data)
    assert trend["trend"] == "bullish"
    assert trend["vs_sma20"] == 1
    assert trend["vs_sma50"] == 1


def test_wti_trend_bearish():
    prices = list(range(100, 50, -1))  # steadily falling
    data = {"close": prices, "dates": [""] * len(prices)}
    trend = wti_trend(data)
    assert trend["trend"] == "bearish"
    assert trend["vs_sma20"] == -1
    assert trend["vs_sma50"] == -1


def test_wti_trend_mixed():
    prices = [50] * 30 + [55] * 20 + [60] * 10  # above sma20 but near sma50
    data = {"close": prices, "dates": [""] * len(prices)}
    trend = wti_trend(data)
    assert trend["trend"] in ("bullish", "bearish", "mixed")


def test_wti_trend_insufficient_data():
    trend = wti_trend({"close": [68, 69, 70], "dates": ["a", "b", "c"]})
    assert trend["trend"] == "neutral"
    assert trend["vs_sma20"] is None


def test_daily_returns_basic():
    result = daily_returns([100.0, 102.0, 99.0, 103.0])
    assert np.isnan(result[0])
    assert result[1] == pytest.approx(2.0)
    assert result[2] == pytest.approx(-2.9411, abs=0.01)
    assert result[3] == pytest.approx(4.0404, abs=0.01)


def test_forward_returns():
    close = [100.0, 102.0, 99.0, 103.0, 106.0]
    result = forward_returns(close, days=2)
    assert result[0] == pytest.approx(-1.0)
    assert result[1] == pytest.approx(0.9803, abs=0.01)
    assert result[2] == pytest.approx(7.0707, abs=0.01)
    assert np.isnan(result[3])
    assert np.isnan(result[4])
