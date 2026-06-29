"""Tier B: remittance provider scrapers (AUD→NPR scope)."""

from tier_b.remitly import RemitlyScraper
from tier_b.worldremit import WorldRemitScraper
from tier_b.instarem import InstaremScraper
from tier_b.instarem_nium import InstaremNiumScraper
from tier_b.wise_transfer import WiseTransferScraper
from tier_b.western_union import WesternUnionScraper
from tier_b.western_union_api import WesternUnionApiScraper
from tier_b.xoom import XoomScraper
from tier_b.moneygram import MoneyGramScraper
from tier_b.xe import XeScraper
from tier_b.skrill import SkrillScraper
from tier_b.ria import RiaScraper
from tier_b.revolut import RevolutScraper
from tier_b.ace import AceScraper
from tier_b.lulu import LuLuScraper
from tier_b.taptap_send import TaptapSendScraper
from tier_b.unavailable_providers import (
    AceUnavailableScraper,
    LuLuUnavailableScraper,
    MoneyGramUnavailableScraper,
    RevolutUnavailableScraper,
)

# No Playwright — fast on Railway with LIVE_API_SKIP_BROWSER=true
API_SCRAPERS = [
    WiseTransferScraper,
    RemitlyScraper,
    WorldRemitScraper,
    InstaremScraper,
    InstaremNiumScraper,
    XoomScraper,
    WesternUnionApiScraper,
]

# Playwright — one browser at a time; skip on Railway with LIVE_API_SKIP_BROWSER=true
BROWSER_SCRAPERS = [
    XeScraper,
    RiaScraper,
    TaptapSendScraper,
    SkrillScraper,
]

# No guest quote — instant error without launching Chromium (saves RAM on Railway)
NO_QUOTE_SCRAPERS = [
    MoneyGramUnavailableScraper,
    AceUnavailableScraper,
    LuLuUnavailableScraper,
    RevolutUnavailableScraper,
]

ALL_BROWSER_SCRAPERS = API_SCRAPERS + BROWSER_SCRAPERS

__all__ = [
    "API_SCRAPERS",
    "BROWSER_SCRAPERS",
    "NO_QUOTE_SCRAPERS",
    "ALL_BROWSER_SCRAPERS",
    "WiseTransferScraper",
    "RemitlyScraper",
    "WorldRemitScraper",
    "InstaremScraper",
    "InstaremNiumScraper",
    "WesternUnionScraper",
    "WesternUnionApiScraper",
    "XoomScraper",
    "MoneyGramScraper",
    "XeScraper",
    "SkrillScraper",
    "RiaScraper",
    "RevolutScraper",
    "AceScraper",
    "LuLuScraper",
    "TaptapSendScraper",
]
