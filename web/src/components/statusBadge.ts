import { h } from "../dom";
import { STATUS_LABELS, type DeckStatus } from "../deckStats";

const STATUS_TITLES: Record<DeckStatus, string> = {
  complete: "Every card is owned",
  "in-progress": "Some cards are owned, but more copies are still needed",
  incomplete: "Cards are missing and none are owned yet",
};

/** A coloured pill for a deck's completion status. */
export function statusBadge(status: DeckStatus | null): HTMLElement | false {
  if (!status) return false;
  return h(
    "span",
    { class: `badge badge-status badge-status-${status}`, title: STATUS_TITLES[status] },
    STATUS_LABELS[status],
  );
}
