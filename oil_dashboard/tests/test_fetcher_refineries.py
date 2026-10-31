from unittest import mock

from openpyxl import Workbook

import data.fetcher_refineries as fetcher


def _capacity_workbook_bytes():
    wb = Workbook()
    ws = wb.active
    ws.append(["CORPORATION", "SURVEY", "PERIOD", "COMPANY_NAME", "RDIST_LABEL",
               "STATE_NAME", "SITE", "PADD", "PRODUCT", "SUPPLY", "QUANTITY"])
    ws.append(["ABC CORP", "820", "26", "ABC REFINING", "Texas Gulf Coast",
               "Texas", "HOUSTON", "3", "TOTAL OPERABLE CAPACITY",
               "Atmospheric Crude Distillation Capacity (barrels per calendar day)", "500000"])
    ws.append(["ABC CORP", "820", "26", "ABC REFINING", "Texas Gulf Coast",
               "Texas", "HOUSTON", "3", "TOTAL OPERABLE CAPACITY",
               "Atmospheric Crude Distillation Capacity (barrels per stream day)", "550000"])
    ws.append(["XYZ CORP", "820", "26", "XYZ REFINING", "Midwest",
               "Illinois", "CHICAGO", "2", "TOTAL OPERABLE CAPACITY",
               "Atmospheric Crude Distillation Capacity (barrels per calendar day)", "120000"])
    ws.append(["SKIP", "820", "26", "SKIP CO", "West Coast",
               "California", "LA", "5", "CAT CRACKING: FRESH FEED",
               "Atmospheric Crude Distillation Capacity (barrels per calendar day)", "999"])
    import io
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestParseCapacityWorkbook:
    def test_extracts_calendar_day_capacity_only(self):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.content = _capacity_workbook_bytes()
        with mock.patch("data.fetcher_refineries.requests.get", return_value=resp):
            rows = fetcher._parse_capacity_workbook("https://example.com/refcap.xlsx")

        assert len(rows) == 2
        assert rows[0]["company"] == "ABC REFINING"
        assert rows[0]["site"] == "HOUSTON"
        assert rows[0]["state"] == "Texas"
        assert rows[0]["padd"] == "3"
        assert rows[0]["capacity_bpd"] == 500000
        assert rows[1]["capacity_bpd"] == 120000

    def test_sorted_descending_by_capacity(self):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.content = _capacity_workbook_bytes()
        with mock.patch("data.fetcher_refineries.requests.get", return_value=resp):
            rows = fetcher._parse_capacity_workbook("https://example.com/refcap.xlsx")
        assert rows[0]["capacity_bpd"] >= rows[1]["capacity_bpd"]

    def test_returns_empty_on_network_error(self):
        with mock.patch("data.fetcher_refineries.requests.get",
                        side_effect=Exception("boom")):
            rows = fetcher._parse_capacity_workbook("https://example.com/refcap.xlsx")
        assert rows == []


class TestGetRefineryCapacity:
    def test_caches_result(self, sample_cache_dir):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.content = _capacity_workbook_bytes()
        with mock.patch("data.fetcher_refineries.requests.get", return_value=resp):
            first = fetcher.get_refinery_capacity(year=2026)
            second = fetcher.get_refinery_capacity(year=2026)
        assert first == second
        assert len(first) == 2

    def test_failure_cached_with_short_ttl(self, sample_cache_dir):
        """A failed fetch must not be cached under the 30-day capacity TTL."""
        from data.cache import invalidate
        from data.cache import _cache_file
        invalidate(fetcher.CACHE_KEY_CAP)
        with mock.patch("data.fetcher_refineries.requests.get",
                        side_effect=Exception("boom")):
            result = fetcher.get_refinery_capacity(year=2026)
        assert result == []
        import json
        entry = json.loads(_cache_file(fetcher.CACHE_KEY_CAP).read_text())
        assert entry["ttl"] == fetcher.CACHE_TTL_REFINERY_CAP_FAILURE
        assert entry["ttl"] < fetcher.CACHE_TTL_REFINERY_CAP


class TestGetRefineryUtilization:
    def _mock_response(self, records):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"response": {"data": records}}
        return resp

    def test_builds_series_from_api(self, sample_cache_dir):
        records = [
            {"period": "2026-08-07", "series": "WPULEUS3", "value": "96.2"},
            {"period": "2026-08-07", "series": "WCRRIUS2", "value": "17179"},
            {"period": "2026-07-31", "series": "WPULEUS3", "value": "96.5"},
            {"period": "2026-07-31", "series": "WCRRIUS2", "value": "17153"},
        ]
        # Same records returned for every area; the US (NUS) is what we assert on.
        with mock.patch("data.fetcher_refineries.requests.get",
                        return_value=self._mock_response(records)):
            result = fetcher.get_refinery_utilization(weeks=2)

        assert result["available"] is True
        assert result["dates"] == ["2026-07-31", "2026-08-07"]
        us_pct = result["utilization_pct"]["NUS"]
        assert us_pct == [96.5, 96.2]
        assert result["crude_inputs"]["NUS"] == [17153.0, 17179.0]

    def test_returns_unavailable_on_error(self, sample_cache_dir):
        from data.cache import invalidate
        invalidate(fetcher.CACHE_KEY_UTIL)
        with mock.patch("data.fetcher_refineries.requests.get",
                        side_effect=Exception("boom")):
            result = fetcher.get_refinery_utilization(weeks=2)
        assert result["available"] is False
        assert result["dates"] == []
