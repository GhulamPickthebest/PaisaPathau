"""Skrill Money Transfer — browser calculator (AU→NPR)."""

from __future__ import annotations

from typing import Any

from constants import SKRILL_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from tier_b.browser_helpers import dismiss_cookie_banners
from utils import retry

SKRILL_CALCULATOR_URL = "https://transfers.skrill.com/smt/calculator/"


class SkrillScraper(BaseBrowserScraper):
    provider_name = "Skrill"
    corridors = active_corridors(SKRILL_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError("Skrill browser scraper only supports AUD")

        preview: dict[str, Any] | None = None

        with self.page_context(context_options=AU_CONTEXT) as page:
            def on_response(response) -> None:
                nonlocal preview
                if (
                    "transfers.skrill.com/api/transfers/v4/preview" in response.url
                    and response.status == 200
                ):
                    try:
                        payload = response.json()
                        amounts = payload.get("amounts") or {}
                        if float(amounts.get("fxRate") or 0) > 95:
                            preview = payload
                    except Exception:
                        pass

            page.on("response", on_response)
            page.goto(SKRILL_CALCULATOR_URL, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(3000)
            dismiss_cookie_banners(page)

            page.locator(".country-select").first.click()
            page.wait_for_timeout(800)
            page.get_by_text("Australia", exact=False).first.click(timeout=8000)
            page.wait_for_timeout(1500)

            page.locator(".country-select").nth(1).click()
            page.wait_for_timeout(800)
            page.get_by_text("Nepal", exact=False).first.click(timeout=8000)
            page.wait_for_timeout(1500)

            page.locator("input").first.fill(str(int(self.send_amount)), force=True)
            page.wait_for_timeout(5000)

        if not preview:
            raise ValueError("Skrill preview API did not return AUD→NPR quote")

        amounts = preview["amounts"]
        rate = float(amounts["fxRate"])
        receive = float(amounts["receive"])
        send = float(amounts["send"])
        total = float(amounts.get("total") or send)
        fee = round(max(send - total, float(amounts.get("fee") or 0)), 2)

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed="Minutes to 2 business days",
            delivery_method="Bank account / eSewa",
        )
