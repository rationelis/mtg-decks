import { h } from "../dom";
import type { SortKey } from "../sort";

/** Shortcut button that jumps straight to "priciest first" sorting,
 * shared by the bulk browser and per-list view. Keeps the given sort
 * <select> in sync so the two controls never disagree. */
export function createPriciestButton(
  sortSelect: HTMLSelectElement,
  onSelect: (key: SortKey) => void,
): HTMLElement {
  return h(
    "button",
    {
      type: "button",
      class: "priciest-button",
      title: "Sort by price, most expensive first",
      onclick: () => {
        sortSelect.value = "price-desc";
        onSelect("price-desc");
      },
    },
    "💰 Priciest first",
  );
}
