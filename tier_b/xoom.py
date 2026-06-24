"""Xoom scraper — requires authenticated session; fails fast."""

from __future__ import annotations

from constants import XOOM_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class XoomScraper(BaseBrowserScraper):
    provider_name = "Xoom (PayPal)"
    corridors = active_corridors(XOOM_LOCALE)

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "Xoom (PayPal) requires sign-in; no public AUD→NPR calculator"
        )
