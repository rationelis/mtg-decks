import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { Allocation, CardData, ListEntry, Usage } from "./types";

// Mirrors scripts/build/tests/test_emit_shape.py - both sides load the
// same fixture files under scripts/build/tests/fixtures/ so a field
// added/renamed/removed on either side (Python's emit.py, or these
// TypeScript interfaces) is caught here instead of drifting silently
// (see REFACTOR.md §8.3).
function loadFixture(name: string): string[] {
  const url = new URL(`../../scripts/build/tests/fixtures/${name}`, import.meta.url);
  return JSON.parse(readFileSync(url, "utf-8"));
}

describe("CardData shape matches the shared Python/TypeScript fixture", () => {
  it("has exactly the fields scripts/build/emit.py writes", () => {
    // A full object literal typed as CardData: TypeScript's excess-
    // property + missing-property checks mean this assignment fails to
    // compile if CardData's fields ever drift from this exact set.
    const sample: CardData = {
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
    };
    expect(Object.keys(sample).sort()).toEqual(loadFixture("card_json_fields.json").sort());
  });
});

describe("ListEntry shape matches the shared fixture", () => {
  it("has exactly the fields emit.py writes when ownership is present", () => {
    const sample: Required<ListEntry> = {
      name: "Sol Ring",
      qty: 1,
      ownedQty: 1,
      missingQty: 0,
    };
    expect(Object.keys(sample).sort()).toEqual(
      loadFixture("list_entry_json_fields.json").sort(),
    );
  });
});

describe("Usage/Allocation shapes match the shared fixture", () => {
  it("Usage has exactly the fields emit.py writes", () => {
    const sample: Usage = { owned: 2, available: 0, allocations: [] };
    expect(Object.keys(sample).sort()).toEqual(loadFixture("usage_json_fields.json").sort());
  });

  it("Allocation has exactly the fields emit.py writes", () => {
    const sample: Allocation = { listId: "a", listName: "Deck A", quantity: 1 };
    expect(Object.keys(sample).sort()).toEqual(
      loadFixture("allocation_json_fields.json").sort(),
    );
  });
});
