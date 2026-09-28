import { h } from "../dom";

export interface ExportRow {
  name: string;
  qty: number;
  /** Optional free-text note (e.g. which other deck also wants this
   * card) rendered as its own "# ..." comment line, right under the
   * card - the project's own list-file comment convention (see
   * README.md), and easy to strip before pasting into Cardmarket if it
   * doesn't like the extra line. */
  note?: string;
}

/** Renders `rows` as plain-text lines in the project's own list format
 * (e.g. "2x Lightning Bolt") - bare card names only, no set/printing
 * info, so it pastes straight into Cardmarket's mass-entry search or
 * wantlist import. Any `note` becomes its own comment line right after
 * the card it belongs to. */
export function formatExportRows(rows: ExportRow[]): string {
  return rows
    .filter((r) => r.qty > 0)
    .sort((a, b) => a.name.localeCompare(b.name))
    .flatMap((r) => (r.note ? [`${r.qty}x ${r.name}`, `# ${r.note}`] : [`${r.qty}x ${r.name}`]))
    .join("\n");
}

export interface ExportButton {
  element: HTMLElement;
  /** Re-reads `getLabel()` - call after anything that changes the count
   * it displays (active tab, filters, ...). */
  refresh(): void;
}

/** A button that copies whatever `getRows` returns *at click time* to the
 * clipboard, as plain "1x Card Name" lines (see formatExportRows). Falls
 * back to a copyable prompt() if the Clipboard API is unavailable or
 * denied. `getLabel` drives the button's text (e.g. "Export Missing
 * (12)") and is re-evaluated on `refresh()`. */
export function createExportButton(
  getRows: () => ExportRow[],
  getLabel: () => string,
): ExportButton {
  const button = h("button", { type: "button", class: "export-button" }, getLabel());

  function refresh(): void {
    button.textContent = getLabel();
  }

  button.addEventListener("click", () => {
    const text = formatExportRows(getRows());
    if (!text) return;

    void navigator.clipboard.writeText(text).then(
      () => {
        button.textContent = "Copied!";
        window.setTimeout(refresh, 1200);
      },
      () => {
        // Clipboard API unavailable/denied - fall back to a prompt() so
        // the text is still selectable/copyable by hand.
        window.prompt("Copy this list:", text);
      },
    );
  });

  return { element: button, refresh };
}
