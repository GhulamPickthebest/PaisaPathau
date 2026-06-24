"""Instarem (by Nium) — same Nium platform API as Instarem."""

from __future__ import annotations

from tier_b.instarem import InstaremScraper


class InstaremNiumScraper(InstaremScraper):
    provider_name = "Instarem (by Nium)"
