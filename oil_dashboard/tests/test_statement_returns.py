from analysis.statement_returns import (
    aggregate_returns,
    classify_direction,
    compute_statement_returns,
    map_statement_dates,
)


def _wti(prices=None, start="2026-01-05"):
    """Build a daily WTI series with a known stepping base price."""
    if prices is None:
        prices = [100 + i for i in range(20)]  # flat +1 per day
    dates = []
    day = __import__("datetime").date.fromisoformat(start)
    for _ in prices:
        dates.append(day.isoformat())
        day = day + __import__("datetime").timedelta(days=1)
    return {"dates": dates, "close": prices}


def _item(date, title="stmt", category="officials", source="SecEnergy"):
    return {
        "date": date + "T12:00:00+00:00",
        "title": title,
        "category": category,
        "source": source,
        "description": "",
        "link": "https://example.com/x",
    }


class TestMapStatementDates:
    def test_maps_all_statements_including_series_end(self):
        wti = _wti()
        items = [
            _item("2026-01-05"),
            _item("2026-01-24"),  # last day: no forward window, but must appear
        ]
        result = map_statement_dates(items, wti)
        assert result["available"] is True
        assert len(result["markers"]) == 2
        assert result["markers"][0]["close"] == 100.0
        assert result["markers"][1]["close"] == 119.0

    def test_skips_statement_outside_wti_range(self):
        wti = _wti()
        items = [_item("2025-01-01")]
        result = map_statement_dates(items, wti)
        assert result["available"] is False
        assert result["markers"] == []

    def test_empty_wti(self):
        result = map_statement_dates([_item("2026-01-05")], {"dates": [], "close": []})
        assert result["available"] is False
        assert result["markers"] == []


class TestComputeStatementReturns:
    def test_computes_1_3_5_day_forward_returns(self):
        # price 100->101->102...: from day0 (100), +3 = 103 => +3.0%
        wti = _wti()
        items = [_item("2026-01-05")]
        result = compute_statement_returns(items, wti)
        assert result["available"] is True
        ev = result["events"][0]
        assert ev["fwd_1d"] == 1.0
        assert ev["fwd_3d"] == 3.0
        assert ev["fwd_5d"] == 5.0

    def test_skips_statement_outside_wti_range(self):
        wti = _wti()
        items = [_item("2025-01-01")]
        result = compute_statement_returns(items, wti)
        assert result["available"] is False
        assert result["events"] == []

    def test_skips_statement_too_close_to_end(self):
        # last statement date has no 5-day forward price -> skipped
        wti = _wti()
        items = [_item("2026-01-24")]  # last day of a 20-day series
        result = compute_statement_returns(items, wti)
        assert result["events"] == []

    def test_empty_wti(self):
        result = compute_statement_returns([_item("2026-01-05")], {"dates": [], "close": []})
        assert result["available"] is False
        assert result["events"] == []


class TestAggregateReturns:
    def test_groups_by_category_and_overall(self):
        wti = _wti()
        items = [
            _item("2026-01-05", category="officials"),
            _item("2026-01-06", category="military", source="Pentagon"),
        ]
        events = compute_statement_returns(items, wti)["events"]
        agg = aggregate_returns(events)
        assert agg["overall"]["fwd_1d"]["count"] == 2
        assert agg["categories"]["officials"]["fwd_1d"]["count"] == 1
        assert agg["categories"]["military"]["fwd_1d"]["count"] == 1

    def test_aggregates_mean_correctly(self):
        wti = _wti()
        items = [_item("2026-01-05"), _item("2026-01-10")]
        events = compute_statement_returns(items, wti)["events"]
        agg = aggregate_returns(events)
        # base 100 -> 103 = +3.00%; base 105 -> 108 = +2.86%
        assert agg["overall"]["fwd_3d"]["mean"] == round((3.0 + 2.86) / 2, 2)


class TestClassifyDirection:
    def test_classifies_up_down_flat(self):
        wti = _wti()
        items = [
            _item("2026-01-05"),          # +1/day => up
            _item("2026-01-06"),
        ]
        events = compute_statement_returns(items, wti)["events"]
        classified = classify_direction(events, horizon=3)
        assert all(e["direction"] == "up" for e in classified["events"])
        assert classified["overall"]["up"] == 100.0
        assert classified["overall"]["count"] == 2

    def test_down_market(self):
        wti = _wti(prices=[100 - i for i in range(20)])
        items = [_item("2026-01-05")]
        events = compute_statement_returns(items, wti)["events"]
        classified = classify_direction(events, horizon=3)
        assert classified["events"][0]["direction"] == "down"
        assert classified["overall"]["down"] == 100.0

    def test_flat_market(self):
        wti = _wti(prices=[100] * 20)
        items = [_item("2026-01-05")]
        events = compute_statement_returns(items, wti)["events"]
        classified = classify_direction(events, horizon=3)
        assert classified["events"][0]["direction"] == "flat"

    def test_empty_events(self):
        classified = classify_direction([], horizon=3)
        assert classified["events"] == []
        assert classified["overall"]["count"] == 0
