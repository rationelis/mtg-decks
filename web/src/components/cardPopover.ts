import { getUsage } from "../data";
import { clear, h } from "../dom";
import { normalizeName } from "../normalize";
import type { CardData, Usage } from "../types";

/** Context for opening a popover from a specific list's row, so the
 * popover can lead with a one-line summary framed for that deck's
 * situation (see REFACTOR.md §9.6) instead of only the raw numbers. */
export interface PopoverContext {
  listName: string;
  missingQty: number;
}

let closeCurrent: (() => void) | null = null;

/** Opens a small detail popover near `anchor` showing a card's bulk
 * allocation (Owned/Available/which decks currently hold it), lazily
 * fetched from usage.json. Only one popover is ever open at a time;
 * clicking outside it or pressing Escape closes it. */
export function openCardPopover(anchor: HTMLElement, card: CardData, context?: PopoverContext): void {
  closeCurrent?.();

  const popover = h("div", { class: "card-popover", role: "dialog" }, h("p", { class: "loading" }, "Loading…"));
  document.body.append(popover);
  position(popover, anchor);

  function close(): void {
    popover.remove();
    document.removeEventListener("keydown", onKeyDown, true);
    document.removeEventListener("mousedown", onOutsideClick, true);
    if (closeCurrent === close) closeCurrent = null;
  }
  function onKeyDown(e: KeyboardEvent): void {
    if (e.key === "Escape") close();
  }
  function onOutsideClick(e: MouseEvent): void {
    const target = e.target as Node;
    if (!popover.contains(target) && target !== anchor && !anchor.contains(target)) close();
  }
  // Capture phase + a microtask delay so the click that opened this
  // popover doesn't immediately also count as the "outside click" that
  // closes it.
  window.setTimeout(() => {
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("mousedown", onOutsideClick, true);
  }, 0);
  closeCurrent = close;

  void getUsage()
    .then((usage) => {
      if (!popover.isConnected) return; // closed before the fetch resolved
      const key = normalizeName(card.name);
      render(popover, card, usage[key] ?? null, context, close);
    })
    .catch(() => {
      if (!popover.isConnected) return;
      clear(popover);
      popover.append(h("p", { class: "popover-error" }, "Could not load allocation data."));
    });
}

function position(popover: HTMLElement, anchor: HTMLElement): void {
  const rect = anchor.getBoundingClientRect();
  popover.style.position = "fixed";
  popover.style.top = `${Math.min(rect.bottom + 6, window.innerHeight - 20)}px`;
  popover.style.left = `${Math.min(rect.left, window.innerWidth - 280)}px`;
}

function allocationList(usage: Usage): HTMLElement {
  if (usage.allocations.length === 0) {
    return h("p", { class: "popover-in" }, "In: —");
  }
  return h(
    "div",
    { class: "popover-in" },
    h("span", {}, "In:"),
    h(
      "ul",
      {},
      ...usage.allocations.map((a) =>
        h("li", {}, `${a.listName} — ${a.quantity} cop${a.quantity === 1 ? "y" : "ies"}`),
      ),
    ),
  );
}

function summaryLine(usage: Usage, context: PopoverContext): HTMLElement | false {
  if (context.missingQty <= 0) return false;
  const holders = usage.allocations.map((a) => a.listName).join(", ");
  if (usage.available <= 0) {
    return h(
      "p",
      { class: "popover-summary" },
      h("strong", {}, "Owned — unavailable"),
      h(
        "span",
        {},
        holders
          ? ` ${usage.owned} cop${usage.owned === 1 ? "y" : "ies"} owned, currently in ${holders}`
          : ` ${usage.owned} cop${usage.owned === 1 ? "y" : "ies"} owned, none free right now`,
      ),
    );
  }
  return h(
    "p",
    { class: "popover-summary" },
    h("strong", {}, "Partially available"),
    h("span", {}, ` ${usage.available} of ${usage.owned} owned cop${usage.owned === 1 ? "y" : "ies"} free`),
  );
}

function render(
  popover: HTMLElement,
  card: CardData,
  usage: Usage | null,
  context: PopoverContext | undefined,
  close: () => void,
): void {
  clear(popover);

  const closeButton = h(
    "button",
    { type: "button", class: "popover-close", onclick: close, title: "Close" },
    "×",
  );

  if (!usage) {
    popover.append(
      closeButton,
      h(
        "div",
        {},
        h("h3", {}, card.name),
        h("p", { class: "popover-note" }, "Not tracked in bulk (e.g. a basic land - always available)."),
      ),
    );
    return;
  }

  popover.append(
    closeButton,
    h(
      "div",
      {},
      h("h3", {}, card.name),
      context && summaryLine(usage, context),
      h("p", {}, `Owned: ${usage.owned}`),
      h("p", {}, `Available: ${usage.available}`),
      allocationList(usage),
    ),
  );
}
