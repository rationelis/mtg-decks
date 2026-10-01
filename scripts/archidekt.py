"""Shared helpers for talking to the Archidekt API.

Every script that hits Archidekt was independently reimplementing "fetch a
deck, skip Sideboard/Maybeboard, sum up CardMarket prices" - this module is
the one place that logic lives now.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from net import get_json  # noqa: E402

API_URL = "https://archidekt.com/api/decks/{deck_id}/"
EXCLUDED_CATEGORIES = {"Sideboard", "Maybeboard"}


def fetch_deck(deck_id: str) -> dict:
    """Fetch a deck's raw JSON from Archidekt, retrying transient failures
    (timeouts, connection errors, 5xx, 429) with exponential backoff (see
    scripts/net.py). Raises requests.RequestException if every attempt
    fails - callers decide whether that's fatal (a one-off CLI script) or
    just a warning (the main build, which degrades pricing gracefully).
    """
    url = API_URL.format(deck_id=deck_id)
    data = get_json(url)
    if data is None:
        raise requests.HTTPError(f"Archidekt deck {deck_id} not found (HTTP 404).")
    return data


def main_deck_entries(deck: dict) -> list[dict]:
    """Card entries in `deck`, excluding Sideboard/Maybeboard."""
    entries = []
    for entry in deck.get("cards", []):
        categories = entry.get("categories", [])
        main_category = categories[0] if categories else "Uncategorized"
        if main_category not in EXCLUDED_CATEGORIES:
            entries.append(entry)
    return entries


def oracle_name(entry: dict) -> str:
    return entry.get("card", {}).get("oracleCard", {}).get("name", "Unknown")


def unit_price_cm(entry: dict) -> float:
    """Best-effort Cardmarket unit price for `entry`'s picked printing.

    Archidekt tracks normal and foil average prices separately (`cm` /
    `cmfoil`); a foil-modifier entry often has a real price only under
    `cmfoil`, which would otherwise look unpriced. Falls back to the
    other finish's average, and finally to `cmMinimum` (the cheapest
    live Cardmarket listing across all finishes) for very new cards
    whose averages haven't been computed yet, before giving up.
    """
    prices = entry.get("card", {}).get("prices", {})
    is_foil = "foil" in (entry.get("modifier") or "").lower()
    primary, secondary = ("cmfoil", "cm") if is_foil else ("cm", "cmfoil")
    return (
        prices.get(primary)
        or prices.get(secondary)
        or prices.get("cmMinimum")
        or 0.0
    )


def price_entry(entry: dict) -> dict[str, Any]:
    """The priced printing's identity (set + collector number) alongside
    its unit price, so callers can tell whether a bulk/list price is for
    the exact printing a source file pinned, or just "a" printing (see
    REFACTOR.md §6.4). Archidekt's `editioncode` is the Scryfall-style
    set code; `collectorNumber` may be absent for very old entries.
    """
    card = entry.get("card", {})
    edition = card.get("edition", {}) or {}
    return {
        "price_eur": unit_price_cm(entry),
        "set": str(edition.get("editioncode", "")).lower(),
        "collector_number": str(card.get("collectorNumber", "")),
    }


def price_map(deck: dict, normalize) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Per-card Cardmarket pricing for `deck`'s main-deck entries, keyed by
    `normalize(name)` (pass parse.normalize_name) so callers can merge the
    result straight into a build-compatible price cache. Each value is
    `{price_eur, set, collector_number}` - the printing Archidekt priced,
    so the build can tell an "exact" price (matches a pinned printing)
    from a "fallback" one (priced a different printing of the same
    card). If the same name appears more than once (e.g. two printings),
    the last one wins. Returns (prices, names_with_no_price).
    """
    prices: dict[str, dict[str, Any]] = {}
    unpriced: list[str] = []
    for entry in main_deck_entries(deck):
        name = oracle_name(entry)
        priced = price_entry(entry)
        if priced["price_eur"]:
            prices[normalize(name)] = priced
        else:
            unpriced.append(name)
    return prices, unpriced


def total_price_cm(deck: dict) -> float:
    return sum(unit_price_cm(e) * e.get("quantity", 1) for e in main_deck_entries(deck))


def name_counter(deck: dict) -> Counter:
    """Card name -> total quantity, main deck only."""
    counter: Counter = Counter()
    for entry in main_deck_entries(deck):
        counter[oracle_name(entry)] += entry.get("quantity", 1)
    return counter
