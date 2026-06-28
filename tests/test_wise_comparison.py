"""Tests for Wise comparison helper and Xoom scraper."""

from unittest.mock import MagicMock, patch

from tier_b.wise_comparison import fetch_comparison_quote
from tier_b.western_union_api import WesternUnionApiScraper
from tier_b.xoom import XoomScraper


def test_fetch_comparison_quote_parses_xoom():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "providers": [
            {
                "alias": "xoom",
                "quotes": [
                    {
                        "rate": 102.5,
                        "fee": 0.0,
                        "receivedAmount": 102500.0,
                        "deliveryEstimation": {"duration": {"min": "PT5M"}},
                    }
                ],
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("tier_b.wise_comparison.requests.get", return_value=mock_response):
        quote = fetch_comparison_quote("xoom", "AUD", send_amount=1000)

    assert quote["rate"] == 102.5
    assert quote["receive_amount"] == 102500.0


def test_xoom_scraper_builds_record():
    with patch(
        "tier_b.xoom.fetch_comparison_quote",
        return_value={
            "rate": 102.5,
            "fee": 0.0,
            "receive_amount": 102500.0,
            "delivery": {},
        },
    ):
        record = XoomScraper(send_amount=1000).fetch_corridor("AUD")

    assert record.status == "ok"
    assert record.provider == "Xoom (PayPal)"
    assert record.exchange_rate == 102.5


def test_western_union_api_scraper_builds_record():
    with patch(
        "tier_b.western_union_api.fetch_comparison_quote",
        return_value={
            "rate": 101.2,
            "fee": 2.9,
            "receive_amount": 101200.0,
            "delivery": {"min": "PT5M", "max": "P1D"},
        },
    ):
        record = WesternUnionApiScraper(send_amount=1000).fetch_corridor("AUD")

    assert record.status == "ok"
    assert record.provider == "Western Union"
    assert record.exchange_rate == 101.2
    assert record.source == "wise_comparison"
