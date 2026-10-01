import { createFilterBar } from "../components/filterBar";
import { renderCardView, type CardRow, type ViewMode } from "../components/cardView";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getBulk, getCards, getMeta } from "../data";
import { h, clear } from "../dom";
import { filterFromParams, filterToParams, matchesFilter, type FilterState } from "../filters";
import { normalizeName } from "../normalize";
import { priceNote } from "../priceNote";
import { replaceQueryParams } from "../router";
import { sortRows, type SortKey } from "../sort";
import type { CardData, CardList, CardsIndex } from "../types";

const UNRESOLVED_PLACEHOLDER: Omit<CardData, "name"> = {
  mana_cost: "",
  mana_value: 0,
  colors: [],
  color_identity: [],
  type_line: "",
  oracle_text: "",
  set: "",
  set_name: "",
  rarity: "",
  image_uri: null,
  scryfall_uri: null,
  price_eur: null,
  price_state: "unavailable",
  released_at: null,
};

/** Bulk has no ownership columns of its own - it IS the inventory - so
 * its rows are just a straight (name, qty, card) projection with no
 * diffing needed. */
function bulkRows(bulk: CardList, cards: CardsIndex): CardRow[] {
  return bulk.entries.map((e) => ({
    name: e.name,
    qty: e.qty,
    card: cards[normalizeName(e.name)] ?? { name: e.name, ...UNRESOLVED_PLACEHOLDER },
  }));
}

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
