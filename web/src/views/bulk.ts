import { createFilterBar } from "../components/filterBar";
import { renderCardView, type ViewMode } from "../components/cardView";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getBulk, getCards, getMeta } from "../data";
import { bulkRows } from "../diff";
import { h, clear } from "../dom";
import { matchesFilter, type FilterState } from "../filters";
import { priceNote } from "../priceNote";
import { sortRows, type SortKey } from "../sort";

export async function renderBulk(root: HTMLElement): Promise<void> {
  clear(root);
  root.append(h("h1", {}, "Bulk"), h("p", { class: "loading" }, "Loading bulk…"));

  const [bulk, cards, meta] = await Promise.all([getBulk(), getCards(), getMeta()]);
  const rows = bulkRows(bulk, cards);

  clear(root);

  const resultsContainer = h("div", { class: "results" });
  let sortKey: SortKey = "name-asc";
  let currentFilter: FilterState | null = null;
  let mode: ViewMode = "gallery";

  function render(): void {
    const filtered = currentFilter
      ? rows.filter((r) => matchesFilter(r.card, currentFilter!))
      : rows;
    renderCardView(resultsContainer, sortRows(filtered, sortKey), { mode });
  }

  const filterBar = createFilterBar((state) => {
    currentFilter = state;
    render();
  });
  const sortSelect = createSortSelect((key) => {
    sortKey = key;
    render();
  }) as HTMLSelectElement;
  const viewToggle = createViewToggle(mode, (newMode) => {
    mode = newMode;
    render();
  });

  const priciestButton = createPriciestButton(sortSelect, (key) => {
    sortKey = key;
    render();
  });

  const totalQty = bulk.entries.reduce((sum, e) => sum + e.qty, 0);
  const pricedRows = rows.filter((r) => r.card.price_eur != null);
  const totalValue = pricedRows.reduce((sum, r) => sum + (r.card.price_eur ?? 0) * r.qty, 0);

  root.append(
    h("h1", {}, "Bulk"),
    h("p", { class: "subtitle" }, `${bulk.entries.length} unique cards, ${totalQty} total`),
    h(
      "p",
      { class: "subtitle" },
      `💶 Estimated value: €${totalValue.toFixed(2)} (${pricedRows.length}/${bulk.entries.length} priced)`,
    ),
    h("p", { class: "price-note" }, priceNote(meta)),
    h(
      "div",
      { class: "toolbar" },
      filterBar,
      h("div", { class: "toolbar-actions" }, sortSelect, priciestButton, viewToggle),
    ),
    resultsContainer,
  );

  render();
}
