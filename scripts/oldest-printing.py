#!/usr/bin/env python3
"""
Find the oldest printing of each card in a decklist.

Queries the Scryfall API to find the first printing of each card,
useful for selecting the most "vintage" version of your cards.

Usage:
    python3 oldest-printing.py <decklist.txt>

Example:
    python3 oldest-printing.py ../decks/quick_draw.txt

Output format:
    Card Name (SET) collector_number
"""

import sys
import time
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from parse import parse_entries  # noqa: E402

API_DELAY = 0.1


def fetch_oldest_printing(card_name):
    """Query Scryfall for the oldest printing of a card."""
    encoded = urllib.parse.quote(card_name)
    url = f"https://api.scryfall.com/cards/search?q=!%22{encoded}%22&order=released&dir=asc&unique=prints"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "data" not in data or not data["data"]:
        return card_name, "???", "?"

    card = data["data"][0]
    return (
        card.get("name", card_name),
        card.get("set", "").upper(),
        card.get("collector_number", "?"),
    )


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    cache = {}

    for entry in parse_entries(Path(sys.argv[1])):
        if entry.name not in cache:
            try:
                cache[entry.name] = fetch_oldest_printing(entry.name)
            except requests.RequestException as e:
                print(f"Error fetching {entry.name}: {e}", file=sys.stderr)
                cache[entry.name] = (entry.name, "ERR", "?")
            time.sleep(API_DELAY)

        name, set_code, collector_number = cache[entry.name]
        for _ in range(entry.qty):
            print(f"{name} ({set_code}) {collector_number}")


if __name__ == "__main__":
    main()
