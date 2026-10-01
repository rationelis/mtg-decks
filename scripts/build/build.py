#!/usr/bin/env python3
"""Build normalized static JSON data for the MTG bulk viewer web app.

Single command, five stages (see REFACTOR.md §5):

  1. Parse every card-list text file (bulk.txt, decks/, collections/).
  2. Resolve every unique card name's identity against Scryfall, verify
     any pinned printings, and detect conflicting pins across files.
  3. Fetch real (bulk-mirror) and reference (list) Cardmarket prices via
     Archidekt.
  4. Allocate bulk supply across "real" active decks (see
     scripts/build/allocate.py).
  5. Emit static JSON into web/public/data/.

Stages 1-2 are strict: any data-integrity problem (a malformed entry
line, an unknown card name, a pinned printing that doesn't exist or
doesn't match, or conflicting pins for the same card across files) is a
hard, build-stopping error. Every such error is collected (not just the
first one found) and printed in deterministic path:line order; nothing
is written - not even the identity cache - if any exist.

Pricing (stage 3) is tolerant: a network hiccup degrades to a warning and
previously-cached prices, never a build failure.

Usage:
    python3 scripts/build/build.py [--bulk-deck <archidekt_deck_id>]

The bulk-mirror deck id only needs to be passed once; after that it's
remembered in cache/bulk-prices.json and reused automatically.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from allocate import allocate  # noqa: E402
from archidekt import fetch_deck, price_map  # noqa: E402
from emit import emit_all  # noqa: E402
from parse import CardList, discover_card_lists, normalize_name  # noqa: E402
from resolve import (  # noqa: E402
    apply_bulk_prices,
    apply_list_prices,
    load_cache,
    prune_cache,
    resolve_identity,
    save_cache,
)

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "cache" / "card-data.json"
BULK_PRICES_PATH = ROOT / "cache" / "bulk-prices.json"
LIST_PRICES_PATH = ROOT / "cache" / "list-prices.json"
DATA_DIR = ROOT / "web" / "public" / "data"


def collect_unique_names(bulk: CardList, lists: list[CardList]) -> set[str]:
    names: set[str] = set()
    for card_list in [bulk, *lists]:
        for entry in card_list.entries:
            names.add(entry.name)
    return names


def load_bulk_prices() -> dict[str, Any] | None:
    if not BULK_PRICES_PATH.exists():
        return None
    return json.loads(BULK_PRICES_PATH.read_text(encoding="utf-8"))


def load_list_prices() -> dict[str, Any] | None:
    if not LIST_PRICES_PATH.exists():
        return None
    return json.loads(LIST_PRICES_PATH.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def fetch_bulk_prices(deck_id: str | None, warnings: list[str]) -> dict[str, Any] | None:
    """Fetch + write cache/bulk-prices.json for the bulk-mirror Archidekt
    deck. Falls back to whatever's already cached on disk if the network
    is unavailable, or if no deck id is known at all (§5.2/§6.4/§6.5).
    """
    existing = load_bulk_prices()
    if deck_id is None:
        deck_id = existing.get("archidektDeckId") if existing else None
    if deck_id is None:
        warnings.append(
            "No bulk-mirror Archidekt deck id known - no cards will show a price. "
            "Run with --bulk-deck <archidekt_deck_id> once."
        )
        return existing

    try:
        deck = fetch_deck(deck_id)
    except requests.RequestException as e:
        warnings.append(
            f"Could not fetch bulk-mirror deck {deck_id} from Archidekt ({e}); "
            "using previously cached prices."
        )
        return existing

    deck_name = deck.get("name", "Unknown deck")
    prices, unpriced = price_map(deck, normalize_name)
    if unpriced:
        print(
            f"NOTE: {len(unpriced)} card(s) in the bulk-mirror deck have no Cardmarket "
            "price on Archidekt (pick a specific printing for them there):",
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
    _save_json(BULK_PRICES_PATH, payload)
    print(f"Fetched {len(prices)} bulk-mirror Cardmarket price(s) from deck {deck_id}.")
    return payload


def fetch_list_prices(lists: list[CardList], warnings: list[str]) -> dict[str, Any] | None:
    """Fetch + write cache/list-prices.json from scratch for every
    deck/collection with a known Archidekt id - reference pricing for
    cards you don't (fully) own (§5.2/§6.4). A single list's fetch
    failure only skips that list's prices this run; it is deliberately
    not merged with the previous run's data for that source (the
    simplest correct behavior for what's already a rebuild-from-scratch
    cache).
    """
    targets = [(f"{cl.kind}-{cl.id}", cl.archidekt_id) for cl in lists if cl.archidekt_id]
    if not targets:
        return None

    cache: dict[str, Any] = {"sources": {}, "prices": {}}
    any_fetched = False
    for label, deck_id in targets:
        assert deck_id is not None
        try:
            deck = fetch_deck(deck_id)
        except requests.RequestException as e:
            warnings.append(
                f"[{label}] could not fetch Archidekt deck {deck_id} ({e}); "
                "skipping its reference prices this run."
            )
            continue

        deck_name = deck.get("name", "Unknown deck")
        prices, _unpriced = price_map(deck, normalize_name)
        flat_prices = {k: v["price_eur"] for k, v in prices.items()}
        cache["sources"][label] = {
            "archidektDeckId": deck_id,
            "deckName": deck_name,
            "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pricedCount": len(flat_prices),
        }
        cache["prices"].update(flat_prices)
        any_fetched = True

    if not any_fetched:
        return None

    cache["prices"] = dict(sorted(cache["prices"].items()))
    _save_json(LIST_PRICES_PATH, cache)
    print(f"Fetched reference Cardmarket prices for {len(cache['sources'])} list(s).")
    return cache


def main() -> int:
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument(
        "--bulk-deck",
        default=None,
        help="Archidekt deck id for the bulk-mirror deck (only needed once; "
        "remembered in cache/bulk-prices.json afterwards).",
    )
    args = arg_parser.parse_args()

    bulk, lists, parse_errors = discover_card_lists(ROOT)
    print(f"Discovered {len(lists)} deck/collection list(s).")

    cache = load_cache(CACHE_PATH)
    card_data, pins, identity_errors, warnings = resolve_identity(bulk, lists, cache)

    errors = sorted(parse_errors + identity_errors, key=lambda e: (e.path, e.line))
    if errors:
        plural = "error" if len(errors) == 1 else "errors"
        print(f"\nBuild failed: {len(errors)} data-integrity {plural}.\n", file=sys.stderr)
        for error in errors:
            print(str(error), file=sys.stderr)
            print(file=sys.stderr)
        print(
            "Nothing was written (including the identity cache) - fix the above and "
            "re-run.",
            file=sys.stderr,
        )
        return 1

    unique_names = collect_unique_names(bulk, lists)
    pruned = prune_cache(cache, unique_names)
    save_cache(CACHE_PATH, cache)
    if pruned:
        print(f"Pruned {pruned} stale cache entr{'y' if pruned == 1 else 'ies'}.")

    bulk_prices = fetch_bulk_prices(args.bulk_deck, warnings)
    bulk_prices_meta: dict[str, Any] | None = None
    if bulk_prices:
        applied = apply_bulk_prices(card_data, bulk_prices.get("prices", {}), pins)
        bulk_prices_meta = {
            "fetchedAt": bulk_prices.get("fetchedAt"),
            "source": bulk_prices.get("source"),
            "archidektDeckId": bulk_prices.get("archidektDeckId"),
            "deckName": bulk_prices.get("deckName"),
            "appliedCount": applied,
        }
        print(f"Applied {applied} Cardmarket price(s) from {BULK_PRICES_PATH.name}.")

    list_prices = fetch_list_prices(lists, warnings)
    list_prices_meta: dict[str, Any] | None = None
    if list_prices:
        applied = apply_list_prices(card_data, list_prices.get("prices", {}))
        list_prices_meta = {
            "sources": list_prices.get("sources", {}),
            "appliedCount": applied,
        }
        print(
            f"Applied {applied} reference Cardmarket price(s) from "
            f"{LIST_PRICES_PATH.name} (unowned-card fallback)."
        )

    usage, entry_ownership = allocate(bulk, lists, card_data)

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    emit_all(
        DATA_DIR,
        bulk,
        lists,
        card_data,
        usage,
        entry_ownership,
        warnings,
        generated_at,
        bulk_prices_meta,
        list_prices_meta,
    )

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    print(f"Done. {len(card_data)} unique card(s) resolved, {len(warnings)} warning(s).")
    print(f"Data written to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
