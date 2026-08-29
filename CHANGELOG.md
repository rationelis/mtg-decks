# Changelog

Every tagged release records when this repo's pricing was last refreshed
from Cardmarket (via Archidekt), so the web app - and anyone reading
history - knows how fresh the "owned card" prices were at that point.
Everything else (which cards were added/removed) is visible in the
regular git log; this file exists specifically for the pricing timestamp.

Add a new entry each time you run `mask release <version>` (or the
underlying steps by hand - see [README.md](README.md#releasing-a-new-bulk-version)):

```markdown
## [vX.Y.Z] - YYYY-MM-DD

- Cardmarket prices fetched: YYYY-MM-DD (via Archidekt deck 25868036)
- Total value: EUR total (printed by `mask fetch-bulk-prices` /
  `mask release` when it fetches)
- Notes: whatever changed in bulk.txt / decks / collections worth mentioning
```

## [v0.1] - 2026-08-29

Value of bulk: EUR 367.05.
Note: Initial release.
