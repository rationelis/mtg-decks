import { describe, expect, it } from "vitest";
import { sortRows } from "./sort";
import type { CardData } from "./types";

function row(name: string, overrides: Partial<CardData> = {}) {
  const card: CardData = {
    name,
    mana_cost: "",
    mana_value: 0,
    colors: [],
    color_identity: [],
    type_line: "",
    oracle_text: "",
    set: "",
    set_name: "",
    rarity: "",
    image_uri: null,
    scryfall_uri: null,
    price_eur: null,
    price_state: "unavailable",
    released_at: null,
    ...overrides,
  };
  return { card };
}

describe("sortRows", () => {
  it("sorts by name ascending/descending", () => {
    const rows = [row("Banana"), row("Apple"), row("Cherry")];
    expect(sortRows(rows, "name-asc").map((r) => r.card.name)).toEqual([
      "Apple",
      "Banana",
      "Cherry",
    ]);
    expect(sortRows(rows, "name-desc").map((r) => r.card.name)).toEqual([
      "Cherry",
      "Banana",
      "Apple",
    ]);
  });

  it("sorts by mana value", () => {
    const rows = [
      row("A", { mana_value: 3 }),
      row("B", { mana_value: 1 }),
      row("C", { mana_value: 2 }),
    ];
    expect(sortRows(rows, "mv-asc").map((r) => r.card.name)).toEqual(["B", "C", "A"]);
    expect(sortRows(rows, "mv-desc").map((r) => r.card.name)).toEqual(["A", "C", "B"]);
  });

  it("sorts unpriced cards (null) to the bottom for price-desc and top for price-asc", () => {
    const rows = [row("A", { price_eur: 5 }), row("B", { price_eur: null }), row("C", { price_eur: 1 })];
    expect(sortRows(rows, "price-desc").map((r) => r.card.name)).toEqual(["A", "C", "B"]);
    expect(sortRows(rows, "price-asc").map((r) => r.card.name)).toEqual(["B", "C", "A"]);
  });

  it("sorts by release date", () => {
    const rows = [
      row("Old", { released_at: "1993-08-05" }),
      row("New", { released_at: "2024-01-01" }),
    ];
    expect(sortRows(rows, "released-desc").map((r) => r.card.name)).toEqual(["New", "Old"]);
    expect(sortRows(rows, "released-asc").map((r) => r.card.name)).toEqual(["Old", "New"]);
  });

  it("does not mutate the input array", () => {
    const rows = [row("B"), row("A")];
    const original = [...rows];
    sortRows(rows, "name-asc");
    expect(rows).toEqual(original);
  });
});
