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

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from parse import parse_entries  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    for filepath in sys.argv[1:]:
        path = Path(filepath)
        count = sum(e.qty for e in parse_entries(path))
        status = "✅" if count == 100 else "❌"
        print(f"{status} {path.name}: {count} cards")


if __name__ == "__main__":
    main()
