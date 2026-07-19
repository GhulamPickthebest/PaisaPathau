"""Tests for SSE streaming helpers."""

import json

from stream_fetch import encode_sse, iter_cached_sse_events


def test_encode_sse_format():
    chunk = encode_sse("meta", {"send_amount": 1000})
    assert chunk.startswith("event: meta\n")
    assert "data: " in chunk
    assert json.loads(chunk.split("data: ", 1)[1].strip())["send_amount"] == 1000


def test_iter_cached_sse_events_replays_rows():
    payload = {
        "send_amount": 1000,
        "last_updated": "2026-07-19T01:00:00+00:00",
        "all_rates": [
            {
                "provider": "Wise",
                "exchange_rate": 105.272,
                "receive_amount": 104000,
                "delivery_method": "Bank Transfer",
                "fee": 14.0,
                "status": "ok",
                "source": "wise_v3_quotes",
                "timestamp": "2026-07-19T01:00:00+00:00",
            }
        ],
        "aud_npr_transfer_methods": {
            "last_updated": "2026-07-19T01:00:00+00:00",
            "rows": [
                {
                    "provider": "Wise",
                    "transfer_method": "Bank Transfer",
                    "new_user_rate": 105.272,
                    "existing_user_rate": 105.272,
                    "receive_amount_new": 104000,
                    "fee": 14.0,
                    "status": "ok",
                    "notes": "",
                    "quoted_at": "2026-07-19T01:00:00+00:00",
                }
            ],
        },
    }
    events = list(iter_cached_sse_events(payload))
    assert any(e.startswith("event: meta\n") for e in events)
    assert any("table_row" in e for e in events)
    assert any(e.startswith("event: done\n") for e in events)
