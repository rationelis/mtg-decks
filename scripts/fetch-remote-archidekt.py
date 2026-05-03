#!/usr/bin/env python3
"""
Fetch deck data from Archidekt with category labels.

Queries the Archidekt API to get a complete deck including your custom
category labels. Each card shows its main category and subcategories,
along with card details like mana cost, type line, and oracle text.

Usage:
    python3 fetch-remote-archidekt.py <deck_id>

Example:
    python3 fetch-remote-archidekt.py 21248219

Output:
    Deck statistics followed by card details, one card per block.
"""

import requests
import sys
from collections import defaultdict

API_URL = "https://archidekt.com/api/decks/{deck_id}/"


def build_type_line(oracle_card):
    """Build type line from super types, types, and subtypes."""
    parts = []

    super_types = oracle_card.get("superTypes", [])
    types = oracle_card.get("types", [])
    sub_types = oracle_card.get("subTypes", [])

    # Super types and types
    type_part = " ".join(super_types + types)
    if type_part:
        parts.append(type_part)

    # Subtypes after em dash
    if sub_types:
        parts.append("—")
        parts.append(" ".join(sub_types))

    return " ".join(parts)


def extract_card_data(card_entry):
    """Extract relevant data from an Archidekt card entry."""
    card = card_entry.get("card", {})
    oracle_card = card.get("oracleCard", {})

    # Handle double-faced cards
    faces = oracle_card.get("faces", [])
    if faces and len(faces) > 1:
        mana_cost = " // ".join(f.get("manaCost", "") for f in faces)
        oracle_text = "\n---\n".join(f.get("text", "") for f in faces)
        # For DFC, use combined type line
        type_parts = []
        for f in faces:
            f_super = f.get("superTypes", [])
            f_types = f.get("types", [])
            f_sub = f.get("subTypes", [])
            type_str = " ".join(f_super + f_types)
            if f_sub:
                type_str += " — " + " ".join(f_sub)
            type_parts.append(type_str)
        type_line = " // ".join(type_parts)
    else:
        mana_cost = oracle_card.get("manaCost", "")
        oracle_text = oracle_card.get("text", "")
        type_line = build_type_line(oracle_card)

    # Extract categories
    categories = card_entry.get("categories", [])
    main_category = categories[0] if categories else "Uncategorized"
    subcategories = categories[1:] if len(categories) > 1 else []

    # Extract price (CardMarket)
    prices = card.get("prices", {})
    price_cm = prices.get("cm") or 0.0

    return {
        "name": oracle_card.get("name", "Unknown"),
        "main_category": main_category,
        "subcategories": subcategories,
        "mana_cost": mana_cost,
        "type_line": type_line,
        "oracle_text": oracle_text,
        "quantity": card_entry.get("quantity", 1),
        "cmc": oracle_card.get("cmc", 0),
        "price_cm": price_cm,
    }


def calculate_statistics(cards):
    """Calculate deck statistics."""
    category_counts = defaultdict(int)
    total_cards = 0
    total_cmc = 0
    non_land_cards = 0
    total_price = 0.0
    type_counts = defaultdict(int)

    for card in cards:
        qty = card["quantity"]
        total_cards += qty
        category_counts[card["main_category"]] += qty

        # Add price (quantity * unit price)
        total_price += card["price_cm"] * qty

        # Extract primary type
        type_line = card["type_line"]
        is_land = "Land" in type_line

        if is_land:
            type_counts["Lands"] += qty
        else:
            # Only count CMC for non-lands
            total_cmc += card["cmc"] * qty
            non_land_cards += qty

            if "Creature" in type_line:
                type_counts["Creatures"] += qty
            elif "Instant" in type_line:
                type_counts["Instants"] += qty
            elif "Sorcery" in type_line:
                type_counts["Sorceries"] += qty
            elif "Artifact" in type_line:
                type_counts["Artifacts"] += qty
            elif "Enchantment" in type_line:
                type_counts["Enchantments"] += qty
            elif "Planeswalker" in type_line:
                type_counts["Planeswalkers"] += qty

    avg_cmc = total_cmc / non_land_cards if non_land_cards > 0 else 0

    return {
        "total_cards": total_cards,
        "non_land_cards": non_land_cards,
        "total_cmc": total_cmc,
        "avg_cmc": avg_cmc,
        "total_price": total_price,
        "category_counts": dict(sorted(category_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
    }


def print_statistics(stats):
    """Print deck statistics."""
    print("=" * 60)
    print("DECK STATISTICS")
    print("=" * 60)
    print(f"Total Cards: {stats['total_cards']}")
    print(f"Non-Land Cards: {stats['non_land_cards']}")
    print(f"Total Mana Value: {stats['total_cmc']:.2f}")
    print(f"Avg Mana Value: {stats['avg_cmc']:.2f}")
    print(f"Total Price (CardMarket): €{stats['total_price']:.2f}")
    print()

    print("Cards by Main Category:")
    for category, count in stats["category_counts"].items():
        print(f"  {category}: {count}")
    print()

    print("Cards by Type:")
    for card_type, count in stats["type_counts"].items():
        print(f"  {card_type}: {count}")
    print()
    print("=" * 60)
    print()


def print_card(card):
    """Print card details."""
    print(f"Name: {card['name']}")
    print(f"Main Category: {card['main_category']}")
    if card["subcategories"]:
        print(f"Subcategories: {', '.join(card['subcategories'])}")
    print(f"Mana Cost: {card['mana_cost']}")
    print(f"Type: {card['type_line']}")
    print(f"Text: {card['oracle_text']}")
    print(f"Quantity: {card['quantity']}")

    # Show price (unit price and total if quantity > 1)
    unit_price = card['price_cm']
    qty = card['quantity']
    if qty > 1:
        total_price = unit_price * qty
        print(f"Price: €{unit_price:.2f} each (€{total_price:.2f} total)")
    else:
        print(f"Price: €{unit_price:.2f}")

    print("=" * 60)
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    deck_id = sys.argv[1].strip()

    # Fetch deck data
    try:
        url = API_URL.format(deck_id=deck_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching deck: {e}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()

    # Extract card entries
    card_entries = data.get("cards", [])
    if not card_entries:
        print("No cards found in deck.", file=sys.stderr)
        sys.exit(1)

    # Process all cards
    cards = [extract_card_data(entry) for entry in card_entries]

    # Filter out Sideboard and Maybeboard
    excluded_categories = {"Sideboard", "Maybeboard"}
    main_deck_cards = [
        card for card in cards if card["main_category"] not in excluded_categories
    ]

    # Calculate and print statistics (main deck only)
    stats = calculate_statistics(main_deck_cards)
    print_statistics(stats)

    # Print main deck cards only
    for card in main_deck_cards:
        print_card(card)


if __name__ == "__main__":
    main()
