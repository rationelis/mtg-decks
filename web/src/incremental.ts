/** Renders `items` into `container` in batches, only appending more rows
 * once a sentinel near the bottom scrolls into view. This keeps the
 * initial paint of a large table/grid instant (first batch only) without
 * needing a full virtual-scroll library - simple, boring, good enough
 * at the scale of a personal collection. */
export function renderIncrementally<T>(
  container: HTMLElement,
  items: T[],
  renderItem: (item: T, index: number) => HTMLElement,
  options: { batchSize?: number; sentinelTag?: string; sentinelColspan?: number } = {},
): void {
  const { batchSize = 80, sentinelTag = "div", sentinelColspan } = options;
  container.replaceChildren();
  let cursor = 0;

  const sentinel = document.createElement(sentinelTag);
  sentinel.className = "sentinel-row";
  // The sentinel must have real size to reliably trigger the
  // IntersectionObserver (a zero-height element can report a zero
  // intersection ratio and never fire) - showing "Loading more…" text
  // both guarantees that and gives visible feedback while scrolling.
  if (sentinelTag === "tr") {
    const cell = document.createElement("td");
    cell.className = "sentinel-label";
    cell.textContent = "Loading more…";
    if (sentinelColspan) cell.colSpan = sentinelColspan;
    sentinel.append(cell);
  } else {
    sentinel.textContent = "Loading more…";
    sentinel.classList.add("sentinel-label");
  }

  function appendBatch(): void {
    const frag = document.createDocumentFragment();
    const end = Math.min(cursor + batchSize, items.length);
    for (; cursor < end; cursor++) {
      frag.append(renderItem(items[cursor], cursor));
    }
    container.append(frag);

    if (cursor >= items.length) {
      sentinel.remove();
      observer.disconnect();
    } else {
      // Keep the sentinel last so it stays the scroll trigger for the
      // next batch, and so it visually reads as "more is loading below".
      container.append(sentinel);
    }
  }

  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) appendBatch();
    },
    { rootMargin: "600px" },
  );

  appendBatch();
  if (cursor < items.length) {
    observer.observe(sentinel);
  }
}
