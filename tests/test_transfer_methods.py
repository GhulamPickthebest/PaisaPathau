"""Tests for Remitly dual strict_promo merge logic."""

from transfer_methods.aud_npr import _remitly_estimates_by_method


def test_remitly_estimates_by_method_deduplicates():
    data = {
        "estimate": {"pay_out_method": "BANK_DEPOSIT", "receive_amount": "107200"},
        "pay_out_price_estimates": {
            "estimates": [
                {"pay_out_method": "DIRECT_TO_PHONE", "receive_amount": "107200"},
                {"pay_out_method": "CASH_PICKUP", "receive_amount": "107200"},
            ]
        },
    }
    by_method = _remitly_estimates_by_method(data)
    assert set(by_method.keys()) == {"BANK_DEPOSIT", "DIRECT_TO_PHONE", "CASH_PICKUP"}
