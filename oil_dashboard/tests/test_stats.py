import numpy as np
from analysis.stats import cross_correlation, optimal_lag, signal_win_rate


def test_cross_correlation_identical_percent_changes():
    s = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    cc = cross_correlation(s, s, max_lag=3)
    assert isinstance(cc, dict)
    assert len(cc) > 0


def test_cross_correlation_inverted():
    s1 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    s2 = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    cc = cross_correlation(s1, s2, max_lag=3)
    assert isinstance(cc, dict)
    assert 1 in cc


def test_optimal_lag_finds_best():
    s1 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    s2 = [np.nan, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    result = optimal_lag(s1, s2, max_lag=3)
    assert "lag" in result
    assert "correlation" in result


def test_cross_correlation_nan_handled():
    s1 = [1.0, 2.0, np.nan, 4.0, 5.0]
    s2 = [5.0, 4.0, 3.0, 2.0, 1.0]
    cc = cross_correlation(s1, s2, max_lag=2)
    assert isinstance(cc, dict)


def test_signal_win_rate_no_signals():
    import pandas as pd
    df = pd.DataFrame({"date": ["2025-01-01"], "score": [0]})
    returns = [100.0]
    rate = signal_win_rate(df, returns)
    assert rate == 0.0


def test_signal_win_rate_empty_dataframe():
    import pandas as pd
    df = pd.DataFrame({"date": [], "score": []})
    returns = []
    rate = signal_win_rate(df, returns)
    assert rate == 0.0
