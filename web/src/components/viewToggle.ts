import { h } from "../dom";
import type { ViewMode } from "./cardView";

/** Two-button Gallery/List switch, shared by the bulk browser and the
 * per-deck list view (they just default to a different starting mode). */
export function createViewToggle(
  initial: ViewMode,
  onChange: (mode: ViewMode) => void,
): HTMLElement {
  const buttons: Record<ViewMode, HTMLElement> = {
    gallery: h("button", { type: "button", class: "view-toggle-btn" }, "🖼 Gallery"),
    list: h("button", { type: "button", class: "view-toggle-btn" }, "☰ List"),
  };

  function setActive(mode: ViewMode): void {
    for (const [m, btn] of Object.entries(buttons) as [ViewMode, HTMLElement][]) {
      btn.classList.toggle("active", m === mode);
    }
  }

  (Object.entries(buttons) as [ViewMode, HTMLElement][]).forEach(([mode, btn]) => {
    btn.addEventListener("click", () => {
      setActive(mode);
      onChange(mode);
    });
  });

  setActive(initial);
  return h("div", { class: "view-toggle" }, buttons.gallery, buttons.list);
}
