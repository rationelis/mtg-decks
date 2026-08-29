import type { BuildMeta, CardList, CardsIndex, IndexEntry } from "./types";

// import.meta.env.BASE_URL already ends with "/" (Vite guarantees this).
const DATA_BASE = `${import.meta.env.BASE_URL}data/`;

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(DATA_BASE + path);
  if (!res.ok) {
    throw new Error(`Failed to load ${path}: HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

// Every JSON file is fetched at most once per page load and memoized as a
// singleton promise, so navigating between views never re-downloads data
// that's already in memory - this is the whole "quick and lazy" strategy:
// nothing loads until a view needs it, and nothing loads twice.
function memoize<T>(loader: () => Promise<T>): () => Promise<T> {
  let promise: Promise<T> | null = null;
  return () => {
    if (!promise) {
      promise = loader().catch((err) => {
        promise = null; // allow retrying after a transient failure
        throw err;
      });
    }
    return promise;
  };
}

export const getCards = memoize(() => fetchJson<CardsIndex>("cards.json"));
export const getBulk = memoize(() => fetchJson<CardList>("bulk.json"));
export const getIndex = memoize(() => fetchJson<IndexEntry[]>("index.json"));
export const getMeta = memoize(() => fetchJson<BuildMeta>("meta.json"));

const listLoaders = new Map<string, () => Promise<CardList>>();

export function getList(kind: string, id: string): Promise<CardList> {
  const key = `${kind}-${id}`;
  let loader = listLoaders.get(key);
  if (!loader) {
    loader = memoize(() => fetchJson<CardList>(`lists/${key}.json`));
    listLoaders.set(key, loader);
  }
  return loader();
}
