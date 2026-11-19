import { createCommanderCard } from "../components/commanderCard";
import { createFilterBar } from "../components/filterBar";
import { renderCardView, type CardRow, type ViewMode } from "../components/cardView";
import { createExportButton, type ExportRow } from "../components/exportButton";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { statusBadge } from "../components/statusBadge";
import { createViewToggle } from "../components/viewToggle";
import { getCards, getList, getMeta } from "../data";
import {
  deckStatus,
  findCommanderEntry,
  formatPriceTotal,
  priceToComplete,
  priceTotalNote,
  theoreticalMinimum,
} from "../deckStats";
import { h, clear } from "../dom";
import { filterFromParams, filterToParams, matchesFilter, type FilterState } from "../filters";
import { cardForEntry } from "../printing";
import { priceNote } from "../priceNote";
import { replaceQueryParams } from "../router";
import { sortRows, type SortKey } from "../sort";
import type { CardData, CardsIndex, ListEntry } from "../types";

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
    card: lookupCard(e, cards),
  }));

  const ownedCount = rows.reduce((sum, r) => sum + r.ownedQty, 0);
  const missingCount = rows.reduce((sum, r) => sum + r.missingQty, 0);
  const missingPrice = priceToComplete(rows);
  const minimumValue = theoreticalMinimum(rows);
  const status = deckStatus(list.entries);

  // The commander is already one of the deck's entries (and so already
  // counted in every total above), so it's shown in its own section and
  // left out of the main card list rather than being counted or listed
  // twice.
  const commanderEntry = findCommanderEntry(list.entries, list.commander);
  const commanderRow = commanderEntry ? rows[list.entries.indexOf(commanderEntry)] : undefined;
  const commanderCard =
    commanderRow?.card ??
    (list.commander ? lookupCard({ name: list.commander }, cards) : undefined);
  const listRows = commanderRow ? rows.filter((r) => r !== commanderRow) : rows;

  clear(root);

  let activeTab: Tab = "all";
  let currentFilter: FilterState = filterFromParams(params);
  let sortKey: SortKey = "name-asc";
  let mode: ViewMode = "gallery";

  const resultsContainer = h("div", { class: "results" });

  function rowsForTab(tab: Tab, source: Required<CardRow>[] = listRows): Required<CardRow>[] {
    if (tab === "owned") return source.filter((r) => r.ownedQty > 0);
    if (tab === "missing") return source.filter((r) => r.missingQty > 0);
    return source;
  }

  // Exports cover the whole deck, commander included.
  function exportRowsForTab(tab: Tab): ExportRow[] {
    return rowsForTab(tab, rows)
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
    listRows.map((r) => r.card),
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
        statusBadge(status),
      ),
    ),
    h(
      "div",
      { class: "deck-overview" },
      ...(commanderCard
        ? [
            createCommanderCard(commanderCard, {
              listName: list.name,
              ownedQty: commanderRow?.ownedQty,
              missingQty: commanderRow?.missingQty,
            }),
          ]
        : []),
      h(
        "div",
        { class: "deck-overview-side" },
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
            h(
              "span",
              { class: "stat-value", title: priceTotalNote(missingPrice) },
              formatPriceTotal(missingPrice),
            ),
            h("span", { class: "stat-label" }, "Price to complete"),
          ),
          h(
            "div",
            { class: "stat" },
            h(
              "span",
              { class: "stat-value", title: priceTotalNote(minimumValue) },
              formatPriceTotal(minimumValue),
            ),
            h("span", { class: "stat-label" }, "Theoretical minimum"),
          ),
        ),
        h("p", { class: "price-note" }, priceNote(meta)),
      ),
    ),
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

function lookupCard(entry: { name: string; printing?: string }, cards: CardsIndex): CardData {
  return (
    cardForEntry(cards, entry) ?? {
      name: entry.name,
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
      printings: {},
    }
  );
}
