"""Ria Money Transfer — calculator API blocked from server IPs."""

from __future__ import annotations

from constants import RIA_LOCALE, active_corridors
from tier_b.unavailable import UnavailableQuoteScraper


class RiaScraper(UnavailableQuoteScraper):
    provider_name = "Ria Money Transfer"
    corridors = active_corridors(RIA_LOCALE)
    unavailable_reason = (
        "Ria calculator API blocks automated access; browser integration needed"
    )
