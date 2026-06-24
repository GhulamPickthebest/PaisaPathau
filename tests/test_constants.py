"""Tests for corridor and provider coverage constants."""

from constants import (
    ACTIVE_SEND_CURRENCIES,
    PROVIDER_PRIORITY,
    TIER_B_CORRIDORS,
    TIER_C_CURRENCIES,
    active_corridors,
)


def test_tier_b_corridor_matrix_matches_active_currencies():
    for provider, corridors in TIER_B_CORRIDORS.items():
        assert provider in PROVIDER_PRIORITY
        for currency in corridors:
            assert currency in ACTIVE_SEND_CURRENCIES, (
                f"{provider} lists {currency} but it is not in ACTIVE_SEND_CURRENCIES"
            )


def test_all_tier_b_providers_registered():
    from tier_b import API_SCRAPERS, BROWSER_SCRAPERS

    registered = {
        cls.provider_name
        for cls in API_SCRAPERS + BROWSER_SCRAPERS
    }
    assert registered == set(TIER_B_CORRIDORS.keys())


def test_active_corridors_filters_send_currencies():
    from constants import REMITLY_LOCALE

    corridors = active_corridors(REMITLY_LOCALE)
    assert corridors == ["AUD", "USD", "GBP", "CAD", "NZD", "EUR", "AED"]


def test_tier_c_includes_gulf_and_asia_reference_currencies():
    for currency in ("QAR", "KWD", "JPY", "EUR", "INR"):
        assert currency in TIER_C_CURRENCIES
