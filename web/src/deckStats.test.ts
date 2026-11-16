import { describe, expect, it } from "vitest";
import {
  deckStatus,
  findCommanderEntry,
  formatPriceTotal,
  priceToComplete,
  priceTotalNote,
  theoreticalMinimum,
} from "./deckStats";

const row = (qty: number, price: number | null, ownedQty?: number, missingQty?: number) => ({
  qty,
  ownedQty,
  missingQty,
  card: { price_eur: price },
});

describe("theoreticalMinimum", () => {
  it("sums qty x price over owned and missing cards", () => {
    const t = theoreticalMinimum([row(2, 1.5, 2, 0), row(1, 10, 0, 1)]);
    expect(t).toEqual({ total: 13, pricedQty: 3, unpricedQty: 0 });
    expect(formatPriceTotal(t)).toBe("€13.00");
    expect(priceTotalNote(t)).toBeUndefined();
  });

  it("does not treat unpriced cards as €0", () => {
    const t = theoreticalMinimum([row(1, 4, 1, 0), row(3, null, 0, 3)]);
    expect(t).toEqual({ total: 4, pricedQty: 1, unpricedQty: 3 });
    expect(formatPriceTotal(t)).toBe("€4.00+");
    expect(priceTotalNote(t)).toMatch(/3 copies have no price/);
  });
});

describe("priceToComplete", () => {
  it("only counts missing copies", () => {
    const t = priceToComplete([row(2, 1.5, 2, 0), row(3, 10, 1, 2), row(1, null, 0, 1)]);
    expect(t).toEqual({ total: 20, pricedQty: 2, unpricedQty: 1 });
  });
});

describe("deckStatus", () => {
  it("is complete when nothing is missing", () => {
    expect(deckStatus([row(1, 1, 1, 0), row(2, 1, 2, 0)])).toBe("complete");
  });
  it("is in progress when some are owned and some missing", () => {
    expect(deckStatus([row(1, 1, 1, 0), row(2, 1, 0, 2)])).toBe("in-progress");
    expect(deckStatus([row(2, 1, 1, 1)])).toBe("in-progress");
  });
  it("is incomplete when nothing is owned", () => {
    expect(deckStatus([row(1, 1, 0, 1)])).toBe("incomplete");
  });
  it("is null without allocation data", () => {
    expect(deckStatus([row(1, 1)])).toBeNull();
    expect(deckStatus([])).toBeNull();
  });
});

describe("findCommanderEntry", () => {
  const entries = [{ name: "Sol Ring" }, { name: "Esika, God of the Tree // The Prismatic Bridge" }];
  it("matches exact and single-face names", () => {
    expect(findCommanderEntry(entries, "sol ring")).toBe(entries[0]);
    expect(findCommanderEntry(entries, "Esika, God of the Tree")).toBe(entries[1]);
  });
  it("returns undefined when absent", () => {
    expect(findCommanderEntry(entries, null)).toBeUndefined();
    expect(findCommanderEntry(entries, "Nope")).toBeUndefined();
  });
});
