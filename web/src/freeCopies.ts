import type { UsageIndex } from "./types";

/** Narrows bulk rows to the copies that aren't currently claimed by a
 * deck, using the build's allocation data (usage.json: `available` is
 * owned minus what active decks hold - see scripts/build/allocate.py).
 *
 * - A name with no usage entry (e.g. a basic land) is always free, so it
 *   is kept untouched.
 * - A name with no free copies is dropped.
 * - Otherwise the free count is spread over the name's rows in order, so
 *   a card you own twice with one copy in a deck shows once (qty 1).
 *   Which physical copy sits in a deck isn't tracked, so for a name with
 *   several printings the free copies go to the earlier rows first.
 */
export function freeRows<T extends { name: string; qty: number }>(
  rows: T[],
  usage: UsageIndex,
  keyOf: (name: string) => string,
): T[] {
  const remaining = new Map<string, number>();
  const result: T[] = [];
  for (const row of rows) {
    const key = keyOf(row.name);
    const info = usage[key];
    if (!info) {
      result.push(row);
      continue;
    }
    const left = remaining.get(key) ?? info.available;
    const take = Math.min(row.qty, left);
    remaining.set(key, left - take);
    if (take > 0) result.push(take === row.qty ? row : { ...row, qty: take });
  }
  return result;
}
