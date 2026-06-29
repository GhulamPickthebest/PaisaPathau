"""Providers without a public guest quote — fail fast without Playwright."""

from __future__ import annotations

from constants import (
    ACE_LOCALE,
    LULU_LOCALE,
    MONEYGRAM_LOCALE,
    REVOLUT_LOCALE,
    active_corridors,
)
from tier_b.unavailable import UnavailableQuoteScraper


class MoneyGramUnavailableScraper(UnavailableQuoteScraper):
    provider_name = "MoneyGram"
    corridors = active_corridors(MONEYGRAM_LOCALE)
    unavailable_reason = "Fee-quote API blocked (captcha/partner API required)"


class AceUnavailableScraper(UnavailableQuoteScraper):
    provider_name = "ACE Money Transfer"
    corridors = active_corridors(ACE_LOCALE)
    unavailable_reason = "Calculator rate requires login; no guest quote"


class LuLuUnavailableScraper(UnavailableQuoteScraper):
    provider_name = "LuLu Exchange"
    corridors = active_corridors(LULU_LOCALE)
    unavailable_reason = "Live rates only in LuLu Money app after eKYC"


class RevolutUnavailableScraper(UnavailableQuoteScraper):
    provider_name = "Revolut"
    corridors = active_corridors(REVOLUT_LOCALE)
    unavailable_reason = "AUD→NPR not on public web/API (app login required)"
