#!/usr/bin/env python3
"""
Fetch card descriptions from Scryfall for a decklist.

Queries the Scryfall API to get card details including name, mana cost,
type line, and oracle text. Handles double-faced cards by combining
both faces. Each unique card is only fetched once.

Usage:
    python3 describe.py <decklist.txt>

Example:
    python3 describe.py ../decks/quick_draw.txt

Output:
    Card details printed to stdout, one card per block separated by "===".
"""

import requests
import sys
import time

API_URL = "https://api.scryfall.com/cards/named"
API_DELAY = 0.1


def fetch_card(name):
    """Fetch card data from Scryfall."""
    resp = requests.get(API_URL, params={"exact": name}, timeout=10)
    if resp.status_code != 200:
        return None

    data = resp.json()

    if "card_faces" in data:
        mana_cost = " // ".join(f.get("mana_cost", "") for f in data["card_faces"])
        oracle_text = "\n---\n".join(f.get("oracle_text", "") for f in data["card_faces"])
    else:
        mana_cost = data.get("mana_cost", "")
        oracle_text = data.get("oracle_text", "")

    return {
        "name": data.get("name", ""),
        "mana_cost": mana_cost,
        "type_line": data.get("type_line", ""),
        "oracle_text": oracle_text,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    seen = set()

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                name = parts[1].strip()
            else:
                name = line

            if name in seen:
                continue
            seen.add(name)

            card = fetch_card(name)
            if card:
                print(f"Name: {card['name']}")
                print(f"Mana Cost: {card['mana_cost']}")
                print(f"Type: {card['type_line']}")
                print(f"Oracle Text:\n{card['oracle_text']}")
                print("\n" + "=" * 60 + "\n")
            else:
                print(f"Name: {name}\nError: Not found\n", file=sys.stderr)

            time.sleep(API_DELAY)


if __name__ == "__main__":
    main()
