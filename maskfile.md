# Tasks

MTG Decks management tasks for mask CLI.

## check

> Verify all decks have exactly 100 cards

Checks that all deck files in the `decks/` directory have the correct number of cards for Commander format (100 cards).

**OPTIONS**

- deck
  - flags: -d --deck
  - type: string
  - desc: Check a specific deck file instead of all decks

```bash
if [[ -n "$deck" ]]; then
    python3 scripts/check-sizes.py "$deck"
else
    python3 scripts/check-sizes.py decks/*.txt
fi
```

## diff (deck_a) (deck_b)

> Compare two decklists and show the differences

Shows cards removed from deck A and cards added in deck B, useful for tracking changes or comparing precon to modified versions.

**Example:** `mask diff precons/21731507_golden_power.txt decks/21731507_golden_power.txt`

```bash
if [[ -z "$deck_a" ]] || [[ -z "$deck_b" ]]; then
    echo "Error: Both deck_a and deck_b arguments are required"
    echo "Usage: mask diff <deck_a> <deck_b>"
    exit 1
fi

python3 scripts/diff.py "$deck_a" "$deck_b"
```

## diff-archidekt (deck_id) (local_file)

> Compare Archidekt remote deck with local decklist

Fetches the current state of a deck from Archidekt and compares it to your local decklist file, showing what cards were added or removed.

**Example:** `mask diff-archidekt 21248219 decks/21248219_blitzkikker.txt`

```bash
if [[ -z "$deck_id" ]] || [[ -z "$local_file" ]]; then
    echo "Error: Both deck_id and local_file arguments are required"
    echo "Usage: mask diff-archidekt <deck_id> <local_file>"
    exit 1
fi

python3 scripts/diff-archidekt.py "$deck_id" "$local_file"
```

## oldest (deck)

> Find the oldest printing of each card in a deck

Queries the Scryfall API to find the first printing of each card, useful for selecting the most "vintage" version of your cards.

**Example:** `mask oldest decks/21248219_blitzkikker.txt`

```bash
if [[ -z "$deck" ]]; then
    echo "Error: deck argument is required"
    echo "Usage: mask oldest <deck_file>"
    exit 1
fi

python3 scripts/oldest-printing.py "$deck"
```

## fetch-local (deck)

> Fetch card data from Scryfall for a local decklist

Reads a local text file and queries the Scryfall API to get card details including name, mana cost, type line, and oracle text.

**Example:** `mask fetch-local decks/21248219_blitzkikker.txt`

```bash
if [[ -z "$deck" ]]; then
    echo "Error: deck argument is required"
    echo "Usage: mask fetch-local <deck_file>"
    exit 1
fi

python3 scripts/fetch-local-scryfall.py "$deck"
```

## fetch-remote (deck_id)

> Fetch deck data from Archidekt with categories

Queries the Archidekt API to get a complete deck including custom category labels, card details, and pricing information.

**Example:** `mask fetch-remote 21248219`

```bash
if [[ -z "$deck_id" ]]; then
    echo "Error: deck_id argument is required"
    echo "Usage: mask fetch-remote <deck_id>"
    exit 1
fi

python3 scripts/fetch-remote-archidekt.py "$deck_id"
```

## analyze (deck_id)

> Analyze price distribution of a deck

Fetches deck data from Archidekt and performs statistical analysis including concentration metrics, Gini coefficient, and insights about cost distribution.

**Example:** `mask analyze 21248219`

```bash
if [[ -z "$deck_id" ]]; then
    echo "Error: deck_id argument is required"
    echo "Usage: mask analyze <deck_id>"
    exit 1
fi

python3 scripts/analyze-deck-price.py "$deck_id"
```

## update-readme

> Update README.md with current deck prices

Scans the `decks/` directory, fetches current prices from Archidekt, and updates the README.md table. Primarily used by GitHub Actions.

```bash
python3 scripts/update-readme.py
```
