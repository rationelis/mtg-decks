import { describe, expect, it } from "vitest";
import {
  emptyFilter,
  filterFromParams,
  filterToParams,
  isFilterEmpty,
  matchesFilter,
} from "./filters";
import type { CardData } from "./types";

function card(overrides: Partial<CardData> = {}): CardData {
  return {
    name: "Sol Ring",
    mana_cost: "{1}",
    mana_value: 1,
    colors: [],
    color_identity: [],
    type_line: "Artifact",
    oracle_text: "{T}: Add {C}{C}.",
    set: "cmm",
    set_name: "Commander Masters",
    rarity: "uncommon",
    image_uri: null,
    scryfall_uri: null,
    price_eur: 1.2,
    price_state: "exact",
    released_at: "2023-08-04",
    ...overrides,
  };
}

describe("matchesFilter", () => {
  it("matches everything against an empty filter", () => {
    expect(matchesFilter(card(), emptyFilter())).toBe(true);
  });

  it("filters by search text against name and oracle text", () => {
    const f = { ...emptyFilter(), search: "add {c}" };
    expect(matchesFilter(card(), f)).toBe(true);
    expect(matchesFilter(card({ oracle_text: "unrelated" }), f)).toBe(false);
  });

  it("filters by exact color identity match, not subset", () => {
    const f = { ...emptyFilter(), colors: new Set(["U", "B"]) };
    expect(matchesFilter(card({ colors: ["U", "B"] }), f)).toBe(true);
    expect(matchesFilter(card({ colors: ["U"] }), f)).toBe(false);
    expect(matchesFilter(card({ colors: ["U", "B", "R"] }), f)).toBe(false);
  });

  it("treats an empty colors list as colorless (C)", () => {
    const f = { ...emptyFilter(), colors: new Set(["C"]) };
    expect(matchesFilter(card({ colors: [] }), f)).toBe(true);
  });

  it("filters by mana value range", () => {
    const f = { ...emptyFilter(), manaMin: 2, manaMax: 4 };
    expect(matchesFilter(card({ mana_value: 3 }), f)).toBe(true);
    expect(matchesFilter(card({ mana_value: 1 }), f)).toBe(false);
    expect(matchesFilter(card({ mana_value: 5 }), f)).toBe(false);
  });

  it("filters by type substring, case-insensitively", () => {
    const f = { ...emptyFilter(), type: "artifact" };
    expect(matchesFilter(card({ type_line: "Legendary Artifact" }), f)).toBe(true);
    expect(matchesFilter(card({ type_line: "Creature" }), f)).toBe(false);
  });

  it("filters by rarity exactly", () => {
    const f = { ...emptyFilter(), rarity: "rare" };
    expect(matchesFilter(card({ rarity: "rare" }), f)).toBe(true);
    expect(matchesFilter(card({ rarity: "uncommon" }), f)).toBe(false);
  });

  it("filters by set code exactly", () => {
    const f = { ...emptyFilter(), set: "cmm" };
    expect(matchesFilter(card({ set: "cmm" }), f)).toBe(true);
    expect(matchesFilter(card({ set: "lea" }), f)).toBe(false);
  });

  it("filters by price range, excluding unpriced cards", () => {
    const f = { ...emptyFilter(), priceMin: 1, priceMax: 5 };
    expect(matchesFilter(card({ price_eur: 2 }), f)).toBe(true);
    expect(matchesFilter(card({ price_eur: null }), f)).toBe(false);
    expect(matchesFilter(card({ price_eur: 10 }), f)).toBe(false);
  });
});

describe("filterToParams / filterFromParams", () => {
  it("round-trips a non-empty filter through URL params", () => {
    const f = {
      ...emptyFilter(),
      search: "bolt",
      colors: new Set(["R"]),
      manaMin: 1,
      manaMax: 3,
      type: "instant",
      rarity: "common",
      set: "lea",
      priceMin: 0,
      priceMax: 2,
    };
    const roundTripped = filterFromParams(filterToParams(f));
    expect(roundTripped.search).toBe(f.search);
    expect([...roundTripped.colors]).toEqual([...f.colors]);
    expect(roundTripped.manaMin).toBe(f.manaMin);
    expect(roundTripped.manaMax).toBe(f.manaMax);
    expect(roundTripped.type).toBe(f.type);
    expect(roundTripped.rarity).toBe(f.rarity);
    expect(roundTripped.set).toBe(f.set);
    expect(roundTripped.priceMin).toBe(f.priceMin);
    expect(roundTripped.priceMax).toBe(f.priceMax);
  });

  it("produces empty params for an empty filter", () => {
    expect(filterToParams(emptyFilter()).toString()).toBe("");
  });

  it("isFilterEmpty agrees with an empty filter", () => {
    expect(isFilterEmpty(emptyFilter())).toBe(true);
    expect(isFilterEmpty({ ...emptyFilter(), search: "x" })).toBe(false);
  });
});
