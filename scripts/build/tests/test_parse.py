import json
from pathlib import Path

import pytest

from parse import (
    discover_card_lists,
    normalize_name,
    parse_card_list,
    parse_entries,
    parse_entry_line,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_normalize_name_matches_fixture_cases():
    cases = json.loads((FIXTURES / "normalize_cases.json").read_text(encoding="utf-8"))
    for raw, expected in cases:
        assert normalize_name(raw) == expected


def test_basic_entry_parsing(tmp_path):
    p = write(tmp_path, "bulk.txt", "1x Lightning Bolt\n3 Counterspell\n")
    entries = parse_entries(p)
    assert [(e.name, e.qty) for e in entries] == [
        ("Lightning Bolt", 1),
        ("Counterspell", 3),
    ]


def test_printing_pin_and_foil(tmp_path):
    p = write(tmp_path, "bulk.txt", "1x Mystical Tutor (DMR) 289\n1 The Swarmlord (40K) 4 *F*\n")
    entries = parse_entries(p)
    assert entries[0].name == "Mystical Tutor"
    assert entries[0].set == "DMR"
    assert entries[0].collector_number == "289"
    assert entries[0].foil is False

    assert entries[1].name == "The Swarmlord"
    assert entries[1].set == "40K"
    assert entries[1].collector_number == "4"
    assert entries[1].foil is True


def test_hyphenated_collector_number(tmp_path):
    p = write(tmp_path, "bulk.txt", "1x Delighted Halfling (KTK-234)\n")
    # Note: no trailing number here means this is NOT a valid pin (needs
    # "(SET) NUM" - two tokens), so regex will treat whole thing as name
    # unless both groups match. This specific line only has one token in
    # parens, so it should be a grammar error, silently skipped here.
    entries = parse_entries(p)
    assert entries == []


def test_hyphenated_collector_number_as_valid_pin(tmp_path):
    p = write(tmp_path, "bulk.txt", "1x Delighted Halfling (PLST) KTK-234\n")
    entries = parse_entries(p)
    assert entries[0].name == "Delighted Halfling"
    assert entries[0].set == "PLST"
    assert entries[0].collector_number == "KTK-234"


def test_double_faced_card_name_kept_whole(tmp_path):
    p = write(tmp_path, "bulk.txt", "1x Fire // Ice\n")
    entries = parse_entries(p)
    assert entries[0].name == "Fire // Ice"


def test_malformed_line_is_silently_skipped_by_loose_parser(tmp_path):
    p = write(tmp_path, "bulk.txt", "garbage line with no quantity\n1x Sol Ring\n")
    entries = parse_entries(p)
    assert [e.name for e in entries] == ["Sol Ring"]


def test_invalid_pin_syntax_is_silently_skipped_by_loose_parser(tmp_path):
    p = write(tmp_path, "bulk.txt", "3x Sol Ring nonsense ()\n")
    entries = parse_entries(p)
    assert entries == []


def test_zero_quantity_is_silently_skipped_by_loose_parser(tmp_path):
    p = write(tmp_path, "bulk.txt", "0x Sol Ring\n")
    entries = parse_entries(p)
    assert entries == []


def test_strict_parse_card_list_reports_malformed_line(tmp_path):
    p = write(tmp_path, "bulk.txt", "garbage line with no quantity\n1x Sol Ring\n")
    card_list, errors = parse_card_list(p, kind="bulk", root=tmp_path)
    assert len(errors) == 1
    assert errors[0].line == 1
    assert "Invalid card entry" in errors[0].message
    assert [e.name for e in card_list.entries] == ["Sol Ring"]


def test_strict_parse_card_list_reports_zero_quantity(tmp_path):
    p = write(tmp_path, "bulk.txt", "0x Sol Ring\n")
    _, errors = parse_card_list(p, kind="bulk", root=tmp_path)
    assert len(errors) == 1
    assert "Quantity must be positive" in errors[0].message


def test_strict_parse_card_list_reports_invalid_pin_syntax(tmp_path):
    p = write(tmp_path, "bulk.txt", "3x Sol Ring nonsense ()\n")
    _, errors = parse_card_list(p, kind="bulk", root=tmp_path)
    assert len(errors) == 1
    assert "Invalid printing pin syntax" in errors[0].message


def test_entry_line_numbers_are_1_indexed(tmp_path):
    p = write(tmp_path, "bulk.txt", "# a comment\n1x Sol Ring\ngarbage\n")
    _, errors = parse_card_list(p, kind="bulk", root=tmp_path)
    assert errors[0].line == 3


def test_metadata_parsing(tmp_path):
    p = write(
        tmp_path,
        "mydeck.txt",
        "# commander: Atraxa\n# proxy: true\n# collection: true\n1x Sol Ring\n",
    )
    card_list, errors = parse_card_list(p, kind="deck", root=tmp_path)
    assert errors == []
    assert card_list.commander == "Atraxa"
    assert card_list.proxy is True
    assert card_list.collection is True


def test_discover_card_lists_requires_bulk(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_card_lists(tmp_path)


def test_discover_card_lists_collects_errors_across_files(tmp_path):
    write(tmp_path, "bulk.txt", "garbage\n1x Sol Ring\n")
    decks_dir = tmp_path / "decks"
    decks_dir.mkdir()
    write(decks_dir, "1234_test.txt", "also garbage\n1x Lightning Bolt\n")

    bulk, lists, errors = discover_card_lists(tmp_path)
    assert bulk.name == "Bulk"
    assert len(lists) == 1
    assert len(errors) == 2
    paths = {e.path for e in errors}
    assert "bulk.txt" in paths
    assert any("1234_test.txt" in p for p in paths)


def test_parse_entry_line_helper():
    e = parse_entry_line("2x Sol Ring")
    assert e is not None
    assert e.name == "Sol Ring"
    assert e.qty == 2
    assert parse_entry_line("not a valid line") is None
