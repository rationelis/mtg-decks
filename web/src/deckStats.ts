import { normalizeName } from "./normalize";
import type { CardData } from "./types";

/** The minimum a row needs for deck statistics - a structural subset of
 * the view's `CardRow` so callers don't need to adapt anything. */
export interface StatRow {
  qty: number;
  ownedQty?: number;
  missingQty?: number;
  card: Pick<CardData, "price_eur">;
}

export interface PriceTotal {
  /** Sum over every copy that has a price. Never includes a made-up €0
   * for unpriced copies - see `unpricedQty`. */
  total: number;
  /** Copies that contributed to `total`. */
  pricedQty: number;
  /** Copies with no price at all, which `total` knows nothing about. When
   * this is > 0, `total` is only a lower bound. */
  unpricedQty: number;
}

function sumPrices(rows: StatRow[], qtyOf: (row: StatRow) => number): PriceTotal {
  let total = 0;
  let pricedQty = 0;
  let unpricedQty = 0;
  for (const row of rows) {
    const qty = qtyOf(row);
    if (qty <= 0) continue;
    if (row.card.price_eur == null) {
      unpricedQty += qty;
    } else {
      total += row.card.price_eur * qty;
      pricedQty += qty;
    }
  }
  return { total, pricedQty, unpricedQty };
}

/** Estimated cost of the copies still missing from the deck. */
export function priceToComplete(rows: StatRow[]): PriceTotal {
  return sumPrices(rows, (r) => r.missingQty ?? 0);
}

/** Σ (qty × reference price) over every card in the deck, owned or not. */
export function theoreticalMinimum(rows: StatRow[]): PriceTotal {
  return sumPrices(rows, (r) => r.qty);
}

/** "€12.34", or "€12.34+" when some copies had no price and so the figure
 * is only a lower bound. */
export function formatPriceTotal(price: PriceTotal): string {
  const amount = `€${price.total.toFixed(2)}`;
  return price.unpricedQty > 0 ? `${amount}+` : amount;
}

/** Tooltip/footnote explaining an incomplete total - undefined when every
 * copy was priced. */
export function priceTotalNote(price: PriceTotal): string | undefined {
  if (price.unpricedQty <= 0) return undefined;
  const n = price.unpricedQty;
  return `${n} cop${n === 1 ? "y has" : "ies have"} no price and ${n === 1 ? "is" : "are"} not included`;
}

export type DeckStatus = "complete" | "in-progress" | "incomplete";

/** Deck status, derived purely from the build's allocation data (never
 * stored separately):
 *  - complete: nothing missing
 *  - in-progress: some copies owned, but more still needed
 *  - incomplete: copies missing and none owned yet
 * Returns null when the rows carry no allocation data at all (e.g. a
 * collection), since there is nothing to judge. */
export function deckStatus(rows: Pick<StatRow, "ownedQty" | "missingQty">[]): DeckStatus | null {
  if (rows.length === 0 || rows.every((r) => r.ownedQty === undefined && r.missingQty === undefined)) {
    return null;
  }
  const owned = rows.reduce((sum, r) => sum + (r.ownedQty ?? 0), 0);
  const missing = rows.reduce((sum, r) => sum + (r.missingQty ?? 0), 0);
  if (missing <= 0) return "complete";
  return owned > 0 ? "in-progress" : "incomplete";
}

export const STATUS_LABELS: Record<DeckStatus, string> = {
  complete: "Complete",
  "in-progress": "In progress",
  incomplete: "Incomplete",
};

/** Finds the entry that represents the deck's commander. Matches the full
 * name or just one face of a double-faced "A // B" entry. */
export function findCommanderEntry<T extends { name: string }>(
  entries: T[],
  commander: string | null,
): T | undefined {
  if (!commander) return undefined;
  const target = normalizeName(commander);
  const faces = (name: string) => normalizeName(name).split(" // ").map((f) => f.trim());
  return (
    entries.find((e) => normalizeName(e.name) === target) ??
    entries.find((e) => faces(e.name).includes(target))
  );
}
