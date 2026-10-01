import { createFilterBar } from "../components/filterBar";
import { renderCardView, type CardRow, type ViewMode } from "../components/cardView";
import { createExportButton, type ExportRow } from "../components/exportButton";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getCards, getList, getMeta } from "../data";
import { h, clear } from "../dom";
import { filterFromParams, filterToParams, matchesFilter, type FilterState } from "../filters";
import { normalizeName } from "../normalize";
import { priceNote } from "../priceNote";
import { replaceQueryParams } from "../router";
import { sortRows, type SortKey } from "../sort";
import type { CardsIndex, ListEntry } from "../types";

type Tab = "all" | "owned" | "missing";

export async function renderList(
  root: HTMLElement,
  kind: string,
  id: string,
  params: URLSearchParams,
): Promise<void> {
  clear(root);
  root.append(h("p", { class: "loading" }, "Loading…"));

  const [list, cards, meta] = await Promise.all([getList(kind, id), getCards(), getMeta()]);

  // Owned/Missing is already allocation-aware (one physical copy can
  // only be claimed by one "real" active deck at a time, computed once
  // at build time - see scripts/build/allocate.py). The frontend just
  // renders fields the build already computed; it never diffs anything
  // itself.
  const rows: Required<CardRow>[] = list.entries.map((e: ListEntry) => ({
    name: e.name,
    qty: e.qty,
    ownedQty: e.ownedQty ?? 0,
    missingQty: e.missingQty ?? 0,
    card: lookupCard(e.name, cards),
  }));

  const ownedCount = rows.reduce((sum, r) => sum + r.ownedQty, 0);
  const missingCount = rows.reduce((sum, r) => sum + r.missingQty, 0);
  const missingPrice = rows.reduce(
    (sum, r) => sum + (r.missingQty > 0 ? (r.card.price_eur ?? 0) * r.missingQty : 0),
    0,
  );

  clear(root);

  let activeTab: Tab = "all";
  let currentFilter: FilterState = filterFromParams(params);
  let sortKey: SortKey = "name-asc";
  let mode: ViewMode = "gallery";

  const resultsContainer = h("div", { class: "results" });

  function rowsForTab(tab: Tab): Required<CardRow>[] {
    if (tab === "owned") return rows.filter((r) => r.ownedQty > 0);
    if (tab === "missing") return rows.filter((r) => r.missingQty > 0);
    return rows;
  }

  function exportRowsForTab(tab: Tab): ExportRow[] {
    return rowsForTab(tab)
      .filter((r) => matchesFilter(r.card, currentFilter))
      .map((r) => ({
        name: r.name,
        qty: tab === "owned" ? r.ownedQty : tab === "missing" ? r.missingQty : r.qty,
      }));
  }

  function exportLabel(): string {
    const tabLabel = activeTab === "owned" ? "Owned" : activeTab === "missing" ? "Missing" : "All";
    const count = exportRowsForTab(activeTab).reduce((sum, r) => sum + r.qty, 0);
    return `Export ${tabLabel} (${count})`;
  }

  function render(): void {
    const visible = rowsForTab(activeTab).filter((r) => matchesFilter(r.card, currentFilter));
    renderCardView(resultsContainer, sortRows(visible, sortKey), {
      mode,
      showDiffColumns: true,
      listName: list.name,
    });
    exportButton.refresh();
  }

  const tabLabels: Record<Tab, string> = {
    all: `All (${rows.length})`,
    owned: `Owned (${ownedCount})`,
    missing: `Missing (${missingCount})`,
  };
  const tabButtons = new Map<Tab, HTMLElement>(
    (["all", "owned", "missing"] as Tab[]).map((tab) => [
      tab,
      h("button", { type: "button", class: tab === "all" ? "tab active" : "tab" }, tabLabels[tab]),
    ]),
  );

  for (const [tab, button] of tabButtons) {
    button.addEventListener("click", () => {
      activeTab = tab;
      for (const b of tabButtons.values()) b.classList.remove("active");
      button.classList.add("active");
      render();
    });
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

  const exportButton = createExportButton(() => exportRowsForTab(activeTab), exportLabel);

  root.append(
    h(
      "div",
      { class: "list-header" },
      h("a", { href: "#/decks", class: "back-link" }, "← Decks"),
      h(
        "h1",
        {},
        list.name,
        list.proxy && h("span", { class: "badge badge-proxy" }, "proxy"),
        list.collection && h("span", { class: "badge badge-collection" }, "collection"),
        list.status === "archived" && h("span", { class: "badge badge-archived" }, "archived"),
      ),
      list.commander && h("p", { class: "commander" }, `Commander: ${list.commander}`),
    ),
    h(
      "div",
      { class: "stats" },
      h(
        "div",
        { class: "stat" },
        h("span", { class: "stat-value" }, String(ownedCount)),
        h("span", { class: "stat-label" }, "Owned"),
      ),
      h(
        "div",
        { class: "stat" },
        h("span", { class: "stat-value" }, String(missingCount)),
        h("span", { class: "stat-label" }, "Missing"),
      ),
      h(
        "div",
        { class: "stat" },
        h("span", { class: "stat-value" }, `€${missingPrice.toFixed(2)}`),
        h("span", { class: "stat-label" }, "Price to complete"),
      ),
    ),
    h("p", { class: "price-note" }, priceNote(meta)),
    h("div", { class: "tabs" }, ...tabButtons.values()),
    h(
      "div",
      { class: "toolbar" },
      filterBar,
      h(
        "div",
        { class: "toolbar-actions" },
        sortSelect,
        priciestButton,
        viewToggle,
        exportButton.element,
      ),
    ),
    resultsContainer,
  );

  render();
}

function lookupCard(name: string, cards: CardsIndex) {
  return (
    cards[normalizeName(name)] ?? {
      name,
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
      price_state: "unavailable" as const,
      released_at: null,
    }
  );
}
