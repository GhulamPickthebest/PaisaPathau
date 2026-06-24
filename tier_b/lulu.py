"""LuLu Exchange — browser marketing site (indicative rates; app for live quotes)."""

from __future__ import annotations

import re

from constants import LULU_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from tier_b.browser_helpers import dismiss_cookie_banners
from utils import PermanentScraperError, retry

LULU_HOME_URL = "https://www.lulumoney.com/"
LULU_TRANSFER_URL = "https://luluexchange.com/services/money-transfer/"


class LuLuScraper(BaseBrowserScraper):
    provider_name = "LuLu Exchange"
    corridors = active_corridors(LULU_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError("LuLu browser scraper only supports AUD")

        with self.page_context(context_options=AU_CONTEXT) as page:
            captured_rate: float | None = None

            def on_response(response) -> None:
                nonlocal captured_rate
                if response.status != 200:
                    return
                url = response.url.lower()
                if not any(token in url for token in ("rate", "exchange", "remit", "quote")):
                    return
                if "lulu" not in url:
                    return
                try:
                    data = response.json()
                    captured_rate = _extract_npr_rate(data) or captured_rate
                except Exception:
                    pass

            page.on("response", on_response)

            for url in (LULU_HOME_URL, LULU_TRANSFER_URL):
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                page.wait_for_timeout(4000)
                dismiss_cookie_banners(page)
                if captured_rate:
                    break

                body = page.inner_text("body")
                text_rate = _parse_rate_from_text(body)
                if text_rate:
                    captured_rate = text_rate
                    break

        if not captured_rate:
            raise PermanentScraperError(
                "LuLu live AUD→NPR rate only in LuLu Money app; website has no guest API"
            )

        fee = 0.0
        receive = round(self.send_amount * captured_rate, 2)
        return self._build_record(
            from_currency=from_currency,
            exchange_rate=captured_rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed="Same day to 2 business days",
            delivery_method="Bank transfer (LuLu Now)",
        )


def _parse_rate_from_text(body: str) -> float | None:
    patterns = [
        r"1(?:\.00)?\s*AUD\s*=\s*([\d,.]+)\s*NPR",
        r"AUD\s*to\s*NPR[^\d]*([\d,.]+)",
        r"Nepal[^\d]*([\d,.]+)\s*NPR",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(",", ""))
            if value > 50:
                return value
    return None


def _extract_npr_rate(data: object) -> float | None:
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = str(key).lower()
            if "npr" in key_lower and isinstance(value, (int, float, str)):
                try:
                    rate = float(value)
                    if rate > 50:
                        return rate
                except ValueError:
                    pass
            nested = _extract_npr_rate(value)
            if nested:
                return nested
    elif isinstance(data, list):
        for item in data:
            nested = _extract_npr_rate(item)
            if nested:
                return nested
    return None
