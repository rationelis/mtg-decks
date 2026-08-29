#!/usr/bin/env python3
"""
Fetch reference Cardmarket prices for a deck/collection you don't (fully)
own, via Archidekt - e.g. a wishlist that mirrors a public Archidekt
decklist 1:1. This lets the web app show a "price to complete" even for
cards nowhere in your physical bulk.

This is entirely optional and separate from cache/bulk-prices.json (your
actual owned collection's real prices). A card's owned price always wins
if it's both owned and referenced here - see resolve.apply_list_prices.

Usage:
    python3 scripts/fetch-list-prices.py <label> <archidekt_deck_id>

Example:
    python3 scripts/fetch-list-prices.py orcs 25657626
    # https://archidekt.com/decks/25657626/oops_all_orcs -> cache/list-prices.json

Every label's prices are merged into the same cache/list-prices.json,
keyed by normalized card name. Run again with the same label to refresh
it, or a new label to add another reference deck. After running,
rebuild data (`mask build-data`) to apply it.
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

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "list-prices.json"


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    label = sys.argv[1].strip()
    deck_id = sys.argv[2].strip()

    deck = fetch_deck(deck_id)
    deck_name = deck.get("name", "Unknown deck")
    entries = main_deck_entries(deck)
    print(f"Deck: {deck_name!r} - {len(entries)} entries (Sideboard/Maybeboard excluded).")

    if not entries:
        print("No cards found in deck.", file=sys.stderr)
        sys.exit(1)

    prices, unpriced = price_map(deck, normalize_name)
    print(f"Priced {len(prices)} card(s) under label {label!r}.")
    if unpriced:
        print(
            f"WARNING: {len(unpriced)} card(s) have no Cardmarket price on Archidekt "
            "(pick a specific printing for them there):",
            file=sys.stderr,
        )
        for name in sorted(unpriced):
            print(f"  - {name}", file=sys.stderr)

    cache = (
        json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if CACHE_PATH.exists()
        else {"sources": {}, "prices": {}}
    )

    cache["sources"][label] = {
        "archidektDeckId": deck_id,
        "deckName": deck_name,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pricedCount": len(prices),
    }
    cache["prices"].update(prices)
    cache["prices"] = dict(sorted(cache["prices"].items()))

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Written to {CACHE_PATH}")
    print("Next: mask build-data, to apply these as fallback prices for unowned cards.")


if __name__ == "__main__":
    main()
