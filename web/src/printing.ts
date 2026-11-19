import { normalizeName } from "./normalize";
import type { CardData, CardsIndex } from "./types";

/** Mirrors scripts/build/parse.py's printing_key(): "hob/246". */
export function printingKey(set: string, collectorNumber: string): string {
  return `${set.trim().toLowerCase()}/${collectorNumber.trim().toLowerCase()}`;
}

/** The card to display for one list entry: the card's default record,
 * with the printing-specific fields (art, set, rarity, price) overridden
 * by the entry's pinned printing when the build verified one. Two copies
 * of the same card in different printings therefore show different art
 * and prices, while ownership stays keyed by name. */
export function cardForEntry(
  cards: CardsIndex,
  entry: { name: string; printing?: string },
): CardData | undefined {
  const card = cards[normalizeName(entry.name)];
  if (!card) return undefined;
  const printing = entry.printing ? card.printings?.[entry.printing] : undefined;
  return printing ? { ...card, ...printing } : card;
}
