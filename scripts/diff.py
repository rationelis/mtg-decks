#!/usr/bin/env python3
"""
diff.py - Compare two MTG decklists and show the differences.

Usage:
    python3 diff.py <decklist_a> <decklist_b>

Example:
    python3 diff.py precons/creative_energy.txt decks/creative_energy.txt

Output shows cards removed from A and cards added in B.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from parse import parse_entries  # noqa: E402


def load_deck(path) -> Counter:
    """Load a decklist and return a Counter of card names."""
    cards: Counter = Counter()
    for entry in parse_entries(Path(path)):
        cards[entry.name] += entry.qty
    return cards


def main():
    if len(sys.argv) != 3:
        print("Usage: diff.py <decklist_a> <decklist_b>", file=sys.stderr)
        sys.exit(1)

    deck_a = load_deck(sys.argv[1])
    deck_b = load_deck(sys.argv[2])

    removed = deck_a - deck_b
    added = deck_b - deck_a

    if removed:
        print("Out:")
        for name, qty in sorted(removed.items()):
            print(f"{qty} {name}")

    if added:
        print("In:")
        for name, qty in sorted(added.items()):
            print(f"{qty} {name}")

    total = sum(removed.values())
    print(f"\nTotal changes: {total}")


if __name__ == "__main__":
    main()
