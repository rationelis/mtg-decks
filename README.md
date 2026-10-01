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
build computes Owned/Missing by allocating `bulk.txt` across every "real"
active deck at once (so two decks can't both claim the same scarce
physical copy - see "Card allocation" below), then ships the result as
static JSON. This means a deck can list cards you don't own yet (see
`decks/25657626_oops_all_orcs.txt`, a wishlist with an empty overlap with
`bulk.txt`) without that being a data-modeling problem.

## The web app

A static, read-only site for exploring `bulk.txt` and any deck/collection,
built at [`web/`](web). Card identity (mana cost, colors, type, oracle
text, image, etc.) is resolved from Scryfall at build time and shipped as
static JSON - the deployed site never calls any API. Pricing is separate
(see below) and never comes from Scryfall.

```bash
mask build        # resolve card names, fetch prices, allocate bulk -> web/public/data/*.json
mask dev          # build data, then run the site locally with hot reload
mask build-site   # build data, then build the deployable static site
```

`mask build` is the one command that does everything. Any
data-integrity problem - a malformed line, an unknown card name, a
pinned printing that doesn't exist or doesn't match, or conflicting pins
for the same card across files - stops the build and prints every such
problem (not just the first), with nothing written. Pricing problems
(e.g. Archidekt being unreachable) are warnings only, never a build
failure.

Deploys to GitHub Pages automatically via
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) on every push
to `main` (and weekly, to keep prices fresh).

## Pricing

Prices never come from Scryfall - only from real Cardmarket listings, via
Archidekt. Mirror your bulk into an Archidekt deck (one row per card you
physically have - [example](https://archidekt.com/decks/25868036/bulk));
Archidekt already shows each row's Cardmarket price. `mask build
<archidekt_deck_id>` links that deck once (remembered afterwards in
cache/bulk-prices.json) and fetches its prices into it; every later
`mask build` reuses the same deck id and refreshes its prices
automatically. A card not in your bulk-mirror deck (or with no printing
picked there) simply has no price - the fix is to mirror it into
Archidekt and rebuild, not a guessed-at Scryfall estimate.

A priced card's `price_state` tells you how literally to trust the
number: `exact` means the price came from the exact printing currently
displayed; `fallback` means it's a reference price for a *different*
printing of the same card (or a reference/wishlist deck you don't own);
`unavailable` means no price at all. The web app shows a small note
wherever prices are displayed, naming the Cardmarket fetch date and
reminding you that prices change over time.

### Pricing cards you don't own yet

A proxy deck or wishlist (e.g. `decks/25657626_oops_all_orcs.txt`) has
little or no overlap with your bulk-mirror deck, so it would normally
show no prices at all. Every deck/collection file already carries its
own Archidekt deck id (the `NNNN_` filename prefix, or a `#
archidekt: NNNN` metadata line), so `mask build` automatically fetches
reference Cardmarket prices for all of them in the same run - so "price
to complete" is real instead of always "-". A list with no resolvable
Archidekt id is skipped with a warning (rename it to `NNNN_name.txt` or
add a `# archidekt: NNNN` line to fix that).

To fetch one ad-hoc reference deck under a custom label instead - e.g.
someone else's public decklist that isn't one of your own files - pass a
label and deck id explicitly, then rebuild:

```bash
mask fetch-list-prices orcs 25657626   # https://archidekt.com/decks/25657626/oops_all_orcs
mask build
```

Every source's prices are merged into `cache/list-prices.json`; an owned
card's real bulk price always takes priority over a reference price if a
card happens to be in both.

## Card allocation

Ownership is still never stored as such, but it's no longer computed
independently per list either: one physical copy can only be claimed by
one "real" active deck (`status: active`, not `proxy`, not `collection`)
at a time. If two active decks both want the same scarce card, the
first one encountered (in file path order) gets it; the other shows it
as missing. Archived decks, proxy decks, and collections/wishlists don't
reserve physical cards - each is diffed independently against whatever's
left over after active decks have claimed their share, exactly like a
brand-new deck asking for that card today. Basic lands are exempt
entirely (bulk.txt never tracks them). Click any card to see exactly
which deck(s) currently hold it.

## Keeping prices fresh

Update `bulk.txt` (and/or decks/collections) and mirror the same changes
into your Archidekt bulk deck, then rebuild:

```bash
mask build
```

Added a brand-new deck/collection file? Nothing extra to do - `mask
build` already discovers it and fetches its reference prices
automatically as long as it has a resolvable Archidekt id.

Commit the updated `bulk.txt` and `cache/*.json` and push - the deploy
workflow rebuilds the site (and also reruns weekly on its own to catch
any drift).

## Scripts

This project uses Python with `requests` for every script that talks to
Scryfall/Archidekt (see `scripts/net.py` for the shared HTTP retry
helper), and the standard library otherwise. It also uses
[mask](https://github.com/jacobdeichert/mask) as the task runner - run
`mask --help` for the full list of tasks (build, dev, check deck sizes,
diff decklists, Archidekt price analysis, etc).
