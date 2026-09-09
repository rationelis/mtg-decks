# mtg-decks

My MTG decklists in version control, plus a static, read-only web app for
browsing bulk and comparing it against decks/collections.
[Archidekt folder](https://archidekt.com/folders/1542764)

## Repository layout

```text
bulk.txt        everything physically owned, as one flat list
decks/          decks (a subfolder decks/archived/ holds retired ones)
collections/    other desired-card lists (wishlists, cubes, etc.) - optional
precons/        untouched precon reference lists, for manual diffing only
cache/          Scryfall identity cache + Cardmarket bulk prices, committed
scripts/build/  the build pipeline (parse → resolve → emit JSON)
web/            the static viewer (Vite + TypeScript)
```

All three list types (`bulk.txt`, `decks/*.txt`, `collections/*.txt`) share
one plain-text format:

```text
1x Lightning Bolt
3x Counterspell
1 Sol Ring
1x Mystical Tutor (DMR) 289
1 The Swarmlord (40K) 4 *F*
```

Quantity may be written as `1x` or `1`. Double-faced/split cards are written
as `Front // Back`. A trailing `(SET) NUM` pins a specific printing (its
image/set/rarity) without affecting ownership diffing, which is always by
bare card name; the collector number may contain a hyphen (e.g. a The List
reprint like `KTK-234`), and an optional trailing `*F*` marks that copy as
foil. Lines starting with `#` are comments; a `# key: value`
comment sets optional metadata:

```text
# commander: Henzie "Toolbox" Torre
# proxy: true
```

Recognized keys: `name`, `commander`, `archidekt`, `status`
(`active`/`archived`), `proxy` (`true`/`false`), `collection`
(`true`/`false` - marks a list under `decks/` as really a wishlist, e.g.
`decks/25657626_oops_all_orcs.txt`, without moving it into
`collections/`). None are required - a plain list with zero metadata
works fine.

**Ownership is never stored.** A deck/collection is a *desired* list; the
app computes Owned/Missing live in the browser by comparing it against
`bulk.txt`. This means a deck can list cards you don't own yet (see
`decks/25657626_oops_all_orcs.txt`, a wishlist with an empty overlap with
`bulk.txt`) without that being a data-modeling problem.

## The web app

A static, read-only site for exploring `bulk.txt` and any deck/collection,
built at [`web/`](web). Card identity (mana cost, colors, type, oracle
text, image, etc.) is resolved from Scryfall at build time and shipped as
static JSON - the deployed site never calls any API. Pricing is separate
(see below) and never comes from Scryfall.

```bash
mask build-data   # resolve card names -> web/public/data/*.json
mask dev          # build data, then run the site locally with hot reload
mask build-site   # build data, then build the deployable static site
```

Deploys to GitHub Pages automatically via
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) on every push
to `main` (and weekly, to keep prices fresh).

## Pricing

Prices never come from Scryfall - only from real Cardmarket listings, via
Archidekt. Mirror your bulk into an Archidekt deck (one row per card you
physically have - [example](https://archidekt.com/decks/25868036/bulk));
Archidekt already shows each row's Cardmarket price.
`scripts/fetch-bulk-prices.py` fetches that deck into
`cache/bulk-prices.json`, and the build applies those prices to every
card it covers. A card not in your bulk-mirror deck (or with no printing
picked there) simply has no price - the fix is to mirror it into
Archidekt and re-run the fetch, not a guessed-at Scryfall estimate. The
web app shows a small note wherever prices are displayed, naming the
Cardmarket fetch date and reminding you that prices change over time.

### Pricing cards you don't own yet

A proxy deck or wishlist (e.g. `decks/25657626_oops_all_orcs.txt`) has
little or no overlap with your bulk-mirror deck, so it would normally
show no prices at all. Every deck/collection file already carries its
own Archidekt deck id (the `NNNN_` filename prefix, or a `#
archidekt: NNNN` metadata line), so one command fetches reference
Cardmarket prices for all of them in one pass - so "price to complete"
is real instead of always "-":

```bash
mask fetch-list-prices
mask build-data
```

A list with no resolvable Archidekt id is skipped with a warning (rename
it to `NNNN_name.txt` or add a `# archidekt: NNNN` line to fix that). To
fetch one ad-hoc reference deck under a custom label instead - e.g.
someone else's public decklist that isn't one of your own files -  pass
a label and deck id explicitly:

```bash
mask fetch-list-prices orcs 25657626   # https://archidekt.com/decks/25657626/oops_all_orcs
mask build-data
```

Every source's prices are merged into `cache/list-prices.json`; an owned
card's real bulk price always takes priority over a reference price if a
card happens to be in both.

## Keeping prices fresh

Update `bulk.txt` (and/or decks/collections) and mirror the same changes
into your Archidekt bulk deck, then refresh prices and rebuild:

```bash
mask fetch-bulk-prices <archidekt_deck_id>   # e.g. 25868036
mask build-data
```

Commit the updated `bulk.txt` and `cache/*.json` and push - the deploy
workflow rebuilds the site (and also reruns weekly on its own to catch
any drift).

## Scripts

This project uses Python with `requests` for the Archidekt-facing scripts,
and the standard library only for the build pipeline
(`scripts/build/*.py`). It also uses [mask](https://github.com/jacobdeichert/mask)
as the task runner - run `mask --help` for the full list of tasks (build,
dev, check deck sizes, diff decklists, Archidekt price analysis, etc).
