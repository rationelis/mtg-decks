#!/usr/bin/env python3
"""
diff-archidekt.py - Compare Archidekt remote deck with local decklist.

Fetches the current state of a deck from Archidekt and compares it to your
local decklist file, showing what cards were added or removed.

Usage:
    python3 diff-archidekt.py <deck_id> <local_file>

Example:
    python3 diff-archidekt.py 21248219 decks/archived/21248219_blitzkikker.txt

Output:
    Shows cards removed from remote (Out) and cards added to remote (In),
    along with total changes count.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from archidekt import fetch_deck, name_counter  # noqa: E402
from parse import parse_entries  # noqa: E402


def load_local_deck(path: str) -> Counter:
    """Load a local decklist and return a Counter of card names."""
    if not Path(path).exists():
        print(f"Error: Local file not found: {path}", file=sys.stderr)
        sys.exit(1)

    cards: Counter = Counter()
    for entry in parse_entries(Path(path)):
        cards[entry.name] += entry.qty
    return cards


def print_changes(local_only: Counter, remote_only: Counter) -> None:
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

    remote_deck = name_counter(fetch_deck(deck_id))

    print(f"Loading local deck from {local_path}...", file=sys.stderr)
    local_deck = load_local_deck(local_path)

    print(file=sys.stderr)

    local_only = local_deck - remote_deck
    remote_only = remote_deck - local_deck

    print_changes(local_only, remote_only)


if __name__ == "__main__":
    main()
