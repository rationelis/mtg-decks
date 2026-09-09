import { h } from "../dom";
import { emptyFilter, type FilterState } from "../filters";

const COLORS = ["W", "U", "B", "R", "G", "C"] as const;
const RARITIES = ["common", "uncommon", "rare", "mythic", "special", "bonus"];
const DEBOUNCE_MS = 150;

function numberInput(placeholder: string, onValue: (v: number | null) => void): HTMLInputElement {
  return h("input", {
    type: "number",
    step: "any",
    placeholder,
    class: "num-input",
    oninput: (e: Event) => {
      const raw = (e.target as HTMLInputElement).value;
      onValue(raw === "" ? null : Number(raw));
    },
  }) as HTMLInputElement;
}

/** Builds the shared search/filter bar used by both the bulk browser and
 * list detail views. Calls `onChange` (debounced for free-text fields)
 * whenever the filter state changes. */
export function createFilterBar(onChange: (state: FilterState) => void): HTMLElement {
  const state = emptyFilter();
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
        class: `color-pip color-${c}`,
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

  const manaMin = numberInput("Min MV", (v) => {
    state.manaMin = v;
    emitDebounced();
  });
  const manaMax = numberInput("Max MV", (v) => {
    state.manaMax = v;
    emitDebounced();
  });

  const priceMin = numberInput("Min €", (v) => {
    state.priceMin = v;
    emitDebounced();
  });
  const priceMax = numberInput("Max €", (v) => {
    state.priceMax = v;
    emitDebounced();
  });

  const typeInput = h("input", {
    type: "text",
    placeholder: "Type contains…",
    class: "type-input",
    oninput: (e: Event) => {
      state.type = (e.target as HTMLInputElement).value;
      emitDebounced();
    },
  }) as HTMLInputElement;

  const setInput = h("input", {
    type: "text",
    placeholder: "Set code…",
    class: "set-input",
    oninput: (e: Event) => {
      state.set = (e.target as HTMLInputElement).value;
      emitDebounced();
    },
  }) as HTMLInputElement;

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
        setInput.value = "";
        raritySelect.value = "";
        colorPips.forEach((btn) => btn.classList.remove("active"));
        emit();
      },
    },
    "Reset",
  );

  return h(
    "div",
    { class: "filter-bar" },
    searchInput,
    h("div", { class: "color-pips" }, ...colorPips),
    h("label", { class: "range-group" }, "MV", manaMin, "–", manaMax),
    typeInput,
    raritySelect,
    setInput,
    h("label", { class: "range-group" }, "€", priceMin, "–", priceMax),
    resetButton,
  );
}
