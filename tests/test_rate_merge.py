"""Tests for snapshot merge logic."""

from rate_merge import merge_payloads, merge_rate_records, merge_transfer_rows


def test_merge_rate_records_keeps_previous_ok_on_error():
    previous = [
        {
            "provider": "Wise",
            "from_currency": "AUD",
            "customer_type": "",
            "rate_label": "",
            "status": "ok",
            "exchange_rate": 105.0,
        }
    ]
    new = [
        {
            "provider": "Wise",
            "from_currency": "AUD",
            "customer_type": "",
            "rate_label": "",
            "status": "error",
            "exchange_rate": 0,
        }
    ]
    merged = merge_rate_records(new, previous)
    assert len(merged) == 1
    assert merged[0]["status"] == "ok"
    assert merged[0]["exchange_rate"] == 105.0


def test_merge_transfer_rows_skips_failed_without_previous():
    new = [
        {
            "provider": "MoneyGram",
            "transfer_method": "Bank Transfer",
            "status": "unavailable",
            "new_user_rate": None,
        }
    ]
    merged = merge_transfer_rows(new, [])
    assert merged == []


def test_merge_payloads_sets_snapshot_fields():
    merged = merge_payloads(
        {"all_rates": [], "last_updated": "now"},
        None,
        refresh_seconds=60,
    )
    assert merged["fetch_mode"] == "snapshot"
    assert merged["snapshot_refresh_seconds"] == 60
