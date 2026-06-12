"""Optional alerting via webhook when scrape cycles fail."""

from __future__ import annotations

from typing import Sequence

import requests

from config import settings
from utils import logger


def send_alert(title: str, messages: Sequence[str]) -> None:
    if not settings.alert_webhook_url:
        return

    payload = {
        "text": f"*{title}*\n" + "\n".join(f"• {m}" for m in messages),
    }

    try:
        response = requests.post(
            settings.alert_webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        logger.info("Alert sent successfully")
    except requests.RequestException as exc:
        logger.error("Failed to send alert: %s", exc)


def alert_on_high_failure_rate(
    total: int,
    ok_count: int,
    error_messages: Sequence[str],
    threshold: float = 0.5,
) -> None:
    failed_count = total - ok_count
    if total == 0:
        return
    failure_rate = failed_count / total
    if failure_rate >= threshold:
        send_alert(
            "PaisaPathau Scraper: High failure rate",
            [
                f"Failed {failed_count} of {total} fetches ({failure_rate:.0%})",
                *list(error_messages)[:10],
            ],
        )
