import type { BuildMeta, CardData } from "./types";

/** One line of copy explaining where prices came from, shared by every
 * view that shows prices. Kept as plain text (no HTML) since it's set
 * via textContent. */
export function priceNote(meta: BuildMeta): string {
  const bulkPrices = meta.bulkPrices;
  if (!bulkPrices) {
    return (
      "💶 No prices yet - run `mask build <archidekt_deck_id>` " +
      "to link your bulk-mirror deck and fetch real Cardmarket prices via Archidekt."
    );
  }
  const date = new Date(bulkPrices.fetchedAt).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  let note =
    `💶 Prices are real Cardmarket listings, fetched via Archidekt on ${date}. ` +
    "Cards with no price haven't been mirrored into that Archidekt deck yet. " +
    "A tilde (~€) means the price isn't confirmed for the exact printing shown. " +
    "Prices change over time - check Cardmarket for current listings.";
  const listSources = meta.listPrices?.sources ? Object.values(meta.listPrices.sources) : [];
  if (listSources.length > 0) {
    note +=
      " Some missing cards also show a reference price from a wishlist source deck.";
  }
  return note;
}

/** A price formatted for display, distinguishing an `exact` price (the
 * card's actual resolved/pinned printing) from a `fallback` one (a real
 * price, but not confidently for that exact printing - a tilde prefix
 * flags this) from `unavailable` (no price at all) - see
 * REFACTOR.md §6.4. */
export function formatPriceLabel(card: CardData): string {
  if (card.price_eur == null) return "—";
  const amount = `€${card.price_eur.toFixed(2)}`;
  return card.price_state === "fallback" ? `~${amount}` : amount;
}

/** Tooltip text explaining a fallback price - undefined when there's
 * nothing extra to explain (exact price, or no price at all). */
export function priceTitle(card: CardData): string | undefined {
  if (card.price_eur == null || card.price_state !== "fallback") return undefined;
  return "Reference price - may be for a different printing than shown, or from a wishlist/reference deck you don't own.";
}
