import requests

import resolve
from parse import CardList, Entry
from resolve import collect_pins, resolve_pin_conflicts


def make_list(id_, kind, name, entries, is_bulk=False):
    return CardList(
        id=id_,
        kind="bulk" if is_bulk else kind,
        status="active",
        name=name,
        source_path=f"{kind}/{id_}.txt" if not is_bulk else "bulk.txt",
        entries=entries,
    )


def pinned_entry(name, set_code, num, line):
    return Entry(name=name, qty=1, line=line, set=set_code, collector_number=num)


# --- Pin conflict resolution (pure logic, no network) -----------------------


def test_bulk_pin_is_always_authoritative():
    bulk = make_list("bulk", "bulk", "Bulk", [pinned_entry("Sol Ring", "C21", "263", 1)], is_bulk=True)
    deck = make_list("a", "deck", "A", [pinned_entry("Sol Ring", "LEA", "1", 5)])

    pins = collect_pins(bulk, [deck])
    authoritative, errors = resolve_pin_conflicts(pins)

    assert authoritative["sol ring"].set == "C21"
    assert len(errors) == 1
    assert errors[0].path == "deck/a.txt"
    assert errors[0].line == 5
    assert "Conflicting printing pin" in errors[0].message


def test_no_bulk_pin_falls_back_to_smallest_path_line_and_never_conflicts():
    bulk = make_list("bulk", "bulk", "Bulk", [], is_bulk=True)
    deck_a = make_list("a", "deck", "A", [pinned_entry("Sol Ring", "LEA", "1", 3)])
    deck_b = make_list("b", "deck", "B", [pinned_entry("Sol Ring", "C21", "263", 2)])

    pins = collect_pins(bulk, [deck_a, deck_b])
    authoritative, errors = resolve_pin_conflicts(pins)

    # deck/a.txt < deck/b.txt lexicographically, so deck_a wins regardless
    # of line number - but with no physical truth recorded in bulk.txt for
    # this name, there's nothing to be in conflict with.
    assert authoritative["sol ring"].path == "deck/a.txt"
    assert errors == []


def test_bulk_owning_multiple_printings_never_conflicts_with_itself():
    bulk = make_list(
        "bulk",
        "bulk",
        "Bulk",
        [
            pinned_entry("Arcane Signet", "C20", "237", 44),
            pinned_entry("Arcane Signet", "CMM", "367", 45),
        ],
        is_bulk=True,
    )

    pins = collect_pins(bulk, [])
    authoritative, errors = resolve_pin_conflicts(pins)

    assert errors == []
    assert authoritative["arcane signet"].line == 44


def test_deck_pin_matching_any_owned_printing_is_not_a_conflict():
    bulk = make_list(
        "bulk",
        "bulk",
        "Bulk",
        [
            pinned_entry("Arcane Signet", "C20", "237", 44),
            pinned_entry("Arcane Signet", "CMM", "367", 45),
        ],
        is_bulk=True,
    )
    deck = make_list("a", "deck", "A", [pinned_entry("Arcane Signet", "cmm", "367", 10)])

    pins = collect_pins(bulk, [deck])
    _, errors = resolve_pin_conflicts(pins)

    assert errors == []


def test_deck_pin_matching_no_owned_printing_is_a_conflict():
    bulk = make_list(
        "bulk",
        "bulk",
        "Bulk",
        [
            pinned_entry("Arcane Signet", "C20", "237", 44),
            pinned_entry("Arcane Signet", "CMM", "367", 45),
        ],
        is_bulk=True,
    )
    deck = make_list("a", "deck", "A", [pinned_entry("Arcane Signet", "M3C", "283", 10)])

    pins = collect_pins(bulk, [deck])
    _, errors = resolve_pin_conflicts(pins)

    assert len(errors) == 1
    assert errors[0].path == "deck/a.txt"
    assert errors[0].line == 10


def test_matching_pins_across_files_produce_no_error():
    bulk = make_list("bulk", "bulk", "Bulk", [pinned_entry("Sol Ring", "C21", "263", 1)], is_bulk=True)
    deck = make_list("a", "deck", "A", [pinned_entry("Sol Ring", "c21", "263", 5)])

    pins = collect_pins(bulk, [deck])
    _, errors = resolve_pin_conflicts(pins)

    assert errors == []


# --- resolve_identity (network calls monkeypatched) -------------------------


def _bulk_with(entries):
    return make_list("bulk", "bulk", "Bulk", entries, is_bulk=True)


def test_resolve_identity_happy_path(monkeypatch):
    bulk = _bulk_with([Entry(name="Sol Ring", qty=1, line=1)])

    def fake_post_json(url, payload):
        return {
            "data": [
                {
                    "name": "Sol Ring",
                    "cmc": 1.0,
                    "colors": [],
                    "color_identity": [],
                    "type_line": "Artifact",
                    "oracle_text": "",
                    "set": "lea",
                    "set_name": "Limited Edition Alpha",
                    "rarity": "uncommon",
                    "scryfall_uri": "https://scryfall.com/x",
                    "id": "abc",
                }
            ],
            "not_found": [],
        }

    monkeypatch.setattr(resolve, "post_json", fake_post_json)

    card_data, pins, errors, warnings = resolve.resolve_identity(bulk, [], {})

    assert errors == []
    assert card_data["sol ring"].name == "Sol Ring"
    assert card_data["sol ring"].type_line == "Artifact"


def test_resolve_identity_unknown_name_is_hard_error(monkeypatch):
    bulk = _bulk_with([Entry(name="Totally Fake Card", qty=1, line=7)])

    def fake_post_json(url, payload):
        return {"data": [], "not_found": [{"name": "Totally Fake Card"}]}

    def fake_get_json(url, params=None):
        return None  # fuzzy lookup also finds nothing

    monkeypatch.setattr(resolve, "post_json", fake_post_json)
    monkeypatch.setattr(resolve, "get_json", fake_get_json)

    card_data, pins, errors, warnings = resolve.resolve_identity(bulk, [], {})

    assert len(errors) == 1
    assert errors[0].path == "bulk.txt"
    assert errors[0].line == 7
    assert "Unknown card name" in errors[0].message


def test_resolve_identity_unknown_name_includes_fuzzy_suggestion(monkeypatch):
    bulk = _bulk_with([Entry(name="Sol Rng", qty=1, line=7)])

    def fake_post_json(url, payload):
        return {"data": [], "not_found": [{"name": "Sol Rng"}]}

    def fake_get_json(url, params=None):
        return {"name": "Sol Ring"}

    monkeypatch.setattr(resolve, "post_json", fake_post_json)
    monkeypatch.setattr(resolve, "get_json", fake_get_json)

    _, _, errors, _ = resolve.resolve_identity(bulk, [], {})

    assert len(errors) == 1
    assert 'did you mean "Sol Ring"' in errors[0].message


def test_resolve_identity_network_down_reuses_confidently_resolved_cache(monkeypatch):
    bulk = _bulk_with([Entry(name="Sol Ring", qty=1, line=1)])
    cache = {
        "sol ring": {
            "name": "Sol Ring",
            "type_line": "Artifact",
            "fuzzy_matched_from": None,
        }
    }

    def fake_post_json(url, payload):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(resolve, "post_json", fake_post_json)

    card_data, pins, errors, warnings = resolve.resolve_identity(bulk, [], cache)

    assert errors == []
    assert card_data["sol ring"].name == "Sol Ring"
    assert any("reused previously-resolved cache" in w for w in warnings)


def test_resolve_identity_network_down_errors_when_cache_was_fuzzy_matched(monkeypatch):
    bulk = _bulk_with([Entry(name="Sol Ring", qty=1, line=3)])
    cache = {
        "sol ring": {
            "name": "Sol Ring",
            "type_line": "Artifact",
            "fuzzy_matched_from": "Sol Rng",  # never confidently resolved
        }
    }

    def fake_post_json(url, payload):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(resolve, "post_json", fake_post_json)

    _, _, errors, _ = resolve.resolve_identity(bulk, [], cache)

    assert len(errors) == 1
    assert errors[0].line == 3
    assert "never confidently resolved" in errors[0].message


def test_resolve_identity_network_down_errors_when_nothing_cached(monkeypatch):
    bulk = _bulk_with([Entry(name="Sol Ring", qty=1, line=3)])

    def fake_post_json(url, payload):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(resolve, "post_json", fake_post_json)

    _, _, errors, _ = resolve.resolve_identity(bulk, [], {})

    assert len(errors) == 1
    assert "never confidently resolved" in errors[0].message


def test_resolve_identity_pin_mismatch_is_hard_error(monkeypatch):
    bulk = _bulk_with([pinned_entry("Sol Ring", "WRONG", "999", 4)])

    def fake_post_json(url, payload):
        return {
            "data": [
                {
                    "name": "Sol Ring",
                    "cmc": 1.0,
                    "type_line": "Artifact",
                    "set": "lea",
                    "set_name": "Limited Edition Alpha",
                    "rarity": "uncommon",
                    "id": "abc",
                }
            ],
            "not_found": [],
        }

    def fake_get_json(url, params=None):
        # the pinned printing exists but is a different card
        return {"name": "Some Other Card"}

    monkeypatch.setattr(resolve, "post_json", fake_post_json)
    monkeypatch.setattr(resolve, "get_json", fake_get_json)

    _, _, errors, _ = resolve.resolve_identity(bulk, [], {})

    assert len(errors) == 1
    assert errors[0].line == 4
    assert "does not match" in errors[0].message


def test_resolve_identity_pin_not_found_is_hard_error(monkeypatch):
    bulk = _bulk_with([pinned_entry("Sol Ring", "ZZZ", "1", 4)])

    def fake_post_json(url, payload):
        return {
            "data": [
                {
                    "name": "Sol Ring",
                    "cmc": 1.0,
                    "type_line": "Artifact",
                    "set": "lea",
                    "set_name": "Limited Edition Alpha",
                    "rarity": "uncommon",
                    "id": "abc",
                }
            ],
            "not_found": [],
        }

    def fake_get_json(url, params=None):
        return None  # the pinned printing doesn't exist

    monkeypatch.setattr(resolve, "post_json", fake_post_json)
    monkeypatch.setattr(resolve, "get_json", fake_get_json)

    _, _, errors, _ = resolve.resolve_identity(bulk, [], {})

    assert len(errors) == 1
    assert "was not found on Scryfall" in errors[0].message
