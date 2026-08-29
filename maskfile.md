# Tasks

MTG Decks management tasks for mask CLI.

## sort-bulk

> Sort bulk.txt alphabetically by card name, in place

Only bulk.txt is sorted - it's a flat "everything I own" list with no
meaningful order. Decks/collections/precons are left untouched since their
line order is often curated (e.g. a precon mirrors the printed product's
decklist) and diffing (`mask diff`) doesn't depend on line order anyway.

```bash
python3 scripts/sort-bulk.py
```

## build-data

> Resolve card names and generate static JSON data for the web app

Parses bulk.txt plus every list under decks/ and collections/, resolves
every unique card name's identity against Scryfall (using
cache/card-data.json to avoid re-resolving known cards), and writes
static JSON into web/public/data/ for the frontend to fetch. Pricing
never comes from Scryfall: if cache/bulk-prices.json exists (see `mask
fetch-bulk-prices`), its real Cardmarket prices are applied to any card
it covers; everything else simply has no price.

**OPTIONS**

- strict
  - flags: --strict
  - type: bool
  - desc: Exit non-zero if any card failed to resolve

```bash
if [[ "$strict" == "true" ]]; then
    python3 scripts/build/build.py --strict
else
    python3 scripts/build/build.py
fi
```

## dev

> Run the web app locally with hot reload

Builds the latest card data, then starts the Vite dev server.

```bash
python3 scripts/build/build.py
cd web && npm install && npm run dev
```

## build-site

> Build the static production site

Regenerates card data, then builds the deployable static site into
web/dist/.

```bash
python3 scripts/build/build.py
cd web && npm install && npm run build
```

## fetch-bulk-prices (archidekt_deck)

> Fetch real Cardmarket prices for owned cards from an Archidekt bulk-mirror deck

Fetches every card + Cardmarket price from an Archidekt deck that mirrors
your physical bulk collection, and writes cache/bulk-prices.json. Run
`mask build-data` afterwards to apply the new prices.

**Example:** `mask fetch-bulk-prices 25868036`

```bash
if [[ -z "$archidekt_deck" ]]; then
    echo "Usage: mask fetch-bulk-prices <archidekt_deck_id>"
    exit 1
fi

python3 scripts/fetch-bulk-prices.py "$archidekt_deck"
```

## fetch-list-prices (label) (archidekt_deck)

> Fetch reference Cardmarket prices for a deck you don't (fully) own

Fetches every card + Cardmarket price from any public Archidekt deck (not
necessarily your own) and merges it into cache/list-prices.json under the
given label. Used as a fallback price for cards missing from
cache/bulk-prices.json - e.g. a wishlist like decks/orcs.txt that mirrors
a public Archidekt decklist you don't own yet. An owned card's real bulk
price always wins over this. Run `mask build-data` afterwards to apply.

This is standalone and re-runnable per reference deck - it is NOT part of
`mask release`, which is only for your owned-bulk pricing snapshot.

**Example:** `mask fetch-list-prices orcs 25657626`

```bash
if [[ -z "$label" ]] || [[ -z "$archidekt_deck" ]]; then
    echo "Usage: mask fetch-list-prices <label> <archidekt_deck_id>"
    echo "Example: mask fetch-list-prices orcs 25657626"
    exit 1
fi

python3 scripts/fetch-list-prices.py "$label" "$archidekt_deck"
```

## release (version) (archidekt_deck)

> Sort bulk.txt, fetch fresh Cardmarket prices, rebuild data, and prep a tagged release

Sorts bulk.txt alphabetically, fetches current Cardmarket prices for your
bulk collection from an Archidekt bulk-mirror deck (defaults to 25868036 -
https://archidekt.com/decks/25868036/bulk), rebuilds the static JSON
data, then prints the remaining manual steps: log the fetch in
CHANGELOG.md, commit, and tag.

**Example:** `mask release v1.2.0`

```bash
if [[ -z "$version" ]]; then
    echo "Usage: mask release <version> [archidekt_deck]"
    echo "Example: mask release v1.2.0"
    exit 1
fi

deck_id="${archidekt_deck:-25868036}"

python3 scripts/sort-bulk.py
python3 scripts/fetch-bulk-prices.py "$deck_id"
python3 scripts/build/build.py

echo
echo "Prices refreshed for $version. Remaining steps:"
echo "  1. Add a row to CHANGELOG.md (fetch date + total value are in"
echo "     cache/bulk-prices.json / printed above)"
echo "  2. git add -A && git commit -m \"Release $version\""
echo "  3. GIT_EDITOR=true git tag -a $version -m \"$version\""
echo "  4. git push && git push --tags"
```

## check

> Verify all decks have exactly 100 cards

Checks that all deck files in the `decks/` directory have the correct number
of cards for Commander format (100 cards). Non-Commander lists (e.g. a
wishlist) are expected to fail this check - it's a sanity check for decks,
not a requirement for every list in decks/.

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

Shows cards removed from deck A and cards added in deck B, useful for
tracking changes or comparing precon to modified versions.

**Example:** `mask diff precons/creative_energy.txt decks/some_deck.txt`

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

Fetches the current state of a deck from Archidekt and compares it to your
local decklist file, showing what cards were added or removed.

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

Queries the Scryfall API to find the first printing of each card, useful for
selecting the most "vintage" version of your cards.

**Example:** `mask oldest decks/21248219_blitzkikker.txt`

```bash
if [[ -z "$deck" ]]; then
    echo "Error: deck argument is required"
    echo "Usage: mask oldest <deck_file>"
    exit 1
fi

python3 scripts/oldest-printing.py "$deck"
```

## fetch-remote (deck_id)

> Fetch deck data from Archidekt with categories

Queries the Archidekt API to get a complete deck including custom category
labels, card details, and pricing information.

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

Fetches deck data from Archidekt and performs statistical analysis including
concentration metrics, Gini coefficient, and insights about cost
distribution.

**Example:** `mask analyze 21248219`

```bash
if [[ -z "$deck_id" ]]; then
    echo "Error: deck_id argument is required"
    echo "Usage: mask analyze <deck_id>"
    exit 1
fi

python3 scripts/analyze-deck-price.py "$deck_id"
```
