#!/usr/bin/env python3
"""Build normalized static JSON data for the MTG bulk viewer web app.

Reads bulk.txt plus every list under decks/ and collections/ (precons/
is intentionally skipped - it's for manual precon-vs-deck diffing, not
part of the viewer), resolves every unique card name's identity against
Scryfall (with a persistent cache in cache/card-data.json), and writes
static JSON into web/public/data/ for the frontend to fetch.

Pricing never comes from Scryfall. If cache/bulk-prices.json exists (see
scripts/fetch-bulk-prices.py), its real Cardmarket prices are applied to
any card it covers; everything else simply has no price until you
mirror it into your Archidekt bulk deck and re-fetch.

Usage:
    python3 scripts/build/build.py [--strict]

Options:
    --strict   exit non-zero if any card name failed to resolve
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emit import emit_all  # noqa: E402
from parse import CardList, discover_card_lists, normalize_name  # noqa: E402
from resolve import (  # noqa: E402
    apply_bulk_prices,
    apply_list_prices,
    load_cache,
    prune_cache,
    resolve_names,
    save_cache,
)

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "cache" / "card-data.json"
BULK_PRICES_PATH = ROOT / "cache" / "bulk-prices.json"
LIST_PRICES_PATH = ROOT / "cache" / "list-prices.json"
DATA_DIR = ROOT / "web" / "public" / "data"


def collect_names(lists: list[CardList]) -> set[str]:
    names: set[str] = set()
    for card_list in lists:
        for entry in card_list.entries:
            names.add(entry.name)
    return names


def collect_printing_hints(lists: list[CardList]) -> dict[str, tuple[str, str]]:
    """Map normalized name -> (set, collector_number) for every entry that
    pins a specific printing (e.g. "Mystical Tutor (DMR) 289"). Lists are
    processed in order and later ones win on conflicts - callers should
    pass bulk last, since it represents the physically-owned printing.
    """
    hints: dict[str, tuple[str, str]] = {}
    for card_list in lists:
        for entry in card_list.entries:
            if entry.set and entry.collector_number:
                hints[normalize_name(entry.name)] = (entry.set, entry.collector_number)
    return hints


def load_bulk_prices() -> dict[str, Any] | None:
    if not BULK_PRICES_PATH.exists():
        return None
    return json.loads(BULK_PRICES_PATH.read_text(encoding="utf-8"))


def load_list_prices() -> dict[str, Any] | None:
    if not LIST_PRICES_PATH.exists():
        return None
    return json.loads(LIST_PRICES_PATH.read_text(encoding="utf-8"))


def main() -> int:
    strict = "--strict" in sys.argv[1:]

    bulk, lists = discover_card_lists(ROOT)
    all_lists = [bulk, *lists]

    unique_names = collect_names(all_lists)
    print(f"Discovered {len(all_lists) - 1} deck/collection list(s), "
          f"{len(unique_names)} unique card name(s) total.")

    cache = load_cache(CACHE_PATH)
    printing_hints = collect_printing_hints([*lists, bulk])
    card_data, warnings = resolve_names(unique_names, cache, printing_hints)
    pruned = prune_cache(cache, unique_names)
    save_cache(CACHE_PATH, cache)
    if pruned:
        print(f"Pruned {pruned} stale cache entr{'y' if pruned == 1 else 'ies'}.")

    bulk_prices = load_bulk_prices()
    bulk_prices_meta: dict[str, Any] | None = None
    if bulk_prices:
        applied = apply_bulk_prices(card_data, bulk_prices.get("prices", {}))
        bulk_prices_meta = {
            "fetchedAt": bulk_prices.get("fetchedAt"),
            "source": bulk_prices.get("source"),
            "archidektDeckId": bulk_prices.get("archidektDeckId"),
            "deckName": bulk_prices.get("deckName"),
            "appliedCount": applied,
        }
        print(f"Applied {applied} Cardmarket price(s) from {BULK_PRICES_PATH.name}.")
    else:
        print(
            f"No {BULK_PRICES_PATH.name} found - no cards will show a price. "
            "Run scripts/fetch-bulk-prices.py to fetch real Cardmarket prices for owned cards."
        )

    list_prices = load_list_prices()
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

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    emit_all(
        DATA_DIR, bulk, lists, card_data, warnings, generated_at, bulk_prices_meta, list_prices_meta
    )

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    unresolved_count = sum(1 for d in card_data.values() if not d.resolved)
    print(
        f"Done. {len(card_data)} unique cards resolved, "
        f"{unresolved_count} unresolved, {len(warnings)} warning(s)."
    )
    print(f"Data written to {DATA_DIR}")

    if strict and (unresolved_count > 0 or warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
