"""MoneyGram scraper — blocked by captcha; fails fast."""

from __future__ import annotations

from constants import MONEYGRAM_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class MoneyGramScraper(BaseBrowserScraper):
    provider_name = "MoneyGram"
    corridors = active_corridors(MONEYGRAM_LOCALE)

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "MoneyGram API blocked by bot protection; manual integration needed"
        )
