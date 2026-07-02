"""Shared utilities: logging, retries, and parsing helpers."""

from __future__ import annotations

import logging
import re
import time
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

from config import LOGS_DIR, settings

T = TypeVar("T")


class PermanentScraperError(Exception):
    """Non-transient scraper failure that should not be retried."""


def setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("paisapathau")
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


def retry(
    max_attempts: int | None = None,
    delay: float | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    attempts = max_attempts or settings.max_retries
    wait = delay if delay is not None else settings.retry_delay_seconds

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except PermanentScraperError:
                    raise
                except exceptions as exc:
                    last_error = exc
                    logger.warning(
                        "%s attempt %s/%s failed: %s",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                    )
                    if attempt < attempts:
                        time.sleep(wait * attempt)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


def parse_rate_from_text(text: str) -> float | None:
    """Extract the first plausible exchange rate from free-form text."""
    patterns = [
        r"1\s*[A-Z]{3}\s*=\s*([\d,]+\.?\d*)",
        r"([\d,]+\.?\d*)\s*NPR",
        r"rate[:\s]+([\d,]+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            try:
                return float(value)
            except ValueError:
                continue
    return None


def parse_money_amount(text: str) -> float | None:
    match = re.search(r"([\d,]+\.?\d*)", text.replace(",", ""))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def compute_receive_amount(
    send_amount: float, fee: float, exchange_rate: float
) -> tuple[float, float]:
    net_send = round(send_amount - fee, 2)
    receive = round(net_send * exchange_rate, 2)
    return net_send, receive


def truncate_decimal(value: float, places: int = 3) -> float:
    """Truncate a float to *places* decimals without rounding."""
    factor = 10**places
    if value >= 0:
        return int(value * factor) / factor
    return -int(-value * factor) / factor


def format_exchange_rate(value: float | None, places: int = 3) -> str:
    """Display exchange rate to fixed decimals (truncated, not rounded)."""
    if value is None:
        return "—"
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return "—"
    truncated = truncate_decimal(rate, places)
    return f"{truncated:.{places}f}"
