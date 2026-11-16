import { h } from "../dom";
import type { CardData } from "../types";
import { openCardPopover } from "./cardPopover";

export interface CommanderOptions {
  listName: string;
  ownedQty?: number;
  missingQty?: number;
}

/** A prominent commander card for the top of a deck page. Clicking it opens
 * the same card-detail dialog used by the regular card views. */
export function createCommanderCard(card: CardData, options: CommanderOptions): HTMLElement {
  const missing = (options.missingQty ?? 0) > 0;
  const hasAllocation = options.missingQty !== undefined;

  const onclick = (e: Event) => {
    e.preventDefault();
    openCardPopover(
      e.currentTarget as HTMLElement,
      card,
      hasAllocation ? { listName: options.listName, missingQty: options.missingQty ?? 0 } : undefined,
    );
  };

  const visual = card.image_uri
    ? h("img", { src: card.image_uri, alt: card.name })
    : h("span", { class: "commander-card-placeholder" }, card.name);

  return h(
    "div",
    { class: "commander-section" },
    h(
      "a",
      {
        href: "#",
        class: missing ? "commander-card commander-card-missing" : "commander-card",
        title: `${card.name} (commander) - click for card details`,
        onclick,
      },
      visual,
      missing && h("span", { class: "commander-missing-label" }, "⚠ Not owned"),
    ),
  );
}
