# Deck Overview Generator

Generate a "Deck Overview" table for the README listing all decks in `decks/`.

## Output Format

| Deck | Commander | Colors | Type |
|------|-----------|--------|------|

- **Deck**: Filename converted to title case (underscores → spaces)
- **Commander**: First card listed in the deck file
- **Colors**: Commander's color identity (⚪🔵⚫🔴🟢 or W/U/B/R/G notation)
- **Type**: Deck archetype based on commander/cards (e.g., Tribal, Spellslinger, Aristocrats)

## Deck File Format

Files in `decks/` are plain text with one card per line: `<count> <card name>`

## Color Identity Lookup

Use the Scryfall API to fetch commander color identity:
```
https://api.scryfall.com/cards/named?exact=<card_name>
```

Sort the table alphabetically by deck name.
