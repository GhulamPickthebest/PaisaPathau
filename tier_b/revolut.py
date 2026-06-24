"""Revolut — no public remittance quote for AUD→NPR."""

from __future__ import annotations

from constants import REVOLUT_LOCALE, active_corridors
from tier_b.unavailable import UnavailableQuoteScraper


class RevolutScraper(UnavailableQuoteScraper):
    provider_name = "Revolut"
    corridors = active_corridors(REVOLUT_LOCALE)
    unavailable_reason = "Revolut public quote API does not support AUD→NPR corridor"
