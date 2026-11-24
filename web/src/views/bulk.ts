import { createFilterBar } from "../components/filterBar";
import { renderCardView, type CardRow, type ViewMode } from "../components/cardView";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getBulk, getCards, getMeta, getUsage } from "../data";
import { h, clear } from "../dom";
import { filterFromParams, filterToParams, matchesFilter, type FilterState } from "../filters";
import { freeRows } from "../freeCopies";
import { normalizeName } from "../normalize";
import { cardForEntry } from "../printing";
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
  cardmarket_id: null,
  printings: {},
};

/** Bulk has no ownership columns of its own - it IS the inventory - so
 * its rows are just a straight (name, qty, card) projection with no
 * diffing needed. */
function bulkRows(bulk: CardList, cards: CardsIndex): CardRow[] {
  return bulk.entries.map((e) => ({
    name: e.name,
    qty: e.qty,
    foil: e.foil ?? false,
    card: cardForEntry(cards, e) ?? { name: e.name, ...UNRESOLVED_PLACEHOLDER },
  }));
}

export async function renderBulk(root: HTMLElement, params: URLSearchParams): Promise<void> {
  clear(root);
  root.append(h("h1", {}, "Bulk"), h("p", { class: "loading" }, "Loading bulk…"));

  const [bulk, cards, meta, usage] = await Promise.all([
    getBulk(),
    getCards(),
    getMeta(),
    getUsage(),
  ]);
  const rows = bulkRows(bulk, cards);
  // Same rows, narrowed to copies no deck currently holds.
  const freeOnlyRows = freeRows(rows, usage, normalizeName);

  clear(root);

  const resultsContainer = h("div", { class: "results" });
  let sortKey: SortKey = "name-asc";
  let currentFilter: FilterState = filterFromParams(params);
  let notInDecks = params.get("free") === "1";
  let mode: ViewMode = "gallery";

  function syncUrl(): void {
    const next = filterToParams(currentFilter);
    if (notInDecks) next.set("free", "1");
    replaceQueryParams(next);
  }

  function render(): void {
    const source = notInDecks ? freeOnlyRows : rows;
    const filtered = source.filter((r) => matchesFilter(r.card, currentFilter, r.foil));
    renderCardView(resultsContainer, sortRows(filtered, sortKey), { mode });
  }

  const filterBar = createFilterBar(
    rows.map((r) => r.card),
    (state) => {
      currentFilter = state;
      syncUrl();
      render();
    },
    currentFilter,
  );
  const notInDecksToggle = h(
    "button",
    {
      type: "button",
      class: notInDecks ? "view-toggle-btn active" : "view-toggle-btn",
      "aria-pressed": String(notInDecks),
      title: "Only show cards that aren't currently in a deck (partly-used cards show just their free copies)",
      onclick: () => {
        notInDecks = !notInDecks;
        notInDecksToggle.classList.toggle("active", notInDecks);
        notInDecksToggle.setAttribute("aria-pressed", String(notInDecks));
        syncUrl();
        render();
      },
    },
    "📦 Not in decks",
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
      h("div", { class: "toolbar-actions" }, notInDecksToggle, sortSelect, priciestButton, viewToggle),
    ),
    resultsContainer,
  );

  render();
}
