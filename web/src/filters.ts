import type { CardData } from "./types";

export interface FilterState {
  search: string;
  colors: Set<string>; // subset of W/U/B/R/G/C
  manaMin: number | null;
  manaMax: number | null;
  type: string;
  rarity: string;
  set: string;
  priceMin: number | null;
  priceMax: number | null;
}

export function emptyFilter(): FilterState {
  return {
    search: "",
    colors: new Set(),
    manaMin: null,
    manaMax: null,
    type: "",
    rarity: "",
    set: "",
    priceMin: null,
    priceMax: null,
  };
}

export function isFilterEmpty(f: FilterState): boolean {
  return (
    f.search === "" &&
    f.colors.size === 0 &&
    f.manaMin === null &&
    f.manaMax === null &&
    f.type === "" &&
    f.rarity === "" &&
    f.set === "" &&
    f.priceMin === null &&
    f.priceMax === null
  );
}

export function matchesFilter(card: CardData, f: FilterState): boolean {
  if (f.search) {
    const q = f.search.toLowerCase();
    const haystack = `${card.name} ${card.oracle_text}`.toLowerCase();
    if (!haystack.includes(q)) return false;
  }

  if (f.colors.size > 0) {
    const cardColors = new Set(card.colors.length > 0 ? card.colors : ["C"]);
    if (cardColors.size !== f.colors.size) return false;
    for (const c of cardColors) {
      if (!f.colors.has(c)) return false;
    }
  }

  if (f.manaMin !== null && card.mana_value < f.manaMin) return false;
  if (f.manaMax !== null && card.mana_value > f.manaMax) return false;

  if (f.type && !card.type_line.toLowerCase().includes(f.type.toLowerCase())) {
    return false;
  }

  if (f.rarity && card.rarity !== f.rarity) return false;

  if (f.set && !card.set.toLowerCase().includes(f.set.toLowerCase())) {
    return false;
  }

  const price = card.price_eur;
  if (f.priceMin !== null && (price === null || price < f.priceMin)) return false;
  if (f.priceMax !== null && (price === null || price > f.priceMax)) return false;

  return true;
}
