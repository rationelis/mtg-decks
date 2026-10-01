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

## build [archidekt_deck]

> Resolve card names, fetch prices, allocate bulk, and generate static JSON data for the web app

The one command that does everything (see REFACTOR.md §5): parses
bulk.txt plus every list under decks/ and collections/, resolves every
unique card name's identity against Scryfall (using cache/card-data.json
to avoid re-resolving known cards), fetches real Cardmarket prices for
your bulk-mirror Archidekt deck plus reference prices for every
deck/collection with a known Archidekt id, allocates bulk supply across
your active decks, and writes static JSON into web/public/data/ for the
frontend to fetch.

Any data-integrity problem (a malformed line, an unknown card name, a
pinned printing that doesn't exist or doesn't match, or conflicting pins
for the same card across files) stops the build and prints every such
problem, with nothing written. Pricing problems (a network hiccup
reaching Archidekt) are warnings only, never a build failure.

Pass an Archidekt deck id once to link (or relink) your bulk-mirror
deck - it's remembered in cache/bulk-prices.json afterwards, so plain
`mask build` is enough from then on.

**Example:** `mask build` (reuse the last-linked bulk-mirror deck)
**Example:** `mask build 25868036` (link/relink the bulk-mirror deck)

```bash
if [[ -n "$archidekt_deck" ]]; then
    python3 scripts/build/build.py --bulk-deck "$archidekt_deck"
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

## fetch-list-prices (label) (archidekt_deck)

> Fetch a reference Cardmarket price for one ad-hoc deck you don't own

Every deck/collection under decks/ and collections/ that already has a
known Archidekt id is fetched automatically by `mask build`. This task is
only for a one-off extra source that isn't one of your own files - e.g.
someone else's public decklist that mirrors a wishlist. Merged into
cache/list-prices.json; run `mask build` afterwards to apply.

**Example:** `mask fetch-list-prices orcs 25657626`

```bash
if [[ -z "$label" ]] || [[ -z "$archidekt_deck" ]]; then
    echo "Usage: mask fetch-list-prices <label> <archidekt_deck_id>"
    exit 1
fi

python3 scripts/fetch-list-prices.py "$label" "$archidekt_deck"
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
