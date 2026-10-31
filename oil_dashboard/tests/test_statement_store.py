import data.statement_store as store


def _item(title, source, category="officials", date="2026-08-14T10:00:00+00:00"):
    return {
        "title": title,
        "link": "https://example.com/x",
        "source": source,
        "category": category,
        "date": date,
        "description": "",
    }


class TestAppendNew:
    def test_appends_new_items(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        added = store.append_new([_item("oil plan", "SecEnergy")])
        assert added == 1
        rows = store.load_all()
        assert len(rows) == 1
        assert rows[0]["title"] == "oil plan"
        assert rows[0]["first_seen_at"] != ""

    def test_dedupes_by_title_and_source(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        store.append_new([_item("oil plan", "SecEnergy")])
        added = store.append_new([
            _item("oil plan", "SecEnergy"),      # duplicate
            _item("crude sanctions", "SecState"),  # new
        ])
        assert added == 1
        rows = store.load_all()
        assert len(rows) == 2

    def test_duplicate_title_different_source_is_kept(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        store.append_new([_item("oil plan", "SecEnergy")])
        added = store.append_new([_item("oil plan", "DOE")])
        assert added == 1
        assert len(store.load_all()) == 2

    def test_title_case_insensitive_dedupe(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        store.append_new([_item("Oil Plan", "SecEnergy")])
        added = store.append_new([_item("oil plan", "SecEnergy")])
        assert added == 0
        assert len(store.load_all()) == 1

    def test_no_write_when_nothing_new(self, tmp_path, monkeypatch):
        store_path = tmp_path / "store.csv"
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", store_path)
        store.append_new([_item("oil plan", "SecEnergy")])
        mtime_before = store_path.stat().st_mtime_ns
        store.append_new([_item("oil plan", "SecEnergy")])
        assert store_path.stat().st_mtime_ns == mtime_before


class TestLoadAll:
    def test_empty_store_returns_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        assert store.load_all() == []

    def test_round_trip_preserves_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        store.append_new([_item("oil plan", "SecEnergy")])
        rows = store.load_all()
        assert rows[0]["date"] == "2026-08-14T10:00:00+00:00"
        assert rows[0]["category"] == "officials"
        assert rows[0]["source"] == "SecEnergy"
        assert rows[0]["link"] == "https://example.com/x"

    def test_newest_first(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.statement_store.STORAGE_CSV", tmp_path / "store.csv")
        store.append_new([
            _item("older", "SecEnergy", date="2026-08-13T10:00:00+00:00"),
            _item("newer", "SecEnergy", date="2026-08-14T10:00:00+00:00"),
        ])
        rows = store.load_all()
        assert rows[0]["title"] == "newer"
        assert rows[1]["title"] == "older"
