from allocate import CardData, allocate
from parse import CardList, Entry


def make_list(id_, kind, name, entries, status="active", proxy=False, collection=False):
    return CardList(
        id=id_,
        kind=kind,
        status=status,
        name=name,
        source_path=f"{kind}/{id_}.txt",
        entries=entries,
        proxy=proxy,
        collection=collection,
    )


def e(name, qty, line=1):
    return Entry(name=name, qty=qty, line=line)


def card(type_line="Artifact"):
    return CardData(name="x", type_line=type_line)


def test_worked_example_from_refactor_md():
    bulk = make_list("bulk", "bulk", "Bulk", [e("Sol Ring", 2)])
    deck_a = make_list("a", "deck", "Deck A", [e("Sol Ring", 1)])
    deck_b = make_list("b", "deck", "Deck B", [e("Sol Ring", 1)])
    deck_c = make_list("c", "deck", "Deck C", [e("Sol Ring", 1)])
    lists = [deck_a, deck_b, deck_c]
    card_data = {"sol ring": card()}

    usage, ownership = allocate(bulk, lists, card_data)

    u = usage["sol ring"]
    assert u.owned == 2
    assert u.available == 0
    assert [(a.list_id, a.quantity) for a in u.allocations] == [("a", 1), ("b", 1)]

    assert ownership["deck-a"][0].owned_qty == 1
    assert ownership["deck-a"][0].missing_qty == 0
    assert ownership["deck-b"][0].owned_qty == 1
    assert ownership["deck-b"][0].missing_qty == 0
    assert ownership["deck-c"][0].owned_qty == 0
    assert ownership["deck-c"][0].missing_qty == 1


def test_basic_land_always_fully_owned_and_excluded_from_usage():
    bulk = make_list("bulk", "bulk", "Bulk", [])
    deck = make_list("a", "deck", "Deck A", [e("Forest", 10)])
    card_data = {"forest": card(type_line="Basic Land - Forest")}

    usage, ownership = allocate(bulk, [deck], card_data)

    assert "forest" not in usage
    assert ownership["deck-a"][0] == ownership["deck-a"][0]
    assert ownership["deck-a"][0].owned_qty == 10
    assert ownership["deck-a"][0].missing_qty == 0


def test_archived_proxy_and_collection_do_not_claim_allocated_demand():
    bulk = make_list("bulk", "bulk", "Bulk", [e("Sol Ring", 1)])
    active_deck = make_list("a", "deck", "Active", [e("Sol Ring", 1)])
    archived_deck = make_list("b", "deck", "Archived", [e("Sol Ring", 1)], status="archived")
    proxy_deck = make_list("c", "deck", "Proxy", [e("Sol Ring", 1)], proxy=True)
    collection = make_list("d", "collection", "Wishlist", [e("Sol Ring", 1)])
    lists = [active_deck, archived_deck, proxy_deck, collection]
    card_data = {"sol ring": card()}

    usage, ownership = allocate(bulk, lists, card_data)

    u = usage["sol ring"]
    assert u.available == 0
    assert [a.list_id for a in u.allocations] == ["a"]

    # The active deck claims the only copy.
    assert ownership["deck-a"][0].owned_qty == 1
    # Everyone else independently diffs against the same (now-zero)
    # available pool - none of them deplete it further for each other.
    assert ownership["deck-b"][0].owned_qty == 0
    assert ownership["deck-b"][0].missing_qty == 1
    assert ownership["collection-d"][0].owned_qty == 0
    assert ownership["collection-d"][0].missing_qty == 1


def test_non_active_lists_each_independently_see_full_available_pool():
    bulk = make_list("bulk", "bulk", "Bulk", [e("Sol Ring", 1)])
    archived_1 = make_list("b", "deck", "Archived 1", [e("Sol Ring", 1)], status="archived")
    archived_2 = make_list("c", "deck", "Archived 2", [e("Sol Ring", 1)], status="archived")
    lists = [archived_1, archived_2]
    card_data = {"sol ring": card()}

    usage, ownership = allocate(bulk, lists, card_data)

    assert usage["sol ring"].available == 1
    # Both archived decks see the one available copy as owned - they
    # don't compete with each other since neither is "real" demand.
    assert ownership["deck-b"][0].owned_qty == 1
    assert ownership["deck-c"][0].owned_qty == 1


def test_split_entry_claims_in_file_order_within_one_list():
    bulk = make_list("bulk", "bulk", "Bulk", [e("Mountain-not-basic", 3)])
    deck = make_list(
        "a",
        "deck",
        "Deck A",
        [e("Mountain-not-basic", 2, line=1), e("Mountain-not-basic", 2, line=2)],
    )
    card_data = {"mountain-not-basic": card(type_line="Land")}

    usage, ownership = allocate(bulk, [deck], card_data)

    assert usage["mountain-not-basic"].owned == 3
    assert ownership["deck-a"][0].owned_qty == 2
    assert ownership["deck-a"][0].missing_qty == 0
    assert ownership["deck-a"][1].owned_qty == 1
    assert ownership["deck-a"][1].missing_qty == 1


def test_deck_order_is_deterministic_by_list_order_passed_in():
    bulk = make_list("bulk", "bulk", "Bulk", [e("Sol Ring", 1)])
    first = make_list("a", "deck", "First", [e("Sol Ring", 1)])
    second = make_list("b", "deck", "Second", [e("Sol Ring", 1)])
    card_data = {"sol ring": card()}

    usage, ownership = allocate(bulk, [first, second], card_data)

    assert ownership["deck-a"][0].owned_qty == 1
    assert ownership["deck-b"][0].owned_qty == 0
    assert [a.list_id for a in usage["sol ring"].allocations] == ["a"]
