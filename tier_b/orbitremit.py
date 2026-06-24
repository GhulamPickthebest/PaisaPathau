"""OrbitRemit scraper — Cloudflare protected; fails fast."""

from __future__ import annotations

from constants import ORBITREMIT_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class OrbitRemitScraper(BaseBrowserScraper):
    provider_name = "OrbitRemit"
    corridors = active_corridors(ORBITREMIT_LOCALE)

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "OrbitRemit blocked by Cloudflare bot protection"
        )
