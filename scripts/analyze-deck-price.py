#!/usr/bin/env python3
"""
Analyze price distribution of an Archidekt deck.

Fetches deck data from Archidekt and performs statistical analysis on card
prices including concentration metrics, Gini coefficient, and insights about
cost distribution and replaceability.

Usage:
    python3 analyze-deck-price.py <deck_id>

Example:
    python3 analyze-deck-price.py 21248219

Output:
    Price distribution analysis with statistics and insights.
"""

import requests
import sys
from statistics import mean, median


API_URL = "https://archidekt.com/api/decks/{deck_id}/"


def fetch_deck_prices(deck_id):
    """Fetch deck and extract card prices."""
    try:
        url = API_URL.format(deck_id=deck_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching deck: {e}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    card_entries = data.get("cards", [])

    if not card_entries:
        print("No cards found in deck.", file=sys.stderr)
        sys.exit(1)

    # Extract prices, excluding Sideboard and Maybeboard
    excluded_categories = {"Sideboard", "Maybeboard"}
    prices = []

    for entry in card_entries:
        categories = entry.get("categories", [])
        main_category = categories[0] if categories else "Uncategorized"

        # Skip excluded categories
        if main_category in excluded_categories:
            continue

        # Get price and quantity
        card = entry.get("card", {})
        price_data = card.get("prices", {})
        unit_price = price_data.get("cm") or 0.0
        quantity = entry.get("quantity", 1)

        # Add each copy as a separate entry
        for _ in range(quantity):
            prices.append(unit_price)

    return prices


def calculate_gini(values):
    """Calculate Gini coefficient (0 = equal, 1 = highly concentrated)."""
    if not values or all(v == 0 for v in values):
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)
    total = sum(sorted_values)

    if total == 0:
        return 0.0

    # Gini formula: (2 * sum(i * value[i])) / (n * sum(values)) - (n + 1) / n
    cumsum = sum((i + 1) * val for i, val in enumerate(sorted_values))
    gini = (2 * cumsum) / (n * total) - (n + 1) / n

    return gini


def analyze_concentration(prices):
    """Calculate concentration metrics for top cards."""
    sorted_prices = sorted(prices, reverse=True)
    total = sum(prices)

    if total == 0:
        return {3: 0, 5: 0, 10: 0}

    def top_n_percent(n):
        top_n_sum = sum(sorted_prices[:n])
        return (top_n_sum / total) * 100

    return {
        3: top_n_percent(3),
        5: top_n_percent(5),
        10: top_n_percent(10)
    }


def generate_insights(prices, total, mean_price, median_price, concentration, gini):
    """Generate concise insights about the price distribution."""
    sorted_prices = sorted(prices, reverse=True)
    insights = []

    # Inequality assessment
    if gini < 0.4:
        inequality = "low"
    elif gini < 0.6:
        inequality = "moderate"
    else:
        inequality = "high"

    insights.append(f"Price inequality is {inequality} (Gini: {gini:.2f})")

    # Top card concentration
    top_3_pct = concentration[3]
    if top_3_pct > 40:
        insights.append(f"Top 3 cards dominate the cost ({top_3_pct:.1f}% of total)")
    elif top_3_pct > 25:
        insights.append(f"Top 3 cards contribute significantly ({top_3_pct:.1f}% of total)")
    else:
        insights.append(f"Cost is relatively distributed (top 3: {top_3_pct:.1f}%)")

    # Replaceability assessment
    top_5_value = sum(sorted_prices[:5])
    savings_pct = (top_5_value / total) * 100 if total > 0 else 0

    if savings_pct > 30:
        insights.append(f"Replacing top 5 cards could save €{top_5_value:.2f} ({savings_pct:.1f}% reduction)")
    else:
        insights.append(f"No single card dominates; cost spread across deck")

    # Mean vs median comparison
    if mean_price > median_price * 2:
        insights.append(f"Mean (€{mean_price:.2f}) >> median (€{median_price:.2f}): few expensive cards skew average")
    elif mean_price > median_price * 1.5:
        insights.append(f"Mean slightly above median: some pricier cards pull average up")

    # Budget characterization
    if median_price < 1.0:
        insights.append(f"Budget-friendly deck (median: €{median_price:.2f} per card)")
    elif median_price > 5.0:
        insights.append(f"Premium deck (median: €{median_price:.2f} per card)")

    return insights[:5]  # Return max 5 insights


def print_analysis(prices):
    """Print complete price distribution analysis."""
    if not prices:
        print("No cards with prices found.", file=sys.stderr)
        sys.exit(1)

    # Basic stats
    total = sum(prices)
    mean_price = mean(prices)
    median_price = median(prices)

    # Concentration
    concentration = analyze_concentration(prices)

    # Gini coefficient
    gini = calculate_gini(prices)

    # Generate insights
    insights = generate_insights(prices, total, mean_price, median_price, concentration, gini)

    # Print results
    print("=" * 70)
    print("DECK PRICE ANALYSIS")
    print("=" * 70)
    print(f"Cards analyzed: {len(prices)}")
    print()

    # Basic Statistics
    print("BASIC STATISTICS")
    print("-" * 70)
    print(f"Total price:  €{total:.2f}")
    print(f"  → Total cost to build this deck")
    print()
    print(f"Mean price:   €{mean_price:.2f}")
    print(f"  → Average cost per card")
    print()
    print(f"Median price: €{median_price:.2f}")
    print(f"  → Middle value - half the cards cost more, half cost less")
    print()

    # Concentration Metrics
    print("COST CONCENTRATION")
    print("-" * 70)
    print("What % of total cost comes from the most expensive cards?")
    print()
    print(f"Top 3 cards:  {concentration[3]:>5.1f}%")
    print(f"Top 5 cards:  {concentration[5]:>5.1f}%")
    print(f"Top 10 cards: {concentration[10]:>5.1f}%")
    print()
    print("Higher % = cost dominated by a few expensive cards")
    print("Lower % = cost spread more evenly across the deck")
    print()

    # Gini Coefficient
    print("INEQUALITY METRIC")
    print("-" * 70)
    print(f"Gini coefficient: {gini:.3f}")
    print()
    print("Measures price inequality (0.0 = all cards same price, 1.0 = extreme)")
    print("  • 0.00 - 0.40: Low inequality (budget-friendly, even distribution)")
    print("  • 0.40 - 0.60: Moderate inequality (mixed price points)")
    print("  • 0.60 - 1.00: High inequality (few expensive cards, many cheap)")
    print()

    # Insights
    print("KEY INSIGHTS")
    print("-" * 70)
    for insight in insights:
        print(f"• {insight}")
    print()
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    deck_id = sys.argv[1].strip()

    # Fetch and analyze
    prices = fetch_deck_prices(deck_id)
    print_analysis(prices)


if __name__ == "__main__":
    main()
