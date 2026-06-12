#!/usr/bin/env python3
"""Quick test runner for Tier B providers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tier_b import API_SCRAPERS, BROWSER_SCRAPERS


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Tier B provider scrapers")
    parser.add_argument("--provider", help="Provider name substring filter")
    parser.add_argument("--currency", help="Single corridor currency (e.g. AUD)")
    parser.add_argument("--api-only", action="store_true", help="Skip browser scrapers")
    args = parser.parse_args()

    groups = list(API_SCRAPERS)
    if not args.api_only:
        groups.extend(BROWSER_SCRAPERS)

    for scraper_cls in groups:
        name = scraper_cls.provider_name
        if args.provider and args.provider.lower() not in name.lower():
            continue

        print(f"\n=== {name} ===")
        scraper = scraper_cls(send_amount=1000)
        corridors = [args.currency] if args.currency else scraper.corridors
        for currency in corridors:
            try:
                record = scraper.fetch_corridor(currency)
                print(
                    f"  {currency}: {record.status} rate={record.exchange_rate} "
                    f"fee={record.fee} receive={record.receive_amount}"
                )
            except Exception as exc:
                print(f"  {currency}: ERROR {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
