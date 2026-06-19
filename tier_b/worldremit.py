"""WorldRemit calculator GraphQL API scraper."""

from __future__ import annotations

from constants import WORLDREMIT_LOCALE, active_corridors
from models import RateRecord
from tier_b.calculator_api import CalculatorApiScraper

# GraphQL send-country codes (ISO2)
WORLDREMIT_COUNTRY: dict[str, str] = {
    "AUD": "AU",
    "USD": "US",
    "GBP": "GB",
    "CAD": "CA",
    "NZD": "NZ",
    "EUR": "DE",
}

CREATE_CALCULATION = """
mutation createCalculation(
  $amount: BigDecimal!, $type: CalculationType!,
  $sendCountryCode: CountryCode!, $sendCurrencyCode: CurrencyCode!,
  $receiveCountryCode: CountryCode!, $receiveCurrencyCode: CurrencyCode!,
  $payOutMethodCode: String, $correspondentId: String
) {
  createCalculation(
    calculationInput: {
      amount: $amount,
      send: { country: $sendCountryCode, currency: $sendCurrencyCode },
      type: $type,
      receive: { country: $receiveCountryCode, currency: $receiveCurrencyCode },
      payOutMethodCode: $payOutMethodCode,
      correspondentId: $correspondentId
    }
  ) {
    calculation {
      send { amount currency }
      receive { amount currency }
      exchangeRate { value crossedOutValue }
      informativeSummary {
        fee { value { amount currency } }
        totalToPay { amount currency }
      }
    }
  }
}
"""


class WorldRemitScraper(CalculatorApiScraper):
    provider_name = "WorldRemit"
    corridors = active_corridors(WORLDREMIT_LOCALE)
    GQL_URL = "https://api.worldremit.com/graphql"

    def __init__(self, send_amount=None, browser=None, **_kwargs) -> None:
        super().__init__(send_amount=send_amount, browser=browser)
        self.session.headers.update(
            {
                "Origin": "https://www.worldremit.com",
                "Referer": "https://www.worldremit.com/",
                "X-WR-Platform": "WEB",
            }
        )

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        return self.fetch_corridor_records(from_currency)[0]

    def fetch_corridor_records(self, from_currency: str) -> list[RateRecord]:
        send_country = WORLDREMIT_COUNTRY.get(from_currency)
        if not send_country:
            raise ValueError(f"Unsupported corridor: {from_currency}")

        payload = {
            "operationName": "createCalculation",
            "variables": {
                "amount": int(self.send_amount),
                "type": "SEND",
                "sendCountryCode": send_country,
                "sendCurrencyCode": from_currency,
                "receiveCountryCode": "NP",
                "receiveCurrencyCode": "NPR",
                "payOutMethodCode": "BNK",
                "correspondentId": "",
            },
            "query": CREATE_CALCULATION,
        }
        response = self.session.post(self.GQL_URL, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise ValueError(data["errors"][0].get("message", "GraphQL error"))

        calc = data.get("data", {}).get("createCalculation", {}).get("calculation")
        if not calc:
            raise ValueError(f"No WorldRemit quote for {from_currency}/NPR")

        send_amount = float(calc["send"]["amount"])
        receive_amount = float(calc["receive"]["amount"])
        fee = float(calc["informativeSummary"]["fee"]["value"]["amount"])
        exchange = calc["exchangeRate"]
        promo_rate = float(exchange["value"])
        existing_rate = float(exchange.get("crossedOutValue") or 0)
        effective_new_rate = self._effective_rate(send_amount, receive_amount)

        common = {
            "from_currency": from_currency,
            "fee": fee,
            "transfer_speed": "Minutes to 1 day",
            "delivery_method": "Bank transfer",
        }

        records = [
            self._build_record(
                **common,
                exchange_rate=effective_new_rate,
                receive_amount=receive_amount,
                customer_type="new_user",
                rate_label="New User",
            )
        ]

        if existing_rate > 0:
            existing_receive = round((send_amount - fee) * existing_rate, 2)
            records.append(
                self._build_record(
                    **common,
                    exchange_rate=existing_rate,
                    receive_amount=existing_receive,
                    customer_type="existing_user",
                    rate_label="Existing User",
                )
            )
        elif promo_rate != effective_new_rate:
            records.append(
                self._build_record(
                    **common,
                    exchange_rate=promo_rate,
                    receive_amount=round(send_amount * promo_rate, 2),
                    customer_type="existing_user",
                    rate_label="Existing User",
                )
            )

        return records
