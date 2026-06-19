"""Data models for rate records and pipeline output."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class RateRecord:
    provider: str
    from_currency: str
    to_currency: str
    exchange_rate: float
    send_amount: float
    receive_amount: float
    fee: float
    timestamp: str
    status: Literal["ok", "error"]
    from_country: str = ""
    from_flag: str = ""
    net_send_amount: float = 0.0
    transfer_speed: str = ""
    delivery_method: str = ""
    source: Literal["api", "scraper"] = "api"
    customer_type: str = ""
    rate_label: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        if not self.from_country or not self.from_flag:
            from constants import CURRENCY_META

            meta = CURRENCY_META.get(self.from_currency, {})
            if not self.from_country:
                self.from_country = meta.get("country", self.from_currency)
            if not self.from_flag:
                self.from_flag = meta.get("flag", "")
        if self.net_send_amount == 0.0 and self.status == "ok":
            self.net_send_amount = round(self.send_amount - self.fee, 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("error_message", None)
        return data

    @classmethod
    def error_record(
        cls,
        provider: str,
        from_currency: str,
        send_amount: float,
        source: Literal["api", "scraper"] = "api",
        error_message: str = "",
    ) -> RateRecord:
        return cls(
            provider=provider,
            from_currency=from_currency,
            from_country="",
            from_flag="",
            to_currency="NPR",
            send_amount=send_amount,
            exchange_rate=0.0,
            fee=0.0,
            net_send_amount=0.0,
            receive_amount=0.0,
            transfer_speed="",
            delivery_method="",
            timestamp=utc_now_iso(),
            source=source,
            status="error",
            error_message=error_message,
        )


@dataclass
class PipelineResult:
    all_rates: list[RateRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok_rates(self) -> list[RateRecord]:
        return [r for r in self.all_rates if r.status == "ok"]

    @property
    def corridors(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[RateRecord]] = {}
        for rate in self.all_rates:
            grouped.setdefault(rate.from_currency, []).append(rate)

        corridors: list[dict[str, Any]] = []
        for currency in sorted(grouped.keys()):
            rates = grouped[currency]
            sample = rates[0]
            corridors.append(
                {
                    "from_currency": currency,
                    "from_country": sample.from_country,
                    "from_flag": sample.from_flag,
                    "rates": [r.to_dict() for r in rates],
                }
            )
        return corridors

    @property
    def unique_providers(self) -> set[str]:
        return {r.provider for r in self.all_rates if r.status == "ok"}

    @property
    def unique_corridors(self) -> set[str]:
        return {r.from_currency for r in self.all_rates if r.status == "ok"}


@dataclass
class TransferMethodRow:
    provider: str
    transfer_method: str
    fee: float | None
    new_user_rate: float | None
    existing_user_rate: float | None
    min_amount: float | None
    max_amount: float | None
    fastest_speed: str
    slowest_speed: str
    send_amount: float
    status: Literal["ok", "unavailable", "error"] = "ok"
    receive_amount_new: float | None = None
    receive_amount_existing: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
