#!/usr/bin/env python3
"""
diff-archidekt.py - Compare Archidekt remote deck with local decklist.

Fetches the current state of a deck from Archidekt and compares it to your
local decklist file, showing what cards were added or removed.

Usage:
    python3 diff-archidekt.py <deck_id> <local_file>

Example:
    python3 diff-archidekt.py 21248219 decks/21248219_blitzkikker.txt

Output:
    Shows cards removed from remote (Out) and cards added to remote (In),
    along with total changes count.
"""

import requests
import sys
from collections import Counter
from pathlib import Path

API_URL = "https://archidekt.com/api/decks/{deck_id}/"


def fetch_archidekt_deck(deck_id):
    """Fetch deck from Archidekt and return a Counter of card names."""
    try:
        url = API_URL.format(deck_id=deck_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching deck: {e}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    card_entries = data.get("cards", [])

    if not card_entries:
        print("No cards found in deck.", file=sys.stderr)
        sys.exit(1)

    cards = Counter()
    excluded_categories = {"Sideboard", "Maybeboard"}

    for entry in card_entries:
        categories = entry.get("categories", [])
        main_category = categories[0] if categories else "Uncategorized"

        # Skip sideboard and maybeboard
        if main_category in excluded_categories:
            continue

        card = entry.get("card", {})
        oracle_card = card.get("oracleCard", {})
        name = oracle_card.get("name", "Unknown")
        quantity = entry.get("quantity", 1)

        cards[name] += quantity

    return cards


def load_local_deck(path):
    """Load a local decklist and return a Counter of card names."""
    cards = Counter()

    if not Path(path).exists():
        print(f"Error: Local file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                qty, name = int(parts[0]), parts[1]
                cards[name] += qty

    return cards


def print_changes(local_only, remote_only):
    """Print the differences between remote and local decks."""
    if local_only:
        print("Out:")
        for name, qty in sorted(local_only.items()):
            print(f"{qty} {name}")

    if remote_only:
        if local_only:
            print()
        print("In:")
        for name, qty in sorted(remote_only.items()):
            print(f"{qty} {name}")

    total_changes = sum(local_only.values()) + sum(remote_only.values())
    print(f"\nTotal changes: {total_changes}")


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    deck_id = sys.argv[1].strip()
    local_path = sys.argv[2].strip()

    print(f"Fetching remote deck {deck_id}...", file=sys.stderr)
    remote_deck = fetch_archidekt_deck(deck_id)

    print(f"Loading local deck from {local_path}...", file=sys.stderr)
    local_deck = load_local_deck(local_path)

    print(file=sys.stderr)

    # Calculate differences
    local_only = local_deck - remote_deck
    remote_only = remote_deck - local_deck

    print_changes(local_only, remote_only)


if __name__ == "__main__":
    main()
