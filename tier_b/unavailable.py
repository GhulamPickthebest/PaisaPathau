"""Base scraper for providers without a public guest quote API."""

from __future__ import annotations

from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class UnavailableQuoteScraper(BaseBrowserScraper):
    """Fails fast with a documented reason (still appears in output as error)."""

    unavailable_reason: str = "No public quote API available"

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(self.unavailable_reason)
