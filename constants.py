"""Shared constants: currency metadata and provider corridor definitions."""

from __future__ import annotations

# Active scrape scope — expand this list when adding corridors later.
ACTIVE_SEND_CURRENCIES: list[str] = ["AUD"]
TARGET_CURRENCY = "NPR"


def active_corridors(source: list[str] | dict[str, str]) -> list[str]:
    """Return send currencies from *source* that are in ACTIVE_SEND_CURRENCIES."""
    keys = list(source.keys()) if isinstance(source, dict) else list(source)
    return [currency for currency in keys if currency in ACTIVE_SEND_CURRENCIES]

# ISO currency -> display metadata
CURRENCY_META: dict[str, dict[str, str]] = {
    "AUD": {"country": "Australia", "flag": "🇦🇺"},
    "USD": {"country": "United States", "flag": "🇺🇸"},
    "GBP": {"country": "United Kingdom", "flag": "🇬🇧"},
    "CAD": {"country": "Canada", "flag": "🇨🇦"},
    "NZD": {"country": "New Zealand", "flag": "🇳🇿"},
    "EUR": {"country": "Eurozone", "flag": "🇪🇺"},
    "AED": {"country": "United Arab Emirates", "flag": "🇦🇪"},
    "SAR": {"country": "Saudi Arabia", "flag": "🇸🇦"},
    "SGD": {"country": "Singapore", "flag": "🇸🇬"},
    "QAR": {"country": "Qatar", "flag": "🇶🇦"},
    "KWD": {"country": "Kuwait", "flag": "🇰🇼"},
    "BHD": {"country": "Bahrain", "flag": "🇧🇭"},
    "OMR": {"country": "Oman", "flag": "🇴🇲"},
    "MYR": {"country": "Malaysia", "flag": "🇲🇾"},
    "JPY": {"country": "Japan", "flag": "🇯🇵"},
    "KRW": {"country": "South Korea", "flag": "🇰🇷"},
    "HKD": {"country": "Hong Kong", "flag": "🇭🇰"},
    "INR": {"country": "India", "flag": "🇮🇳"},
    "ILS": {"country": "Israel", "flag": "🇮🇱"},
    "CHF": {"country": "Switzerland", "flag": "🇨🇭"},
    "NOK": {"country": "Norway", "flag": "🇳🇴"},
    "SEK": {"country": "Sweden", "flag": "🇸🇪"},
    "DKK": {"country": "Denmark", "flag": "🇩🇰"},
    "THB": {"country": "Thailand", "flag": "🇹🇭"},
    "NPR": {"country": "Nepal", "flag": "🇳🇵"},
}

# Remitly locale path segments
REMITLY_LOCALE: dict[str, str] = {
    "AUD": "au",
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
    "NZD": "nz",
    "EUR": "de",
    "AED": "ae",
}

# Western Union country site codes
WU_LOCALE: dict[str, str] = {
    "AUD": "au",
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
    "NZD": "nz",
    "SAR": "sa",
    "AED": "ae",
}

WORLDREMIT_LOCALE: dict[str, str] = {
    "AUD": "au",
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
    "NZD": "nz",
    "EUR": "de",
}

XOOM_LOCALE: dict[str, str] = {
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
    "EUR": "de",
}

MONEYGRAM_LOCALE: dict[str, str] = {
    "AUD": "au",
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
}

XE_LOCALE: dict[str, str] = {
    "AUD": "au",
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
    "NZD": "nz",
}

INSTAREM_LOCALE: dict[str, str] = {
    "AUD": "au",
    "SGD": "sg",
    "GBP": "gb",
}

OFX_LOCALE: dict[str, str] = {
    "AUD": "au",
    "USD": "us",
    "GBP": "gb",
    "CAD": "ca",
    "NZD": "nz",
}

ORBITREMIT_LOCALE: dict[str, str] = {
    "AUD": "au",
    "NZD": "nz",
    "GBP": "gb",
}

TORFX_LOCALE: dict[str, str] = {
    "AUD": "au",
    "GBP": "gb",
    "NZD": "nz",
}

# Tier B provider corridor lists (AUD→NPR only for now)
TIER_B_CORRIDORS: dict[str, list[str]] = {
    "Remitly": ["AUD"],
    "Western Union": ["AUD"],
    "WorldRemit": ["AUD"],
    "Instarem": ["AUD"],
}

# Tier C: extra mid-market currencies (disabled while scoped to AUD only)
TIER_C_CURRENCIES: list[str] = []

# Tier A Wise corridors
WISE_CORRIDORS: list[str] = list(ACTIVE_SEND_CURRENCIES)

# Standard transfer method labels (AUD/NPR matrix)
STANDARD_TRANSFER_METHODS: list[str] = [
    "Bank Transfer",
    "Cash Pickup",
    "Mobile Money Transfer",
    "Wallet Transfer",
]

# Provider delivery speed ranges for NPR corridors
PROVIDER_TRANSFER_SPEEDS: dict[str, dict[str, str]] = {
    "Remitly": {"fastest": "Minutes", "slowest": "3 business days"},
    "WorldRemit": {"fastest": "Minutes", "slowest": "1 business day"},
    "Instarem": {"fastest": "Same day", "slowest": "2 business days"},
    "Western Union": {"fastest": "Minutes", "slowest": "3 business days"},
    "Wise": {"fastest": "30 minutes", "slowest": "2 business days"},
    "Xe Money Transfer": {"fastest": "1 business day", "slowest": "4 business days"},
}

# WorldRemit payOutMethodCode -> standard label (NPR from AU)
WORLDREMIT_PAYOUT_METHODS: dict[str, str] = {
    "BNK": "Bank Transfer",
    "CSH": "Cash Pickup",
    "MOB": "Mobile Money Transfer",
}

# WorldRemit MOB (Khalti) also satisfies wallet delivery for NPR
WORLDREMIT_WALLET_ALIAS_CODE = "MOB"

REMITLY_PAYOUT_METHODS: dict[str, str] = {
    "BANK_DEPOSIT": "Bank Transfer",
    "CASH_PICKUP": "Cash Pickup",
    "DIRECT_TO_PHONE": "Mobile Money Transfer",
}
