"""Tests for consumer-ready public quotes table."""

from models import utc_now_iso
from public_quotes import build_public_table_rows, is_valid_public_quote


def test_public_table_excludes_errors_and_zero_quotes():
    now = utc_now_iso()
    payload = {
        "last_updated": now,
        "all_rates": [
            {
                "provider": "Wise",
                "status": "ok",
                "exchange_rate": 106.0,
                "receive_amount": 104700,
                "fee": 14.33,
                "source": "wise_v3_quotes",
                "delivery_method": "Bank transfer",
                "timestamp": now,
            },
            {
                "provider": "MoneyGram",
                "status": "error",
                "exchange_rate": 0,
                "receive_amount": 0,
                "timestamp": now,
            },
            {
                "provider": "Remitly",
                "status": "error",
                "exchange_rate": 0,
                "receive_amount": 0,
                "timestamp": now,
            },
        ],
    }
    rows = build_public_table_rows(payload)
    providers = {row["provider"] for row in rows}
    assert providers == {"Wise"}
    assert rows[0]["fee"] == 14.33


def test_public_table_prefers_fee_inclusive_wise():
    now = utc_now_iso()
    payload = {
        "all_rates": [
            {
                "provider": "Wise (mid-market)",
                "status": "ok",
                "exchange_rate": 107.5,
                "receive_amount": 107500,
                "fee": 0,
                "source": "api",
                "timestamp": now,
            },
            {
                "provider": "Wise",
                "status": "ok",
                "exchange_rate": 106.0,
                "receive_amount": 104700,
                "fee": 14.33,
                "source": "wise_v3_quotes",
                "delivery_method": "Bank transfer",
                "timestamp": now,
            },
        ]
    }
    rows = build_public_table_rows(payload)
    assert len(rows) == 1
    assert rows[0]["provider"] == "Wise"
    assert rows[0]["fee"] == 14.33


def test_public_table_marks_fallback_and_keeps_timestamp():
    now = utc_now_iso()
    payload = {
        "all_rates": [
            {
                "provider": "Remitly",
                "status": "ok",
                "exchange_rate": 105.5,
                "receive_amount": 105000,
                "fee": 0,
                "delivery_method": "Bank deposit",
                "timestamp": now,
                "is_fallback": True,
                "quote_freshness": "fallback",
            }
        ]
    }
    rows = build_public_table_rows(payload)
    assert len(rows) == 1
    assert rows[0]["is_fallback"] is True
    assert rows[0]["quote_freshness"] == "fallback"
    assert rows[0]["quoted_at"] == now


def test_public_table_excludes_expired_quotes():
    payload = {
        "all_rates": [
            {
                "provider": "Xe Money Transfer",
                "status": "ok",
                "exchange_rate": 104.0,
                "receive_amount": 104000,
                "fee": 0,
                "delivery_method": "Bank transfer",
                # Older than default 24h expire window.
                "timestamp": "2026-07-01T01:00:00+00:00",
            }
        ]
    }
    assert build_public_table_rows(payload) == []


def test_admin_lists_missing_configured_providers():
    from public_quotes import build_admin_diagnostics

    payload = {
        "last_updated": utc_now_iso(),
        "all_rates": [
            {
                "provider": "Wise",
                "status": "ok",
                "exchange_rate": 106.0,
                "receive_amount": 104700,
                "fee": 14.0,
                "source": "wise_v3_quotes",
                "timestamp": utc_now_iso(),
            }
        ],
        "aud_npr_transfer_methods": {"rows": []},
        "errors": [],
    }
    admin = build_admin_diagnostics(payload)
    missing = {
        item["provider"]: item["status"]
        for item in admin["unavailable"]
        if item.get("status") == "missing"
    }
    assert missing.get("Skrill") == "missing"


def test_is_valid_public_quote_requires_receive():
    assert not is_valid_public_quote(
        {"status": "ok", "exchange_rate": 105, "receive_amount": 0}
    )
    assert is_valid_public_quote(
        {"status": "ok", "exchange_rate": 105, "receive_amount": 100}
    )


def test_is_valid_public_quote_requires_receive():
    assert not is_valid_public_quote(
        {"status": "ok", "exchange_rate": 105, "receive_amount": 0}
    )
    assert is_valid_public_quote(
        {"status": "ok", "exchange_rate": 105, "receive_amount": 100}
    )
