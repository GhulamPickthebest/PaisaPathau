"""Xe Money Transfer scraper via public currency converter."""

from __future__ import annotations

import re

from constants import XE_LOCALE, active_corridors
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError, retry


class XeScraper(BaseBrowserScraper):
    provider_name = "Xe Money Transfer"
    corridors = active_corridors(XE_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        url = (
            "https://www.xe.com/currencyconverter/convert/"
            f"?Amount={int(self.send_amount)}&From={from_currency}&To=NPR"
        )

        with self.page_context() as page:
            page.goto(url, wait_until="commit", timeout=self.timeout)
            page.wait_for_timeout(6000)

            body = page.inner_text("body")
            patterns = [
                rf"1\.00\s*{from_currency}\s*=\s*([\d,.]+)\s*NPR",
                rf"1\s*{from_currency}\s*=\s*([\d,.]+)\s*NPR",
            ]
            rate: float | None = None
            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    rate = float(match.group(1).replace(",", ""))
                    break

            if not rate:
                raise PermanentScraperError(
                    f"Could not parse Xe rate for {from_currency}"
                )

            fee = self._parse_fee_from_page(page)
            return self._build_record(
                from_currency=from_currency,
                exchange_rate=rate,
                fee=fee,
                transfer_speed="1-4 business days",
                delivery_method="Bank transfer",
            )
