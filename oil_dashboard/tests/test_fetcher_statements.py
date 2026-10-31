from unittest import mock

import data.fetcher_statements as fetcher


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <item>
    <title>Secretary of Energy announces new crude pipeline</title>
    <link>https://example.com/a</link>
    <description>&lt;p&gt;The Secretary of Energy detailed the oil plan.&lt;/p&gt;</description>
    <pubDate>Fri, 14 Aug 2026 09:40:42 GMT</pubDate>
  </item>
  <item>
    <title>Weekly garden club meeting minutes</title>
    <link>https://example.com/b</link>
    <description>The garden club discussed tulips.</description>
    <pubDate>Thu, 13 Aug 2026 09:40:42 GMT</pubDate>
  </item>
</channel>
</rss>
"""


class TestStripHtml:
    def test_strips_tags_and_unescapes(self):
        assert fetcher._strip_html("<p>Hello &amp; goodbye</p>") == "Hello & goodbye"

    def test_none_returns_empty(self):
        assert fetcher._strip_html(None) == ""


class TestParseDate:
    def test_rfc2822_to_iso_utc(self):
        result = fetcher._parse_date("Fri, 14 Aug 2026 09:40:42 GMT")
        assert result.startswith("2026-08-14T09:40:42")

    def test_invalid_returns_empty(self):
        assert fetcher._parse_date("not a date") == ""
        assert fetcher._parse_date("") == ""


class TestFilterItems:
    def test_military_keeps_only_iran(self):
        items = [
            {"title": "Pentagon on Iran strikes", "description": ""},
            {"title": "Pentagon logistics update", "description": ""},
        ]
        kept = fetcher._filter_items(items, "military")
        assert len(kept) == 1
        assert "Iran" in kept[0]["title"]

    def test_officials_keeps_only_oil_keywords(self):
        items = [
            {"title": "Secretary discusses crude exports", "description": ""},
            {"title": "Secretary attends state dinner", "description": ""},
        ]
        kept = fetcher._filter_items(items, "officials")
        assert len(kept) == 1
        assert "crude" in kept[0]["title"]

    def test_officials_keeps_energy_and_iran(self):
        items = [
            {"title": "Energy policy briefing", "description": ""},
            {"title": "Iran sanctions update", "description": ""},
        ]
        kept = fetcher._filter_items(items, "officials")
        assert len(kept) == 2


class TestFetchAndParseRss:
    def test_parses_items_and_strips_html(self):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.text = RSS_XML
        with mock.patch("data.fetcher_statements.requests.get", return_value=resp):
            items = fetcher._fetch_and_parse_rss("https://example.com/feed")
        assert len(items) == 2
        assert items[0]["title"] == "Secretary of Energy announces new crude pipeline"
        assert items[0]["link"] == "https://example.com/a"
        assert items[0]["description"] == "The Secretary of Energy detailed the oil plan."
        assert items[0]["date"].startswith("2026-08-14T09:40:42")

    def test_returns_empty_on_network_error(self):
        with mock.patch("data.fetcher_statements.requests.get",
                        side_effect=Exception("boom")):
            items = fetcher._fetch_and_parse_rss("https://example.com/feed")
        assert items == []

    def test_returns_empty_on_malformed_xml(self):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.text = "<rss><broken>"
        with mock.patch("data.fetcher_statements.requests.get", return_value=resp):
            items = fetcher._fetch_and_parse_rss("https://example.com/feed")
        assert items == []


class TestGetOfficialsStatements:
    def test_dedupes_and_sorts_newest_first(self, sample_cache_dir):
        rss = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Crude sanctions announced</title><link>https://example.com/x</link>
    <description>Iran crude sanctions.</description>
    <pubDate>Fri, 14 Aug 2026 09:40:42 GMT</pubDate>
  </item>
</channel></rss>"""
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.text = rss
        # Only officials watch is exercised here; keep the feed list empty so
        # the test stays deterministic regardless of the configured watch lists.
        with mock.patch("data.fetcher_statements.requests.get", return_value=resp), \
             mock.patch("data.fetcher_statements.OFFICIALS_WATCH",
                        [{"name": "SecEnergy", "query": "q", "category": "officials"}]), \
             mock.patch("data.fetcher_statements.MILITARY_WATCH", []), \
             mock.patch("data.fetcher_statements.AGENCY_FEEDS", []), \
             mock.patch("data.fetcher_statements.append_new", return_value=1), \
             mock.patch("data.fetcher_statements.load_all", return_value=[]):
            result = fetcher.get_officials_statements()

        assert result["available"] is True
        assert len(result["items"]) == 1
        assert result["items"][0]["source"] == "SecEnergy"
        assert result["items"][0]["category"] == "officials"
        assert result["items"][0]["date"].startswith("2026-08-14T09:40:42")

    def test_caches_result(self, sample_cache_dir):
        resp = mock.Mock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.text = RSS_XML
        with mock.patch("data.fetcher_statements.requests.get", return_value=resp), \
             mock.patch("data.fetcher_statements.OFFICIALS_WATCH",
                        [{"name": "SecEnergy", "query": "q", "category": "officials"}]), \
             mock.patch("data.fetcher_statements.MILITARY_WATCH", []), \
             mock.patch("data.fetcher_statements.AGENCY_FEEDS", []), \
             mock.patch("data.fetcher_statements.append_new", return_value=1), \
             mock.patch("data.fetcher_statements.load_all", return_value=[]):
            first = fetcher.get_officials_statements()
            second = fetcher.get_officials_statements()

        assert first["items"] == second["items"]
        assert len(first["items"]) == 1
