import { h } from "../dom";
import { cloneFilter, emptyFilter, type FilterState } from "../filters";
import type { CardData } from "../types";

const COLORS = ["W", "U", "B", "R", "G", "C"] as const;
const RARITIES = ["common", "uncommon", "rare", "mythic", "special", "bonus"];
const DEBOUNCE_MS = 150;

interface SetOption {
  code: string;
  label: string;
}

/** One option per distinct set among `cards`, newest release first, so
 * e.g. right after a prerelease its set sorts to the top of the list
 * instead of getting lost alphabetically. */
function buildSetOptions(cards: CardData[]): SetOption[] {
  const byCode = new Map<string, { name: string; releasedAt: string | null }>();
  for (const card of cards) {
    if (!card.set || byCode.has(card.set)) continue;
    byCode.set(card.set, { name: card.set_name || card.set.toUpperCase(), releasedAt: card.released_at });
  }
  return [...byCode.entries()]
    .sort((a, b) => (b[1].releasedAt ?? "").localeCompare(a[1].releasedAt ?? ""))
    .map(([code, { name }]) => ({ code, label: `${name} (${code.toUpperCase()})` }));
}

function numberInput(
  placeholder: string,
  initial: number | null,
  onValue: (v: number | null) => void,
): HTMLInputElement {
  return h("input", {
    type: "number",
    step: "any",
    placeholder,
    class: "num-input",
    value: initial === null ? undefined : String(initial),
    oninput: (e: Event) => {
      const raw = (e.target as HTMLInputElement).value;
      onValue(raw === "" ? null : Number(raw));
    },
  }) as HTMLInputElement;
}

/** Builds the shared search/filter bar used by both the bulk browser and
 * list detail views. `cards` is whatever population of cards the current
 * view can show (all of bulk, or one deck/collection) and drives the set
 * dropdown's options. `initial` seeds the bar's state (e.g. from a shared
 * link's query string - see filters.ts's filterFromParams); omit it to
 * start from an empty filter. Calls `onChange` (debounced for free-text
 * fields) whenever the filter state changes. */
export function createFilterBar(
  cards: CardData[],
  onChange: (state: FilterState) => void,
  initial?: FilterState,
): HTMLElement {
  const state = initial ? cloneFilter(initial) : emptyFilter();
  let debounceHandle: number | undefined;

  const emit = () => onChange(state);
  const emitDebounced = () => {
    window.clearTimeout(debounceHandle);
    debounceHandle = window.setTimeout(emit, DEBOUNCE_MS);
  };

  const searchInput = h("input", {
    type: "search",
    placeholder: "Search name or oracle text…",
    class: "search-input",
    value: state.search || undefined,
    oninput: (e: Event) => {
      state.search = (e.target as HTMLInputElement).value;
      emitDebounced();
    },
  }) as HTMLInputElement;

  // Selecting pips filters for cards whose color identity is *exactly*
  // the selected set (not "any of"), so e.g. picking W+U finds Azorius
  // cards specifically rather than every card that happens to be white
  // or blue - this is what makes multicolor filtering useful.
  const colorPips = COLORS.map((c) => {
    const btn = h(
      "button",
      {
        type: "button",
        class: state.colors.has(c) ? `color-pip color-${c} active` : `color-pip color-${c}`,
        title: c === "C" ? "Colorless" : c,
        onclick: () => {
          if (state.colors.has(c)) state.colors.delete(c);
          else state.colors.add(c);
          btn.classList.toggle("active");
          emit();
        },
      },
      c,
    );
    return btn;
  });

  const manaMin = numberInput("Min MV", state.manaMin, (v) => {
    state.manaMin = v;
    emitDebounced();
  });
  const manaMax = numberInput("Max MV", state.manaMax, (v) => {
    state.manaMax = v;
    emitDebounced();
  });

  const priceMin = numberInput("Min €", state.priceMin, (v) => {
    state.priceMin = v;
    emitDebounced();
  });
  const priceMax = numberInput("Max €", state.priceMax, (v) => {
    state.priceMax = v;
    emitDebounced();
  });

  const typeInput = h("input", {
    type: "text",
    placeholder: "Type contains…",
    class: "type-input",
    value: state.type || undefined,
    oninput: (e: Event) => {
      state.type = (e.target as HTMLInputElement).value;
      emitDebounced();
    },
  }) as HTMLInputElement;

  const setOptions = buildSetOptions(cards);
  const setOptionLabels = new Map(setOptions.map((o) => [o.code, o.label]));

  const updateSetTitle = () => {
    setSelect.title = state.set ? (setOptionLabels.get(state.set) ?? "") : "Filter by set";
  };

  const setSelect = h(
    "select",
    {
      class: "set-select",
      onchange: (e: Event) => {
        state.set = (e.target as HTMLSelectElement).value;
        updateSetTitle();
        emit();
      },
    },
    h("option", { value: "" }, "Any set"),
    ...setOptions.map((o) => h("option", { value: o.code }, o.label)),
  ) as HTMLSelectElement;
  setSelect.value = state.set;
  updateSetTitle();

  const raritySelect = h(
    "select",
    {
      class: "rarity-select",
      onchange: (e: Event) => {
        state.rarity = (e.target as HTMLSelectElement).value;
        emit();
      },
    },
    h("option", { value: "" }, "Any rarity"),
    ...RARITIES.map((r) => h("option", { value: r }, r)),
  ) as HTMLSelectElement;
  raritySelect.value = state.rarity;

  const resetButton = h(
    "button",
    {
      type: "button",
      class: "reset-button",
      onclick: () => {
        Object.assign(state, emptyFilter());
        searchInput.value = "";
        manaMin.value = "";
        manaMax.value = "";
        priceMin.value = "";
        priceMax.value = "";
        typeInput.value = "";
        setSelect.value = "";
        updateSetTitle();
        raritySelect.value = "";
        colorPips.forEach((btn) => btn.classList.remove("active"));
        emit();
      },
    },
    "Reset",
  );

  const copyLinkButton = h(
    "button",
    {
      type: "button",
      class: "copy-link-button",
      title: "Copy a link to this exact filtered view",
      onclick: () => {
        void navigator.clipboard.writeText(location.href).then(
          () => {
            const original = copyLinkButton.textContent;
            copyLinkButton.textContent = "Copied!";
            window.setTimeout(() => {
              copyLinkButton.textContent = original;
            }, 1200);
          },
          () => {
            // Clipboard API unavailable/denied - the URL is already up to
            // date in the address bar, so it's still copyable by hand.
          },
        );
      },
    },
    "Copy link",
  );

  return h(
    "div",
    { class: "filter-bar" },
    searchInput,
    h("div", { class: "color-pips" }, ...colorPips),
    h("label", { class: "range-group" }, "MV", manaMin, "–", manaMax),
    typeInput,
    raritySelect,
    setSelect,
    h("label", { class: "range-group" }, "€", priceMin, "–", priceMax),
    resetButton,
    copyLinkButton,
  );
}
