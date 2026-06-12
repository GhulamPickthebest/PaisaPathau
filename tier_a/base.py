"""Base class for Tier A API scrapers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from config import settings
from models import RateRecord


class BaseApiScraper(ABC):
    provider_name: str = "Unknown"

    def __init__(self, send_amount: float | None = None) -> None:
        self.send_amount = send_amount or settings.send_amount

    @abstractmethod
    def fetch_all(self) -> list[RateRecord]:
        ...

    @abstractmethod
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        ...
