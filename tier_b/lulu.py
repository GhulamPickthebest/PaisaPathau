"""LuLu Exchange / LuLu Money — no public guest quote API."""

from __future__ import annotations

from constants import LULU_LOCALE, active_corridors
from tier_b.unavailable import UnavailableQuoteScraper


class LuLuScraper(UnavailableQuoteScraper):
    provider_name = "LuLu Exchange"
    corridors = active_corridors(LULU_LOCALE)
    unavailable_reason = "LuLu Money public rate API unavailable for AUD→NPR"
