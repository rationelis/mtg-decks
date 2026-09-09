#!/usr/bin/env python3
"""
Fetch reference Cardmarket prices for decks/collections you don't (fully)
own, via Archidekt - e.g. a proxy deck or wishlist. This lets the web app
show a "price to complete" even for cards nowhere in your physical bulk.

This is entirely optional and separate from cache/bulk-prices.json (your
actual owned collection's real prices). A card's owned price always wins
if it's both owned and referenced here - see resolve.apply_list_prices.

Usage:
    python3 scripts/fetch-list-prices.py
        Fetches every deck/collection under decks/ and collections/ that
        has a known Archidekt deck id - taken from its "NNNN_name.txt"
        filename (see parse.py) or a "# archidekt: NNNN" metadata line -
        keyed by that list's own id. Lists with no resolvable id are
        skipped with a warning. Rebuilds cache/list-prices.json from
        scratch each time, so it never accumulates stale entries.

    python3 scripts/fetch-list-prices.py <label> <archidekt_deck_id>
        Fetches one ad-hoc reference deck under a custom label instead -
        e.g. someone else's public decklist that mirrors a wishlist you
        don't have a local Archidekt id for. Merged into whatever's
        already in cache/list-prices.json.

Examples:
    python3 scripts/fetch-list-prices.py
    python3 scripts/fetch-list-prices.py orcs 25657626
    # https://archidekt.com/decks/25657626/oops_all_orcs -> cache/list-prices.json

After running, rebuild data (`mask build-data`) to apply the new prices.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from archidekt import fetch_deck, main_deck_entries, price_map  # noqa: E402
from parse import discover_card_lists, normalize_name  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "cache" / "list-prices.json"


def auto_targets() -> list[tuple[str, str]]:
    """(label, archidekt_deck_id) for every non-bulk list with a resolvable
    Archidekt id, label = f"{kind}-{id}" (matches lists/{kind}-{id}.json,
    so a source is always traceable back to the exact list it prices)."""
    _, lists = discover_card_lists(ROOT)
    targets: list[tuple[str, str]] = []
    skipped: list[str] = []
    for card_list in lists:
        if card_list.archidekt_id:
            targets.append((f"{card_list.kind}-{card_list.id}", card_list.archidekt_id))
        else:
            skipped.append(card_list.source_path)
    if skipped:
        print(
            "Skipping (no Archidekt id - rename to 'NNNN_name.txt' or add "
            f"a '# archidekt: NNNN' line): {', '.join(skipped)}",
            file=sys.stderr,
        )
    return targets


def fetch_one(label: str, deck_id: str, cache: dict) -> None:
    deck = fetch_deck(deck_id)
    deck_name = deck.get("name", "Unknown deck")
    entries = main_deck_entries(deck)
    print(f"[{label}] {deck_name!r} - {len(entries)} entries (Sideboard/Maybeboard excluded).")

    if not entries:
        print(f"[{label}] No cards found in deck.", file=sys.stderr)
        return

    prices, unpriced = price_map(deck, normalize_name)
    print(f"[{label}] Priced {len(prices)} card(s).")
    if unpriced:
        print(
            f"[{label}] WARNING: {len(unpriced)} card(s) have no Cardmarket price on "
            "Archidekt (pick a specific printing for them there):",
            file=sys.stderr,
        )
        for name in sorted(unpriced):
            print(f"  - {name}", file=sys.stderr)

    cache["sources"][label] = {
        "archidektDeckId": deck_id,
        "deckName": deck_name,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pricedCount": len(prices),
    }
    cache["prices"].update(prices)


def save_cache(cache: dict) -> None:
    cache["prices"] = dict(sorted(cache["prices"].items()))
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if len(sys.argv) == 1:
        targets = auto_targets()
        if not targets:
            print("No decks/collections with a known Archidekt id found.", file=sys.stderr)
            sys.exit(1)
        # Rebuilt from scratch (not merged) - auto mode always covers every
        # discoverable list, so anything not seen this run is genuinely
        # gone (renamed/deleted) rather than something worth preserving.
        cache: dict = {"sources": {}, "prices": {}}
        for label, deck_id in targets:
            fetch_one(label, deck_id, cache)
    elif len(sys.argv) == 3:
        label, deck_id = sys.argv[1].strip(), sys.argv[2].strip()
        cache = (
            json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if CACHE_PATH.exists()
            else {"sources": {}, "prices": {}}
        )
        fetch_one(label, deck_id, cache)
    else:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    save_cache(cache)
    print(f"Written to {CACHE_PATH}")
    print("Next: mask build-data, to apply these as fallback prices for unowned cards.")


if __name__ == "__main__":
    main()
