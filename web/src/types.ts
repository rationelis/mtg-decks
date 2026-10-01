// Shapes mirror exactly what scripts/build/emit.py writes - the build is
// the single source of truth for what "normalized card data" means. See
// scripts/build/tests/test_emit_shape.py and types.test.ts for the
// shape-pinning tests that keep the two sides from drifting silently.

export type PriceState = "exact" | "fallback" | "unavailable";

export interface CardData {
  name: string;
  mana_cost: string;
  mana_value: number;
  colors: string[];
  color_identity: string[];
  type_line: string;
  oracle_text: string;
  set: string;
  set_name: string;
  rarity: string;
  image_uri: string | null;
  scryfall_uri: string | null;
  price_eur: number | null;
  price_state: PriceState;
  released_at: string | null;
}

/** Keyed by normalizeName(card.name). */
export type CardsIndex = Record<string, CardData>;

export interface ListEntry {
  name: string;
  qty: number;
  /** Present on every list except bulk.json - see scripts/build/allocate.py. */
  ownedQty?: number;
  missingQty?: number;
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
  warnings: string[];
  bulkPrices: BulkPricesMeta | null;
  listPrices: ListPricesMeta | null;
}

/** One deck's claim on a card's bulk supply (see scripts/build/allocate.py). */
export interface Allocation {
  listId: string;
  listName: string;
  quantity: number;
}

/** Keyed by normalizeName(card.name) - basic lands never appear here
 * (see scripts/build/allocate.py's is_basic_land). */
export interface Usage {
  owned: number;
  available: number;
  allocations: Allocation[];
}

export type UsageIndex = Record<string, Usage>;
