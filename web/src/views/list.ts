import { createFilterBar } from "../components/filterBar";
import { renderCardView, type ViewMode } from "../components/cardView";
import { createPriciestButton } from "../components/priciestButton";
import { createSortSelect } from "../components/sortSelect";
import { createViewToggle } from "../components/viewToggle";
import { getBulk, getCards, getList, getMeta } from "../data";
import { diffList, type DiffRow } from "../diff";
import { h, clear } from "../dom";
import { matchesFilter, type FilterState } from "../filters";
import { priceNote } from "../priceNote";
import { sortRows, type SortKey } from "../sort";

type Tab = "all" | "owned" | "missing";

export async function renderList(root: HTMLElement, kind: string, id: string): Promise<void> {
  clear(root);
  root.append(h("p", { class: "loading" }, "Loading…"));

  const [list, bulk, cards, meta] = await Promise.all([
    getList(kind, id),
    getBulk(),
    getCards(),
    getMeta(),
  ]);

  const diff = diffList(list, bulk, cards);
  const ownedCount = diff.reduce((sum, r) => sum + r.ownedQty, 0);
  const missingCount = diff.reduce((sum, r) => sum + r.missingQty, 0);
  const missingPrice = diff.reduce(
    (sum, r) => sum + (r.missingQty > 0 ? (r.card.price_eur ?? 0) * r.missingQty : 0),
    0,
  );

  clear(root);

  let activeTab: Tab = "all";
  let currentFilter: FilterState | null = null;
  let sortKey: SortKey = "name-asc";
  let mode: ViewMode = "gallery";

  const resultsContainer = h("div", { class: "results" });

  function rowsForTab(tab: Tab): DiffRow[] {
    if (tab === "owned") return diff.filter((r) => r.ownedQty > 0);
    if (tab === "missing") return diff.filter((r) => r.missingQty > 0);
    return diff;
  }

  function render(): void {
    let rows = rowsForTab(activeTab);
    if (currentFilter) rows = rows.filter((r) => matchesFilter(r.card, currentFilter!));
    renderCardView(resultsContainer, sortRows(rows, sortKey), { mode, showDiffColumns: true });
  }

  const tabButtons: Record<Tab, HTMLElement> = {
    all: h("button", { type: "button", class: "tab active" }, `All (${diff.length})`),
    owned: h("button", { type: "button", class: "tab" }, `Owned (${ownedCount})`),
    missing: h("button", { type: "button", class: "tab" }, `Missing (${missingCount})`),
  };

  for (const [tab, button] of Object.entries(tabButtons) as [Tab, HTMLElement][]) {
    button.addEventListener("click", () => {
      activeTab = tab;
      for (const b of Object.values(tabButtons)) b.classList.remove("active");
      button.classList.add("active");
      render();
    });
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
    h("div", { class: "tabs" }, ...Object.values(tabButtons)),
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
