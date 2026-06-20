"""Tests for live API response cache."""

from live_api import _cache_get, _cache_set


def test_cache_returns_payload_before_expiry():
    key = (1000.0, True)
    _cache_set(key, {"last_updated": "test", "send_amount": 1000})
    cached = _cache_get(key)
    assert cached is not None
    assert cached["cached"] is True
    assert cached["send_amount"] == 1000


def test_cache_miss_on_unknown_key():
    assert _cache_get((9999.0, False)) is None
