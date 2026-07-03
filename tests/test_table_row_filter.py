"""Tests for table row visibility filtering."""

from stream_fetch import _table_row_event
from table_view import _has_valid_rate, build_rates_table_rows


def test_has_valid_rate_requires_positive_rate():
    assert _has_valid_rate({"exchange_rate": 105.272})
    assert not _has_valid_rate({"exchange_rate": 0})
    assert not _has_valid_rate({"exchange_rate": None})
    assert not _has_valid_rate({"status": "error"})


def test_table_row_event_skips_unavailable():
    assert _table_row_event({"provider": "MoneyGram", "rate": None, "status": "error"}) is None
    assert _table_row_event({"provider": "Wise", "rate": 105.272, "status": "ok"}) is not None


def test_build_rates_table_rows_excludes_error_providers():
    payload = {
        "all_rates": [
            {"provider": "Wise", "exchange_rate": 105.0, "status": "ok", "fee": 0},
            {"provider": "MoneyGram", "exchange_rate": 0, "status": "error", "fee": 0},
        ]
    }
    rows = build_rates_table_rows(payload)
    assert len(rows) == 1
    assert rows[0]["provider"] == "Wise"
