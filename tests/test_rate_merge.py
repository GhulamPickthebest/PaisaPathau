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
            "receive_amount": 105000.0,
            "fee": 14.0,
            "timestamp": "2026-07-18T01:00:00+00:00",
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
            "receive_amount": 0,
        }
    ]
    merged = merge_rate_records(new, previous)
    assert len(merged) == 1
    assert merged[0]["status"] == "ok"
    assert merged[0]["exchange_rate"] == 105.0
    assert merged[0]["is_fallback"] is True
    assert merged[0]["quote_freshness"] == "fallback"
    assert merged[0]["timestamp"] == "2026-07-18T01:00:00+00:00"


def test_merge_rate_records_omits_error_without_previous():
    new = [
        {
            "provider": "Remitly",
            "from_currency": "AUD",
            "customer_type": "",
            "rate_label": "",
            "status": "error",
            "exchange_rate": 0,
            "receive_amount": 0,
        }
    ]
    assert merge_rate_records(new, []) == []


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


def test_merge_payloads_matrix_last_updated_uses_new():
    previous = {
        "all_rates": [],
        "last_updated": "old",
        "aud_npr_transfer_methods": {
            "last_updated": "2026-07-17T00:00:00+00:00",
            "rows": [
                {
                    "provider": "Wise",
                    "transfer_method": "Bank Transfer",
                    "status": "ok",
                    "new_user_rate": 100.0,
                    "receive_amount_new": 100000,
                    "quoted_at": "2026-07-17T00:00:00+00:00",
                }
            ],
        },
    }
    new = {
        "all_rates": [],
        "last_updated": "2026-07-18T12:00:00+00:00",
        "aud_npr_transfer_methods": {
            "last_updated": "2026-07-18T12:00:00+00:00",
            "rows": [
                {
                    "provider": "Wise",
                    "transfer_method": "Bank Transfer",
                    "status": "ok",
                    "new_user_rate": 101.0,
                    "receive_amount_new": 101000,
                    "fee": 14.0,
                }
            ],
        },
    }
    merged = merge_payloads(new, previous, refresh_seconds=60)
    matrix = merged["aud_npr_transfer_methods"]
    assert matrix["last_updated"] == "2026-07-18T12:00:00+00:00"
    assert matrix["rows"][0]["is_fallback"] is False


def test_merge_payloads_sets_snapshot_fields():
    merged = merge_payloads(
        {"all_rates": [], "last_updated": "now"},
        None,
        refresh_seconds=60,
    )
    assert merged["fetch_mode"] == "snapshot"
    assert merged["snapshot_refresh_seconds"] == 60
