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
        "last_updated": "2026-06-29T00:00:00+00:00",
        "all_rates": [
            {
                "provider": "Wise",
                "exchange_rate": 105.272,
                "delivery_method": "Bank Transfer",
                "fee": 0,
                "status": "ok",
            }
        ],
        "aud_npr_transfer_methods": {
            "rows": [
                {
                    "provider": "Wise",
                    "transfer_method": "Bank Transfer",
                    "new_user_rate": 105.272,
                    "existing_user_rate": 105.272,
                    "fee": 0,
                    "status": "ok",
                    "notes": "",
                }
            ]
        },
    }
    events = list(iter_cached_sse_events(payload))
    assert any(e.startswith("event: meta\n") for e in events)
    assert any("table_row" in e for e in events)
    assert any(e.startswith("event: done\n") for e in events)
