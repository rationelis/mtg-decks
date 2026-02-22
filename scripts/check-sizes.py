#!/usr/bin/env python3
"""
check-sizes.py - Verify deck sizes for Commander format

Reports whether each deck has exactly 100 cards (the required size
for Commander format).

Usage:
    python3 scripts/check-sizes.py <decklist> [decklist...]

Example:
    python3 scripts/check-sizes.py decks/quick_draw.txt
    python3 scripts/check-sizes.py decks/*.txt

Output:
    ✅ creative_energy.txt: 100 cards
    ❌ quick_draw.txt: 98 cards
"""

import sys
from pathlib import Path


def count_cards(path):
    """Count total cards in a decklist."""
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if parts and parts[0].isdigit():
                count += int(parts[0])
    return count


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    for filepath in sys.argv[1:]:
        path = Path(filepath)
        count = count_cards(path)
        status = "✅" if count == 100 else "❌"
        print(f"{status} {path.name}: {count} cards")


if __name__ == "__main__":
    main()
