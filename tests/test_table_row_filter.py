"""Tests for table row visibility filtering."""

from models import utc_now_iso
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
    now = utc_now_iso()
    payload = {
        "all_rates": [
            {
                "provider": "Wise",
                "exchange_rate": 105.0,
                "receive_amount": 104000,
                "status": "ok",
                "fee": 14.0,
                "source": "wise_v3_quotes",
                "timestamp": now,
            },
            {
                "provider": "MoneyGram",
                "exchange_rate": 0,
                "receive_amount": 0,
                "status": "error",
                "fee": 0,
            },
        ]
    }
    rows = build_rates_table_rows(payload)
    assert len(rows) == 1
    assert rows[0]["provider"] == "Wise"
