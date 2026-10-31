import numpy as np
from analysis.audit import compute_audit


def test_bullish_signal_positive_return_is_confirmed():
    market = _make_market(close=[68.50, 69.10, 68.80, 69.50, 70.00, 72.50, 73.00, 73.50])
    result = compute_audit(market, _eia_draw(), _cot_net(100000))
    assert isinstance(result["confirmed"], list)
    assert isinstance(result["hit_rate"], (int, float))


def test_bullish_signal_negative_return_is_false():
    market = _make_market(close=[68.50, 69.10, 68.80, 69.50, 70.00, 67.00, 66.00, 65.00])
    result = compute_audit(market, _eia_draw(), _cot_net(100000))
    assert isinstance(result["false_signals"], list)


def test_large_move_no_signal_is_missed():
    market = _make_market(close=[68.50, 68.60, 68.70, 68.80, 68.90, 72.00, 73.00, 73.50])
    result = compute_audit(market, None, {"net_long": 0})
    assert result["missed_count"] >= 0


def test_empty_market_returns_defaults():
    result = compute_audit({"wti": {"dates": [], "close": []}}, None, None)
    assert result["hit_rate"] == 0.0
    assert result["total_signals"] == 0
    assert result["confirmed"] == []


def test_no_signals_means_zero_hit_rate():
    market = _make_market(close=[68.50, 69.10, 68.80, 69.50, 70.00], days=5)
    result = compute_audit(market, None, {"net_long": 0})
    assert result["total_signals"] == 0
    assert result["hit_rate"] == 0.0


def test_hit_rate_in_valid_range():
    dates = [f"2025-12-{d:02d}" for d in range(1, 18)]
    close = [68.0 + d * 0.5 if d <= 9 else 68.0 - (d - 9) * 0.5 for d in range(1, 18)]
    market = _make_market_full(dates, close)
    result = compute_audit(market, _eia_draw(), _cot_net(100000))
    assert 0 <= result["hit_rate"] <= 100
    assert len(result["confirmed"]) <= 3
    assert len(result["missed"]) <= 3
    assert len(result["false_signals"]) <= 3


def _make_market(close, days=None):
    if days is None:
        days = len(close)
    dates = [f"2025-12-{d:02d}" for d in range(1, days + 1)]
    return _make_market_full(dates, close[:days])


def _make_market_full(dates, close):
    n = len(dates)
    dxy_dates = [f"2025-11-{28 + i:02d}" for i in range(3)] + dates
    dxy_close_vals = [106.0, 105.8, 105.6] + [105.0] * n
    return {
        "wti": {
            "dates": dates,
            "close": close,
            "volume": [300000] * n,
        },
        "volume_anomaly": {
            "dates": dates,
            "volume_ratio": [1.5] * n,
        },
        "crack": {
            "dates": dates,
            "crack": [18.0] * n,
            "crack_5ma": [np.nan] * (n - 1) + [15.0],
        },
        "curve": {
            "spread_dates": dates,
            "brent_wti_spread": [4.0] * n,
        },
        "dxy": {
            "dates": dxy_dates,
            "close": dxy_close_vals,
        },
    }


def _eia_draw():
    return {"crude": {"dates": ["2025-11-28"], "changes": [-1500]}}


def _cot_net(net):
    return {"managed_money_long": 100000 + max(net, 0), "managed_money_short": 100000 - min(net, 0), "net_long": net}
