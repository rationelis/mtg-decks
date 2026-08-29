import type { BuildMeta } from "./types";

/** One line of copy explaining where prices came from, shared by every
 * view that shows prices. Kept as plain text (no HTML) since it's set
 * via textContent. */
export function priceNote(meta: BuildMeta): string {
  const bulkPrices = meta.bulkPrices;
  if (!bulkPrices) {
    return (
      "💶 No prices yet - run `mask fetch-bulk-prices <archidekt_deck_id>` " +
      "(or `mask release`) to fetch real Cardmarket prices via Archidekt."
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
    "Prices change over time - check Cardmarket for current listings.";
  const listSources = meta.listPrices?.sources ? Object.values(meta.listPrices.sources) : [];
  if (listSources.length > 0) {
    note +=
      " Some missing cards also show a reference price from a wishlist source deck.";
  }
  return note;
}
