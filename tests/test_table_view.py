"""Tests for HTML table view helpers."""

from table_view import build_rates_table_rows, render_rates_html


def test_build_rates_table_rows_from_all_rates():
    payload = {
        "all_rates": [
            {
                "provider": "Wise",
                "exchange_rate": 105.32,
                "receive_amount": 103200,
                "delivery_method": "Card",
                "fee": 2.0,
                "rate_label": "New User",
                "transfer_speed": "Same day",
                "status": "ok",
                "source": "wise_v3_quotes",
                "timestamp": "2026-07-19T01:00:00+00:00",
            }
        ]
    }
    rows = build_rates_table_rows(payload)
    assert len(rows) == 1
    assert rows[0]["provider"] == "Wise"
    assert rows[0]["rate"] == 105.32
    assert rows[0]["payment_method"] == "Card"
    assert rows[0]["fee"] == 2.0
    assert "New User" in rows[0]["news"]


def test_build_rates_table_rows_prefers_transfer_matrix():
    payload = {
        "all_rates": [
            {
                "provider": "Wise",
                "status": "ok",
                "exchange_rate": 1,
                "receive_amount": 1,
                "timestamp": "2026-07-19T01:00:00+00:00",
            }
        ],
        "aud_npr_transfer_methods": {
            "last_updated": "2026-07-19T01:00:00+00:00",
            "rows": [
                {
                    "provider": "Wise",
                    "transfer_method": "Bank Transfer",
                    "new_user_rate": 107.31,
                    "existing_user_rate": 107.31,
                    "receive_amount_new": 106000,
                    "fee": 3.0,
                    "notes": "Public quote",
                    "status": "ok",
                    "quoted_at": "2026-07-19T01:00:00+00:00",
                }
            ],
        },
    }
    rows = build_rates_table_rows(payload)
    assert len(rows) == 1
    assert rows[0]["payment_method"] == "Bank Transfer"
    assert rows[0]["rate"] == 107.31


def test_render_rates_html_includes_table_headers():
    html = render_rates_html(
        {
            "send_amount": 1000,
            "last_updated": "2026-06-29T00:00:00+00:00",
            "all_rates": [
                {
                    "provider": "Wise",
                    "exchange_rate": 105.2729,
                    "receive_amount": 104000,
                    "delivery_method": "Bank Transfer",
                    "fee": 14.0,
                    "status": "ok",
                    "source": "wise_v3_quotes",
                    "timestamp": "2026-07-19T01:00:00+00:00",
                }
            ],
        }
    )
    assert "<th>Provider</th>" in html
    assert "Wise" in html
    assert "105.272" in html
    assert "105.273" not in html
