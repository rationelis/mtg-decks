import { getBulk, getCards, getIndex, getList } from "../data";
import { diffList } from "../diff";
import { h, clear } from "../dom";
import type { IndexEntry } from "../types";

/** A list under decks/ can still really be a wishlist/collection (see
 * IndexEntry.collection), and every list under collections/ is one by
 * kind - either way, a commander isn't relevant for it. */
function isCollectionLike(entry: IndexEntry): boolean {
  return entry.kind === "collection" || entry.collection;
}

export async function renderDecks(root: HTMLElement): Promise<void> {
  clear(root);

  // Index is tiny and loads first, so the page has something useful to
  // show (names, status) before any of the heavier per-list/price data
  // arrives. Everything numeric streams in afterwards.
  const index = await getIndex();

  const active = index.filter((l) => l.status === "active");
  const archived = index.filter((l) => l.status === "archived");

  const activeDecks = active.filter((l) => !isCollectionLike(l));
  const activeCollections = active.filter(isCollectionLike);
  const archivedDecks = archived.filter((l) => !isCollectionLike(l));
  const archivedCollections = archived.filter(isCollectionLike);

  const rowsById = new Map<string, HTMLElement>();

  const sections: (HTMLElement | string)[] = [
    h(
      "div",
      { class: "list-header" },
      h("a", { href: "#/", class: "back-link" }, "← Bulk"),
      h("h1", {}, "Decks & Collections"),
    ),
  ];

  if (activeDecks.length > 0) {
    sections.push(h("h2", { class: "section-header" }, "Decks"));
    sections.push(buildTable(activeDecks, rowsById, { showCommander: true, nameLabel: "Deck" }));
  }

  if (activeCollections.length > 0) {
    sections.push(h("h2", { class: "section-header" }, "Collections"));
    sections.push(
      buildTable(activeCollections, rowsById, { showCommander: false, nameLabel: "Collection" }),
    );
  }

  if (archivedDecks.length > 0) {
    sections.push(archivedDetails("archived deck", archivedDecks));
  }
  if (archivedCollections.length > 0) {
    sections.push(archivedDetails("archived collection", archivedCollections));
  }

  root.append(...sections);

  // Progressive enhancement: fill in owned/missing/price once the
  // (small) shared data files and each list's entries have loaded.
  void fillInStats(active, rowsById);
}

function archivedDetails(label: string, entries: IndexEntry[]): HTMLElement {
  const plural = entries.length === 1 ? label : `${label}s`;
  return h(
    "details",
    { class: "archived-section" },
    h("summary", {}, `${entries.length} ${plural}`),
    h(
      "ul",
      {},
      ...entries.map((entry) =>
        h("li", {}, h("a", { href: `#/list/${entry.kind}/${entry.id}` }, entry.name)),
      ),
    ),
  );
}

function buildTable(
  entries: IndexEntry[],
  rowsById: Map<string, HTMLElement>,
  options: { showCommander: boolean; nameLabel: string },
): HTMLElement {
  const headerCells = [h("th", {}, options.nameLabel)];
  if (options.showCommander) headerCells.push(h("th", {}, "Commander"));
  headerCells.push(
    h("th", {}, "Owned"),
    h("th", {}, "Missing"),
    h("th", {}, "Price to complete"),
    h("th", {}, ""),
  );

  const tbody = h("tbody");
  for (const entry of entries) {
    const row = renderSkeletonRow(entry, options);
    rowsById.set(`${entry.kind}-${entry.id}`, row);
    tbody.append(row);
  }

  return h(
    "table",
    { class: "deck-table" },
    h("thead", {}, h("tr", {}, ...headerCells)),
    tbody,
  );
}

function renderSkeletonRow(entry: IndexEntry, options: { showCommander: boolean }): HTMLElement {
  const cells = [
    h(
      "td",
      { class: "cell-deck-name" },
      h("a", { href: `#/list/${entry.kind}/${entry.id}` }, entry.name),
      entry.proxy && h("span", { class: "badge badge-proxy" }, "proxy"),
      entry.collection && h("span", { class: "badge badge-collection" }, "collection"),
    ),
  ];
  if (options.showCommander) {
    cells.push(h("td", { class: "cell-commander" }, entry.commander ?? "—"));
  }
  cells.push(
    h("td", { class: "cell-owned" }, "…"),
    h("td", { class: "cell-missing" }, "…"),
    h("td", { class: "cell-price" }, "…"),
    h("td", { class: "cell-total" }, `${entry.entryCount} unique / ${entry.totalQty} total`),
  );
  return h("tr", {}, ...cells);
}

async function fillInStats(
  entries: IndexEntry[],
  rowsById: Map<string, HTMLElement>,
): Promise<void> {
  const [cards, bulk] = await Promise.all([getCards(), getBulk()]);

  await Promise.all(
    entries.map(async (entry) => {
      const row = rowsById.get(`${entry.kind}-${entry.id}`);
      if (!row) return;

      const list = await getList(entry.kind, entry.id);
      const diff = diffList(list, bulk, cards);

      const ownedCount = diff.reduce((sum, r) => sum + r.ownedQty, 0);
      const missingCount = diff.reduce((sum, r) => sum + r.missingQty, 0);
      const missingPrice = diff.reduce(
        (sum, r) => sum + (r.missingQty > 0 ? (r.card.price_eur ?? 0) * r.missingQty : 0),
        0,
      );

      const ownedCell = row.querySelector(".cell-owned");
      const missingCell = row.querySelector(".cell-missing");
      const priceCell = row.querySelector(".cell-price");
      if (ownedCell) ownedCell.textContent = String(ownedCount);
      if (missingCell) {
        missingCell.textContent = String(missingCount);
        missingCell.classList.toggle("missing", missingCount > 0);
      }
      if (priceCell) priceCell.textContent = `€${missingPrice.toFixed(2)}`;
    }),
  );
}
