// Shapes mirror exactly what scripts/build/emit.py writes - the build is
// the single source of truth for what "normalized card data" means.

export interface CardData {
  name: string;
  resolved: boolean;
  mana_cost: string;
  mana_value: number;
  colors: string[];
  color_identity: string[];
  type_line: string;
  oracle_text: string;
  set: string;
  rarity: string;
  image_uri: string | null;
  scryfall_uri: string | null;
  price_eur: number | null;
  released_at: string | null;
}

/** Keyed by normalizeName(card.name). */
export type CardsIndex = Record<string, CardData>;

export interface ListEntry {
  name: string;
  qty: number;
}

export type ListKind = "bulk" | "deck" | "collection";
export type ListStatus = "active" | "archived";

export interface CardList {
  id: string;
  kind: ListKind;
  status: ListStatus;
  name: string;
  commander: string | null;
  archidektId: string | null;
  proxy: boolean;
  collection: boolean;
  sourcePath: string;
  entries: ListEntry[];
}

export interface IndexEntry {
  id: string;
  kind: ListKind;
  status: ListStatus;
  name: string;
  commander: string | null;
  proxy: boolean;
  collection: boolean;
  sourcePath: string;
  entryCount: number;
  totalQty: number;
}

export interface BulkPricesMeta {
  fetchedAt: string;
  source: string;
  archidektDeckId: string;
  deckName: string | null;
  appliedCount: number;
}

export interface ListPriceSource {
  archidektDeckId: string;
  deckName: string | null;
  fetchedAt: string;
  pricedCount: number;
}

export interface ListPricesMeta {
  sources: Record<string, ListPriceSource>;
  appliedCount: number;
}

export interface BuildMeta {
  generatedAt: string;
  uniqueCardCount: number;
  unresolvedCount: number;
  warnings: string[];
  bulkPrices: BulkPricesMeta | null;
  listPrices: ListPricesMeta | null;
}
