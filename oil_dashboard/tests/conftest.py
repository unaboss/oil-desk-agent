import pytest
import numpy as np


@pytest.fixture
def sample_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    monkeypatch.setattr("data.cache.DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def sample_market_data():
    dates = ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04", "2025-12-05"]
    return {
        "wti": {
            "dates": dates,
            "close": [68.50, 69.10, 68.80, 69.50, 70.00],
            "volume": [300000, 250000, 400000, 350000, 280000],
        },
        "volume_anomaly": {
            "dates": dates,
            "volume": [300000, 250000, 400000, 350000, 280000],
            "volume_ma": [320000, 315000, 310000, 300000, 290000],
            "volume_ratio": [0.94, 0.79, 1.29, 1.17, 0.97],
        },
        "crack": {
            "dates": dates,
            "crack": [15.0, 16.0, 14.5, 17.0, 18.0],
            "crack_5ma": [np.nan, np.nan, np.nan, np.nan, 16.1],
        },
        "curve": {
            "spread_dates": dates,
            "brent_wti_spread": [3.0, 2.5, -3.2, 2.8, 3.5],
        },
        "dxy": {
            "dates": ["2025-11-28", "2025-11-29", "2025-11-30",
                       "2025-12-01", "2025-12-02", "2025-12-03",
                       "2025-12-04", "2025-12-05"],
            "close": [106.0, 105.9, 105.7, 105.5, 105.8, 105.2, 104.8, 104.5],
        },
    }


@pytest.fixture
def bullish_market_data():
    """Market data where every signal should be bullish (+1)."""
    dates = ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04", "2025-12-05"]
    return {
        "wti": {
            "dates": dates,
            "close": [68.50, 69.10, 68.80, 69.50, 70.00],
        },
        "volume_anomaly": {
            "dates": dates,
            "volume_ratio": [1.5, 1.6, 1.7, 1.8, 1.9],  # all >1 = bullish
        },
        "crack": {
            "dates": dates,
            "crack": [18.0, 18.5, 19.0, 19.5, 20.0],
            "crack_5ma": [np.nan, np.nan, np.nan, np.nan, 15.0],  # crack > ma = bullish
        },
        "curve": {
            "spread_dates": dates,
            "brent_wti_spread": [4.0, 4.5, 5.0, 5.5, 6.0],  # all > 0 = backwardation = bullish
        },
        "dxy": {
            "dates": ["2025-11-28", "2025-11-29", "2025-11-30",
                       "2025-12-01", "2025-12-02", "2025-12-03",
                       "2025-12-04", "2025-12-05"],
            "close": [106.0, 105.9, 105.7, 105.5, 105.8, 105.2, 104.8, 104.5],  # DXY falling = bullish
        },
    }


@pytest.fixture
def bearish_market_data():
    """Market data where every signal should be bearish (-1)."""
    dates = ["2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04", "2025-12-05"]
    return {
        "wti": {
            "dates": dates,
            "close": [70.00, 69.50, 69.00, 68.50, 68.00],
        },
        "volume_anomaly": {
            "dates": dates,
            "volume_ratio": [0.5, 0.4, 0.3, 0.2, 0.1],  # all <1 = bearish
        },
        "crack": {
            "dates": dates,
            "crack": [10.0, 9.5, 9.0, 8.5, 8.0],
            "crack_5ma": [np.nan, np.nan, np.nan, np.nan, 15.0],  # crack < ma = bearish
        },
        "curve": {
            "spread_dates": dates,
            "brent_wti_spread": [-1.0, -1.5, -2.0, -2.5, -3.0],  # all < 0 = contango = bearish
        },
        "dxy": {
            "dates": ["2025-11-28", "2025-11-29", "2025-11-30",
                       "2025-12-01", "2025-12-02", "2025-12-03",
                       "2025-12-04", "2025-12-05"],
            "close": [104.0, 104.2, 104.5, 105.0, 105.3, 105.8, 106.2, 106.5],  # DXY rising = bearish
        },
    }


@pytest.fixture
def bullish_eia():
    return {"crude": {"dates": ["2025-11-28"], "changes": [-1500]}}  # draw = bullish


@pytest.fixture
def bearish_eia():
    return {"crude": {"dates": ["2025-11-28"], "changes": [2000]}}  # build = bearish


@pytest.fixture
def cot_bullish():
    return {"managed_money_long": 250000, "managed_money_short": 150000, "net_long": 100000}


@pytest.fixture
def cot_bearish():
    return {"managed_money_long": 150000, "managed_money_short": 250000, "net_long": -100000}
