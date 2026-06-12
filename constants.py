"""Shared constants: currency metadata and provider corridor definitions."""

from __future__ import annotations

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

# Tier B provider corridor lists
TIER_B_CORRIDORS: dict[str, list[str]] = {
    "Remitly": ["AUD", "USD", "GBP", "CAD", "NZD", "EUR", "AED"],
    "Western Union": ["AUD", "USD", "GBP", "CAD", "NZD", "SAR", "AED"],
    "WorldRemit": ["AUD", "USD", "GBP", "CAD", "NZD", "EUR"],
    "Xoom": ["USD", "GBP", "CAD", "EUR"],
    "MoneyGram": ["AUD", "USD", "GBP", "CAD"],
    "Xe Money Transfer": ["AUD", "USD", "GBP", "CAD", "NZD"],
    "Instarem": ["AUD", "SGD", "GBP"],
    "OFX": ["AUD", "USD", "GBP", "CAD", "NZD"],
    "OrbitRemit": ["AUD", "NZD", "GBP"],
    "TorFX": ["AUD", "GBP", "NZD"],
}

# Tier C: mid-market only (no remittance fee data)
TIER_C_CURRENCIES: list[str] = [
    "QAR",
    "SAR",
    "KWD",
    "BHD",
    "OMR",
    "MYR",
    "JPY",
    "KRW",
    "SGD",
    "HKD",
    "INR",
    "ILS",
    "CHF",
    "NOK",
    "SEK",
    "DKK",
    "THB",
    "EUR",
]

# Tier A Wise corridors (all supported send currencies)
WISE_CORRIDORS: list[str] = [
    "AUD",
    "USD",
    "GBP",
    "CAD",
    "NZD",
    "EUR",
    "AED",
    "SAR",
    "SGD",
    "QAR",
    "KWD",
    "BHD",
    "OMR",
    "MYR",
    "JPY",
    "KRW",
    "HKD",
    "INR",
    "ILS",
    "CHF",
    "NOK",
    "SEK",
    "DKK",
    "THB",
]
