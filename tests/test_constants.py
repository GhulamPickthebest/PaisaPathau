"""Tests for corridor and provider coverage constants."""

from constants import (
    ACTIVE_SEND_CURRENCIES,
    AUD_NPR_PROVIDERS,
    PROVIDER_PRIORITY,
    TIER_B_CORRIDORS,
    TIER_C_CURRENCIES,
    active_corridors,
)


def test_aud_only_scope():
    assert ACTIVE_SEND_CURRENCIES == ["AUD"]
    assert TIER_C_CURRENCIES == []


def test_tier_b_corridor_matrix_matches_active_currencies():
    for provider, corridors in TIER_B_CORRIDORS.items():
        assert provider in PROVIDER_PRIORITY
        assert corridors == ["AUD"], f"{provider} should be AUD-only for now"


def test_all_tier_b_providers_registered():
    from tier_b import API_SCRAPERS, BROWSER_SCRAPERS, NO_QUOTE_SCRAPERS

    registered = {
        cls.provider_name
        for cls in API_SCRAPERS + BROWSER_SCRAPERS + NO_QUOTE_SCRAPERS
    }
    assert registered == set(TIER_B_CORRIDORS.keys())


def test_active_corridors_filters_send_currencies():
    from constants import REMITLY_LOCALE

    assert active_corridors(REMITLY_LOCALE) == ["AUD"]


def test_aud_npr_provider_list():
    expected = {
        "Wise",
        "Remitly",
        "WorldRemit",
        "Xoom (PayPal)",
        "MoneyGram",
        "Western Union",
        "Instarem",
        "Xe Money Transfer",
        "Skrill",
        "Ria Money Transfer",
        "Instarem (by Nium)",
        "Revolut",
        "ACE Money Transfer",
        "LuLu Exchange",
        "Taptap Send",
    }
    assert set(AUD_NPR_PROVIDERS) == expected
