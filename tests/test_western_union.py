"""Tests for Western Union dual-rate helpers."""

from tier_b.western_union import scale_existing_receive


def test_scale_existing_receive_from_promo_ratio():
    # WU promo block at $100: 10347.36 existing, 10743.06 new
    existing = scale_existing_receive(107430.62, 10347.36, 10743.06)
    assert existing == 103473.62
