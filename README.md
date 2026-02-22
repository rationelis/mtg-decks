# mtg-decks

My MTG decklists in version control.

- `decks/` - Current decklists
- `precons/` - Original precons (for reference)

## Scripts

Helper scripts in `scripts/`. All read decklist files and output to stdout.

```bash
# Check deck sizes (Commander = 100 cards)
python3 scripts/check-sizes.py decks/*.txt

# Find oldest printing of each card
python3 scripts/oldest-printing.py decks/quick_draw.txt

# Compare two decklists
python3 scripts/diff.py precons/creative_energy.txt decks/creative_energy.txt

# Fetch card descriptions from Scryfall
python3 scripts/describe.py decks/world_shaper.txt
```

Requires `requests`: `pip install requests`
