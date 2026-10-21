#!/usr/bin/env python3
"""Calculate average main-category counts across Archidekt decks."""

# To fetch IDs: Array.from(document.getElementsByClassName("deckLink_thumbnail__U3ZsF")).map((item) => item.href);
# xargs python3 scripts/average.py < ids.txt

import sys
from collections import defaultdict

import requests

from archidekt import fetch_deck, main_deck_entries


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <deck_id> [deck_id ...]")
        sys.exit(1)

    deck_ids = sys.argv[1:]
    category_totals = defaultdict(int)
    successful_decks = 0

    for deck_id in deck_ids:
        try:
            deck = fetch_deck(deck_id)
            entries = main_deck_entries(deck)
        except requests.RequestException as e:
            print(f"Error fetching {deck_id}: {e}", file=sys.stderr)
            continue

        if not entries:
            print(f"No cards found in deck {deck_id}", file=sys.stderr)
            continue

        deck_categories = defaultdict(int)

        for entry in entries:
            categories = entry.get("categories", [])
            category = categories[0] if categories else "Uncategorized"
            quantity = entry.get("quantity", 1)
            deck_categories[category] += quantity

        for category, count in deck_categories.items():
            category_totals[category] += count

        successful_decks += 1
        print(f"Fetched deck {deck_id}")

    if successful_decks == 0:
        print("No decks fetched successfully.", file=sys.stderr)
        sys.exit(1)

    print(f"\nAverages across {successful_decks} decks:")
    print("-" * 40)

    for category, total in sorted(category_totals.items()):
        average = total / successful_decks
        print(f"{category:<25} {average:6.2f}")

    print("-" * 40)


if __name__ == "__main__":
    main()
