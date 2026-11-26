import { h } from "../dom";
import type { CardRow } from "./cardView";

/** Columns of Cardmarket's CSV import format, in order. */
export const CSV_COLUMNS = [
  "cardmarketId",
  "quantity",
  "name",
  "set",
  "cn",
  "condition",
  "language",
  "isPlayset",
  "isFirstEd",
  "isReverseHolo",
  "isSigned",
  "price",
  "comment",
  "finishType",
] as const;

/** Nothing in this project tracks condition or language, so every exported
 * copy is declared Near Mint / English. */
const CONDITION = "NM";
const LANGUAGE = "English";

/** One exported line: a card row plus the quantity to export for it (a
 * deck's "Missing" tab exports the missing count, not the deck qty). */
export interface CsvRow {
  row: CardRow;
  qty: number;
}

/** RFC 4180 quoting: wrap in quotes only when needed, doubling any
 * embedded quotes. */
export function csvField(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

/** Cardmarket's "cn" is the collector number reduced to just the number:
 * "039" -> "39". Anything around the digits (a "KTK-" The List prefix, a
 * "★" or letter suffix) is dropped; a number with no digits gives "". */
export function collectorNumberDigits(cn: string): string {
  const tail = cn.split("-").pop() ?? "";
  const digits = tail.match(/\d+/)?.[0];
  return digits === undefined ? "" : String(Number(digits));
}

/** Renders `rows` as Cardmarket-import CSV text (CRLF line endings, header
 * first), sorted by name, skipping zero-quantity rows. `isReverseHolo` and
 * `finishType` both carry the foil flag (Cardmarket's Magic foil is "Foil"
 * vs "Regular"). `price` is deliberately left empty -
 * Cardmarket's import tool does the pricing - as is `comment`. A card with
 * no Cardmarket id gets an empty `cardmarketId`; the importer then matches
 * on name and set. */
export function formatCsv(rows: CsvRow[]): string {
  const lines = rows
    .filter((r) => r.qty > 0)
    .sort((a, b) => cardName(a.row).localeCompare(cardName(b.row)))
    .map(({ row, qty }) =>
      [
        row.card.cardmarket_id == null ? "" : String(row.card.cardmarket_id),
        String(qty),
        cardName(row),
        row.card.set_name,
        collectorNumberDigits(row.card.collector_number),
        CONDITION,
        LANGUAGE,
        "false", // isPlayset
        "false", // isFirstEd
        row.foil ? "true" : "false", // isReverseHolo
        "false", // isSigned
        "", // price
        "", // comment
        row.foil ? "Foil" : "Regular", // finishType
      ]
        .map(csvField)
        .join(","),
    );
  return [CSV_COLUMNS.join(","), ...lines].join("\r\n") + "\r\n";
}

function cardName(row: CardRow): string {
  return row.card.name || row.name;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** Local-time stamp like "2026-11-26_143005", sortable and filename-safe. */
export function timestamp(date: Date = new Date()): string {
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
  );
}

/** "My Deck: Atraxa!" -> "my-deck-atraxa" */
export function slugify(text: string): string {
  return (
    text
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "export"
  );
}

export function csvFilename(scope: string, date: Date = new Date(), setName?: string): string {
  const parts = ["mtg", slugify(scope), ...(setName ? [slugify(setName)] : []), timestamp(date)];
  return `${parts.join("-")}.csv`;
}

/** The set name shared by every exported card, or undefined when they come
 * from several sets (or none) - so a set-filtered export is named after
 * its set, and a mixed one isn't misleadingly labelled. */
export function singleSetName(rows: CsvRow[]): string | undefined {
  const names = new Set(
    rows.filter((r) => r.qty > 0).map((r) => r.row.card.set_name),
  );
  const [only] = names;
  return names.size === 1 && only ? only : undefined;
}

function download(filename: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const link = h("a", { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** A button that downloads whatever `getRows` returns *at click time* as a
 * timestamped CSV. `getScope` names the file (e.g. "bulk" or a deck name
 * plus tab). */
export function createCsvButton(getRows: () => CsvRow[], getScope: () => string): HTMLElement {
  return h(
    "button",
    {
      type: "button",
      class: "export-button",
      title: "Download the cards currently shown as a CSV file",
      onclick: () => {
        const rows = getRows();
        if (!rows.some((r) => r.qty > 0)) return;
        download(csvFilename(getScope(), new Date(), singleSetName(rows)), formatCsv(rows));
      },
    },
    "⬇ Export CSV",
  );
}
