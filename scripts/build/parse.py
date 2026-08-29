"""Parsing of MTG plain-text card lists (bulk, decks, collections).

Grammar (backwards compatible with every list already in this repo):

    <qty>[x] <name>              e.g. "1x Lightning Bolt" or "4 Mountain"
    <qty>[x] <name> (SET) NUM    pins a specific printing, e.g.
                                 "1x Mystical Tutor (DMR) 289"
    <qty>[x] <name> (SET) NUM *F* same as above, foil copy
    # a plain comment            ignored
    # key: value                 optional structured metadata (see below)
    Front // Back                double-faced / split card name, kept whole

All lists (bulk, decks, collections) share this exact grammar - there is
only one parser. What a file *means* comes from where it lives (bulk.txt,
decks/, collections/) plus optional metadata comments, not from a
different file format.

The "(SET) NUM" suffix is optional and only affects which printing's
image/rarity/set the build displays for that card - it never changes the
card's identity for ownership diffing, which is always by bare name (see
Entry.name vs Entry.set/collector_number below). The collector number may
contain a hyphen (e.g. a The List/Secret Lair number such as "KTK-234").
A trailing "*F*" marks that copy as foil.

Recognized metadata keys (all optional; a plain list with zero metadata
still works, using sensible defaults derived from the file's path):

    name       display name override (default: title-cased filename stem)
    commander  commander card name, shown in the UI (default: none)
    archidekt  Archidekt deck id override (default: numeric filename prefix)
    status     "active" | "archived" (default: "archived" if the file
               lives under an "archived/" directory, else "active")
    proxy      "true" | "false" - informational flag (default: "false")
    collection "true" | "false" - informational flag (default: "false"),
               marks a list under decks/ as really a wishlist/collection
               (e.g. not a 100-card Commander deck) without having to
               move the file into collections/
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ENTRY_RE = re.compile(
    r"^(?P<qty>\d+)\s*x?\s+(?P<name>.+?)"
    r"(?:\s*\((?P<set>[A-Za-z0-9]{2,6})\)\s+(?P<num>[A-Za-z0-9-]+))?"
    r"(?:\s*\*(?P<foil>F)\*)?$",
    re.IGNORECASE,
)
METADATA_RE = re.compile(r"^#\s*([\w-]+)\s*:\s*(.+?)\s*$")
FILENAME_ID_RE = re.compile(r"^(\d+)_(.+)$")


@dataclass(frozen=True)
class Entry:
    name: str
    qty: int
    set: str | None = None
    collector_number: str | None = None
    foil: bool = False


@dataclass
class CardList:
    id: str
    kind: str  # "bulk" | "deck" | "collection"
    status: str  # "active" | "archived"
    name: str
    source_path: str
    entries: list[Entry] = field(default_factory=list)
    commander: str | None = None
    archidekt_id: str | None = None
    proxy: bool = False
    collection: bool = False


def normalize_name(name: str) -> str:
    """Normalize a card name into a stable cache/lookup key."""
    return unicodedata.normalize("NFC", name).strip().casefold()


def _default_display_name(stem: str) -> tuple[str, str | None]:
    """Derive (display_name, archidekt_id) from a filename stem."""
    m = FILENAME_ID_RE.match(stem)
    if m:
        archidekt_id, rest = m.group(1), m.group(2)
    else:
        archidekt_id, rest = None, stem
    display = rest.replace("_", " ").replace("-", " ").strip()
    display = " ".join(word.capitalize() for word in display.split(" "))
    return display, archidekt_id


def _parse_file(path: Path) -> tuple[dict[str, str], list[Entry]]:
    """Parse a card-list file's metadata comments and entries in one pass.

    This is the one place the file grammar is actually read; both
    parse_card_list (which also cares about metadata) and the lean
    parse_entries (which doesn't) build on it.
    """
    metadata: dict[str, str] = {}
    entries: list[Entry] = []

    with path.open(encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            meta_match = METADATA_RE.match(line)
            if meta_match:
                metadata[meta_match.group(1).lower()] = meta_match.group(2)
                continue

            if line.startswith("#"):
                continue  # plain comment

            entry_match = ENTRY_RE.match(line)
            if not entry_match:
                continue  # ignore malformed lines rather than fail the build

            entries.append(
                Entry(
                    name=entry_match.group("name").strip(),
                    qty=int(entry_match.group("qty")),
                    set=entry_match.group("set"),
                    collector_number=entry_match.group("num"),
                    foil=entry_match.group("foil") is not None,
                )
            )

    return metadata, entries


def parse_entries(path: Path) -> list[Entry]:
    """Parse just the (qty, name) entries out of any list-formatted text
    file - bulk, deck, collection, precon, or an arbitrary decklist passed
    to one of the scripts/ CLI tools. Metadata comments are recognized
    (and skipped) but not returned; callers that need them use
    parse_card_list instead.

    This is the single shared implementation for every script that used to
    hand-roll its own quantity-parsing regex.
    """
    _, entries = _parse_file(path)
    return entries


def parse_card_list(path: Path, kind: str, root: Path) -> CardList:
    """Parse a single card-list text file into a CardList."""
    stem = path.stem
    default_name, default_archidekt_id = _default_display_name(stem)
    relative = path.relative_to(root)
    default_status = "archived" if "archived" in relative.parts[:-1] else "active"

    list_id = default_archidekt_id or stem
    metadata, entries = _parse_file(path)

    return CardList(
        id=metadata.get("archidekt", list_id),
        kind=kind,
        status=metadata.get("status", default_status),
        name=metadata.get("name", default_name),
        source_path=str(relative),
        entries=entries,
        commander=metadata.get("commander"),
        archidekt_id=metadata.get("archidekt", default_archidekt_id),
        proxy=metadata.get("proxy", "false").strip().lower() == "true",
        collection=metadata.get("collection", "false").strip().lower() == "true",
    )


def discover_card_lists(root: Path) -> tuple[CardList, list[CardList]]:
    """Find bulk.txt plus every deck/collection list in the repo.

    Returns (bulk, other_lists). precons/ is intentionally not scanned -
    it exists for manual precon-vs-deck diffing, not for the viewer.
    """
    bulk_path = root / "bulk.txt"
    if not bulk_path.exists():
        raise FileNotFoundError(f"bulk.txt not found at {bulk_path}")
    bulk = parse_card_list(bulk_path, kind="bulk", root=root)
    bulk.id = "bulk"
    bulk.name = "Bulk"

    lists: list[CardList] = []
    for folder, kind in (("decks", "deck"), ("collections", "collection")):
        dir_path = root / folder
        if not dir_path.exists():
            continue
        for file_path in sorted(dir_path.rglob("*.txt")):
            lists.append(parse_card_list(file_path, kind=kind, root=root))

    return bulk, lists
