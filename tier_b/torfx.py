"""TorFX scraper — Cloudflare protected; fails fast."""

from __future__ import annotations

from constants import TORFX_LOCALE
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class TorFxScraper(BaseBrowserScraper):
    provider_name = "TorFX"
    corridors = list(TORFX_LOCALE.keys())

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "TorFX blocked by Cloudflare bot protection"
        )
