"""Tests for Wise v3 quotes helper."""

from unittest.mock import MagicMock, patch

from tier_b.wise_quotes import fetch_wise_transfer_quote


def test_fetch_wise_transfer_quote_parses_v3_response():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "rate": 106.093,
        "rateTimestamp": "2026-07-10T02:00:00Z",
        "paymentOptions": [
            {
                "payIn": "BANK_TRANSFER",
                "payOut": "BANK_TRANSFER",
                "targetAmount": 104716.0,
                "formattedEstimatedDelivery": "in 30 minutes",
                "fee": {"total": 13.27, "transferwise": 13.27},
            }
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("tier_b.wise_quotes.requests.post", return_value=mock_response):
        quote = fetch_wise_transfer_quote("AUD", send_amount=1000)

    assert quote["rate"] == 106.093
    assert quote["fee"] == 13.27
    assert quote["receive_amount"] == 104716.0
    assert quote["source"] == "wise_v3_quotes"
    assert quote["rate_timestamp"] == "2026-07-10T02:00:00Z"
