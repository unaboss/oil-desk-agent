import pytest
from analysis.trump_event_study import compute_trump_event_study


class TestTrumpEventStudy:
    def test_classification_lagging(self, tmp_path, monkeypatch):
        csv = tmp_path / "trump.csv"
        csv.write_text(
            "date,statement,claim_type,source_url\n"
            "2025-12-01,\"lagging stmt\",tariff,https://x.com/whatever\n"
        )
        monkeypatch.setattr("analysis.trump_event_study.RESEARCH_TRUMP_CSV", csv)
        market = _study_market(pre_pct=0.04, fwd_pct=0.005)
        result = compute_trump_event_study(market, start="2025-12-01", end="2025-12-05")
        classes = [e["classification"] for e in result["events"]]
        assert "Lagging" in classes

    def test_classification_pre_reversal(self, tmp_path, monkeypatch):
        csv = tmp_path / "trump.csv"
        csv.write_text(
            "date,statement,claim_type,source_url\n"
            "2025-12-01,\"reversal stmt\",tariff,https://x.com/whatever\n"
        )
        monkeypatch.setattr("analysis.trump_event_study.RESEARCH_TRUMP_CSV", csv)
        market = _study_market(pre_pct=-0.04, fwd_pct=0.04)
        result = compute_trump_event_study(market, start="2025-12-01", end="2025-12-05")
        classes = [e["classification"] for e in result["events"]]
        assert "Pre-reversal" in classes

    def test_classification_confirmation(self, tmp_path, monkeypatch):
        csv = tmp_path / "trump.csv"
        csv.write_text(
            "date,statement,claim_type,source_url\n"
            "2025-12-01,\"confirm stmt\",tariff,https://x.com/whatever\n"
        )
        monkeypatch.setattr("analysis.trump_event_study.RESEARCH_TRUMP_CSV", csv)
        market = _study_market(pre_pct=0.04, fwd_pct=0.04)
        result = compute_trump_event_study(market, start="2025-12-01", end="2025-12-05")
        classes = [e["classification"] for e in result["events"]]
        assert "Confirmation" in classes

    def test_classification_no_signal(self, tmp_path, monkeypatch):
        csv = tmp_path / "trump.csv"
        csv.write_text(
            "date,statement,claim_type,source_url\n"
            "2025-12-01,\"quiet stmt\",tariff,https://x.com/whatever\n"
        )
        monkeypatch.setattr("analysis.trump_event_study.RESEARCH_TRUMP_CSV", csv)
        market = _study_market(pre_pct=0.005, fwd_pct=0.005)
        result = compute_trump_event_study(market, start="2025-12-01", end="2025-12-05")
        classes = [e["classification"] for e in result["events"]]
        assert "No signal" in classes

    def test_lag_rate_calculation(self, tmp_path, monkeypatch):
        csv = tmp_path / "trump.csv"
        csv.write_text(
            "date,statement,claim_type,source_url\n"
            "2025-12-01,lagging1,tariff,https://x.com/a\n"
            "2025-12-01,lagging2,tariff,https://x.com/b\n"
            "2025-12-01,lagging3,tariff,https://x.com/c\n"
            "2025-12-01,confirm,tariff,https://x.com/d\n"
            "2025-12-01,reversal,tariff,https://x.com/e\n"
        )
        monkeypatch.setattr("analysis.trump_event_study.RESEARCH_TRUMP_CSV", csv)
        market = _study_market(pre_pct=0.04, fwd_pct=0.04)
        result = compute_trump_event_study(market, start="2025-12-01", end="2025-12-05")
        assert 0 <= result["lag_rate"] <= 100
        assert result["total"] == 5


def _study_market(pre_pct, fwd_pct):
    """Build WTI market with 5 lookback + 1 statement + 3 forward data points."""
    p1 = 70.00
    p0 = p1 / (1 + pre_pct)
    p2 = p1 * (1 + fwd_pct)
    new_dates = [
        "2025-11-24", "2025-11-25", "2025-11-26", "2025-11-27", "2025-11-28",
        "2025-12-01", "2025-12-02", "2025-12-03", "2025-12-04",
    ]
    new_close = [p0] * 5 + [p1] + [p1] * 2 + [p2]
    return {
        "wti": {
            "dates": new_dates,
            "close": new_close,
        },
    }
