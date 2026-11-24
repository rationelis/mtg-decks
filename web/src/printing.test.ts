import { describe, expect, it } from "vitest";
import { cardForEntry, printingKey } from "./printing";
import type { CardData, CardsIndex } from "./types";

const thranduil: CardData = {
  name: "Thranduil, the Elvenking",
  mana_cost: "{2}{B}{G}{U}",
  mana_value: 5,
  colors: ["B", "G", "U"],
  color_identity: ["B", "G", "U"],
  type_line: "Legendary Creature — Elf Noble",
  oracle_text: "",
  set: "hob",
  set_name: "The Hobbit",
  rarity: "rare",
  image_uri: "plain.jpg",
  scryfall_uri: null,
  price_eur: 0.44,
  price_state: "exact",
  released_at: "2026-08-14",
  cardmarket_id: 1,
  printings: {
    "hob/167": {
      set: "hob",
      set_name: "The Hobbit",
      rarity: "rare",
      image_uri: "plain.jpg",
      scryfall_uri: null,
      price_eur: 0.44,
      price_state: "exact",
      released_at: "2026-08-14",
      cardmarket_id: 1,
    },
    "hob/246": {
      set: "hob",
      set_name: "The Hobbit",
      rarity: "rare",
      image_uri: "borderless.jpg",
      scryfall_uri: null,
      price_eur: 6.8,
      price_state: "exact",
      released_at: "2026-08-14",
      cardmarket_id: 2,
    },
  },
};
const cards: CardsIndex = { "thranduil, the elvenking": thranduil };

describe("printingKey", () => {
  it("lowercases and joins set and number like the Python side", () => {
    expect(printingKey("HOB", "246")).toBe("hob/246");
  });
});

describe("cardForEntry", () => {
  it("uses the pinned printing's art and price for that entry", () => {
    const card = cardForEntry(cards, { name: "Thranduil, the Elvenking", printing: "hob/246" });
    expect(card?.image_uri).toBe("borderless.jpg");
    expect(card?.price_eur).toBe(6.8);
    expect(card?.name).toBe("Thranduil, the Elvenking");
    expect(card?.type_line).toBe(thranduil.type_line);
  });

  it("shows two printings of one card differently", () => {
    const plain = cardForEntry(cards, { name: "Thranduil, the Elvenking", printing: "hob/167" });
    const borderless = cardForEntry(cards, { name: "Thranduil, the Elvenking", printing: "hob/246" });
    expect(plain?.price_eur).not.toBe(borderless?.price_eur);
  });

  it("falls back to the default record when unpinned or the printing is unknown", () => {
    expect(cardForEntry(cards, { name: "Thranduil, the Elvenking" })).toBe(thranduil);
    expect(cardForEntry(cards, { name: "Thranduil, the Elvenking", printing: "hob/999" })).toBe(thranduil);
  });

  it("returns undefined for an unresolved name", () => {
    expect(cardForEntry(cards, { name: "Nope" })).toBeUndefined();
  });
});
