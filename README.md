# mtg-decks

My MTG decklists in version control. [Archidekt folder](https://archidekt.com/folders/1542764)

| Analysed? | Precon? | Deck                   | Commander                  | Colors | Type                           |   Price |
| --------- | ------- | ---------------------- | -------------------------- | ------ | ------------------------------ | ------: |
| ✅        | No      | Blitzkikker            | Henzie "Toolbox" Torre     | ⚫🔴🟢 | Blitz                          | €208.48 |
| ✅        | No      | Unabated Malice        | Shelob, Child of Ungoliant | ⚫🟢   | Token engine                   | €134.45 |
|           | Yes     | Golden Power           | Satya, Aetherflux Genius   | ⚪🔵🔴 | Energy, ETB Clones             |  €63.84 |
|           | Yes     | Bring Your Interaction | Stella Lee, Wild Card      | 🔵🔴   | Cantrip Storm                  |  €74.27 |
|           | Yes     | Tyranid Swarm          | Magus Lucea Kane           | 🔵🔴🟢 | Tyranid Tribal, +1/+1 Counters | €139.33 |
|           | Yes     | World Shaper           | Hearthhull, the Worldseed  | ⚫🔴🟢 | Lands Sacrifice                |  €69.93 |

`decks/` format: `{archidekt_id}_name.txt`

## Scripts

### Deck Analysis

```bash
python3 scripts/check-sizes.py decks/*.txt       # Verify 100 cards
python3 scripts/diff.py old.txt new.txt           # Compare decklists
python3 scripts/oldest-printing.py deck.txt       # Find oldest printings
```

### Card Data

```bash
# Fetch from local file via Scryfall
python3 scripts/fetch-local-scryfall.py decks/21248219_blitzkikker.txt

# Fetch from Archidekt (with categories & pricing)
python3 scripts/fetch-remote-archidekt.py 21248219
```

### Price Analysis

```bash
python3 scripts/get-deck-info.py 21248219        # Quick name & price
python3 scripts/analyze-deck-price.py 21248219   # Statistical analysis
```

Requires `requests`: `pip install requests`
