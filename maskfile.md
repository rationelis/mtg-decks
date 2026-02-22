# MTG Decks

## check-sizes

> Verify all decks have exactly 100 cards (Commander format)

```bash
python3 scripts/check-sizes.py decks/*.txt
```

## oldest (deck)

> Find the oldest printing of each card in a deck

```bash
python3 scripts/oldest-printing.py "$deck"
```

## diff (a) (b)

> Compare two decklists and show the differences

```bash
python3 scripts/diff.py "$a" "$b"
```

## describe (deck)

> Fetch card descriptions from Scryfall

```bash
python3 scripts/describe.py "$deck"
```
