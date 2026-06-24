"""Shared helpers for Playwright remittance scrapers."""

from __future__ import annotations

import re

from playwright.sync_api import Page


def dismiss_cookie_banners(page: Page) -> None:
    """Dismiss common consent overlays that block clicks."""
    selectors = [
        "#onetrust-accept-btn-handler",
        "button:has-text('Accept all')",
        "button:has-text('Accept All')",
        "button:has-text('I Agree')",
        "button:has-text('Agree')",
        "[data-testid='cookie-accept']",
    ]
    for selector in selectors:
        try:
            button = page.locator(selector).first
            if button.count() and button.is_visible():
                button.click(timeout=2000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def parse_aud_npr_rate(text: str) -> float | None:
    """Extract 1 AUD = X NPR from visible page text."""
    patterns = [
        r"1(?:\.00)?\s*AUD\s*=\s*([\d,.]+)\s*NPR",
        r"1\s*AUD\s*=\s*([\d,.]+)",
        r"([\d,.]+)\s*NPR\s*per\s*AUD",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return None
