"""Tests for Instarem rate parsing."""

from tier_b.instarem import parse_instarem_computed_payload


def test_parse_instarem_uses_applied_fx_rate():
    payload = {
        "instarem_fx_rate": 105.7501,
        "regular_instarem_fx_rate": 105.7501,
        "fx_rate": 105.803,
        "transaction_config": {"fx_rate": 105.803},
        "transaction_fee_amount": 0,
        "regular_transaction_fee_amount": 9.5,
        "destination_amount": 105750.1,
    }

    parsed = parse_instarem_computed_payload(payload, 1000.0)

    assert parsed["new_rate"] == 105.7501
    assert parsed["existing_rate"] == 105.7501
    assert parsed["new_receive"] == 105750.1
    assert parsed["existing_receive"] == round(990.5 * 105.7501, 2)


def test_parse_instarem_falls_back_to_fx_rate():
    payload = {
        "fx_rate": 99.5,
        "transaction_config": {"fx_rate": 99.5},
        "transaction_fee_amount": 0,
        "regular_transaction_fee_amount": 0,
    }

    parsed = parse_instarem_computed_payload(payload, 100.0)

    assert parsed["new_rate"] == 99.5
    assert parsed["new_receive"] == 9950.0
