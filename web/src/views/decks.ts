import { getBulk, getCards, getIndex, getList } from "../data";
import { diffList } from "../diff";
import { h, clear } from "../dom";
import type { IndexEntry } from "../types";

export async function renderDecks(root: HTMLElement): Promise<void> {
  clear(root);

  // Index is tiny and loads first, so the page has something useful to
  // show (names, status) before any of the heavier per-list/price data
  // arrives. Everything numeric streams in afterwards.
  const index = await getIndex();

  const activeLists = index.filter((l) => l.status === "active");
  const archivedLists = index.filter((l) => l.status === "archived");

  const rowsById = new Map<string, HTMLElement>();

  const table = h(
    "table",
    { class: "deck-table" },
    h(
      "thead",
      {},
      h(
        "tr",
        {},
        h("th", {}, "Deck / collection"),
        h("th", {}, "Commander"),
        h("th", {}, "Owned"),
        h("th", {}, "Missing"),
        h("th", {}, "Price to complete"),
        h("th", {}, ""),
      ),
    ),
  );
  const tbody = h("tbody");
  table.append(tbody);

  for (const entry of activeLists) {
    const row = renderSkeletonRow(entry);
    rowsById.set(`${entry.kind}-${entry.id}`, row);
    tbody.append(row);
  }

  const sections: (HTMLElement | string)[] = [
    h(
      "div",
      { class: "list-header" },
      h("a", { href: "#/", class: "back-link" }, "← Bulk"),
      h("h1", {}, "Decks & Collections"),
    ),
    table,
  ];

  if (archivedLists.length > 0) {
    sections.push(
      h(
        "details",
        { class: "archived-section" },
        h("summary", {}, `${archivedLists.length} archived`),
        h(
          "ul",
          {},
          ...archivedLists.map((entry) =>
            h("li", {}, h("a", { href: `#/list/${entry.kind}/${entry.id}` }, entry.name)),
          ),
        ),
      ),
    );
  }

  root.append(...sections);

  // Progressive enhancement: fill in owned/missing/price once the
  // (small) shared data files and each list's entries have loaded.
  void fillInStats(activeLists, rowsById);
}

function renderSkeletonRow(entry: IndexEntry): HTMLElement {
  return h(
    "tr",
    {},
    h(
      "td",
      { class: "cell-deck-name" },
      h("a", { href: `#/list/${entry.kind}/${entry.id}` }, entry.name),
      entry.proxy && h("span", { class: "badge badge-proxy" }, "proxy"),
      entry.collection && h("span", { class: "badge badge-collection" }, "collection"),
    ),
    h("td", { class: "cell-commander" }, entry.commander ?? "—"),
    h("td", { class: "cell-owned" }, "…"),
    h("td", { class: "cell-missing" }, "…"),
    h("td", { class: "cell-price" }, "…"),
    h("td", { class: "cell-total" }, `${entry.entryCount} unique / ${entry.totalQty} total`),
  );
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
