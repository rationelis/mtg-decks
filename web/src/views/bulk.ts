import { createFilterBar } from "../components/filterBar";
import { renderCardView, type ViewMode } from "../components/cardView";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getBulk, getCards, getMeta } from "../data";
import { bulkRows } from "../diff";
import { h, clear } from "../dom";
import { filterFromParams, filterToParams, matchesFilter, type FilterState } from "../filters";
import { priceNote } from "../priceNote";
import { replaceQueryParams } from "../router";
import { sortRows, type SortKey } from "../sort";

export async function renderBulk(root: HTMLElement, params: URLSearchParams): Promise<void> {
  clear(root);
  root.append(h("h1", {}, "Bulk"), h("p", { class: "loading" }, "Loading bulk…"));

  const [bulk, cards, meta] = await Promise.all([getBulk(), getCards(), getMeta()]);
  const rows = bulkRows(bulk, cards);

  clear(root);

  const resultsContainer = h("div", { class: "results" });
  let sortKey: SortKey = "name-asc";
  let currentFilter: FilterState = filterFromParams(params);
  let mode: ViewMode = "gallery";

  function render(): void {
    const filtered = rows.filter((r) => matchesFilter(r.card, currentFilter));
    renderCardView(resultsContainer, sortRows(filtered, sortKey), { mode });
  }

  const filterBar = createFilterBar(
    rows.map((r) => r.card),
    (state) => {
      currentFilter = state;
      replaceQueryParams(filterToParams(state));
      render();
    },
    currentFilter,
  );
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

  root.append(
    h("h1", {}, "Bulk"),
    h("p", { class: "subtitle" }, `${bulk.entries.length} unique cards, ${totalQty} total`),
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
