"""Taptap Send — mobile app API requires client headers."""

from __future__ import annotations

from constants import TAPTAP_LOCALE, active_corridors
from tier_b.unavailable import UnavailableQuoteScraper


class TaptapSendScraper(UnavailableQuoteScraper):
    provider_name = "Taptap Send"
    corridors = active_corridors(TAPTAP_LOCALE)
    unavailable_reason = (
        "Taptap Send fxRates API requires mobile app credentials; "
        "AUD→NPR corridor may be unsupported"
    )
