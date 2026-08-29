type Attrs = Record<string, string | number | boolean | ((ev: Event) => void) | undefined>;
type Child = Node | string | number | null | undefined | false;

/** Minimal hyperscript-style DOM builder - no framework needed for three
 * views. Text content is always set via textContent/createTextNode, never
 * innerHTML, so card names/oracle text (which come from an external API)
 * can never be interpreted as markup. */
export function h(tag: string, attrs: Attrs = {}, ...children: Child[]): HTMLElement {
  const el = document.createElement(tag);

  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value as EventListener);
    } else if (key === "class") {
      el.className = String(value);
    } else if (typeof value === "boolean") {
      if (value) el.setAttribute(key, "");
    } else {
      el.setAttribute(key, String(value));
    }
  }

  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }

  return el;
}

export function clear(el: HTMLElement): void {
  el.replaceChildren();
}
