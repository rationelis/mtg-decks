import { h, clear } from "../dom";
import { renderIncrementally } from "../incremental";
import type { CardData } from "../types";

/** One row of card data to render, shared by the bulk browser and the
 * per-deck list view. `ownedQty`/`missingQty` are only present when a row
 * came from a diff against bulk. */
export interface CardRow {
  name: string;
  qty: number;
  card: CardData;
  ownedQty?: number;
  missingQty?: number;
}

export type ViewMode = "gallery" | "list";

export interface CardViewOptions {
  mode: ViewMode;
  showDiffColumns?: boolean;
}

/** Renders `rows` as either an image gallery or a spacious table, sharing
 * one incremental-batch-rendering strategy so neither mode ever blocks
 * the main thread on a big bulk collection. */
export function renderCardView(
  container: HTMLElement,
  rows: CardRow[],
  options: CardViewOptions,
): void {
  clear(container);
  container.append(
    h("p", { class: "result-count" }, `${rows.length} card${rows.length === 1 ? "" : "s"}`),
  );

  if (options.mode === "gallery") {
    renderGallery(container, rows, !!options.showDiffColumns);
  } else {
    renderTable(container, rows, !!options.showDiffColumns);
  }
}

function diffBadge(row: CardRow): HTMLElement | false {
  if (row.ownedQty === undefined || row.missingQty === undefined) return false;
  if (row.missingQty > 0) return false; // the not-owned overlay communicates this instead
  return h("span", { class: "diff-badge owned" }, "owned");
}

/** Hearthstone-style "you don't own this" treatment: a translucent,
 * blue-grey shaded overlay with a warning icon, layered over the card
 * image whenever any copies are missing. */
function notOwnedOverlay(row: CardRow): HTMLElement | false {
  if (row.missingQty === undefined || row.missingQty <= 0) return false;
  const label = row.missingQty > 1 ? `Missing ×${row.missingQty}` : "Not owned";
  return h(
    "div",
    { class: "not-owned-overlay", title: `${row.missingQty} missing` },
    h("span", { class: "not-owned-icon" }, "⚠"),
    h("span", { class: "not-owned-label" }, label),
  );
}

/** Where a card's image should link to: its Scryfall page when known,
 * falling back to the raw image (e.g. for older cached data resolved
 * before scryfall_uri was tracked). null only when there's no image at
 * all to link to. */
function cardLinkHref(card: CardData): string | null {
  return card.scryfall_uri || card.image_uri || null;
}

/** An <img> for a card, optionally wrapped in a link to its Scryfall
 * page - shared by gallery and list mode so there's one clickable-image
 * implementation. */
function cardImage(card: CardData, linkClass?: string): HTMLElement {
  if (!card.image_uri) {
    return h("div", { class: "no-image-placeholder", title: card.oracle_text || card.name }, card.name);
  }
  const img = h("img", {
    src: card.image_uri,
    loading: "lazy",
    alt: card.name,
    title: card.oracle_text || card.name,
  });
  const href = cardLinkHref(card);
  return href
    ? h("a", { href, target: "_blank", rel: "noopener", class: linkClass }, img)
    : img;
}

// --- Gallery mode ----------------------------------------------------------

function renderGallery(container: HTMLElement, rows: CardRow[], showDiff: boolean): void {
  const grid = h("div", { class: "gallery-grid" });
  container.append(grid);
  renderIncrementally(grid, rows, (row) => renderGalleryCard(row, showDiff), {
    batchSize: 60,
    sentinelTag: "div",
  });
}

function renderGalleryCard(row: CardRow, showDiff: boolean): HTMLElement {
  const card = row.card;
  const priceLabel = card.price_eur != null ? `€${card.price_eur.toFixed(2)}` : "—";
  const missing = showDiff && (row.missingQty ?? 0) > 0;

  return h(
    "figure",
    { class: missing ? "gallery-card gallery-card-missing" : "gallery-card" },
    h(
      "div",
      { class: "gallery-card-image" },
      cardImage(card, "gallery-card-link"),
      showDiff && notOwnedOverlay(row),
      row.qty > 1 && h("span", { class: "qty-badge" }, `×${row.qty}`),
      showDiff && diffBadge(row),
      !card.resolved && h("span", { class: "unresolved-badge", title: "Unresolved card name" }, "⚠"),
    ),
    h(
      "figcaption",
      {},
      h("span", { class: "gallery-card-name" }, card.name),
      h("span", { class: "gallery-card-meta" }, card.type_line || "—"),
      h("span", { class: "gallery-card-price" }, priceLabel),
    ),
  );
}

// --- List mode (a spacious table, big thumbnails) ---------------------------

function renderTable(container: HTMLElement, rows: CardRow[], showDiff: boolean): void {
  const table = h(
    "table",
    { class: "card-table" },
    h(
      "thead",
      {},
      h(
        "tr",
        {},
        h("th", { class: "col-image" }, ""),
        h("th", { class: "col-qty" }, "Qty"),
        showDiff && h("th", { class: "col-owned" }, "Owned"),
        showDiff && h("th", { class: "col-missing" }, "Missing"),
        h("th", { class: "col-name" }, "Name"),
        h("th", { class: "col-mana" }, "Mana"),
        h("th", { class: "col-mv" }, "MV"),
        h("th", { class: "col-type" }, "Type"),
        h("th", { class: "col-rarity" }, "Rarity"),
        h("th", { class: "col-set" }, "Set"),
        h("th", { class: "col-price" }, "Price"),
      ),
    ),
  );
  const tbody = h("tbody");
  table.append(tbody);
  container.append(table);

  renderIncrementally(tbody, rows, (row) => renderTableRow(row, showDiff), {
    batchSize: 80,
    sentinelTag: "tr",
    sentinelColspan: showDiff ? 11 : 9,
  });
}

function renderTableRow(row: CardRow, showDiff: boolean): HTMLElement {
  const card = row.card;
  const missing = showDiff && (row.missingQty ?? 0) > 0;
  const cells: (HTMLElement | false)[] = [
    h("td", { class: missing ? "cell-image cell-image-missing" : "cell-image" }, cardImage(card)),
    h("td", { class: "cell-qty" }, String(row.qty)),
    showDiff && h("td", { class: "cell-owned" }, String(row.ownedQty ?? 0)),
    showDiff &&
      h(
        "td",
        { class: (row.missingQty ?? 0) > 0 ? "cell-missing missing" : "cell-missing" },
        String(row.missingQty ?? 0),
      ),
    h(
      "td",
      { class: "cell-name" },
      card.name,
      missing &&
        h(
          "span",
          { class: "not-owned-badge", title: `${row.missingQty} missing` },
          " ⚠ not owned",
        ),
      !card.resolved && h("span", { class: "unresolved-badge", title: "Unresolved card name" }, " ⚠"),
    ),
    h("td", { class: "cell-mana" }, card.mana_cost || "—"),
    h("td", { class: "cell-mv" }, card.resolved ? String(card.mana_value) : "—"),
    h("td", { class: "cell-type" }, card.type_line || "—"),
    h("td", { class: "cell-rarity" }, card.rarity || "—"),
    h("td", { class: "cell-set" }, card.set ? card.set.toUpperCase() : "—"),
    h("td", { class: "cell-price" }, card.price_eur != null ? `€${card.price_eur.toFixed(2)}` : "—"),
  ];
  const rowClasses = [!card.resolved && "unresolved-row", missing && "row-missing"]
    .filter(Boolean)
    .join(" ");
  return h("tr", { class: rowClasses || undefined }, ...cells);
}
