"""Shared Playwright context settings for AU remittance scrapers."""

from __future__ import annotations

from typing import Any

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

AU_CONTEXT: dict[str, Any] = {
    "user_agent": USER_AGENT,
    "viewport": {"width": 1280, "height": 900},
    "locale": "en-AU",
    "timezone_id": "Australia/Sydney",
    "geolocation": {"latitude": -33.8688, "longitude": 151.2093},
    "permissions": ["geolocation"],
    "extra_http_headers": {
        "Accept-Language": "en-AU,en;q=0.9",
    },
}
