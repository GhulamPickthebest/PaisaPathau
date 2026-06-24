"""Tier B: remittance provider scrapers (all corridors → NPR)."""

from tier_b.remitly import RemitlyScraper
from tier_b.worldremit import WorldRemitScraper
from tier_b.instarem import InstaremScraper
from tier_b.western_union import WesternUnionScraper
from tier_b.xoom import XoomScraper
from tier_b.moneygram import MoneyGramScraper
from tier_b.xe import XeScraper
from tier_b.ofx import OfxScraper
from tier_b.orbitremit import OrbitRemitScraper
from tier_b.torfx import TorFxScraper

# Calculator API scrapers (no browser required)
API_SCRAPERS = [
    RemitlyScraper,
    WorldRemitScraper,
    InstaremScraper,
]

# Playwright scrapers (WU + Xe working; others fail fast with documented errors)
BROWSER_SCRAPERS = [
    WesternUnionScraper,
    XeScraper,
    XoomScraper,
    MoneyGramScraper,
    OfxScraper,
    OrbitRemitScraper,
    TorFxScraper,
]

ALL_BROWSER_SCRAPERS = API_SCRAPERS + BROWSER_SCRAPERS

__all__ = [
    "API_SCRAPERS",
    "BROWSER_SCRAPERS",
    "ALL_BROWSER_SCRAPERS",
    "RemitlyScraper",
    "WorldRemitScraper",
    "InstaremScraper",
    "WesternUnionScraper",
    "XoomScraper",
    "MoneyGramScraper",
    "XeScraper",
    "OfxScraper",
    "OrbitRemitScraper",
    "TorFxScraper",
]
