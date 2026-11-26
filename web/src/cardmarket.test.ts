import { describe, expect, it } from "vitest";
import { cardmarketUrl } from "./cardmarket";
import type { CardData } from "./types";

function card(overrides: Partial<CardData>): CardData {
  return {
    name: "Zenos yae Galvus // Shinryu, Transcendent Rival",
    mana_cost: "",
    mana_value: 5,
    colors: [],
    color_identity: [],
    type_line: "",
    oracle_text: "",
    set: "fin",
    set_name: "Final Fantasy",
    collector_number: "",
    rarity: "rare",
    image_uri: null,
    scryfall_uri: null,
    price_eur: null,
    price_state: "unavailable",
    released_at: null,
    cardmarket_id: null,
    printings: {},
    ...overrides,
  };
}

describe("cardmarketUrl", () => {
  it("links to the exact product by id, filtered to Netherlands sellers", () => {
    expect(cardmarketUrl(card({ cardmarket_id: 824280 }), false)).toBe(
      "https://www.cardmarket.com/en/Magic/Products?idProduct=824280&sellerCountry=23",
    );
  });

  it("filters to foil offers for a foil copy", () => {
    expect(cardmarketUrl(card({ cardmarket_id: 824280 }), true)).toContain("isFoil=Y");
  });

  it("falls back to a name search when the printing has no product id", () => {
    const url = cardmarketUrl(card({ name: "Sol Ring" }), true);
    expect(url).toBe("https://www.cardmarket.com/en/Magic/Products/Search?searchString=Sol+Ring");
  });
});
