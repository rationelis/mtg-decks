import type { IndexEntry } from "./types";

/** A list under decks/ can still really be a wishlist/collection (see
 * IndexEntry.collection), and every list under collections/ is one by
 * kind - either way, it holds no physically-sleeved cards. */
export function isCollectionLike(entry: IndexEntry): boolean {
  return entry.kind === "collection" || entry.collection;
}
