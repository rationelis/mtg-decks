import os
import sys
from collections import Counter

decks_dir = "decks"
precons_dir = "precons"


def load_deck(path):
    cards = Counter()
    with open(path, "r") as f:
        for line in f:
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                qty, name = int(parts[0]), parts[1]
                cards[name] += qty
    return cards


if len(sys.argv) > 1:
    deck_files = [sys.argv[1]]
else:
    deck_files = sorted(os.listdir(decks_dir))

for deck_file in deck_files:
    precon_path = os.path.join(precons_dir, deck_file)
    upgraded_path = os.path.join(decks_dir, deck_file)

    if not os.path.exists(precon_path):
        print(f"⚠️ No precon found for {deck_file}")
        continue

    precon = load_deck(precon_path)
    upgraded = load_deck(upgraded_path)

    removed = precon - upgraded
    added = upgraded - precon
    total_swapped = sum(removed.values())

    print(f"=== {deck_file} ===")
    print(f"Swapped cards: {total_swapped}")

    if removed:
        print("  Out:")
        for name, qty in removed.items():
            print(f"    -{qty} {name}")

    if added:
        print("  In:")
        for name, qty in added.items():
            print(f"    +{qty} {name}")
