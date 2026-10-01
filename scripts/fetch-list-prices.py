#!/usr/bin/env python3
"""
Fetch a reference Cardmarket price for one ad-hoc deck you don't own, via
Archidekt - e.g. someone else's public decklist that mirrors a wishlist
you don't have a local Archidekt id for. Merged into whatever's already
in cache/list-prices.json.

This is entirely optional and separate from cache/bulk-prices.json (your
actual owned collection's real prices). A card's owned price always wins
if it's both owned and referenced here - see resolve.apply_list_prices.

Every deck/collection under decks/ and collections/ that already has a
known Archidekt id (its "NNNN_name.txt" filename, or a
"# archidekt: NNNN" metadata line) is fetched automatically by the main
build (`python3 scripts/build/build.py`) - this script is only for a
one-off extra source that isn't one of your own files.

Usage:
    python3 scripts/fetch-list-prices.py <label> <archidekt_deck_id>

Example:
    python3 scripts/fetch-list-prices.py orcs 25657626
    # https://archidekt.com/decks/25657626/oops_all_orcs -> cache/list-prices.json

After running, rebuild data (`python3 scripts/build/build.py`) to apply
the new prices.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from archidekt import fetch_deck, main_deck_entries, price_map  # noqa: E402
from parse import normalize_name  # noqa: E402

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "list-prices.json"


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    label, deck_id = sys.argv[1].strip(), sys.argv[2].strip()

    try:
        deck = fetch_deck(deck_id)
    except requests.RequestException as e:
        print(f"Error fetching Archidekt deck {deck_id}: {e}", file=sys.stderr)
        sys.exit(1)

    deck_name = deck.get("name", "Unknown deck")
    entries = main_deck_entries(deck)
    print(f"[{label}] {deck_name!r} - {len(entries)} entries (Sideboard/Maybeboard excluded).")

    if not entries:
        print(f"[{label}] No cards found in deck.", file=sys.stderr)
        sys.exit(1)

    prices, unpriced = price_map(deck, normalize_name)
    flat_prices = {k: v["price_eur"] for k, v in prices.items()}
    print(f"[{label}] Priced {len(flat_prices)} card(s).")
    if unpriced:
        print(
            f"[{label}] WARNING: {len(unpriced)} card(s) have no Cardmarket price on "
            "Archidekt (pick a specific printing for them there):",
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
        "pricedCount": len(flat_prices),
    }
    cache["prices"].update(flat_prices)
    cache["prices"] = dict(sorted(cache["prices"].items()))

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Written to {CACHE_PATH}")
    print("Next: python3 scripts/build/build.py, to apply these as fallback prices for unowned cards.")


if __name__ == "__main__":
    main()
