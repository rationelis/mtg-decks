"""Pins the exact JSON shapes scripts/build/emit.py writes, so a field
added/renamed/removed on the Python side is caught here instead of
silently drifting from web/src/types.ts (see REFACTOR.md §8.3). The
companion test on the TypeScript side (web/src/types.test.ts) loads the
same fixture files under tests/fixtures/ and pins the matching
TypeScript interfaces against them, so a change to either side without
updating the shared fixture fails loudly on whichever side wasn't
updated.
"""

import json
from pathlib import Path

from allocate import Allocation, EntryOwnership, Usage
from emit import emit_all
from parse import CardList, Entry
from resolve import CardData

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> list[str]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_card_json_field_set_matches_fixture():
    data_dir_card = CardData(name="Sol Ring", price_eur=1.5, price_state="exact")
    bulk = CardList(id="bulk", kind="bulk", status="active", name="Bulk", source_path="bulk.txt", entries=[])

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        emit_all(
            data_dir,
            bulk,
            [],
            {"sol ring": data_dir_card},
            {},
            {},
            [],
            "2024-01-01T00:00:00+00:00",
        )
        cards_json = json.loads((data_dir / "cards.json").read_text(encoding="utf-8"))

    assert set(cards_json["sol ring"].keys()) == set(_load("card_json_fields.json"))


def test_list_entry_json_field_set_matches_fixture_when_ownership_present():
    deck = CardList(
        id="a",
        kind="deck",
        status="active",
        name="Deck A",
        source_path="decks/a.txt",
        entries=[Entry(name="Sol Ring", qty=1, line=1)],
    )
    bulk = CardList(id="bulk", kind="bulk", status="active", name="Bulk", source_path="bulk.txt", entries=[])
    card_data = {"sol ring": CardData(name="Sol Ring")}
    entry_ownership = {"deck-a": [EntryOwnership(owned_qty=1, missing_qty=0)]}

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        emit_all(data_dir, bulk, [deck], card_data, {}, entry_ownership, [], "2024-01-01T00:00:00+00:00")
        list_json = json.loads((data_dir / "lists" / "deck-a.json").read_text(encoding="utf-8"))

    assert set(list_json["entries"][0].keys()) == set(_load("list_entry_json_fields.json"))


def test_usage_json_field_set_matches_fixture():
    bulk = CardList(id="bulk", kind="bulk", status="active", name="Bulk", source_path="bulk.txt", entries=[])
    usage = {
        "sol ring": Usage(owned=2, available=0, allocations=[Allocation("a", "Deck A", 1)]),
    }
    card_data = {"sol ring": CardData(name="Sol Ring")}

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        emit_all(data_dir, bulk, [], card_data, usage, {}, [], "2024-01-01T00:00:00+00:00")
        usage_json = json.loads((data_dir / "usage.json").read_text(encoding="utf-8"))

    assert set(usage_json["sol ring"].keys()) == set(_load("usage_json_fields.json"))
    assert set(usage_json["sol ring"]["allocations"][0].keys()) == set(
        _load("allocation_json_fields.json")
    )
