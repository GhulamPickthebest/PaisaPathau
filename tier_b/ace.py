"""ACE Money Transfer — no public guest quote API."""

from __future__ import annotations

from constants import ACE_LOCALE, active_corridors
from tier_b.unavailable import UnavailableQuoteScraper


class AceScraper(UnavailableQuoteScraper):
    provider_name = "ACE Money Transfer"
    corridors = active_corridors(ACE_LOCALE)
    unavailable_reason = "ACE Money Transfer quote API blocked; sign-in required"
