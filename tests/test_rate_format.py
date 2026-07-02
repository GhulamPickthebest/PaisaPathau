"""Tests for exchange rate precision helpers."""

from utils import format_exchange_rate, truncate_decimal


def test_truncate_decimal_does_not_round_up():
    assert truncate_decimal(105.2729, 3) == 105.272
    assert truncate_decimal(105.2499, 3) == 105.249


def test_format_exchange_rate_shows_three_decimals():
    assert format_exchange_rate(105.2729) == "105.272"
    assert format_exchange_rate(105.249) == "105.249"


def test_format_exchange_rate_handles_none():
    assert format_exchange_rate(None) == "—"
