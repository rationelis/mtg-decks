#!/usr/bin/env python3
"""Sort bulk.txt alphabetically by card name, in place.

Only bulk.txt is sorted - it's a flat "everything I own" list with no
meaningful order, so sorting it keeps it easy to scan and diff in git.
Decks/collections/precons are intentionally left untouched: their line
order often mirrors a curated layout (a precon in particular mirrors the
original product's printed decklist), which sorting would destroy for no
benefit - ownership diffing is already order-independent (diff.py compares
via a Counter, not line position).

Usage:
    python3 scripts/sort-bulk.py [path]   # defaults to bulk.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))

from parse import ENTRY_RE, normalize_name  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def sort_file(path: Path) -> bool:
    """Sort a card-list file's entries alphabetically in place, keeping any
    comment/metadata lines pinned above the entries. Returns whether the
    file's contents changed.
    """
    old_text = path.read_text(encoding="utf-8")

    header: list[str] = []
    entries: list[str] = []
    for line in old_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or not ENTRY_RE.match(stripped):
            header.append(line)
        else:
            entries.append(line)

    entries.sort(key=lambda line: normalize_name(ENTRY_RE.match(line.strip()).group("name")))

    new_text = "\n".join(header + entries) + "\n"
    if new_text == old_text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bulk.txt"
    if not target.exists():
        print(f"Not found: {target}", file=sys.stderr)
        return 1
    changed = sort_file(target)
    print(f"{'Sorted' if changed else 'Already sorted'}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
