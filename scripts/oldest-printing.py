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

import requests

API_DELAY = 0.1


def parse_line(line):
    """Parse a line like '4 Lightning Bolt' into (quantity, name)."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return int(parts[0]), parts[1].strip()
    return 1, line


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

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if not parsed:
                continue

            qty, card_name = parsed

            if card_name not in cache:
                try:
                    cache[card_name] = fetch_oldest_printing(card_name)
                except requests.RequestException as e:
                    print(f"Error fetching {card_name}: {e}", file=sys.stderr)
                    cache[card_name] = (card_name, "ERR", "?")
                time.sleep(API_DELAY)

            name, set_code, collector_number = cache[card_name]
            for _ in range(qty):
                print(f"{name} ({set_code}) {collector_number}")


if __name__ == "__main__":
    main()
