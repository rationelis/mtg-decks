# REFACTOR.md — Project Anatomy & Refactor Plan

This document describes exactly what this project is today, and lays out
a finalized, minimal plan covering three things: general correctness
fixes, a new card-allocation feature, and a stricter, single-command
build workflow. It is written for someone who will implement the plan
directly — decisions below are final, not options to pick from, unless
explicitly marked otherwise.

---

## 1. What this project is

`mtg-decks` is a personal Magic: The Gathering collection/deck tracker.
It has two halves:

1. **A git-versioned data repository** — plain-text card lists (everything
   physically owned, every deck, wishlists/collections, untouched precon
   reference lists) plus small JSON caches of fetched, third-party data
   (Scryfall card identities, Cardmarket prices via Archidekt).
2. **A static website** (`web/`, Vite + TypeScript, no framework) that
   reads build-time-generated JSON and lets you browse/filter/sort your
   bulk collection and every deck, and see Owned/Missing computed against
   your bulk.

A Python build pipeline (`scripts/build/`) is the join point: it parses
the plain-text lists, resolves every unique card name against Scryfall,
overlays real Cardmarket prices fetched via Archidekt, computes
allocation/ownership, and emits normalized static JSON for the frontend.
The deployed site never calls any external API at runtime. Deployment is
GitHub Pages via GitHub Actions.

There is no server, no database, no user accounts — a single-user,
static, read-only tool whose *state* lives entirely in git (the `.txt`
files and the committed JSON caches).

---

## 2. Guiding principle for this refactor

This is a personal, single-user tool. It should stay **static, simple to
understand, easy to edit, easy to build, dependency-light, inexpensive to
maintain, and boring where possible.** Concretely, this refactor:

- Fixes things that can produce **incorrect behavior** — and treats two
  fundamentally different kinds of incorrectness differently: a bad
  *source/identity* problem (does the build know what card this is?)
  must be loud and blocking; a missing/imperfect *price* is normal and
  must never block anything (§6).
- Collapses the day-to-day workflow to **one command, no arguments**
  (§5). Internal stages stay logically separate; orchestration does not.
- Adds a **small, proportional test suite** for pure logic that matters —
  not a testing framework or a testing architecture (§10).
- Keeps the frontend **framework-free**. Duplicated rendering logic gets
  extracted as ordinary functions, not rebuilt around a rendering
  abstraction.
- Keeps the data model exactly as small as it is today. Allocation is
  **derived**, computed fresh from `bulk.txt` + deck/collection files —
  never stored, never backed by physical-card IDs.
- **Does not** introduce a database, an API server, pagination/streaming,
  sophisticated caching, dependency injection, a state-management
  library, a generic pipeline/plugin framework, or a CLI framework —
  none of these are justified by this project's actual size or usage.

The target mental model, after this refactor, is exactly this and
nothing more:

```
plain text → parse → validate → resolve identity → resolve pricing
           → allocate/diff → emit JSON → simple frontend
```

("validate" is not a separate file — see §5 for why folding it into
parse/resolve is the leaner choice, not a shortcut.) If a proposed change
makes that diagram meaningfully more complicated, it needs a concrete
justification tied to correctness, not convention.

---

## 3. Repository layout

```
bulk.txt              Everything physically owned, one flat list
decks/                 One file per deck; decks/archived/ holds retired ones
collections/            Optional: wishlists, cubes, binders — anything diff-worthy that isn't a "deck"
precons/                Untouched precon reference lists, for manual `mask diff` only — never fed to the build
cache/                  Committed JSON: card-data.json (Scryfall identity cache), bulk-prices.json, list-prices.json (Cardmarket via Archidekt)
scripts/                Python: the build pipeline (scripts/build/*.py) + a handful of CLI utilities
web/                    Vite + TypeScript static site (source in web/src, generated data in web/public/data, gitignored)
.github/workflows/      One workflow: build + deploy to GitHub Pages
maskfile.md             Task runner definitions (mask CLI)
```

---

## 4. The core data model

### 4.1 One plain-text grammar for every list

`bulk.txt`, every file under `decks/`, and every file under
`collections/` share one grammar, parsed by a single regex-based parser
(`scripts/build/parse.py`):

```
<qty>[x] <name>
<qty>[x] <name> (SET) NUM
<qty>[x] <name> (SET) NUM *F*
# plain comment
# key: value                (structured metadata)
Front // Back                (double-faced/split card name, kept whole)
```

- Quantity accepts `1x` or plain `1`, and must be a positive integer —
  `0x Sol Ring` is rejected (§6), not silently accepted.
- A trailing `(SET) NUM` pins a specific **printing** (image/set/rarity)
  without ever affecting **identity** for ownership diffing (always by
  bare card name) — but it *is* an identity constraint in its own right:
  it must actually correspond to the named card, or the build now
  refuses to proceed (§6).
- A trailing `*F*` marks a copy foil (parsed, currently unused downstream
  — unchanged by this refactor).
- Every non-blank, non-`#`-prefixed line must match this grammar exactly,
  or the build reports it as an error (§6) — it is never silently
  skipped.

### 4.2 Metadata via `# key: value` comments

Recognized keys: `name`, `commander`, `archidekt`, `status`
(`active`/`archived`), `proxy` (`true`/`false`), `collection`
(`true`/`false`). All optional, all defaulted from the file's path/name
(title-cased filename, `NNNN_` prefix, `archived/` folder membership).

### 4.3 Ownership today: never stored, computed per-list against raw bulk

There is no "owned" field anywhere. A deck/collection file is a
*desired* list; Owned/Missing is computed by diffing that list's entries
against `bulk.json`, independently per list (`web/src/diff.ts`). Basic
lands are always treated as fully owned (`bulk.txt` never tracks them).

**This independent-per-list computation is exactly the thing §9 replaces**
with a single, allocation-aware calculation, computed once at build time
— the underlying inventory model (`bulk.txt` = physical stock,
`decks/*.txt`/`collections/*.txt` = desired contents, ownership never
stored) does not change.

### 4.4 Card identity vs. pricing are strictly separate concerns

- **Identity** (mana cost, colors, type, oracle text, image, set, rarity)
  comes exclusively from **Scryfall**, resolved at build time and cached
  indefinitely in `cache/card-data.json`. This is now a *strict* concern
  — see §6.
- **Price** never comes from Scryfall — only from real Cardmarket
  listings via Archidekt. This is an *enrichment* concern, tolerant of
  gaps and outages by design — also §6.

### 4.5 Name normalization is the join key everywhere

`normalize_name` (Python) / `normalizeName` (TypeScript) is the single
key joining parsed entries, the Scryfall cache, bulk quantities, price
caches, and frontend lookups. Both implementations currently disagree
for some Unicode input — fixed in §8.2.

---

## 5. Build pipeline: one command, five stages

The normal workflow is one command with no arguments:

```
python3 scripts/build/build.py
```

(wrapped as `mask build` — see §5.3). It replaces the entire current
menu of `build-data` / `fetch-bulk-prices` / `fetch-list-prices` /
`refresh-all`, which today must be remembered and run in a particular
order to get a fully-priced, up-to-date site. There is nothing left to
remember: this one command always does the complete normal build.

### 5.1 The five stages

1. **Parse** (`parse.py`) — reads `bulk.txt` plus every list under
   `decks/`/`collections/` (`precons/` is never scanned), producing
   entries. Any line that fails to parse — malformed quantity, invalid
   `(SET) NUM` syntax, garbage text — is captured as a structured error
   (file, line number, raw text) right here, alongside whatever *did*
   parse successfully (§6). **This is also where syntactic "validate"
   lives.** There is no separate `validate.py`: a line that fails to
   parse *is* the validation failure for that category of error, so
   splitting parsing from syntax-checking would add a file without
   removing any complexity.
2. **Resolve identity** (`resolve.py`) — resolves every unique card name
   against Scryfall, strictly: an exact (case-insensitive) name match, or
   nothing (§6.2 — no silent fuzzy acceptance). Also verifies any pinned
   printing actually corresponds to the resolved card. **This is where
   semantic "validate" lives** — resolving identity strictly *is*
   validating it; there's no separate step.

   **If any errors exist after stages 1–2, `build.py` prints every one of
   them (§6.3) and exits non-zero. Nothing is emitted — no output JSON is
   touched.** This is unconditional. There is no `--strict` flag,
   because there is no non-strict mode: a build that can't confidently
   identify every card the source data claims you own is not a build
   that should update the live site. (In CI, this means a failed build
   simply leaves the previously-deployed site live.)
3. **Resolve pricing** — fetches your Archidekt bulk-mirror deck's real
   Cardmarket prices, plus every list's own reference prices (via each
   list's already-inferred Archidekt id — no configuration needed). This
   used to be two separate manual scripts (`fetch-bulk-prices.py`,
   `fetch-list-prices.py`) that had to be run *before* `build-data`; their
   logic is now called automatically, in order, as part of the one
   command. Network failures here are warnings, never build failures
   (§6.4).
4. **Allocate / diff** (`allocate.py`, new — §9) — computes owned,
   allocated, available, and missing for every card, across every list.
5. **Emit** (`emit.py`) — writes `web/public/data/*.json`, including the
   new `price_state` per card (§6.4) and `ownedQty`/`missingQty` per list
   entry (§9).

### 5.2 Configuring the bulk-mirror deck once

The only thing a fresh clone can't know is *which* Archidekt deck mirrors
your physical bulk. This is set once, via the one argument this command
ever needs:

```
python3 scripts/build/build.py --bulk-deck 25868036
```

This fetches and caches that deck's id in `cache/bulk-prices.json` —
exactly what `mask refresh-all` already does today. Every subsequent run,
with zero arguments, reuses the cached id automatically. If no id has
ever been configured, the build still succeeds — pricing is simply
`unavailable` everywhere, with one clear warning explaining how to set
it up. This is the one sanctioned exception to "no arguments for
ordinary use": a genuinely one-time setup step for the one fact the
repository can't infer on its own.

### 5.3 `mask` tasks, consolidated

| Today | After this refactor |
|---|---|
| `build-data`, `fetch-bulk-prices`, `fetch-list-prices`, `refresh-all` (4 tasks, order-dependent) | one task, `mask build` — wraps the one command above |
| — | `mask build --bulk-deck <id>` for the one-time/occasional linking step |
| `dev`, `build-site` | unchanged — still just call the one build command, then Vite |
| `check`, `diff`, `diff-archidekt`, `oldest`, `fetch-remote`, `analyze` | unchanged — genuinely separate, occasional developer utilities, not part of "build my site" |

The one-off "price someone else's public decklist as a reference"
workflow (today's `fetch-list-prices.py <label> <deck_id>`) stays its own
small, rarely-used script — a genuinely exceptional workflow, not part
of the normal build. It only ever writes to a cache file; the next
normal build picks up the result automatically, no extra step required.

---

## 6. Data integrity model: strict identity, tolerant pricing

Two fundamentally different kinds of failure exist in this pipeline, and
they are treated differently on purpose:

- **Source/identity problems** — the data that defines what you own and
  what a deck wants. These must never be silently swallowed. If
  `bulk.txt` says you own a card, the build must either confidently
  identify that exact card, or refuse to proceed and say why.
- **External pricing problems** — Cardmarket/Archidekt is enrichment, not
  a source of truth for identity. Incomplete pricing is normal and
  expected; it must never block a build or corrupt collection data.

### 6.1 What counts as a data-integrity error (build stops)

- A non-blank, non-`#`-prefixed line that doesn't match the entry
  grammar (malformed card line, malformed quantity, invalid `(SET) NUM`
  syntax). Lines starting with `#` remain either recognized metadata or
  free-form comments, exactly as today — a comment isn't inventory, so
  it can't be "malformed" in this sense.
- A quantity of zero — `0x Sol Ring` doesn't mean anything and is
  rejected rather than silently accepted (negative quantities are
  already impossible under the grammar's `\d+`).
- A card name that Scryfall does not resolve to exactly one known card
  via an exact, case-insensitive name match.
- A pinned printing (`(CMM) 396`) whose Scryfall lookup returns a card
  whose name doesn't match the entry's card name. A set/collector-number
  pin identifies a specific printing, not a pricing hint — a mismatch
  means the source data is wrong, not that the display should silently
  fall back to some other printing.
- Two different files pinning different printings for the same card
  name. `bulk.txt`'s pin, if any, is authoritative (it's the printing you
  actually physically have); a conflicting pin elsewhere is an error
  asking you to remove the redundant pin, not something the build
  arbitrates silently.

None of these produce a placeholder, a skipped line, or a best-effort
guess. Each one is reported (§6.3) and the build stops before writing any
output.

### 6.2 What's explicitly removed: unsafe shortcuts

Today's fuzzy-match fallback (`/cards/named?fuzzy=`) auto-accepts a
"close enough" Scryfall match, only logging a warning if the resolved
name doesn't exactly match what was typed. That is exactly the kind of
"ambiguous or otherwise unsafe identity resolution" this refactor
removes: fuzzy lookup is now used *only* to generate a "did you mean"
suggestion inside the error message — it can no longer resolve a card on
its own.

The existing cache-fallback behavior for a genuine Scryfall network
outage is kept, but narrowed: it only ever reuses a name that was
*exactly* resolved in a previous successful build. It cannot be used to
accept a name that has never been confidently resolved — during an
outage, a brand-new, never-seen name is still a hard error, because
there is genuinely no basis for confidence about it yet.

### 6.3 Error reporting format

All errors are collected across every file before anything is printed —
one run surfaces every problem in the source tree at once, in
deterministic file-then-line order (both parsing and Scryfall resolution
already iterate files/lines in a fixed order, so this requires no new
sorting), rather than stopping at the first one:

```
bulk.txt:184
  Invalid card entry: "3xx Sol Ring nonsense ()"

decks/21248219_blitzkikker.txt:42
  Pinned printing (CMM) 396 does not match "Sol Ring" — that printing is a different card.

bulk.txt:57
  Unknown card name: "Sol Rign" (did you mean "Sol Ring"?)
```

This requires `Entry` (`parse.py`) to carry its source line number — a
small, direct addition, not a new abstraction — and a tiny shared
`BuildError(path, line, message)` type used by both `parse.py` and
`resolve.py`.

### 6.4 Pricing: three explicit states, never conflated

Every card's emitted price carries an explicit `price_state` alongside
`price_eur`:

- **`exact`** — a price was found for the card's actual resolved
  identity: either no printing was pinned (so there's nothing more
  specific to be "exact" about than the resolved default printing), or a
  printing *was* pinned and the priced printing matches it.
- **`fallback`** — a price was found, but not confidently for the
  requested printing: either it came from the name-only reference cache
  (`cache/list-prices.json` — always a reference/wishlist estimate, never
  "your" copy), or it came from the bulk-mirror cache under a printing
  that doesn't match a printing you pinned in the source.
- **`unavailable`** — no price found anywhere. `price_eur` is `null`.

The frontend already shows a small provenance note near every price
(`priceNote.ts`); it's extended to visually distinguish `fallback` (e.g.
a `~€4.20` tilde prefix and a tooltip) from `exact` (`€4.20`), so a
fallback price is never presented as if it were the requested printing's
confirmed market price. None of this — a missing price, a fallback
price, or an unreachable Archidekt during a fetch — ever fails the
build; each produces, at most, an entry in the existing `warnings` list.

### 6.5 Summary of the trust model

| Situation | Result |
|---|---|
| Malformed line, bad quantity, invalid pin syntax | **Error** — build stops |
| Card name doesn't resolve exactly | **Error** — build stops |
| Ambiguous/fuzzy-only resolution | **Error** — build stops (fuzzy is a suggestion only) |
| Pinned printing doesn't match the resolved card | **Error** — build stops |
| Conflicting printing pins across files | **Error** — build stops |
| Missing Cardmarket price | Warning — `price_state: "unavailable"` |
| Fallback (mismatched-printing or reference) price | Warning — `price_state: "fallback"` |
| Archidekt/Scryfall temporarily unreachable | Warning — degrade gracefully, reuse cache only where genuinely confident |

A successful build means the collection's identity data is trustworthy.
It says nothing about whether every price is exact — and it isn't
supposed to.

---

## 7. The web app (`web/`)

- **Stack**: Vite + vanilla TypeScript, no UI framework. A ~30-line
  hyperscript-style `h()` helper (`dom.ts`) is the entire rendering
  layer — this is intentional and stays.
- **Routing**: a ~50-line hand-rolled hash router (`router.ts`) with
  per-view dynamic `import()` code-splitting. Filter state round-trips
  through the hash's query string for shareable links.
- **Data loading** (`data.ts`): every JSON file fetched at most once per
  page load via `memoize()`.
- **Views**: `bulk`, `decks` (progressive enhancement), `list` (a deck/
  collection's diff view).
- **"Contested cards"** (`views/list.ts`): a bespoke, per-view
  calculation. **Deleted in §9**, folded into the same allocation-aware
  Owned/Missing calculation instead of remaining a parallel special case.
- **Rendering large lists**: a simple `IntersectionObserver`-based
  batch-append (`incremental.ts`).
- **Filtering** (`filters.ts`): search, color identity (exact-set match),
  mana value range, type substring, rarity, set, price range.
- **Types** (`types.ts`): `CardData` gains `price_state` (§6.4); list
  entries gain `ownedQty`/`missingQty` (§9) — both pinned by the contract
  test in §8.3.
- **Styling**: one hand-written `style.css`.

---

## 8. Correctness fixes

Three concrete, justified fixes remain in scope beyond §6 and §9 (the
previous two — passing `--strict` in CI, and surfacing skipped lines —
are now fully superseded by §6, which makes strictness unconditional and
turns every skipped line into a reported error).

### 8.1 Three independent, hand-rolled HTTP retry implementations

`scripts/build/resolve.py` talks to Scryfall via raw `urllib.request`
with its own retry loop and a manual `certifi` SSL-context workaround.
`scripts/archidekt.py` talks to Archidekt via `requests` with a
*different* retry loop. `scripts/oldest-printing.py` reimplements a
*third*, simpler Scryfall client instead of reusing `resolve.py`'s. This
is duplicated logic for one concern ("fetch JSON from a rate-limited
API, retry on 429/5xx"), not three genuinely different problems.

**Fix:** one small shared helper, e.g. `scripts/http.py`, built on
`requests` (which already handles TLS/CA bundles sensibly, making the
hand-rolled `certifi`/`ssl` workaround in `resolve.py` unnecessary — pure
deletion). Used by `resolve.py`, `archidekt.py`, and
`oldest-printing.py`. This one change also centralizes the
currently-scattered delay/retry constants, fixes the placeholder
`User-Agent` string in one place instead of three, and adds a small
`requirements.txt` (just `requests`) declaring the project's one real
Python dependency. Net *deletion* of code — three retry loops become
one.

### 8.2 Normalization can disagree across the Python/TypeScript boundary

`parse.normalize_name` uses Python's `str.casefold()`;
`normalize.ts`'s `normalizeName` uses JavaScript's `String.toLowerCase()`.
These are not guaranteed to agree for all Unicode input, and this
function is the join key between every list entry, the Scryfall cache,
and the frontend's lookups.

**Fix:** make both sides do the exact same operation. Change Python's
`normalize_name` from `.casefold()` to `.lower()` — functionally
identical to JS's `.toLowerCase()` for the character set real Magic card
names actually use. Pin this down with one tiny cross-language fixture
(§10).

### 8.3 Python's emitted JSON and TypeScript's types can drift silently

`web/src/types.ts` is hand-kept in sync with `emit.py`'s field lists by
comment/convention only. Nothing catches a field being renamed or
removed on the Python side until the site breaks at runtime — and this
now matters more, with `price_state`/`ownedQty`/`missingQty` joining the
contract.

**Fix:** not a schema/codegen system — real infrastructure for a handful
of simple JSON shapes. Just one small Python test that pins the exact
key set emitted for a card entry, a list entry, an index entry, and
`meta.json` (§10). Any accidental rename fails a cheap, fast test
immediately instead of surfacing as a silent frontend bug.

---

## 9. New feature: card allocation

### 9.1 The problem

The current per-list diff answers *"do I physically own this card?"* by
comparing one list's requested quantity against `bulk.txt`, independently
per list. It does not answer *"is my one physical copy actually free for
this list to use, or is it already claimed by another deck I'm actively
running?"*

```
bulk.txt:  1x Sol Ring
Deck A:    1x Sol Ring
Deck B:    1x Sol Ring
```

Both decks currently show Sol Ring as "owned," because each diff runs
independently against the same shared pool of 1 physical copy. Correct
under a pure inventory model, useless for managing a physical collection.

### 9.2 The model: one calculation, not a special case bolted onto the old one

Allocation is not a separate "contested cards" feature layered on top of
Owned/Missing. It **replaces** the current independent-per-list diff with
a single calculation that produces Owned/Missing *and* subsumes what
"contested" used to mean:

```
owned      = quantity in bulk.txt
allocated  = quantity actually claimed by "real" active decks (§9.3),
             in a fixed deterministic order (§9.4)
available  = owned - allocated
```

For a "real" active deck, its own missing count is
`requested - (whatever it was actually allocated)` — which may be less
than `requested` even though `owned >= requested`, if an earlier deck in
the deterministic order already claimed the difference. For every other
list (archived deck, collection/wishlist, proxy deck — §9.3), missing is
`max(requested - available, 0)`: exactly what a brand-new deck would see
if it asked for this card today.

Basic lands are exempt entirely (always available), matching today's
`isBasicLand` behavior.

Worked example:

```
bulk:    2x Sol Ring
Deck A:  1x Sol Ring
Deck B:  1x Sol Ring
Deck C:  1x Sol Ring

Owned:      2
Allocated:  2
Available:  0
Deck C:     missing 1     (A and B, earlier in order, are fully allocated)
```

This single model deletes the need for a separate "Contested" tab and the
separate "shopping list" export in `views/list.ts`: once Missing is
allocation-aware, `Export Missing` already *is* the accurate shopping
list.

### 9.3 What counts as allocated demand — decided

- **`status: active` deck, not `proxy`, not `collection`** → counts as
  allocated demand.
- **`status: archived` deck** → does not count. Its Owned/Missing is
  computed against `available`, same as any hypothetical new deck.
- **`collection: true` / anything under `collections/`** → does not
  count. A wishlist doesn't reserve physical cards.
- **`proxy: true` active deck** → does not count. A proxy deck doesn't
  need the real card in its sleeve; treating its requests as allocated
  demand would falsely shrink `available` for a card whose physical copy
  is actually free.
- **`precons/*.txt`** → stays fully outside the model, unchanged.

### 9.4 Deterministic ordering — decided

When total demand from "real" active decks exceeds `owned`, allocation is
resolved by processing those decks in the same order `parse.py` already
discovers them: `sorted()` over their file paths (already deterministic,
already in the codebase). Each deck greedily claims what's left of
`owned` in that order; whatever it can't get is its own missing count.

This is intentionally simple and not user-configurable. If this default
ordering ever produces an answer that's genuinely annoying in practice,
the smallest fix is an optional `# priority: N` metadata key — but that's
a second real use case that hasn't happened yet, so it is explicitly
**not** built now.

### 9.5 Where it's computed

Per §5, allocation is computed once, at build time, in Python, in
`scripts/build/allocate.py`, run after pricing and before emit:

- Computes, per unique card name: `owned`, an ordered list of
  `(listId, listName, quantity)` allocations to "real" active decks, and
  `available`.
- Computes, per list entry (every list, not just active decks):
  `ownedQty` and `missingQty`, using the rule in §9.2.

`emit.py` writes this directly into the JSON it already produces: each
`lists/{kind}-{id}.json` entry gains `ownedQty`/`missingQty`, and a new
small `usage.json` maps card name → `{ owned, allocations, available }`,
fetched lazily (memoized, like every other data file) only when a card
detail popover is opened.

**Consequence — deletions, not additions:** `web/src/diff.ts` and the
`demandMap`/`sharedMap`/`additionalNeeded`/`contestedRows` logic in
`views/list.ts` are deleted. The frontend stops computing diffs entirely
— it renders fields the build already computed.

### 9.6 UI

No new column on any table. The existing Owned/Missing visual treatment
in `components/cardView.ts` is unchanged in appearance — it now reflects
allocation-aware numbers instead of raw-bulk numbers. The only new UI
surface is a click-triggered card detail popover, reused everywhere a
card is clickable, sourced from `usage.json`:

```
Sol Ring

Owned: 1
Available: 0

In:
  Atraxa — 1 copy
```

```
Sol Ring

Owned: 3
Available: 1

In:
  Atraxa — 1 copy
  Yuriko — 1 copy
```

```
Sol Ring

Owned: 2
Available: 2

In:
  —
```

When opened from within a specific deck's row for a card that deck
couldn't get allocated, the same popover can lead with a one-line summary
framed for that deck's situation, still backed by the same data:

```
Owned — unavailable
1 copy owned, currently in Atraxa
```

One component, one data source, no new concept vocabulary — just a
detail view for numbers the build already computed.

### 9.7 Explicitly out of scope for this feature

No physical-card IDs, no database, no synchronization state, no new
plain-text grammar (the optional `# priority: N` key from §9.4 is not
being added now), no change to what `bulk.txt`/`decks/*.txt`/
`collections/*.txt` store. Allocation is 100% derived, recomputed on
every build.

---

## 10. Testing plan (small, proportional — not a testing architecture)

A handful of focused tests, protecting the things that can actually be
wrong. Python tests use `pytest`; frontend tests use `vitest`. No test
utility framework layered on top of either.

- **`scripts/build/tests/test_parse.py`** — the documented grammar is
  accepted (plain qty, `Nx` qty, printing pin, hyphenated collector
  number, foil marker, `Front // Back`, metadata comments); a malformed
  line, a zero quantity, and invalid pin syntax each produce a structured
  error with the correct file and line number (§6.1, §6.3).
- **`scripts/build/tests/test_resolve.py`** — an exact name match
  resolves; a name with no exact match produces an error carrying a
  fuzzy "did you mean" suggestion, without ever auto-accepting it
  (§6.2); a pinned printing that resolves to a different card's name
  produces a mismatch error (§6.1); two files pinning conflicting
  printings for the same name produce a conflict error, with `bulk.txt`
  established as authoritative when it has an opinion.
- **`scripts/build/tests/test_pricing.py`** — `price_state` is `exact`
  when no printing is pinned and a bulk-mirror price exists, `exact` when
  a pinned printing matches the priced printing, `fallback` when a
  pinned printing doesn't match (or the price came from the reference
  cache), and `unavailable` when no price exists anywhere (§6.4).
- **`scripts/build/tests/test_allocate.py`** — the Sol Ring scenarios
  from §9.2 and §9.4: single owner, exact 1:1, oversubscribed across
  three decks (confirms the deterministic order), archived/collection/
  proxy decks correctly excluded from allocated demand but still diffed
  against `available`, basic lands always available.
- **`scripts/build/tests/test_emit_shape.py`** — pins the exact key set
  emitted for a card entry (including `price_state`), a list entry
  (including `ownedQty`/`missingQty`), an index entry, and `meta.json`
  (§8.3).
- **A shared normalization fixture** — a small JSON file of tricky name →
  normalized-name pairs, loaded by one Python test and one `vitest` test,
  asserting both sides produce identical output (§8.2).
- **`web/src/filters.test.ts`** — `matchesFilter` for search, exact-set
  color-identity matching, mana value/price ranges, type/rarity/set.
- **`web/src/sort.test.ts`** — each `SortKey` produces the expected
  order, including `null`-price/`null`-release-date edge cases.

That's the whole suite. No mocking framework, no snapshot-testing
library, no test-database, no CI matrix beyond "run pytest, run vitest,
run the one build command."

---

## 11. Explicitly out of scope / intentionally left alone

These were considered and deliberately **not** changed. Listed here so
they aren't mistaken for oversights later:

- **`mask check` (100-card deck-size validation)** stays a separate,
  optional, non-blocking developer utility. Deck size is a per-format
  soft convention, not a universal data-integrity invariant — folding it
  into the strict build would break legitimate non-100-card lists
  (wishlists, cubes, in-progress decks).
- **Collecting all errors before reporting, instead of failing fast on
  the first one (§6.3).** This is a deliberate, bounded exception to
  "don't add complexity": it's the same amount of code, just deferred
  printing, and it means one run finds every problem instead of forcing
  a fix-one-rerun-repeat loop.
- **No separate `validate.py` module** (§5.1) — syntactic validation
  lives in `parse.py`, semantic/identity validation lives in
  `resolve.py`, because both are already the natural place those checks
  have the information they need. A dedicated file would relocate
  complexity, not remove it.
- **The `mask` task runner itself.** Works, is documented, is boring. Not
  replaced with a CLI framework.
- **`cards.json` size (~1 MB uncompressed).** Not a problem at this
  collection's actual size. No pagination, streaming, or database.
- **The GitHub Pages + prebuilt-JSON deployment model.** Appropriate for
  this application; not redesigned.
- **No frontend framework, no state-management library.** The hand-rolled
  `h()`/closures approach stays.
- **No CI branch protection / PR-gated checks, no error monitoring for
  the deployed site, no accessibility/i18n pass.** Not the target of
  this refactor.
- **The remaining one-off scripts** (`analyze-deck-price.py`,
  `fetch-remote-archidekt.py`, `get-deck-info.py`, `diff.py`,
  `diff-archidekt.py`, `check-sizes.py`, `sort-bulk.py`) are fine as
  independent, boring CLI scripts, unchanged except where §8.1's shared
  HTTP helper replaces their own retry code.
- **`Entry.foil` remains parsed-but-unused.** Not part of this refactor.

---

## 12. Summary: what must be preserved vs. what's changing

**Preserve:**
- The plain-text, human-editable list grammar, unchanged.
- `bulk.txt` = physical inventory, `decks/*.txt`/`collections/*.txt` =
  desired contents, ownership and allocation both derived, never stored,
  no physical-card IDs.
- Strict separation of card identity (Scryfall) from pricing (Cardmarket
  via Archidekt only) — now made explicit as two differently-trusted
  concerns (§6) rather than just an implementation convention.
- The static-site deployment model.
- `precons/` as manual-diff-only.
- The framework-free frontend.

**Changing (all decided, not open questions):**
- One command, no arguments, runs the entire normal build; the only
  sanctioned argument is the one-time `--bulk-deck` linking step (§5).
- `build-data`/`fetch-bulk-prices`/`fetch-list-prices`/`refresh-all`
  collapse into one `mask build` task (§5.3).
- Any data-integrity problem (malformed line, bad quantity, unresolved
  name, mismatched printing pin, conflicting pins) is now an
  unconditional build error with file:line reporting — `--strict` no
  longer exists because there is no non-strict mode (§6).
- Fuzzy-match auto-acceptance is removed; fuzzy results are suggestions
  in error messages only (§6.2).
- Pricing gains an explicit `exact`/`fallback`/`unavailable` state,
  never silently conflated (§6.4).
- One shared HTTP retry helper replaces three duplicated ones (§8.1).
- Python's `normalize_name` uses `.lower()` to match JS exactly (§8.2).
- A small pinned-shape test guards the Python/TypeScript JSON contract
  (§8.3).
- Allocation becomes a build-time calculation (`scripts/build/
  allocate.py`) that replaces the independent-per-list diff and deletes
  the separate "contested cards" special case (§9).
- A small `pytest`/`vitest` suite covers parsing, identity/pin
  validation, pricing states, allocation, emitted shape, normalization
  agreement, filtering, and sorting (§10).

**Not changing, by design (§11):** `mask check`, the task runner, the
deployment model, JSON file size/pagination strategy, the frontend
framework choice, CI process weight, and the rest of the one-off
scripts.
