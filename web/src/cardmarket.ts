import type { CardData } from "./types";

const BASE = "https://www.cardmarket.com/en/Magic";

/** Cardmarket's numeric seller-country filter (23 = Netherlands). */
const SELLER_COUNTRY = "23";

/** Link to a card's Cardmarket page. Uses Scryfall's Cardmarket product id
 * when the printing has one (it redirects to the exact product page),
 * pre-filtered to foil offers for a foil copy; otherwise falls back to a
 * name search so the button always leads somewhere useful. */
export function cardmarketUrl(card: CardData, foil: boolean): string {
  if (card.cardmarket_id == null) {
    const search = new URLSearchParams({ searchString: card.name });
    return `${BASE}/Products/Search?${search}`;
  }
  const params = new URLSearchParams({
    idProduct: String(card.cardmarket_id),
    sellerCountry: SELLER_COUNTRY,
  });
  if (foil) params.set("isFoil", "Y");
  return `${BASE}/Products?${params}`;
}
