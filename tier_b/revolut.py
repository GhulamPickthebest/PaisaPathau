"""Revolut — attempt public remittance pages (NPR rarely exposed)."""

from __future__ import annotations

import re

from constants import REVOLUT_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from tier_b.browser_helpers import dismiss_cookie_banners, parse_aud_npr_rate
from utils import PermanentScraperError, retry

REVOLUT_SEND_URL = "https://www.revolut.com/money-transfer/"


class RevolutScraper(BaseBrowserScraper):
    provider_name = "Revolut"
    corridors = active_corridors(REVOLUT_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError("Revolut browser scraper only supports AUD")

        with self.page_context(context_options=AU_CONTEXT) as page:
            api_quote: dict | None = None

            def on_response(response) -> None:
                nonlocal api_quote
                if response.status != 200:
                    return
                url = response.url
                if "revolut.com/api" not in url:
                    return
                if not any(token in url for token in ("quote", "rate", "remit", "fx")):
                    return
                try:
                    payload = response.json()
                    if isinstance(payload, dict) and (
                        "rate" in payload or "exchangeRate" in payload or "receive" in payload
                    ):
                        api_quote = payload
                except Exception:
                    pass

            page.on("response", on_response)
            page.goto(REVOLUT_SEND_URL, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(5000)
            dismiss_cookie_banners(page)

            for text in ("Australia", "Nepal", "AUD", "NPR"):
                try:
                    page.get_by_text(text, exact=False).first.click(timeout=2000)
                    page.wait_for_timeout(800)
                except Exception:
                    pass

            amount = page.locator("input[type='number'], input[inputmode='decimal']").first
            if amount.count():
                amount.fill(str(int(self.send_amount)), force=True)
                page.wait_for_timeout(4000)

            if api_quote:
                rate = float(
                    api_quote.get("rate")
                    or api_quote.get("exchangeRate")
                    or 0
                )
                fee = float(api_quote.get("fee") or 0)
                receive = float(api_quote.get("receive") or api_quote.get("receiveAmount") or 0)
                if rate > 0 and receive > 0:
                    return self._build_record(
                        from_currency=from_currency,
                        exchange_rate=rate,
                        fee=fee,
                        receive_amount=receive,
                        transfer_speed="Minutes to 2 business days",
                        delivery_method="Bank transfer",
                    )

            body = page.inner_text("body")
            rate = parse_aud_npr_rate(body)
            if rate:
                return self._build_record(
                    from_currency=from_currency,
                    exchange_rate=rate,
                    fee=0.0,
                    receive_amount=round(self.send_amount * rate, 2),
                    transfer_speed="Minutes to 2 business days",
                    delivery_method="Bank transfer",
                )

        raise PermanentScraperError(
            "Revolut does not expose AUD→NPR on public web/API (app login required)"
        )
