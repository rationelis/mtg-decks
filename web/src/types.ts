// Shapes mirror exactly what scripts/build/emit.py writes - the build is
// the single source of truth for what "normalized card data" means. See
// scripts/build/tests/test_emit_shape.py and types.test.ts for the
// shape-pinning tests that keep the two sides from drifting silently.

export type PriceState = "exact" | "fallback" | "unavailable";

/** The per-printing slice of a card: what can differ between two
 * printings of the same oracle card. Keyed by printingKey() in
 * CardData.printings (see scripts/build/resolve.py's PrintingData). */
export interface CardPrinting {
  set: string;
  set_name: string;
  /** The printing's collector number (e.g. "292"), as Scryfall has it. */
  collector_number: string;
  rarity: string;
  image_uri: string | null;
  scryfall_uri: string | null;
  price_eur: number | null;
  price_state: PriceState;
  released_at: string | null;
  /** Scryfall's Cardmarket product id for this printing (null if none). */
  cardmarket_id: number | null;
}

export interface CardData {
  name: string;
  mana_cost: string;
  mana_value: number;
  colors: string[];
  color_identity: string[];
  type_line: string;
  oracle_text: string;
  /** set..released_at describe the card's default printing; an entry that
   * pins a different printing uses `printings` instead (see printing.ts). */
  set: string;
  set_name: string;
  /** The printing's collector number (e.g. "292"), as Scryfall has it. */
  collector_number: string;
  rarity: string;
  image_uri: string | null;
  scryfall_uri: string | null;
  price_eur: number | null;
  price_state: PriceState;
  released_at: string | null;
  cardmarket_id: number | null;
  printings: Record<string, CardPrinting>;
}

/** Keyed by normalizeName(card.name). */
export type CardsIndex = Record<string, CardData>;

export interface ListEntry {
  name: string;
  qty: number;
  /** printingKey() of the entry's "(SET) NUM" pin; absent when unpinned. */
  printing?: string;
  /** Present (always `true`) only when the source line is marked `*F*`. */
  foil?: boolean;
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
