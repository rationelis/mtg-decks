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

import requests
import sys
import json as json_lib


API_URL = "https://archidekt.com/api/decks/{deck_id}/"


def fetch_deck_info(deck_id):
    """Fetch deck name and calculate total price."""
    try:
        url = API_URL.format(deck_id=deck_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching deck: {e}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()

    # Get deck name
    deck_name = data.get("name", "Unknown Deck")

    # Calculate total price
    card_entries = data.get("cards", [])
    excluded_categories = {"Sideboard", "Maybeboard"}
    total_price = 0.0

    for entry in card_entries:
        categories = entry.get("categories", [])
        main_category = categories[0] if categories else "Uncategorized"

        # Skip excluded categories
        if main_category in excluded_categories:
            continue

        # Get price and quantity
        card = entry.get("card", {})
        price_data = card.get("prices", {})
        unit_price = price_data.get("cm") or 0.0
        quantity = entry.get("quantity", 1)

        total_price += unit_price * quantity

    return {
        "name": deck_name,
        "price": total_price
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    # Parse arguments
    deck_id = sys.argv[1].strip()
    output_format = "table"

    for arg in sys.argv[2:]:
        if arg.startswith("--format="):
            output_format = arg.split("=", 1)[1]

    # Fetch data
    info = fetch_deck_info(deck_id)

    # Output in requested format
    if output_format == "json":
        print(json_lib.dumps(info))
    elif output_format == "price":
        print(f"{info['price']:.2f}")
    else:  # table (default)
        print(f"{info['name']}|{info['price']:.2f}")


if __name__ == "__main__":
    main()
