"""MoneyGram scraper — blocked by captcha; fails fast."""

from __future__ import annotations

from constants import MONEYGRAM_LOCALE
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError


class MoneyGramScraper(BaseBrowserScraper):
    provider_name = "MoneyGram"
    corridors = list(MONEYGRAM_LOCALE.keys())

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise PermanentScraperError(
            "MoneyGram API blocked by bot protection; manual integration needed"
        )
