/** Tiny hash router with per-view code splitting: nothing beyond the shell
 * (this file, dom.ts, data.ts, types.ts) is downloaded until a view is
 * actually visited. A hash may carry a "?key=value" query string after its
 * path (e.g. "#/?set=rea") - that's how filter state becomes a shareable
 * link; see filters.ts's filterToParams/filterFromParams. */

function splitHash(): { path: string; params: URLSearchParams } {
  const raw = location.hash.replace(/^#/, "") || "/";
  const qIndex = raw.indexOf("?");
  const path = qIndex === -1 ? raw : raw.slice(0, qIndex);
  const query = qIndex === -1 ? "" : raw.slice(qIndex + 1);
  return { path, params: new URLSearchParams(query) };
}

/** Rewrites the current hash's query string (leaving its path alone)
 * without triggering a hashchange/re-navigation, so live filter edits
 * update the address bar in place - e.g. for copying a shareable link. */
export function replaceQueryParams(params: URLSearchParams): void {
  const { path } = splitHash();
  const qs = params.toString();
  const newHash = `#${path}${qs ? `?${qs}` : ""}`;
  history.replaceState(null, "", newHash);
}

export async function navigate(root: HTMLElement): Promise<void> {
  const { path, params } = splitHash();

  try {
    if (path === "/" || path === "") {
      const { renderBulk } = await import("./views/bulk");
      await renderBulk(root, params);
      return;
    }

    if (path === "/decks") {
      const { renderDecks } = await import("./views/decks");
      await renderDecks(root);
      return;
    }

    const listMatch = path.match(/^\/list\/([^/]+)\/([^/]+)$/);
    if (listMatch) {
      const [, kind, id] = listMatch;
      const { renderList } = await import("./views/list");
      await renderList(root, kind, id, params);
      return;
    }

    root.textContent = `Not found: ${path}`;
  } catch (err) {
    console.error(err);
    root.textContent = `Failed to load: ${err instanceof Error ? err.message : String(err)}`;
  }
}
