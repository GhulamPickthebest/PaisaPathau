"""OFX scraper — public calculator unavailable; fails fast."""

from __future__ import annotations

from constants import OFX_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class OfxScraper(BaseBrowserScraper):
    provider_name = "OFX"
    corridors = active_corridors(OFX_LOCALE)

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "OFX public quote endpoint unavailable"
        )
