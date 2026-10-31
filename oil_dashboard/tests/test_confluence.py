import pytest
from analysis.confluence import compute_confluence, compute_cot_extreme


class TestComputeConfluence:
    def test_all_bullish_scores_6(self, bullish_market_data, bullish_eia, cot_bullish):
        score = compute_confluence(bullish_market_data, bullish_eia, cot_bullish)
        assert score["score"] >= 4
        assert score["direction"] == "bullish"

    def test_all_bearish_scores_minus_6(self, bearish_market_data, bearish_eia, cot_bearish):
        score = compute_confluence(bearish_market_data, bearish_eia, cot_bearish)
        assert score["direction"] == "bearish"

    def test_mixed_signals_returns_neutral(self, sample_market_data, bearish_eia, cot_bullish):
        score = compute_confluence(sample_market_data, bearish_eia, cot_bullish)
        assert score["direction"] == "neutral"

    def test_empty_market_data_returns_empty_score(self):
        score = compute_confluence({}, None, None)
        assert score["score"] == 0
        assert score["direction"] == "neutral"

    def test_no_volume_anomaly_sets_volume_to_0(self, sample_market_data, bullish_eia, cot_bullish):
        data = dict(sample_market_data)
        data["volume_anomaly"] = {}
        score = compute_confluence(data, bullish_eia, cot_bullish)
        assert score["signals"]["volume"] == 0

    def test_no_eia_sets_inventories_to_0(self, sample_market_data, cot_bullish):
        score = compute_confluence(sample_market_data, None, cot_bullish)
        assert score["signals"]["inventories"] == 0

    def test_crack_date_mismatch_handled(self, sample_market_data, bullish_eia, cot_bullish):
        data = dict(sample_market_data)
        data["crack"]["dates"] = ["2025-12-10"]  # no match with WTI dates
        score = compute_confluence(data, bullish_eia, cot_bullish)
        assert score["signals"]["crack"] == 0

    def test_latest_only_returns_dict(self, sample_market_data, bullish_eia, cot_bullish):
        score = compute_confluence(sample_market_data, bullish_eia, cot_bullish, latest_only=True)
        assert isinstance(score, dict)
        assert "date" in score
        assert "score" in score

    def test_latest_only_false_returns_list(self, sample_market_data, bullish_eia, cot_bullish):
        scores = compute_confluence(sample_market_data, bullish_eia, cot_bullish, latest_only=False)
        assert isinstance(scores, list)
        assert len(scores) == 5


class TestComputeCotExtreme:
    def test_net_long_over_100k_is_extreme(self):
        result = compute_cot_extreme({"managed_money_long": 300000, "managed_money_short": 100000, "net_long": 200000})
        assert result["is_extreme"] is True
        assert result["side"] == "long"
        assert result["net_long"] == 200000

    def test_net_short_over_100k_is_extreme(self):
        result = compute_cot_extreme({"managed_money_long": 100000, "managed_money_short": 250000, "net_long": -150000})
        assert result["is_extreme"] is True
        assert result["side"] == "short"

    def test_small_net_position_not_extreme(self):
        result = compute_cot_extreme({"net_long": 50000})
        assert result["is_extreme"] is False

    def test_no_data_returns_defaults(self):
        result = compute_cot_extreme(None)
        assert result["is_extreme"] is False
        assert result["net_long"] is None

    def test_no_net_long_key(self):
        result = compute_cot_extreme({"managed_money_long": 50000})
        assert result["is_extreme"] is False
        assert result["side"] == ""
