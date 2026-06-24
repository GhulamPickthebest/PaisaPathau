"""Skrill — no public AUD→NPR guest quote API."""

from __future__ import annotations

from constants import SKRILL_LOCALE, active_corridors
from tier_b.unavailable import UnavailableQuoteScraper


class SkrillScraper(UnavailableQuoteScraper):
    provider_name = "Skrill"
    corridors = active_corridors(SKRILL_LOCALE)
    unavailable_reason = "Skrill requires sign-in; no public calculator API for AUD→NPR"
