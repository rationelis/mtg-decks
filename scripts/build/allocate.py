"""Card allocation: one physical copy can only be claimed by one "real"
active deck at a time (see REFACTOR.md §9).

Independent per-list Owned/Missing diffing (the old model) let every deck
claim the same scarce bulk card as "owned" even if only one copy exists.
This module computes a single, deterministic allocation across every list
at once: bulk supply is handed out to "real" active decks first (in file
path order - the first deck encountered gets first claim). Whatever
remains after that (available) is what every other list - archived
decks, proxy decks, collections/wishlists - is diffed against
independently, exactly as a brand-new deck asking for this card today
would see; none of them reserve physical cards, so they never deplete
available from one another.

Basic lands are exempt entirely (bulk.txt never tracks them - there's no
point counting Forests): every entry for a basic land is always fully
owned and never touches the shared pool, and such cards don't appear in
`usage` at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from parse import CardList
from resolve import CardData, normalize_name


@dataclass(frozen=True)
class Allocation:
    list_id: str
    list_name: str
    quantity: int


@dataclass(frozen=True)
class Usage:
    owned: int
    available: int
    allocations: list[Allocation] = field(default_factory=list)


@dataclass(frozen=True)
class EntryOwnership:
    owned_qty: int
    missing_qty: int


def is_basic_land(card: CardData) -> bool:
    return "basic land" in card.type_line.lower()


def _is_real_active_deck(card_list: CardList) -> bool:
    return (
        card_list.kind == "deck"
        and card_list.status == "active"
        and not card_list.proxy
        and not card_list.collection
    )


def _list_key(card_list: CardList) -> str:
    return f"{card_list.kind}-{card_list.id}"


def allocate(
    bulk: CardList,
    lists: list[CardList],
    card_data: dict[str, CardData],
) -> tuple[dict[str, Usage], dict[str, list[EntryOwnership]]]:
    """Returns (usage keyed by normalized card name - excludes basic
    lands entirely, entry_ownership keyed by f"{list.kind}-{list.id}",
    one EntryOwnership per entry, aligned 1:1 with that list's `entries`
    in order). Bulk's own entries never get an EntryOwnership list.
    """
    usage: dict[str, Usage] = {}
    entry_ownership: dict[str, list[EntryOwnership]] = {
        _list_key(cl): [EntryOwnership(0, 0) for _ in cl.entries] for cl in lists
    }

    bulk_qty_by_key: dict[str, int] = {}
    for entry in bulk.entries:
        key = normalize_name(entry.name)
        bulk_qty_by_key[key] = bulk_qty_by_key.get(key, 0) + entry.qty

    real_active_decks = [cl for cl in lists if _is_real_active_deck(cl)]
    other_lists = [cl for cl in lists if not _is_real_active_deck(cl)]

    all_keys = set(bulk_qty_by_key)
    for card_list in lists:
        for entry in card_list.entries:
            all_keys.add(normalize_name(entry.name))

    for key in all_keys:
        card = card_data.get(key)
        if card is not None and is_basic_land(card):
            for card_list in lists:
                ownership = entry_ownership[_list_key(card_list)]
                for i, entry in enumerate(card_list.entries):
                    if normalize_name(entry.name) == key:
                        ownership[i] = EntryOwnership(entry.qty, 0)
            continue  # basic lands never touch the shared pool / usage.json

        remaining = bulk_qty_by_key.get(key, 0)
        allocations: list[Allocation] = []

        for deck in real_active_decks:
            ownership = entry_ownership[_list_key(deck)]
            claimed_total = 0
            for i, entry in enumerate(deck.entries):
                if normalize_name(entry.name) != key:
                    continue
                claim = min(entry.qty, remaining)
                ownership[i] = EntryOwnership(claim, entry.qty - claim)
                remaining -= claim
                claimed_total += claim
            if claimed_total > 0:
                allocations.append(Allocation(deck.id, deck.name, claimed_total))

        available = remaining

        # Every other list (archived deck, collection/wishlist, proxy deck)
        # is not "real" demand - it doesn't reserve physical cards, so each
        # is diffed independently against the same `available`, exactly as
        # a brand-new deck asking for this card today would see (see
        # REFACTOR.md §9.2/§9.3). They never deplete `available` from one
        # another.
        for other in other_lists:
            ownership = entry_ownership[_list_key(other)]
            for i, entry in enumerate(other.entries):
                if normalize_name(entry.name) != key:
                    continue
                claim = min(entry.qty, available)
                ownership[i] = EntryOwnership(claim, entry.qty - claim)

        usage[key] = Usage(owned=bulk_qty_by_key.get(key, 0), available=available, allocations=allocations)

    return usage, entry_ownership
