import { cardmarketUrl } from "../cardmarket";
import { getUsage } from "../data";
import { clear, h } from "../dom";
import { normalizeName } from "../normalize";
import { formatPriceLabel, priceTitle } from "../priceNote";
import type { CardData, Usage } from "../types";

/** Context for opening the detail dialog from a specific list's row, so
 * it can lead with a one-line summary framed for that deck's situation
 * (see REFACTOR.md §9.6) instead of only the raw numbers. */
export interface PopoverContext {
  listName: string;
  missingQty: number;
}

let closeCurrent: (() => void) | null = null;

/** Opens a centered card-detail dialog (image, oracle text, Scryfall
 * link, and - lazily fetched from usage.json - bulk allocation: which
 * decks currently hold this card). Centered on the viewport rather than
 * anchored to the clicked element so it can never end up partially or
 * fully off-screen. Only one dialog is ever open at a time; clicking the
 * backdrop or pressing Escape closes it. */
export function openCardPopover(
  anchor: HTMLElement,
  card: CardData,
  context?: PopoverContext,
  foil = false,
): void {
  closeCurrent?.();

  const backdrop = h("div", { class: "card-modal-backdrop" });
  const dialog = h("div", { class: "card-modal", role: "dialog", "aria-modal": "true" });
  backdrop.append(dialog);
  document.body.append(backdrop);
  renderStatic(dialog, card, close, foil);

  function close(): void {
    backdrop.remove();
    document.removeEventListener("keydown", onKeyDown, true);
    anchor.focus?.();
    if (closeCurrent === close) closeCurrent = null;
  }
  function onKeyDown(e: KeyboardEvent): void {
    if (e.key === "Escape") close();
  }
  function onBackdropClick(e: MouseEvent): void {
    if (e.target === backdrop) close();
  }
  backdrop.addEventListener("mousedown", onBackdropClick);
  document.addEventListener("keydown", onKeyDown, true);
  closeCurrent = close;

  void getUsage()
    .then((usage) => {
      if (!backdrop.isConnected) return; // closed before the fetch resolved
      const key = normalizeName(card.name);
      renderAllocation(dialog, usage[key] ?? null, context);
    })
    .catch(() => {
      if (!backdrop.isConnected) return;
      dialog.querySelector(".allocation-section")?.replaceWith(
        h("p", { class: "popover-error" }, "Could not load allocation data."),
      );
    });
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
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

/** The part of the dialog that never needs the async usage.json fetch:
 * image, name, oracle text, price, and the Scryfall link. Rendered
 * immediately so the dialog is never empty/blank while usage loads. */
function renderStatic(dialog: HTMLElement, card: CardData, close: () => void, foil: boolean): void {
  clear(dialog);

  const closeButton = h(
    "button",
    { type: "button", class: "popover-close", onclick: close, title: "Close" },
    "×",
  );

  const image = card.image_uri
    ? h("img", { class: "popover-image", src: card.image_uri, alt: card.name })
    : h("div", { class: "popover-image popover-image-placeholder" }, card.name);
  const imageBox = h("div", { class: foil ? "popover-image-box is-foil" : "popover-image-box" }, image);

  dialog.append(
    closeButton,
    h(
      "div",
      { class: "popover-body" },
      imageBox,
      h(
        "div",
        { class: "popover-details" },
        h("h3", {}, card.name, foil && h("span", { class: "foil-tag foil-tag-inline" }, "✦ Foil")),
        h("p", { class: "popover-meta" }, [card.type_line, card.mana_cost].filter(Boolean).join(" — ") || "—"),
        card.rarity &&
          h(
            "p",
            { class: `popover-rarity rarity-${card.rarity}` },
            h("strong", {}, capitalize(card.rarity)),
            card.set_name && ` · ${card.set_name}${card.set ? ` (${card.set.toUpperCase()})` : ""}`,
          ),
        card.oracle_text && h("p", { class: "popover-oracle" }, card.oracle_text),
        h(
          "p",
          { class: "popover-price", title: priceTitle(card) },
          `Price: ${formatPriceLabel(card)}${foil ? " (foil)" : ""}`,
        ),
        h(
          "div",
          { class: "popover-links" },
          h(
            "a",
            {
              class: "popover-cardmarket-link",
              href: cardmarketUrl(card, foil),
              target: "_blank",
              rel: "noopener",
              title: foil ? "Open on Cardmarket, filtered to foil offers" : "Open on Cardmarket",
            },
            "Cardmarket ↗",
          ),
          card.scryfall_uri &&
            h(
              "a",
              { class: "popover-scryfall-link", href: card.scryfall_uri, target: "_blank", rel: "noopener" },
              "View on Scryfall ↗",
            ),
        ),
        h("div", { class: "allocation-section" }, h("p", { class: "loading" }, "Loading allocation…")),
      ),
    ),
  );
}

function renderAllocation(dialog: HTMLElement, usage: Usage | null, context: PopoverContext | undefined): void {
  const section = dialog.querySelector(".allocation-section");
  if (!section) return;

  if (!usage) {
    section.replaceWith(
      h(
        "div",
        { class: "allocation-section" },
        h("p", { class: "popover-note" }, "Not tracked in bulk (e.g. a basic land - always available)."),
      ),
    );
    return;
  }

  section.replaceWith(
    h(
      "div",
      { class: "allocation-section" },
      context && summaryLine(usage, context),
      h("p", {}, `Owned: ${usage.owned}`),
      h("p", {}, `Available: ${usage.available}`),
      allocationList(usage),
    ),
  );
}
