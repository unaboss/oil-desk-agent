from analysis.curve_analysis import compute_driver


def _series(prices):
    return {"dates": [f"2026-08-{i:02d}" for i in range(len(prices))], "close": prices}


class TestComputeDriver:
    def test_brent_driving(self):
        # Over the 5-day window: Brent +4%, WTI +1% -> Brent drives.
        wti = _series([100, 100, 100, 100, 100, 101])
        brent = _series([100, 100, 101, 102, 103, 104])
        result = compute_driver(wti, brent, window=5)
        assert result["driver"] == "brent"
        assert abs(result["wti_move_pct"] - 1.0) < 0.01
        assert abs(result["brent_move_pct"] - 4.0) < 0.01
        assert result["spread_change"] == 3.0

    def test_wti_driving(self):
        # WTI drops 5%, Brent drops 1% -> WTI drives (down move).
        wti = _series([100, 99, 98, 97, 96, 95])
        brent = _series([100, 100, 99, 99, 99, 99])
        result = compute_driver(wti, brent, window=5)
        assert result["driver"] == "wti"
        assert result["wti_move_pct"] < 0
        assert result["spread_change"] is not None

    def test_insufficient_data(self):
        wti = _series([100])
        brent = _series([100, 101])
        result = compute_driver(wti, brent, window=5)
        assert result["driver"] == "insufficient"

    def test_tie_when_equal_moves(self):
        wti = _series([100, 101, 102, 103, 104, 105])
        brent = _series([100, 101, 102, 103, 104, 105])
        result = compute_driver(wti, brent, window=5)
        assert result["driver"] == "wti"  # equal moves -> wti wins tie (>=)
        assert result["spread_change"] == 0.0

    def test_ignores_none_closes(self):
        wti = _series([100, None, 102, 103, 104, 105])
        brent = _series([100, 101, 102, 103, 104, 105])
        result = compute_driver(wti, brent, window=5)
        assert result["driver"] != "insufficient"
