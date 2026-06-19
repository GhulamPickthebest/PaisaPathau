"""Tests for Western Union transfer-method helpers."""

from tier_b.western_union import scale_existing_receive
from tier_b.western_union_transfer_methods import (
    existing_rate_for_method,
    parse_modal_options,
)

SAMPLE_MODAL = """
How will your receiver get the money?
Cash pickup
Delivery in minutes
1 AUD = 103.8234 NPR
Popular
Bank account
Delivery in 0-4 business days
1 AUD = 107.1927 NPR
Confirm
"""


def test_parse_modal_options_extracts_bank_and_cash():
    options = parse_modal_options(SAMPLE_MODAL)
    assert len(options) == 2
    assert options[0]["label"] == "Cash pickup"
    assert options[0]["rate"] == 103.8234
    assert options[0]["speed"] == "minutes"
    assert options[1]["label"] == "Bank account"
    assert options[1]["rate"] == 107.1927
    assert options[1]["speed"] == "0-4 business days"


def test_existing_rate_for_bank_uses_landing_promo_ratio():
    existing_rate, existing_receive = existing_rate_for_method(
        "Bank account",
        new_rate=107.1927,
        new_receive=107192.7,
        promo_ratio=(10336.67, 10719.27),
    )
    assert existing_receive == scale_existing_receive(107192.7, 10336.67, 10719.27)
    assert existing_rate == round(existing_receive / 1000, 4)


def test_existing_rate_for_cash_matches_new_rate():
    existing_rate, existing_receive = existing_rate_for_method(
        "Cash pickup",
        new_rate=103.8234,
        new_receive=103823.4,
        promo_ratio=(10336.67, 10719.27),
    )
    assert existing_rate == 103.8234
    assert existing_receive == 103823.4
