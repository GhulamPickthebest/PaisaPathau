"""Xoom scraper — requires authenticated session; fails fast."""

from __future__ import annotations

from constants import XOOM_LOCALE
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class XoomScraper(BaseBrowserScraper):
    provider_name = "Xoom"
    corridors = list(XOOM_LOCALE.keys())

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "Xoom requires sign-in; public calculator API unavailable"
        )
