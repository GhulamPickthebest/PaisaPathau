"""Tier B: remittance provider scrapers (AUD→NPR scope)."""

from tier_b.remitly import RemitlyScraper
from tier_b.worldremit import WorldRemitScraper
from tier_b.instarem import InstaremScraper
from tier_b.instarem_nium import InstaremNiumScraper
from tier_b.wise_transfer import WiseTransferScraper
from tier_b.western_union import WesternUnionScraper
from tier_b.xoom import XoomScraper
from tier_b.moneygram import MoneyGramScraper
from tier_b.xe import XeScraper
from tier_b.skrill import SkrillScraper
from tier_b.ria import RiaScraper
from tier_b.revolut import RevolutScraper
from tier_b.ace import AceScraper
from tier_b.lulu import LuLuScraper
from tier_b.taptap_send import TaptapSendScraper

# No Playwright — fast on Railway with LIVE_API_SKIP_BROWSER=true
API_SCRAPERS = [
    WiseTransferScraper,
    RemitlyScraper,
    WorldRemitScraper,
    InstaremScraper,
    InstaremNiumScraper,
    XoomScraper,
]

# Playwright — set LIVE_API_SKIP_BROWSER=false on Railway for full coverage
BROWSER_SCRAPERS = [
    WesternUnionScraper,
    XeScraper,
    RiaScraper,
    TaptapSendScraper,
    SkrillScraper,
    MoneyGramScraper,
    AceScraper,
    LuLuScraper,
    RevolutScraper,
]

ALL_BROWSER_SCRAPERS = API_SCRAPERS + BROWSER_SCRAPERS

__all__ = [
    "API_SCRAPERS",
    "BROWSER_SCRAPERS",
    "ALL_BROWSER_SCRAPERS",
    "WiseTransferScraper",
    "RemitlyScraper",
    "WorldRemitScraper",
    "InstaremScraper",
    "InstaremNiumScraper",
    "WesternUnionScraper",
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
