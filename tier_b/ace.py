"""ACE Money Transfer — browser calculator on homepage."""

from __future__ import annotations

import re

from constants import ACE_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from tier_b.browser_helpers import dismiss_cookie_banners, parse_aud_npr_rate
from utils import retry

ACE_HOME_URL = "https://acemoneytransfer.com/"


class AceScraper(BaseBrowserScraper):
    provider_name = "ACE Money Transfer"
    corridors = active_corridors(ACE_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError("ACE browser scraper only supports AUD")

        with self.page_context(context_options=AU_CONTEXT) as page:
            page.goto(ACE_HOME_URL, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(3000)
            dismiss_cookie_banners(page)

            self._select_corridor(page)
            page.wait_for_timeout(3000)

            amount_input = page.locator(
                "input[type='number'], input[name*='amount'], input[placeholder*='Amount']"
            ).first
            if amount_input.count():
                amount_input.fill(str(int(self.send_amount)), force=True)
                page.wait_for_timeout(3000)

            body = page.inner_text("body")
            rate = parse_aud_npr_rate(body)
            if not rate:
                rate = self._parse_converted_amount(body)
            if not rate:
                raise ValueError("ACE calculator rate not visible (login may be required)")

            fee = self._parse_fee(body)
            receive = round((self.send_amount - fee) * rate, 2)

            return self._build_record(
                from_currency=from_currency,
                exchange_rate=rate,
                fee=fee,
                receive_amount=receive,
                transfer_speed="Same day to 3 business days",
                delivery_method="Bank / IME Pay / Cash pickup",
            )

    def _select_corridor(self, page) -> None:
        selected = page.evaluate(
            """() => {
                const selects = Array.from(document.querySelectorAll('select'));
                const from = selects.find(s => s.name?.includes('send') || s.className.includes('sending'));
                const to = selects.find(s => s.name?.includes('receiv') || s.className.includes('receiving'));
                let ok = false;
                for (const select of selects) {
                    for (const opt of select.options) {
                        const label = (opt.textContent || '').toLowerCase();
                        if (label.includes('australia')) {
                            select.value = opt.value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            ok = true;
                        }
                    }
                }
                for (const select of selects) {
                    for (const opt of select.options) {
                        const label = (opt.textContent || '').toLowerCase();
                        if (label.includes('nepal')) {
                            select.value = opt.value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            ok = true;
                        }
                    }
                }
                return ok;
            }"""
        )
        if selected:
            return

        page.locator(".select2-selection").first.click(force=True, timeout=5000)
        page.wait_for_timeout(500)
        page.locator(".select2-search__field").first.fill("Australia")
        page.wait_for_timeout(500)
        page.locator(".select2-results__option").filter(has_text="Australia").first.click(
            force=True, timeout=5000
        )
        page.wait_for_timeout(800)

        page.locator(".select2-selection").nth(1).click(force=True, timeout=5000)
        page.wait_for_timeout(500)
        page.locator(".select2-search__field").first.fill("Nepal")
        page.wait_for_timeout(500)
        page.locator(".select2-results__option").filter(has_text="Nepal").first.click(
            force=True, timeout=5000
        )

    def _parse_converted_amount(self, body: str) -> float | None:
        match = re.search(
            r"([\d,.]+)\s*NPR",
            body,
            re.IGNORECASE,
        )
        if not match:
            return None
        receive = float(match.group(1).replace(",", ""))
        if receive > self.send_amount * 10:
            return receive / self.send_amount
        return None

    def _parse_fee(self, body: str) -> float:
        match = re.search(r"fee[^\d$]*\$?\s*([\d,.]+)", body, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
        return 0.0
