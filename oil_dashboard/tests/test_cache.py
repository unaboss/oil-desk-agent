import time
import pytest
from data.cache import get, set, invalidate, invalidate_all


def test_get_empty_key_returns_none(sample_cache_dir):
    data, last_upd, next_upd, stale = get("nonexistent_key")
    assert data is None
    assert last_upd is None
    assert next_upd is None
    assert stale is True


def test_set_then_get_returns_data(sample_cache_dir):
    set("test_key", {"value": 42}, ttl=3600)
    data, _, _, stale = get("test_key")
    assert data == {"value": 42}
    assert stale is False


def test_expired_ttl_returns_stale(sample_cache_dir):
    set("stale_key", {"value": 1}, ttl=0)  # 0-second TTL expired instantly
    time.sleep(0.01)
    data, _, _, stale = get("stale_key")
    assert data is not None
    assert stale is True


def test_invalidate_clears_key(sample_cache_dir):
    set("to_remove", {"x": 1}, ttl=3600)
    invalidate("to_remove")
    data, _, _, stale = get("to_remove")
    assert data is None
    assert stale is True


def test_invalidate_all_clears_everything(sample_cache_dir):
    set("key1", {"a": 1}, ttl=3600)
    set("key2", {"b": 2}, ttl=3600)
    invalidate_all()
    d1, _, _, s1 = get("key1")
    d2, _, _, s2 = get("key2")
    assert d1 is None
    assert d2 is None
    assert s1 is True
    assert s2 is True
