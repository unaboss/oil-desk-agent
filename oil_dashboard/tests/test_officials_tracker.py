from analysis.officials_tracker import (
    count_mentions_per_source,
    group_mentions_by_date,
    extract_iran_mentions,
)


def _item(category, source, title, date="2026-08-14T10:00:00+00:00", desc=""):
    return {
        "title": title,
        "link": "https://example.com/x",
        "source": source,
        "category": category,
        "date": date,
        "description": desc,
    }


class TestCountMentionsPerSource:
    def test_counts_categories_and_sources(self):
        items = [
            _item("officials", "SecEnergy", "oil plan"),
            _item("officials", "SecEnergy", "crude sanctions"),
            _item("military", "Pentagon", "Iran strikes"),
        ]
        result = count_mentions_per_source(items)
        assert result["total"] == 3
        assert result["categories"] == {"officials": 2, "military": 1}
        assert result["sources"] == {"SecEnergy": 2, "Pentagon": 1}

    def test_empty_input(self):
        result = count_mentions_per_source([])
        assert result["total"] == 0
        assert result["categories"] == {}
        assert result["sources"] == {}


class TestGroupMentionsByDate:
    def test_groups_by_day_per_category(self):
        items = [
            _item("officials", "SecEnergy", "a", date="2026-08-14T10:00:00+00:00"),
            _item("officials", "EPA", "b", date="2026-08-14T11:00:00+00:00"),
            _item("military", "Pentagon", "c", date="2026-08-13T10:00:00+00:00"),
        ]
        result = group_mentions_by_date(items)
        assert result["dates"] == ["2026-08-13", "2026-08-14"]
        assert result["categories"]["officials"] == [0, 2]
        assert result["categories"]["military"] == [1, 0]

    def test_skips_unparseable_dates(self):
        items = [_item("officials", "SecEnergy", "x", date="not-a-date")]
        result = group_mentions_by_date(items)
        assert result["dates"] == []
        assert result["categories"] == {"officials": []}


class TestExtractIranMentions:
    def test_keeps_military_items_mentioning_iran(self):
        items = [
            _item("military", "Pentagon", "strikes on Iran"),
            _item("military", "DoD", "iran escalation", desc="no oil"),
            _item("military", "CENTCOM", "routine exercise"),
            _item("officials", "SecState", "talks with Iran"),
        ]
        result = extract_iran_mentions(items)
        titles = [it["title"] for it in result]
        assert titles == ["strikes on Iran", "iran escalation"]
        assert "routine exercise" not in titles
        assert "talks with Iran" not in titles

    def test_newest_first(self):
        items = [
            _item("military", "Pentagon", "old Iran strike", date="2026-08-13T10:00:00+00:00"),
            _item("military", "Pentagon", "new Iran strike", date="2026-08-14T10:00:00+00:00"),
        ]
        result = extract_iran_mentions(items)
        assert [it["title"] for it in result] == ["new Iran strike", "old Iran strike"]

    def test_empty_input(self):
        assert extract_iran_mentions([]) == []
