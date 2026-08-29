"""Shared helpers for talking to the Archidekt API.

Every script that hits Archidekt was independently reimplementing "fetch a
deck, skip Sideboard/Maybeboard, sum up CardMarket prices" - this module is
the one place that logic lives now.
"""

from __future__ import annotations

import sys
import time
from collections import Counter

import requests

API_URL = "https://archidekt.com/api/decks/{deck_id}/"
EXCLUDED_CATEGORIES = {"Sideboard", "Maybeboard"}
MAX_ATTEMPTS = 5
RETRY_DELAY = 2.0  # seconds, doubles after each failed attempt


def fetch_deck(deck_id: str) -> dict:
    """Fetch a deck's raw JSON from Archidekt, retrying transient failures
    (timeouts, connection errors, 5xx, 429) with exponential backoff.
    Exits with an error if every attempt fails.
    """
    url = API_URL.format(deck_id=deck_id)
    delay = RETRY_DELAY
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Fetching Archidekt deck {deck_id} (attempt {attempt}/{MAX_ATTEMPTS})...", file=sys.stderr)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                print(f"  failed: {e}. Retrying in {delay:.0f}s...", file=sys.stderr)
                time.sleep(delay)
                delay *= 2

    print(f"Error fetching deck {deck_id} after {MAX_ATTEMPTS} attempts: {last_error}", file=sys.stderr)
    sys.exit(1)


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
    return entry.get("card", {}).get("prices", {}).get("cm") or 0.0


def price_map(deck: dict, normalize) -> tuple[dict[str, float], list[str]]:
    """Per-card Cardmarket unit prices for `deck`'s main-deck entries, keyed
    by `normalize(name)` (pass parse.normalize_name) so callers can merge
    the result straight into a build-compatible price cache. If the same
    name appears more than once (e.g. two printings), the last one wins.
    Returns (prices, names_with_no_price).
    """
    prices: dict[str, float] = {}
    unpriced: list[str] = []
    for entry in main_deck_entries(deck):
        name = oracle_name(entry)
        price = unit_price_cm(entry)
        if price:
            prices[normalize(name)] = price
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
