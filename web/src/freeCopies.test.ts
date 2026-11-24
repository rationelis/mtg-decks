import { describe, expect, it } from "vitest";
import { freeRows } from "./freeCopies";
import type { UsageIndex } from "./types";

const key = (name: string) => name.toLowerCase();

const usage: UsageIndex = {
  "sol ring": { owned: 2, available: 1, allocations: [{ listId: "a", listName: "A", quantity: 1 }] },
  "mana crypt": { owned: 1, available: 0, allocations: [{ listId: "a", listName: "A", quantity: 1 }] },
  "arcane signet": { owned: 1, available: 1, allocations: [] },
};

describe("freeRows", () => {
  it("drops cards with no free copies", () => {
    const rows = [{ name: "Mana Crypt", qty: 1 }];
    expect(freeRows(rows, usage, key)).toEqual([]);
  });

  it("keeps fully free cards untouched", () => {
    const rows = [{ name: "Arcane Signet", qty: 1 }];
    expect(freeRows(rows, usage, key)).toEqual(rows);
  });

  it("trims the quantity to the number of free copies", () => {
    expect(freeRows([{ name: "Sol Ring", qty: 2 }], usage, key)).toEqual([
      { name: "Sol Ring", qty: 1 },
    ]);
  });

  it("spreads free copies across several rows of one name", () => {
    const rows = [
      { name: "Sol Ring", qty: 1, printing: "a" },
      { name: "Sol Ring", qty: 1, printing: "b" },
    ];
    expect(freeRows(rows, usage, key)).toEqual([{ name: "Sol Ring", qty: 1, printing: "a" }]);
  });

  it("treats names without a usage entry (basic lands) as always free", () => {
    const rows = [{ name: "Forest", qty: 30 }];
    expect(freeRows(rows, usage, key)).toEqual(rows);
  });
});
