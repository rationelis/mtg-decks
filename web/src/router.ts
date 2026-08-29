/** Tiny hash router with per-view code splitting: nothing beyond the shell
 * (this file, dom.ts, data.ts, types.ts) is downloaded until a view is
 * actually visited. */
export async function navigate(root: HTMLElement): Promise<void> {
  const hash = location.hash.replace(/^#/, "") || "/";

  try {
    if (hash === "/" || hash === "") {
      const { renderBulk } = await import("./views/bulk");
      await renderBulk(root);
      return;
    }

    if (hash === "/decks") {
      const { renderDecks } = await import("./views/decks");
      await renderDecks(root);
      return;
    }

    const listMatch = hash.match(/^\/list\/([^/]+)\/([^/]+)$/);
    if (listMatch) {
      const [, kind, id] = listMatch;
      const { renderList } = await import("./views/list");
      await renderList(root, kind, id);
      return;
    }

    root.textContent = `Not found: ${hash}`;
  } catch (err) {
    console.error(err);
    root.textContent = `Failed to load: ${err instanceof Error ? err.message : String(err)}`;
  }
}
