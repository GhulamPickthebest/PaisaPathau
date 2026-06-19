"""Western Union AUD/NPR per-method quotes via the public send-money estimate flow."""

from __future__ import annotations

import re

from tier_b.base import BaseBrowserScraper
from tier_b.western_union import WesternUnionScraper, scale_existing_receive
from utils import logger, retry

WU_SEND_START = "https://www.westernunion.com/au/en/web/send-money/start"

PAYOUT_TO_METHOD = {
    "Bank account": "Bank Transfer",
    "Cash pickup": "Cash Pickup",
    "Mobile wallet": "Mobile Money Transfer",
    "Mobile Wallet": "Mobile Money Transfer",
}

MODAL_OPTION_PATTERN = re.compile(
    r"(Cash pickup|Bank account|Mobile wallet|Mobile Wallet)(.*?)(?=Cash pickup|Bank account|Mobile wallet|Mobile Wallet|$)",
    re.IGNORECASE | re.DOTALL,
)
RATE_PATTERN = re.compile(r"1\s*AUD\s*=\s*([\d,.]+)")
SPEED_PATTERN = re.compile(
    r"(?:Delivery in|Available in)\s+([^\n|]+)", re.IGNORECASE
)
FEE_PATTERN = re.compile(r"([\d,.]+)")


class WesternUnionTransferMethodsScraper(BaseBrowserScraper):
    provider_name = "Western Union"
    corridors = ["AUD"]

    @retry(exceptions=(Exception,))
    def fetch_method_quotes(self, send_amount: float | None = None) -> list[dict]:
        amount = send_amount or self.send_amount
        existing_ratio = self._landing_promo_ratio()

        with self.page_context() as page:
            self._navigate_to_calculator(page)
            self._set_send_amount(page, amount)
            modal_options = self._read_modal_options(page)
            quotes: list[dict] = []

            for index, option in enumerate(modal_options):
                label = option["label"]
                if index == 0 and self._current_payout_label(page) == label:
                    quote = self._read_quote(page)
                else:
                    self._select_payout(page, label)
                    quote = self._read_quote(page)
                method = PAYOUT_TO_METHOD.get(label, label)
                new_rate = quote["rate"]
                new_receive = quote["receive"]
                existing_rate, existing_receive = existing_rate_for_method(
                    label, new_rate, new_receive, existing_ratio
                )
                quotes.append(
                    {
                        "transfer_method": method,
                        "fee": quote["promo_fee"],
                        "new_user_rate": new_rate,
                        "existing_user_rate": existing_rate,
                        "fastest_speed": quote["speed"],
                        "slowest_speed": quote["speed"],
                        "send_amount": amount,
                        "receive_amount_new": new_receive,
                        "receive_amount_existing": existing_receive,
                        "notes": (
                            "Send-money estimate flow (guest); "
                            f"regular fee AUD {quote['regular_fee']:.2f}"
                        ),
                    }
                )

            logger.info(
                "Western Union AUD/NPR send-flow methods: %s quotes",
                len(quotes),
            )
            return quotes

    def fetch_corridor(self, from_currency: str):
        raise NotImplementedError("Use fetch_method_quotes() for transfer-method matrix")

    def _landing_promo_ratio(self) -> tuple[float, float] | None:
        """Return (existing_ref, new_ref) receive amounts from the landing-page promo block."""
        try:
            records = WesternUnionScraper(send_amount=100).fetch_corridor_records("AUD")
        except Exception as exc:
            logger.warning("WU landing promo unavailable: %s", exc)
            return None

        by_type = {r.customer_type: r for r in records if r.status == "ok"}
        new_rec = by_type.get("new_user")
        existing_rec = by_type.get("existing_user")
        if not new_rec or not existing_rec or new_rec.receive_amount <= 0:
            return None
        return existing_rec.receive_amount, new_rec.receive_amount

    def _navigate_to_calculator(self, page, max_attempts: int = 6) -> None:
        for _ in range(max_attempts):
            page.goto(WU_SEND_START, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(2000)
            page.locator("#input_country_selection_search").fill("Nepal")
            page.wait_for_timeout(1000)
            page.locator("text=Nepal").first.click()
            page.locator("#btn_country_selection_continue").click()
            page.wait_for_timeout(3000)
            page.locator('button:has-text("Continue")').last.click()
            page.wait_for_timeout(6000)
            if "Delivery method" in page.inner_text("body"):
                return
        raise ValueError("Western Union send-flow calculator did not load")

    def _set_send_amount(self, page, amount: float) -> None:
        field = page.locator("#input-estimate_details_sender_field")
        field.click(click_count=3)
        field.fill(str(int(amount)))
        page.keyboard.press("Tab")
        page.wait_for_timeout(4000)

    def _read_modal_options(self, page) -> list[dict]:
        self._open_payout_modal(page)
        modal = page.locator(".ReactModalPortal").filter(has_text="receiver get").first
        modal_text = modal.inner_text()
        options = parse_modal_options(modal_text)
        self._close_payout_modal(page)
        return options

    def _open_payout_modal(self, page) -> None:
        page.locator("#control_select-dropdown_estimate_details_payout").click(force=True)
        page.wait_for_timeout(2000)

    def _close_payout_modal(self, page) -> None:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

    def _current_payout_label(self, page) -> str:
        payout = page.locator("#select-dropdown_estimate_details_payout_value").inner_text()
        return _normalize_payout_label(re.sub(r"\d+$", "", payout.strip()))

    def _select_payout(self, page, label: str) -> None:
        self._open_payout_modal(page)
        modal = page.locator(".ReactModalPortal").filter(has_text="receiver get").first
        modal.locator(f"text={label}").first.click(force=True)
        page.wait_for_timeout(1000)
        modal.locator('button:has-text("Confirm")').first.click(force=True)
        page.wait_for_timeout(4000)

    def _read_quote(self, page) -> dict:
        send = _parse_amount(page.locator("#input-estimate_details_sender_field").input_value())
        receive = _parse_amount(
            page.locator("#input-estimate_details_receiver_field").input_value()
        )
        fee_text = page.locator("#text_estimate_details_fees").inner_text()
        float_text = page.locator("#float-container-").inner_text()
        speed_match = SPEED_PATTERN.search(float_text)
        payout = page.locator("#select-dropdown_estimate_details_payout_value").inner_text().strip()
        fees = FEE_PATTERN.findall(fee_text)
        promo_fee = _parse_amount(fees[-1]) if fees else 0.0
        regular_fee = _parse_amount(fees[0]) if len(fees) > 1 else promo_fee
        if send <= 0 or receive <= 0:
            raise ValueError("Invalid Western Union send/receive amounts")
        return {
            "send": send,
            "receive": receive,
            "rate": round(receive / send, 4),
            "promo_fee": promo_fee,
            "regular_fee": regular_fee,
            "speed": speed_match.group(1).strip() if speed_match else "",
            "payout": payout,
        }


def existing_rate_for_method(
    payout_label: str,
    new_rate: float,
    new_receive: float,
    promo_ratio: tuple[float, float] | None,
) -> tuple[float | None, float | None]:
    if payout_label.lower().startswith("bank") and promo_ratio:
        existing_ref, new_ref = promo_ratio
        existing_receive = scale_existing_receive(new_receive, existing_ref, new_ref)
        existing_rate = round(existing_receive / (new_receive / new_rate), 4)
        return existing_rate, existing_receive
    return new_rate, new_receive


def parse_modal_options(modal_text: str) -> list[dict]:
    options: list[dict] = []
    for match in MODAL_OPTION_PATTERN.finditer(modal_text):
        label = _normalize_payout_label(match.group(1))
        body = match.group(2)
        rate_match = RATE_PATTERN.search(body)
        speed_match = SPEED_PATTERN.search(body)
        if not rate_match:
            continue
        options.append(
            {
                "label": label,
                "rate": _parse_amount(rate_match.group(1)),
                "speed": speed_match.group(1).strip() if speed_match else "",
            }
        )
    if not options:
        raise ValueError("No Western Union payout methods found in modal")
    return options


def _normalize_payout_label(label: str) -> str:
    mapping = {
        "bank account": "Bank account",
        "cash pickup": "Cash pickup",
        "mobile wallet": "Mobile wallet",
    }
    return mapping.get(label.strip().lower(), label.strip())


def _parse_amount(value: str) -> float:
    return float(value.replace(",", ""))
