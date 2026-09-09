import { h } from "../dom";
import type { SortKey } from "../sort";

const OPTIONS: [SortKey, string][] = [
  ["name-asc", "Name (A→Z)"],
  ["name-desc", "Name (Z→A)"],
  ["mv-asc", "Mana value (low→high)"],
  ["mv-desc", "Mana value (high→low)"],
  ["price-asc", "Price (low→high)"],
  ["price-desc", "Price (high→low)"],
  ["released-desc", "Release date (new→old)"],
  ["released-asc", "Release date (old→new)"],
];

export function createSortSelect(onChange: (key: SortKey) => void): HTMLElement {
  return h(
    "select",
    {
      class: "sort-select",
      onchange: (e: Event) => onChange((e.target as HTMLSelectElement).value as SortKey),
    },
    ...OPTIONS.map(([value, label]) => h("option", { value }, label)),
  );
}
