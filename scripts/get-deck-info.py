#!/usr/bin/env python3
"""
Get deck name and price from Archidekt for automation.

Fetches the deck name and total CardMarket price from Archidekt API.
Excludes Sideboard and Maybeboard from price calculation.

Usage:
    python3 get-deck-info.py <deck_id> [--format=FORMAT]

Formats:
    table (default): Name|Price (CSV-style, for GitHub Actions)
    json: {"name": "...", "price": 123.45}
    price: Just the price number

Example:
    python3 get-deck-info.py 21248219
    # Output: Brew: Blitzkikker|208.48

    python3 get-deck-info.py 21248219 --format=price
    # Output: 208.48
"""

import json as json_lib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from archidekt import fetch_deck, total_price_cm  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    deck_id = sys.argv[1].strip()
    output_format = "table"
    for arg in sys.argv[2:]:
        if arg.startswith("--format="):
            output_format = arg.split("=", 1)[1]

    deck = fetch_deck(deck_id)
    info = {"name": deck.get("name", "Unknown Deck"), "price": total_price_cm(deck)}

    if output_format == "json":
        print(json_lib.dumps(info))
    elif output_format == "price":
        print(f"{info['price']:.2f}")
    else:  # table (default)
        print(f"{info['name']}|{info['price']:.2f}")


if __name__ == "__main__":
    main()
