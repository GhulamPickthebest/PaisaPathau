#!/usr/bin/env python3
"""PaisaPathau remittance rate scraper entry point."""

from __future__ import annotations

import argparse
import sys

from scheduler import run_fetch_cycle, run_scheduler
from utils import logger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PaisaPathau.com remittance rate scraper and data pipeline",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single fetch cycle and exit (used by GitHub Actions)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Scheduler interval in minutes (default: 30)",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Skip Tier B Playwright scrapers (API-only mode)",
    )
    parser.add_argument(
        "--send-amount",
        type=float,
        default=None,
        help="Override default send amount (default from .env or 1000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        if args.once:
            logger.info("Running single fetch cycle")
            result = run_fetch_cycle(
                send_amount=args.send_amount,
                skip_browser=args.skip_browser,
            )
            return 0 if result.ok_rates else 1

        run_scheduler(
            interval_minutes=args.interval,
            skip_browser=args.skip_browser,
        )
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
