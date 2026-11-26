import { describe, expect, it } from "vitest";
import type { CardRow } from "./components/cardView";
import {
  collectorNumberDigits,
  csvField,
  csvFilename,
  formatCsv,
  singleSetName,
  slugify,
  timestamp,
} from "./components/csvExport";
import type { CardData } from "./types";

function row(name: string, overrides: Partial<CardRow> = {}, card: Partial<CardData> = {}): CardRow {
  return {
    name,
    qty: 1,
    card: {
      name,
      set_name: "Final Fantasy",
      collector_number: "384",
      cardmarket_id: 824280,
      price_eur: 6.6,
      ...card,
    } as CardData,
    ...overrides,
  };
}

describe("csvField", () => {
  it("leaves plain text alone and quotes commas, quotes and newlines", () => {
    expect(csvField("Sol Ring")).toBe("Sol Ring");
    expect(csvField("Yuyan Archers, Elite")).toBe('"Yuyan Archers, Elite"');
    expect(csvField('say "hi"')).toBe('"say ""hi"""');
    expect(csvField("a\nb")).toBe('"a\nb"');
  });
});

describe("collectorNumberDigits", () => {
  it("reduces a collector number to just the number", () => {
    expect(collectorNumberDigits("039")).toBe("39");
    expect(collectorNumberDigits("292")).toBe("292");
    expect(collectorNumberDigits("KTK-234")).toBe("234");
    expect(collectorNumberDigits("234★")).toBe("234");
    expect(collectorNumberDigits("12a")).toBe("12");
    expect(collectorNumberDigits("")).toBe("");
    expect(collectorNumberDigits("★")).toBe("");
  });
});

describe("formatCsv", () => {
  it("writes Cardmarket's import header and one line per card", () => {
    const csv = formatCsv([
      { row: row("Zenos yae Galvus // Shinryu, Transcendent Rival", { foil: true }), qty: 1 },
    ]);
    expect(csv).toBe(
      "cardmarketId,quantity,name,set,cn,condition,language,isPlayset,isFirstEd,isReverseHolo,isSigned,price,comment,finishType\r\n" +
        '824280,1,"Zenos yae Galvus // Shinryu, Transcendent Rival",Final Fantasy,384,NM,English,false,false,true,false,,,Foil\r\n',
    );
  });

  it("marks non-foil, always NM/English, leaves price empty, sorts by name, skips qty 0", () => {
    const csv = formatCsv([
      { row: row("Zoanthrope", {}, { cardmarket_id: null, collector_number: "039" }), qty: 2 },
      { row: row("Aang's Journey"), qty: 1 },
      { row: row("Skipped"), qty: 0 },
    ]);
    const lines = csv.trim().split("\r\n");
    expect(lines).toHaveLength(3);
    expect(lines[1]).toBe("824280,1,Aang's Journey,Final Fantasy,384,NM,English,false,false,false,false,,,Regular");
    expect(lines[2]).toBe(",2,Zoanthrope,Final Fantasy,39,NM,English,false,false,false,false,,,Regular");
  });
});

describe("filenames", () => {
  it("builds a sortable local timestamp", () => {
    expect(timestamp(new Date(2026, 10, 26, 14, 3, 5))).toBe("2026-11-26_140305");
  });

  it("slugifies scope names", () => {
    expect(slugify("Atraxa: Praetors' Voice!")).toBe("atraxa-praetors-voice");
    expect(slugify("Lim-Dûl's Vault")).toBe("lim-dul-s-vault");
    expect(slugify("???")).toBe("export");
  });

  it("combines prefix, scope and timestamp", () => {
    expect(csvFilename("Bulk", new Date(2026, 10, 26, 14, 3, 5))).toBe(
      "mtg-bulk-2026-11-26_140305.csv",
    );
  });

  it("puts the set name between the scope and the timestamp", () => {
    expect(csvFilename("Bulk", new Date(2026, 10, 26, 14, 3, 5), "Final Fantasy")).toBe(
      "mtg-bulk-final-fantasy-2026-11-26_140305.csv",
    );
  });
});

describe("singleSetName", () => {
  it("returns the set when every exported card shares one", () => {
    const rows = [
      { row: row("A"), qty: 1 },
      { row: row("B"), qty: 2 },
    ];
    expect(singleSetName(rows)).toBe("Final Fantasy");
  });

  it("returns undefined for a mix of sets, ignoring zero-quantity rows", () => {
    const mixed = [
      { row: row("A"), qty: 1 },
      { row: row("B", {}, { set_name: "Warhammer 40,000" }), qty: 1 },
    ];
    expect(singleSetName(mixed)).toBeUndefined();
    const withSkipped = [
      { row: row("A"), qty: 1 },
      { row: row("B", {}, { set_name: "Warhammer 40,000" }), qty: 0 },
    ];
    expect(singleSetName(withSkipped)).toBe("Final Fantasy");
  });

  it("returns undefined for an empty or unresolved set name", () => {
    expect(singleSetName([])).toBeUndefined();
    expect(singleSetName([{ row: row("A", {}, { set_name: "" }), qty: 1 }])).toBeUndefined();
  });
});
