import { createFilterBar } from "../components/filterBar";
import { renderCardView, type CardRow, type ViewMode } from "../components/cardView";
import { createExportButton, type ExportRow } from "../components/exportButton";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getBulk, getCards, getIndex, getList, getMeta } from "../data";
import { diffList, isBasicLand, quantityMap, type DiffRow } from "../diff";
import { h, clear } from "../dom";
import { filterFromParams, filterToParams, matchesFilter, type FilterState } from "../filters";
import { isCollectionLike } from "../listKind";
import { normalizeName } from "../normalize";
import { priceNote } from "../priceNote";
import { replaceQueryParams } from "../router";
import { sortRows, type SortKey } from "../sort";
import type { CardList } from "../types";

type Tab = "all" | "owned" | "missing" | "contested";

export async function renderList(
  root: HTMLElement,
  kind: string,
  id: string,
  params: URLSearchParams,
): Promise<void> {
  clear(root);
  root.append(h("p", { class: "loading" }, "Loading…"));

  const [list, bulk, cards, meta, index] = await Promise.all([
    getList(kind, id),
    getBulk(),
    getCards(),
    getMeta(),
    getIndex(),
  ]);

  const diff = diffList(list, bulk, cards);
  const ownedCount = diff.reduce((sum, r) => sum + r.ownedQty, 0);
  const missingCount = diff.reduce((sum, r) => sum + r.missingQty, 0);
  const missingPrice = diff.reduce(
    (sum, r) => sum + (r.missingQty > 0 ? (r.card.price_eur ?? 0) * r.missingQty : 0),
    0,
  );

  // Ownership is diffed against bulk independently per deck (see
  // diff.ts), so two active decks can both show the same scarce card as
  // "owned" even though only one physical copy actually exists. Cross-
  // reference every other real, currently-sleeved deck (not archived,
  // not a wishlist/collection) to compute genuine contention: total
  // demand for a card across every active deck vs. how many you
  // actually own. Only flagged when that's a real shortfall beyond what
  // this deck's own Missing count already accounts for.
  const otherActiveDecks = index.filter(
    (e) => e.status === "active" && !isCollectionLike(e) && !(e.kind === kind && e.id === id),
  );
  const otherLists = await Promise.all(otherActiveDecks.map((e) => getList(e.kind, e.id)));

  const bulkQtyMap = quantityMap(bulk);

  const demandMap = new Map<string, number>();
  const addDemand = (l: CardList) => {
    for (const [normName, qty] of quantityMap(l)) {
      demandMap.set(normName, (demandMap.get(normName) ?? 0) + qty);
    }
  };
  addDemand(list);
  otherLists.forEach(addDemand);

  const sharedMap = new Map<string, { name: string; qty: number }[]>();
  otherActiveDecks.forEach((entry, i) => {
    for (const [normName, qty] of quantityMap(otherLists[i])) {
      const sharers = sharedMap.get(normName) ?? [];
      sharers.push({ name: entry.name, qty });
      sharedMap.set(normName, sharers);
    }
  });

  // A card can appear on more than one line in the same list (e.g. a
  // deck's Forests split across two lines, or the same card pinned to
  // two different printings). diffList() is per-line, so without this
  // both lines would independently compute the exact same "extra copies
  // needed" number and it'd get double-counted in totals/exports. Sum
  // missingQty per name across the whole list, and only ever attribute
  // the shortfall to that name's first line.
  const missingByName = new Map<string, number>();
  const firstRowForName = new Map<string, DiffRow>();
  for (const r of diff) {
    const key = normalizeName(r.name);
    missingByName.set(key, (missingByName.get(key) ?? 0) + r.missingQty);
    if (!firstRowForName.has(key)) firstRowForName.set(key, r);
  }

  /** How many *additional* copies of this card you'd need to buy so every
   * active deck that wants it can actually have one sleeved at once -
   * beyond whatever this deck's own Missing count already covers. 0
   * means bulk has enough to go around (or no other deck wants it).
   * Basic lands are excluded - bulk.txt deliberately never tracks them
   * (see isBasicLand), so "0 in bulk" isn't a real shortfall. */
  function additionalNeeded(row: DiffRow): number {
    if (isBasicLand(row.card)) return 0;
    const key = normalizeName(row.name);
    if (!sharedMap.has(key)) return 0;
    if (firstRowForName.get(key) !== row) return 0;
    const demand = demandMap.get(key) ?? 0;
    const supply = bulkQtyMap.get(key) ?? 0;
    const globalShortfall = Math.max(0, demand - supply);
    const missingThisDeck = missingByName.get(key) ?? 0;
    return Math.max(0, globalShortfall - missingThisDeck);
  }

  function withSharedInfo(rows: DiffRow[]): CardRow[] {
    return rows.map((r) => {
      const extra = additionalNeeded(r);
      if (extra <= 0) return r;
      const key = normalizeName(r.name);
      return {
        ...r,
        contention: {
          additionalNeeded: extra,
          sharedWith: sharedMap.get(key) ?? [],
          totalDemand: demandMap.get(key) ?? 0,
          bulkQty: bulkQtyMap.get(key) ?? 0,
        },
      };
    });
  }

  const contestedRows = diff.filter((r) => additionalNeeded(r) > 0);
  const contestedExtraTotal = contestedRows.reduce((sum, r) => sum + additionalNeeded(r), 0);

  /** The actual "go order this" shopping list: every card this deck is
   * missing, plus - for cards also wanted by other active decks - extra
   * copies beyond that so nobody's left short, each annotated with which
   * other deck(s) are competing for it. One row per card, so a card that's
   * both partly missing *and* contested only appears once with its full
   * combined quantity. */
  function shoppingListRows(): ExportRow[] {
    const rows: ExportRow[] = [];
    for (const r of diff) {
      if (!matchesFilter(r.card, currentFilter)) continue;
      const extra = additionalNeeded(r);
      const qty = r.missingQty + extra;
      if (qty <= 0) continue;
      const contributors = extra > 0 ? sharedMap.get(normalizeName(r.name)) : undefined;
      const note =
        contributors && contributors.length > 0
          ? `also needed by: ${contributors.map((s) => `${s.name} (x${s.qty})`).join(", ")}`
          : undefined;
      rows.push({ name: r.name, qty, note });
    }
    return rows;
  }

  function shoppingListLabel(): string {
    const count = shoppingListRows().reduce((sum, r) => sum + r.qty, 0);
    return `Export Missing + Contested (${count})`;
  }

  clear(root);

  let activeTab: Tab = "all";
  let currentFilter: FilterState = filterFromParams(params);
  let sortKey: SortKey = "name-asc";
  let mode: ViewMode = "gallery";

  const resultsContainer = h("div", { class: "results" });

  function rowsForTab(tab: Tab): DiffRow[] {
    if (tab === "owned") return diff.filter((r) => r.ownedQty > 0);
    if (tab === "missing") return diff.filter((r) => r.missingQty > 0);
    if (tab === "contested") return contestedRows;
    return diff;
  }

  /** Quantity to export for a row, matching what its tab actually shows -
   * e.g. the "Missing" tab exports how many copies are still missing,
   * the "Contested" tab exports how many *extra* copies to buy on top of
   * that so every deck wanting this card can have one. */
  function exportQty(row: DiffRow, tab: Tab): number {
    if (tab === "owned") return row.ownedQty;
    if (tab === "missing") return row.missingQty;
    if (tab === "contested") return additionalNeeded(row);
    return row.qty;
  }

  function exportRowsForTab(tab: Tab): ExportRow[] {
    return rowsForTab(tab)
      .filter((r) => matchesFilter(r.card, currentFilter))
      .map((r) => ({ name: r.name, qty: exportQty(r, tab) }));
  }

  function exportLabel(): string {
    const tabLabel =
      activeTab === "owned"
        ? "Owned"
        : activeTab === "missing"
          ? "Missing"
          : activeTab === "contested"
            ? "Contested"
            : "All";
    const count = exportRowsForTab(activeTab).reduce((sum, r) => sum + r.qty, 0);
    return `Export ${tabLabel} (${count})`;
  }

  function render(): void {
    const rows = rowsForTab(activeTab).filter((r) => matchesFilter(r.card, currentFilter));
    renderCardView(resultsContainer, sortRows(withSharedInfo(rows), sortKey), { mode, showDiffColumns: true });
    exportButton.refresh();
    shoppingListButton.refresh();
  }

  const tabLabels: Record<Tab, string> = {
    all: `All (${diff.length})`,
    owned: `Owned (${ownedCount})`,
    missing: `Missing (${missingCount})`,
    contested: `Contested (${contestedRows.length})`,
  };
  const visibleTabs: Tab[] =
    contestedRows.length > 0 ? ["all", "owned", "missing", "contested"] : ["all", "owned", "missing"];
  const tabButtons = new Map<Tab, HTMLElement>(
    visibleTabs.map((tab) => [
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
    diff.map((r) => r.card),
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
  const shoppingListButton = createExportButton(shoppingListRows, shoppingListLabel);

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
      contestedRows.length > 0 &&
        h(
          "div",
          {
            class: "stat",
            title:
              "Also wanted by other active decks, beyond what bulk currently covers - " +
              "see the Contested tab for which cards and how many extra to buy.",
          },
          h("span", { class: "stat-value" }, String(contestedExtraTotal)),
          h("span", { class: "stat-label" }, `Contested (${contestedRows.length} card${contestedRows.length === 1 ? "" : "s"})`),
        ),
    ),
    h("p", { class: "price-note" }, priceNote(meta)),
    h(
      "div",
      { class: "shopping-list-actions" },
      shoppingListButton.element,
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
