import { normalizeName } from "./normalize";
import type { CardData, CardList, CardsIndex } from "./types";

export interface Row {
  name: string;
  qty: number;
  card: CardData;
}

export interface DiffRow extends Row {
  ownedQty: number;
  missingQty: number;
}

const UNRESOLVED_PLACEHOLDER: Omit<CardData, "name"> = {
  resolved: false,
  mana_cost: "",
  mana_value: 0,
  colors: [],
  color_identity: [],
  type_line: "",
  oracle_text: "",
  set: "",
  rarity: "",
  image_uri: null,
  scryfall_uri: null,
  price_eur: null,
};

function lookupCard(name: string, cards: CardsIndex): CardData {
  return cards[normalizeName(name)] ?? { name, ...UNRESOLVED_PLACEHOLDER };
}

/** Aggregate quantities in a list by normalized name (bulk.txt may list the
 * same card more than once across decks it was copy/pasted from). */
export function quantityMap(list: CardList): Map<string, number> {
  const map = new Map<string, number>();
  for (const entry of list.entries) {
    const key = normalizeName(entry.name);
    map.set(key, (map.get(key) ?? 0) + entry.qty);
  }
  return map;
}

export function bulkRows(bulk: CardList, cards: CardsIndex): Row[] {
  return bulk.entries.map((e) => ({
    name: e.name,
    qty: e.qty,
    card: lookupCard(e.name, cards),
  }));
}

/** Ownership is never stored - it's always this computation, run live in
 * the browser against whatever bulk.json currently says. Each deck is
 * diffed independently: if two decks want the same scarce bulk card,
 * both will show it as "owned" (no cross-deck allocation in v1). */
export function diffList(
  list: CardList,
  bulk: CardList,
  cards: CardsIndex,
): DiffRow[] {
  const bulkQty = quantityMap(bulk);
  return list.entries.map((e) => {
    const key = normalizeName(e.name);
    const available = bulkQty.get(key) ?? 0;
    const ownedQty = Math.min(e.qty, available);
    return {
      name: e.name,
      qty: e.qty,
      ownedQty,
      missingQty: e.qty - ownedQty,
      card: lookupCard(e.name, cards),
    };
  });
}
