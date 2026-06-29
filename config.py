"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"


@dataclass(frozen=True)
class Settings:
    send_amount: float
    exchangerate_api_key: str
    open_exchange_rates_app_id: str
    alert_webhook_url: str
    playwright_headless: bool
    playwright_timeout_ms: int
    max_retries: int
    retry_delay_seconds: float
    log_level: str
    log_file: str
    api_port: int
    live_api_cache_seconds: int
    live_api_skip_browser: bool
    live_api_cors_origins: str
    live_api_warm_cache: bool
    live_api_warm_cache_with_browser: bool

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            send_amount=float(os.getenv("SEND_AMOUNT", "1000")),
            exchangerate_api_key=os.getenv("EXCHANGERATE_API_KEY", ""),
            open_exchange_rates_app_id=os.getenv("OPEN_EXCHANGE_RATES_APP_ID", ""),
            alert_webhook_url=os.getenv("ALERT_WEBHOOK_URL", ""),
            playwright_headless=os.getenv("PLAYWRIGHT_HEADLESS", "true").lower()
            == "true",
            playwright_timeout_ms=int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "45000")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay_seconds=float(os.getenv("RETRY_DELAY_SECONDS", "2")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", str(LOGS_DIR / "scraper.log")),
            api_port=int(os.getenv("PORT", os.getenv("API_PORT", "8000"))),
            live_api_cache_seconds=int(os.getenv("LIVE_API_CACHE_SECONDS", "120")),
            live_api_skip_browser=os.getenv("LIVE_API_SKIP_BROWSER", "true").lower()
            == "true",
            live_api_cors_origins=os.getenv("LIVE_API_CORS_ORIGINS", "*"),
            live_api_warm_cache=os.getenv("LIVE_API_WARM_CACHE", "true").lower()
            == "true",
            live_api_warm_cache_with_browser=os.getenv(
                "LIVE_API_WARM_CACHE_WITH_BROWSER", "false"
            ).lower()
            == "true",
        )


settings = Settings.from_env()
