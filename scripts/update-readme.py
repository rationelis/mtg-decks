#!/usr/bin/env python3
"""
Update README.md with current deck prices from Archidekt.

Scans the decks/ directory for files matching {deck_id}_*.txt pattern,
fetches current price from Archidekt for each deck, and ensures the
README.md stays current.

Usage:
    python3 update-readme.py

This script is primarily used by GitHub Actions to keep prices up-to-date.
"""

import re
import sys
import requests
from pathlib import Path


API_URL = "https://archidekt.com/api/decks/{deck_id}/"
DECKS_DIR = "decks"
README_FILE = "README.md"


def extract_deck_id(filename):
    """Extract deck ID from filename pattern: {id}_name.txt"""
    match = re.match(r'^(\d+)_.*\.txt$', filename)
    return match.group(1) if match else None


def fetch_deck_info(deck_id):
    """Fetch deck name and price from Archidekt."""
    try:
        url = API_URL.format(deck_id=deck_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch deck {deck_id}: {e}", file=sys.stderr)
        return None

    data = resp.json()
    deck_name = data.get("name", "Unknown Deck")

    # Calculate total price (exclude Sideboard/Maybeboard)
    card_entries = data.get("cards", [])
    excluded_categories = {"Sideboard", "Maybeboard"}
    total_price = 0.0

    for entry in card_entries:
        categories = entry.get("categories", [])
        main_category = categories[0] if categories else "Uncategorized"

        if main_category in excluded_categories:
            continue

        card = entry.get("card", {})
        price_data = card.get("prices", {})
        unit_price = price_data.get("cm") or 0.0
        quantity = entry.get("quantity", 1)

        total_price += unit_price * quantity

    return {
        "name": deck_name,
        "price": total_price
    }


def scan_decks():
    """Scan decks directory and fetch info for each deck."""
    decks_path = Path(DECKS_DIR)

    if not decks_path.exists():
        print(f"Error: {DECKS_DIR}/ directory not found", file=sys.stderr)
        sys.exit(1)

    decks = {}

    for file in sorted(decks_path.glob("*.txt")):
        deck_id = extract_deck_id(file.name)

        if not deck_id:
            continue

        print(f"Fetching {deck_id}...")
        info = fetch_deck_info(deck_id)

        if info:
            decks[deck_id] = {
                "file": file.name,
                **info
            }

    return decks


def update_readme(decks):
    """Update README.md with current deck prices."""
    readme_path = Path(README_FILE)

    if not readme_path.exists():
        print(f"Error: {README_FILE} not found", file=sys.stderr)
        sys.exit(1)

    content = readme_path.read_text()
    lines = content.split('\n')

    # Find the table and update it
    updated_lines = []
    in_table = False
    header_line_idx = None

    for i, line in enumerate(lines):
        # Detect table start (header with | Analysed? | Precon? | Deck |...)
        if '| Analysed?' in line and '| Deck' in line:
            in_table = True
            header_line_idx = i
            # Check if Price column exists, if not add it
            if '| Price' not in line:
                line = line.rstrip() + ' | Price   |'
            updated_lines.append(line)
            continue

        # Handle separator line (|----|----|----|)
        if in_table and header_line_idx is not None and i == header_line_idx + 1:
            # This should be the separator line
            if '| Price' not in lines[header_line_idx]:
                # Was added, so add separator
                line = line.rstrip() + ' | ------: |'
            elif line.count('|') < lines[header_line_idx].count('|'):
                # Price column exists in header but not separator
                line = line.rstrip() + ' | ------: |'
            updated_lines.append(line)
            continue

        # Update table rows with prices
        if in_table and line.strip().startswith('|') and '---' not in line and i > header_line_idx + 1:
            parts = line.split('|')
            # Remove empty first element (before first |)
            if len(parts) > 0 and parts[0].strip() == '':
                parts = parts[1:]
            # Remove empty last element (after last |)
            if len(parts) > 0 and parts[-1].strip() == '':
                parts = parts[:-1]

            if len(parts) >= 6:  # Valid data row (should have at least 6 columns)
                # Column indices: 0=Analysed?, 1=Precon?, 2=Deck, 3=Commander, 4=Colors, 5=Type, 6=Price(optional)
                deck_name = parts[2].strip() if len(parts) > 2 else ""

                # Find matching deck by name
                matching_price = None
                for deck_id, info in decks.items():
                    # Match by deck name (case-insensitive, flexible)
                    api_name = info['name'].lower()
                    table_name = deck_name.lower().strip()

                    # Handle [BREW] and [PRECON] prefixes from API
                    api_name_clean = api_name.replace('[brew]', '').replace('[precon]', '').strip()

                    if table_name in api_name_clean or api_name_clean in table_name:
                        matching_price = info['price']
                        break

                # Format price
                if matching_price is not None:
                    price_str = f"€{matching_price:.2f}"
                    if len(parts) >= 7:  # Price column exists, update it
                        parts[6] = f" {price_str:>7} "
                    else:  # Add price column
                        parts.append(f" {price_str:>7} ")
                else:
                    # No match, add empty or keep existing
                    if len(parts) < 7:
                        parts.append("         ")

                # Rebuild line with proper formatting
                line = '| ' + ' | '.join(p.strip() for p in parts) + ' |'

            updated_lines.append(line)
        elif in_table and line.strip() and not line.strip().startswith('|'):
            # End of table
            in_table = False
            updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Write back
    new_content = '\n'.join(updated_lines)
    readme_path.write_text(new_content)

    return True


def main():
    print("Scanning decks directory...")
    decks = scan_decks()

    if not decks:
        print("No decks found with valid IDs.")
        sys.exit(1)

    print(f"\nFound {len(decks)} deck(s)")

    # Display deck summary
    print("\nDeck Summary:")
    for deck_id, info in decks.items():
        print(f"  {info['name']:40} €{info['price']:>7.2f}")

    # Update README
    print(f"\nUpdating {README_FILE}...")
    if update_readme(decks):
        print(f"✓ README updated successfully")
    else:
        print(f"⚠ Failed to update README", file=sys.stderr)


if __name__ == "__main__":
    main()
