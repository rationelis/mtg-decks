import type { CardData } from "./types";

export type SortKey =
  | "name-asc"
  | "name-desc"
  | "mv-asc"
  | "mv-desc"
  | "price-asc"
  | "price-desc"
  | "released-asc"
  | "released-desc";

export function sortRows<T extends { card: CardData }>(rows: T[], key: SortKey): T[] {
  const sorted = [...rows];
  switch (key) {
    case "name-asc":
      sorted.sort((a, b) => a.card.name.localeCompare(b.card.name));
      break;
    case "name-desc":
      sorted.sort((a, b) => b.card.name.localeCompare(a.card.name));
      break;
    case "mv-asc":
      sorted.sort((a, b) => a.card.mana_value - b.card.mana_value);
      break;
    case "mv-desc":
      sorted.sort((a, b) => b.card.mana_value - a.card.mana_value);
      break;
    case "price-asc":
      sorted.sort((a, b) => (a.card.price_eur ?? -1) - (b.card.price_eur ?? -1));
      break;
    case "price-desc":
      sorted.sort((a, b) => (b.card.price_eur ?? -1) - (a.card.price_eur ?? -1));
      break;
    case "released-asc":
      sorted.sort((a, b) => (a.card.released_at ?? "").localeCompare(b.card.released_at ?? ""));
      break;
    case "released-desc":
      sorted.sort((a, b) => (b.card.released_at ?? "").localeCompare(a.card.released_at ?? ""));
      break;
  }
  return sorted;
}
