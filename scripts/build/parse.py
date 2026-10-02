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

Strictness: a line that looks like an attempted card entry (starts with a
digit, or contains "(" suggesting a printing pin) but doesn't parse
cleanly is a hard build-stopping error when parsed via parse_card_list()
(see BuildError below) - see REFACTOR.md §6.1/§6.2. The looser
parse_entries()/parse_entry_line() helpers (used by one-off scripts
like diff.py, check-sizes.py) silently skip malformed lines instead,
unaffected by this strictness.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

LINE_RE = re.compile(r"^(?P<qty>\d+)\s*x?\s+(?P<body>.+)$", re.IGNORECASE)
FOIL_SUFFIX_RE = re.compile(
    r"^(?P<rest>.+?)\s*\*(?P<foil>[FE])\*$",
    re.IGNORECASE,
)
PIN_SUFFIX_RE = re.compile(
    r"^(?P<name>.+?)\s*\((?P<set>[A-Za-z0-9]{2,6})\)\s+(?P<num>[A-Za-z0-9-]+)$",
    re.IGNORECASE,
)
METADATA_RE = re.compile(r"^#\s*([\w-]+)\s*:\s*(.+?)\s*$")
FILENAME_ID_RE = re.compile(r"^(\d+)_(.+)$")


class EntryGrammarError(ValueError):
    """A line looked like a card entry but didn't parse cleanly."""


@dataclass(frozen=True)
class BuildError:
    """A hard, build-stopping data-integrity problem, attributed to the
    exact source location that caused it (see REFACTOR.md §6.1/§6.3)."""

    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}\n  {self.message}"


@dataclass(frozen=True)
class Entry:
    name: str
    qty: int
    line: int
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
    return unicodedata.normalize("NFC", name).strip().lower()


def _parse_entry_text(line: str) -> tuple[int, str, str | None, str | None, bool]:
    """Parse one entry line's text into (qty, name, set, collector_number,
    foil), raising EntryGrammarError with a human-readable message for
    anything that doesn't parse cleanly - see REFACTOR.md §6.1.
    """
    m = LINE_RE.match(line)
    if not m:
        raise EntryGrammarError(f'Invalid card entry: "{line}"')

    qty = int(m.group("qty"))
    if qty == 0:
        raise EntryGrammarError(f'Quantity must be positive: "{line}"')

    body = m.group("body").strip()

    foil = False
    foil_match = FOIL_SUFFIX_RE.match(body)
    if foil_match:
        foil = True
        body = foil_match.group("rest").strip()

    set_code: str | None = None
    collector_number: str | None = None
    if "(" in body:
        pin_match = PIN_SUFFIX_RE.match(body)
        if not pin_match:
            raise EntryGrammarError(f'Invalid printing pin syntax: "{line}"')
        body = pin_match.group("name").strip()
        set_code = pin_match.group("set")
        collector_number = pin_match.group("num")

    return qty, body, set_code, collector_number, foil


def parse_entry_line(line: str) -> Entry | None:
    """Parse a single entry line, returning None instead of raising for
    anything malformed - used by loose one-off scripts that don't need
    build-stopping strictness (e.g. sort-bulk.py)."""
    try:
        qty, name, set_code, collector_number, foil = _parse_entry_text(line)
    except EntryGrammarError:
        return None
    return Entry(
        name=name,
        qty=qty,
        line=0,
        set=set_code,
        collector_number=collector_number,
        foil=foil,
    )


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


def _parse_file(
    path: Path, strict: bool, error_path: str | None = None
) -> tuple[dict[str, str], list[Entry], list[BuildError]]:
    """Parse a card-list file's metadata comments and entries in one pass.

    This is the one place the file grammar is actually read; both
    parse_card_list (strict=True, which also cares about metadata) and the
    lean parse_entries (strict=False) build on it. In strict mode, a
    malformed entry line produces a BuildError instead of being silently
    skipped. `error_path` (defaults to str(path)) is what BuildErrors are
    attributed to, so callers can report a project-relative path instead
    of an absolute filesystem one.
    """
    metadata: dict[str, str] = {}
    entries: list[Entry] = []
    errors: list[BuildError] = []
    rel = error_path if error_path is not None else str(path)

    with path.open(encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            meta_match = METADATA_RE.match(line)
            if meta_match:
                metadata[meta_match.group(1).lower()] = meta_match.group(2)
                continue

            if line.startswith("#"):
                continue  # plain comment

            try:
                qty, name, set_code, collector_number, foil = _parse_entry_text(line)
            except EntryGrammarError as e:
                if strict:
                    errors.append(BuildError(path=rel, line=line_no, message=str(e)))
                continue

            entries.append(
                Entry(
                    name=name,
                    qty=qty,
                    line=line_no,
                    set=set_code,
                    collector_number=collector_number,
                    foil=foil,
                )
            )

    return metadata, entries, errors


def parse_entries(path: Path) -> list[Entry]:
    """Parse just the (qty, name) entries out of any list-formatted text
    file - bulk, deck, collection, precon, or an arbitrary decklist passed
    to one of the scripts/ CLI tools. Metadata comments are recognized
    (and skipped) but not returned; callers that need them use
    parse_card_list instead. Malformed lines are silently skipped (not
    build-stopping) - see parse_card_list for the strict variant.
    """
    _, entries, _ = _parse_file(path, strict=False)
    return entries


def parse_card_list(
    path: Path, kind: str, root: Path
) -> tuple[CardList, list[BuildError]]:
    """Parse a single card-list text file into a CardList, plus any
    build-stopping BuildErrors found in it (empty when the file is clean).
    """
    stem = path.stem
    default_name, default_archidekt_id = _default_display_name(stem)
    relative = path.relative_to(root)
    default_status = "archived" if "archived" in relative.parts[:-1] else "active"

    list_id = default_archidekt_id or stem
    metadata, entries, errors = _parse_file(path, strict=True, error_path=str(relative))

    card_list = CardList(
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
    return card_list, errors


def discover_card_lists(
    root: Path,
) -> tuple[CardList, list[CardList], list[BuildError]]:
    """Find bulk.txt plus every deck/collection list in the repo.

    Returns (bulk, other_lists, errors). precons/ is intentionally not
    scanned - it exists for manual precon-vs-deck diffing, not for the
    viewer.
    """
    bulk_path = root / "bulk.txt"
    if not bulk_path.exists():
        raise FileNotFoundError(f"bulk.txt not found at {bulk_path}")
    bulk, errors = parse_card_list(bulk_path, kind="bulk", root=root)
    bulk.id = "bulk"
    bulk.name = "Bulk"

    lists: list[CardList] = []
    for folder, kind in (("decks", "deck"), ("collections", "collection")):
        dir_path = root / folder
        if not dir_path.exists():
            continue
        for file_path in sorted(dir_path.rglob("*.txt")):
            card_list, file_errors = parse_card_list(file_path, kind=kind, root=root)
            lists.append(card_list)
            errors.extend(file_errors)

    return bulk, lists, errors
