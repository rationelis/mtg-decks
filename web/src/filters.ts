import type { CardData } from "./types";

export interface FilterState {
  search: string;
  colors: Set<string>; // subset of W/U/B/R/G/C
  manaMin: number | null;
  manaMax: number | null;
  type: string;
  rarity: string;
  set: string;
  priceMin: number | null;
  priceMax: number | null;
}

export function emptyFilter(): FilterState {
  return {
    search: "",
    colors: new Set(),
    manaMin: null,
    manaMax: null,
    type: "",
    rarity: "",
    set: "",
    priceMin: null,
    priceMax: null,
  };
}

export function isFilterEmpty(f: FilterState): boolean {
  return (
    f.search === "" &&
    f.colors.size === 0 &&
    f.manaMin === null &&
    f.manaMax === null &&
    f.type === "" &&
    f.rarity === "" &&
    f.set === "" &&
    f.priceMin === null &&
    f.priceMax === null
  );
}

export function cloneFilter(f: FilterState): FilterState {
  return { ...f, colors: new Set(f.colors) };
}

// Query-string keys are short so a shared link stays readable.
const PARAM_KEYS = {
  search: "q",
  colors: "colors",
  manaMin: "mvmin",
  manaMax: "mvmax",
  type: "type",
  rarity: "rarity",
  set: "set",
  priceMin: "pricemin",
  priceMax: "pricemax",
} as const;

/** Serializes a filter into URL query params, so the current filter state
 * (e.g. "set=rea") can be copied out of the address bar and shared as a
 * link that opens pre-filtered for someone else. Omits anything at its
 * default/empty value, so an unfiltered view has no query string at all. */
export function filterToParams(f: FilterState): URLSearchParams {
  const params = new URLSearchParams();
  if (f.search) params.set(PARAM_KEYS.search, f.search);
  if (f.colors.size > 0) params.set(PARAM_KEYS.colors, [...f.colors].join(""));
  if (f.manaMin !== null) params.set(PARAM_KEYS.manaMin, String(f.manaMin));
  if (f.manaMax !== null) params.set(PARAM_KEYS.manaMax, String(f.manaMax));
  if (f.type) params.set(PARAM_KEYS.type, f.type);
  if (f.rarity) params.set(PARAM_KEYS.rarity, f.rarity);
  if (f.set) params.set(PARAM_KEYS.set, f.set);
  if (f.priceMin !== null) params.set(PARAM_KEYS.priceMin, String(f.priceMin));
  if (f.priceMax !== null) params.set(PARAM_KEYS.priceMax, String(f.priceMax));
  return params;
}

/** Inverse of filterToParams(), used to seed a view's filter state from
 * whatever query string was on the URL (e.g. a shared link) when it loaded. */
export function filterFromParams(params: URLSearchParams): FilterState {
  const f = emptyFilter();

  const search = params.get(PARAM_KEYS.search);
  if (search) f.search = search;

  const colors = params.get(PARAM_KEYS.colors);
  if (colors) {
    for (const c of colors.toUpperCase()) {
      if ("WUBRGC".includes(c)) f.colors.add(c);
    }
  }

  const manaMin = params.get(PARAM_KEYS.manaMin);
  if (manaMin !== null && manaMin !== "" && !Number.isNaN(Number(manaMin))) {
    f.manaMin = Number(manaMin);
  }
  const manaMax = params.get(PARAM_KEYS.manaMax);
  if (manaMax !== null && manaMax !== "" && !Number.isNaN(Number(manaMax))) {
    f.manaMax = Number(manaMax);
  }

  const type = params.get(PARAM_KEYS.type);
  if (type) f.type = type;

  const rarity = params.get(PARAM_KEYS.rarity);
  if (rarity) f.rarity = rarity;

  const set = params.get(PARAM_KEYS.set);
  if (set) f.set = set;

  const priceMin = params.get(PARAM_KEYS.priceMin);
  if (priceMin !== null && priceMin !== "" && !Number.isNaN(Number(priceMin))) {
    f.priceMin = Number(priceMin);
  }
  const priceMax = params.get(PARAM_KEYS.priceMax);
  if (priceMax !== null && priceMax !== "" && !Number.isNaN(Number(priceMax))) {
    f.priceMax = Number(priceMax);
  }

  return f;
}

export function matchesFilter(card: CardData, f: FilterState): boolean {
  if (f.search) {
    const q = f.search.toLowerCase();
    const haystack = `${card.name} ${card.oracle_text}`.toLowerCase();
    if (!haystack.includes(q)) return false;
  }

  if (f.colors.size > 0) {
    const cardColors = new Set(card.colors.length > 0 ? card.colors : ["C"]);
    if (cardColors.size !== f.colors.size) return false;
    for (const c of cardColors) {
      if (!f.colors.has(c)) return false;
    }
  }

  if (f.manaMin !== null && card.mana_value < f.manaMin) return false;
  if (f.manaMax !== null && card.mana_value > f.manaMax) return false;

  if (f.type && !card.type_line.toLowerCase().includes(f.type.toLowerCase())) {
    return false;
  }

  if (f.rarity && card.rarity !== f.rarity) return false;

  if (f.set && card.set !== f.set) return false;

  const price = card.price_eur;
  if (f.priceMin !== null && (price === null || price < f.priceMin)) return false;
  if (f.priceMax !== null && (price === null || price > f.priceMax)) return false;

  return true;
}
