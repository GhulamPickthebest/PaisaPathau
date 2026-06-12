"""WorldRemit calculator GraphQL API scraper."""

from __future__ import annotations

from constants import WORLDREMIT_LOCALE
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
      exchangeRate { value }
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
    corridors = list(WORLDREMIT_LOCALE.keys())
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

        rate = float(calc["exchangeRate"]["value"])
        fee = float(calc["informativeSummary"]["fee"]["value"]["amount"])
        receive = float(calc["receive"]["amount"])

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed="Minutes to 1 day",
            delivery_method="Bank transfer",
        )
