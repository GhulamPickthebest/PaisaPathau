"""Shared constants: currency metadata and provider corridor definitions."""

from __future__ import annotations

TARGET_CURRENCY = "NPR"

# Active scrape scope — AUD→NPR only for now (expand ACTIVE_SEND_CURRENCIES later).
ACTIVE_SEND_CURRENCIES: list[str] = ["AUD"]

# Tier C disabled while scoped to AUD→NPR remittance providers only.
TIER_C_CURRENCIES: list[str] = []


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

# Provider locale maps (expand keys when adding send currencies later)
REMITLY_LOCALE: dict[str, str] = {"AUD": "au"}
WU_LOCALE: dict[str, str] = {"AUD": "au"}
WORLDREMIT_LOCALE: dict[str, str] = {"AUD": "au"}
XOOM_LOCALE: dict[str, str] = {"AUD": "au"}
MONEYGRAM_LOCALE: dict[str, str] = {"AUD": "au"}
XE_LOCALE: dict[str, str] = {"AUD": "au"}
INSTAREM_LOCALE: dict[str, str] = {"AUD": "au"}
INSTAREM_NIUM_LOCALE: dict[str, str] = {"AUD": "au"}
WISE_TRANSFER_LOCALE: dict[str, str] = {"AUD": "au"}
SKRILL_LOCALE: dict[str, str] = {"AUD": "au"}
RIA_LOCALE: dict[str, str] = {"AUD": "au"}
REVOLUT_LOCALE: dict[str, str] = {"AUD": "au"}
ACE_LOCALE: dict[str, str] = {"AUD": "au"}
LULU_LOCALE: dict[str, str] = {"AUD": "au"}
TAPTAP_LOCALE: dict[str, str] = {"AUD": "au"}

# Provider → supported send currencies → NPR (AUD only for now)
TIER_B_CORRIDORS: dict[str, list[str]] = {
    "Wise": ["AUD"],
    "Remitly": ["AUD"],
    "WorldRemit": ["AUD"],
    "Xoom (PayPal)": ["AUD"],
    "MoneyGram": ["AUD"],
    "Western Union": ["AUD"],
    "Instarem": ["AUD"],
    "Xe Money Transfer": ["AUD"],
    "Skrill": ["AUD"],
    "Ria Money Transfer": ["AUD"],
    "Instarem (by Nium)": ["AUD"],
    "Revolut": ["AUD"],
    "ACE Money Transfer": ["AUD"],
    "LuLu Exchange": ["AUD"],
    "Taptap Send": ["AUD"],
}

PROVIDER_PRIORITY: dict[str, str] = {
    "Wise": "high",
    "Remitly": "high",
    "Western Union": "high",
    "WorldRemit": "high",
    "Xoom (PayPal)": "medium",
    "MoneyGram": "medium",
    "Xe Money Transfer": "medium",
    "Instarem": "medium",
    "Instarem (by Nium)": "medium",
    "Skrill": "medium",
    "Ria Money Transfer": "medium",
    "Revolut": "medium",
    "ACE Money Transfer": "medium",
    "LuLu Exchange": "medium",
    "Taptap Send": "medium",
}

# Tier A Wise corridors (mid-market reference)
WISE_CORRIDORS: list[str] = list(ACTIVE_SEND_CURRENCIES)

# Standard transfer method labels (AUD/NPR matrix)
STANDARD_TRANSFER_METHODS: list[str] = [
    "Bank Transfer",
    "Cash Pickup",
    "Mobile Money Transfer",
    "Wallet Transfer",
]

PROVIDER_TRANSFER_SPEEDS: dict[str, dict[str, str]] = {
    "Wise": {"fastest": "30 minutes", "slowest": "2 business days"},
    "Remitly": {"fastest": "Minutes", "slowest": "3 business days"},
    "WorldRemit": {"fastest": "Minutes", "slowest": "1 business day"},
    "Instarem": {"fastest": "Same day", "slowest": "2 business days"},
    "Instarem (by Nium)": {"fastest": "Same day", "slowest": "2 business days"},
    "Western Union": {"fastest": "Minutes", "slowest": "3 business days"},
    "Xe Money Transfer": {"fastest": "1 business day", "slowest": "4 business days"},
    "Xoom (PayPal)": {"fastest": "Minutes", "slowest": "3 business days"},
    "MoneyGram": {"fastest": "Minutes", "slowest": "3 business days"},
    "Skrill": {"fastest": "Minutes", "slowest": "3 business days"},
    "Ria Money Transfer": {"fastest": "Minutes", "slowest": "3 business days"},
    "Revolut": {"fastest": "Minutes", "slowest": "2 business days"},
    "ACE Money Transfer": {"fastest": "Same day", "slowest": "3 business days"},
    "LuLu Exchange": {"fastest": "Same day", "slowest": "2 business days"},
    "Taptap Send": {"fastest": "Minutes", "slowest": "1 business day"},
}

WORLDREMIT_PAYOUT_METHODS: dict[str, str] = {
    "BNK": "Bank Transfer",
    "CSH": "Cash Pickup",
    "MOB": "Mobile Money Transfer",
}

WORLDREMIT_WALLET_ALIAS_CODE = "MOB"

REMITLY_PAYOUT_METHODS: dict[str, str] = {
    "BANK_DEPOSIT": "Bank Transfer",
    "CASH_PICKUP": "Cash Pickup",
    "DIRECT_TO_PHONE": "Mobile Money Transfer",
}

# All remittance providers shown in AUD→NPR comparisons
AUD_NPR_PROVIDERS: list[str] = list(TIER_B_CORRIDORS.keys())
