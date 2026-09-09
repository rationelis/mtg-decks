#!/usr/bin/env python3
"""
Fetch real Cardmarket prices for your bulk collection, via Archidekt.

Scryfall doesn't factor into pricing at all - for cards you actually own,
real pricing is available for free: mirror your bulk into an Archidekt
deck (one row per card you physically have), and Archidekt already shows
each row's current Cardmarket price. This script fetches that deck and
writes a small, timestamped price cache that the build uses to price
owned cards.

Cards that aren't in the bulk-mirror deck (e.g. missing cards from a
deck/wishlist you don't own yet) simply have no price - that's a signal
to mirror them into Archidekt and re-run this script, not something this
tool guesses at.

Usage:
    python3 scripts/fetch-bulk-prices.py <archidekt_deck_id>

Example:
    python3 scripts/fetch-bulk-prices.py 25868036
    # https://archidekt.com/decks/25868036/bulk -> cache/bulk-prices.json

After running: rebuild data (`mask build-data`) and commit
cache/bulk-prices.json alongside your bulk.txt changes.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from archidekt import fetch_deck, main_deck_entries, price_map  # noqa: E402
from parse import normalize_name  # noqa: E402

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "bulk-prices.json"


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    deck_id = sys.argv[1].strip()

    deck = fetch_deck(deck_id)
    deck_name = deck.get("name", "Unknown deck")
    entries = main_deck_entries(deck)
    print(f"Deck: {deck_name!r} - {len(entries)} entries (Sideboard/Maybeboard excluded).")

    if not entries:
        print("No cards found in deck.", file=sys.stderr)
        sys.exit(1)

    # Keyed by normalized name to match how the build looks prices up;
    # if the same card appears as more than one row (e.g. two different
    # printings you own), the last one wins - good enough for a single
    # per-name price.
    prices, unpriced = price_map(deck, normalize_name)

    print(f"Priced {len(prices)} card(s).")
    if unpriced:
        print(
            f"WARNING: {len(unpriced)} card(s) have no Cardmarket price on Archidekt "
            "(pick a specific printing for them there):",
            file=sys.stderr,
        )
        for name in sorted(unpriced):
            print(f"  - {name}", file=sys.stderr)

    payload = {
        "source": "cardmarket-via-archidekt",
        "archidektDeckId": deck_id,
        "deckName": deck_name,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prices": dict(sorted(prices.items())),
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Written to {CACHE_PATH}")
    print("Next: mask build-data, then commit cache/bulk-prices.json.")


if __name__ == "__main__":
    main()
