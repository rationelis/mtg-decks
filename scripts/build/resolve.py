"""Resolve card names into normalized identity metadata via the Scryfall API.

Scryfall is used for identity only (name, mana cost/value, colors, type,
oracle text, set, rarity, image, scryfall page link) - never for price.
Pricing comes exclusively from cache/bulk-prices.json (real Cardmarket
prices fetched via Archidekt, see scripts/fetch-bulk-prices.py /
resolve.apply_bulk_prices). A card with no entry there simply has no
price; that's a signal to mirror it into your Archidekt bulk deck and
re-run the fetch, not something this module tries to guess at.

Identity fields are cached indefinitely in cache/card-data.json, keyed by
a normalized name, and re-fetched over the network on every build in
batches of up to 75 names via Scryfall's /cards/collection endpoint. If
the network is unavailable, previously cached identity data is reused -
the build degrades gracefully rather than failing.

A name can optionally be pinned to a specific printing (e.g. "Mystical
Tutor (DMR) 289" in a source file, see parse.py); resolve_names() then
looks that printing up directly via /cards/{set}/{number} and uses its
image/set/rarity for display. This never changes the lookup key, which
stays the bare oracle name, so ownership diffing is unaffected.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parse import normalize_name

COLLECTION_URL = "https://api.scryfall.com/cards/collection"
NAMED_FUZZY_URL = "https://api.scryfall.com/cards/named"
CARD_BY_SET_NUMBER_URL = "https://api.scryfall.com/cards/{set}/{number}"
BATCH_SIZE = 75
REQUEST_DELAY = 0.25  # seconds, per Scryfall's fair-use guidance
USER_AGENT = "mtg-bulk-viewer/1.0 (+https://github.com/)"


@dataclass
class CardData:
    name: str
    resolved: bool
    mana_cost: str = ""
    mana_value: float = 0.0
    colors: list[str] = field(default_factory=list)
    color_identity: list[str] = field(default_factory=list)
    type_line: str = ""
    oracle_text: str = ""
    set: str = ""
    rarity: str = ""
    image_uri: str | None = None
    scryfall_uri: str | None = None
    scryfall_id: str | None = None
    price_eur: float | None = None
    last_checked: str | None = None
    fuzzy_matched_from: str | None = None


def _http_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    delay = REQUEST_DELAY
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(delay)
                delay *= 3
                continue
            raise
    raise urllib.error.URLError("exhausted retries")


def _http_get_json(url: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
    if params:
        query = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    delay = REQUEST_DELAY
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 and attempt < 3:
                time.sleep(delay)
                delay *= 3
                continue
            raise
    return None


def _face_colors(card: dict[str, Any]) -> list[str]:
    if "colors" in card:
        return card["colors"]
    faces = card.get("card_faces", [])
    colors: set[str] = set()
    for face in faces:
        colors.update(face.get("colors", []))
    return sorted(colors)


def _oracle_text(card: dict[str, Any]) -> str:
    if "oracle_text" in card:
        return card["oracle_text"]
    faces = card.get("card_faces", [])
    return "\n---\n".join(f.get("oracle_text", "") for f in faces)


def _mana_cost(card: dict[str, Any]) -> str:
    if "mana_cost" in card and card["mana_cost"]:
        return card["mana_cost"]
    faces = card.get("card_faces", [])
    return " // ".join(f.get("mana_cost", "") for f in faces if f.get("mana_cost"))


def _image_uri(card: dict[str, Any]) -> str | None:
    image_uris = card.get("image_uris")
    if image_uris:
        return image_uris.get("normal") or image_uris.get("small")
    faces = card.get("card_faces", [])
    if faces:
        face_images = faces[0].get("image_uris")
        if face_images:
            return face_images.get("normal") or face_images.get("small")
    return None


def _card_to_data(card: dict[str, Any], now: str) -> CardData:
    return CardData(
        name=card.get("name", ""),
        resolved=True,
        mana_cost=_mana_cost(card),
        mana_value=card.get("cmc", 0.0),
        colors=_face_colors(card),
        color_identity=card.get("color_identity", []),
        type_line=card.get("type_line", ""),
        oracle_text=_oracle_text(card),
        set=card.get("set", ""),
        rarity=card.get("rarity", ""),
        image_uri=_image_uri(card),
        scryfall_uri=card.get("scryfall_uri"),
        scryfall_id=card.get("id"),
        last_checked=now,
    )


def load_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text(encoding="utf-8"))


def save_cache(cache_path: Path, cache: dict[str, dict[str, Any]]) -> None:
    cache_path.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def resolve_names(
    names: set[str],
    cache: dict[str, dict[str, Any]],
    printing_hints: dict[str, tuple[str, str]] | None = None,
) -> tuple[dict[str, CardData], list[str]]:
    """Resolve every requested name to a CardData, updating `cache` in place.

    `printing_hints` maps a normalized name to a (set, collector_number)
    pin - e.g. from a "(DMR) 289" suffix in a source file - and only
    affects which printing's image/set/rarity is displayed; it never
    changes the lookup key, so ownership diffing stays name-based.

    Returns (name -> CardData, warnings).
    """
    warnings: list[str] = []
    result: dict[str, CardData] = {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    pending = sorted(names)
    batches = [pending[i : i + BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]

    not_found: list[str] = []

    for batch in batches:
        identifiers = [{"name": n} for n in batch]
        try:
            response = _http_post_json(COLLECTION_URL, {"identifiers": identifiers})
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            warnings.append(
                f"Scryfall unreachable ({e}); falling back to cached data for this batch."
            )
            for name in batch:
                _use_cache_fallback(name, cache, result, warnings)
            continue

        for card in response.get("data", []):
            data = _card_to_data(card, now)
            # Scryfall's /cards/collection only returns a card in `data`
            # when the requested identifier was an exact (case-insensitive)
            # name match, so the normalized requested name and the
            # normalized canonical name are the same key.
            key = normalize_name(data.name)
            result[key] = data
            cache[key] = asdict(data)

        for nf in response.get("not_found", []):
            nf_name = nf.get("name")
            if nf_name and normalize_name(nf_name) not in result:
                not_found.append(nf_name)

        time.sleep(REQUEST_DELAY)

    # Fuzzy fallback, one request at a time, for anything not_found.
    for name in not_found:
        try:
            card = _http_get_json(NAMED_FUZZY_URL, {"fuzzy": name})
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            warnings.append(f"Scryfall unreachable while fuzzy-resolving '{name}' ({e}).")
            _use_cache_fallback(name, cache, result, warnings)
            continue

        time.sleep(REQUEST_DELAY)

        if card is None:
            warnings.append(f"Unresolved card name: '{name}' (no fuzzy match found).")
            _use_cache_fallback(name, cache, result, warnings, unresolved_name=name)
            continue

        data = _card_to_data(card, now)
        if normalize_name(data.name) != normalize_name(name):
            data.fuzzy_matched_from = name
            warnings.append(
                f"Resolved '{name}' -> '{data.name}' via fuzzy match. "
                "Consider fixing the source file."
            )
        result[normalize_name(name)] = data
        cache[normalize_name(name)] = asdict(data)

    # Anything still missing from `result` (only possible if a name
    # collapses to a normalized key we've already resolved differently,
    # or a genuine unresolved miss with no cache) gets a placeholder.
    for name in names:
        key = normalize_name(name)
        if key not in result:
            _use_cache_fallback(name, cache, result, warnings, unresolved_name=name)

    if printing_hints:
        _resolve_specific_printings(result, cache, printing_hints, warnings, now)

    return result, warnings


def _resolve_specific_printings(
    result: dict[str, CardData],
    cache: dict[str, dict[str, Any]],
    printing_hints: dict[str, tuple[str, str]],
    warnings: list[str],
    now: str,
) -> None:
    """Pin the displayed printing for names annotated with a "(SET) NUM"
    suffix, via a direct Scryfall /cards/{set}/{number} lookup. Replaces
    that name's CardData with the pinned printing's identity fields; the
    result dict's key is unchanged, so this never affects diffing.
    """
    for key, (set_code, number) in printing_hints.items():
        if key not in result:
            continue
        try:
            card = _http_get_json(
                CARD_BY_SET_NUMBER_URL.format(set=set_code.lower(), number=number)
            )
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            warnings.append(
                f"Could not fetch pinned printing '({set_code}) {number}' for "
                f"'{result[key].name}' ({e}); keeping its default printing."
            )
            continue

        time.sleep(REQUEST_DELAY)

        if card is None:
            warnings.append(
                f"Pinned printing '({set_code}) {number}' not found for "
                f"'{result[key].name}'; keeping its default printing."
            )
            continue

        price = result[key].price_eur
        data = _card_to_data(card, now)
        data.price_eur = price
        result[key] = data
        cache[key] = asdict(data)


def prune_cache(cache: dict[str, dict[str, Any]], names: set[str]) -> int:
    """Drop cache entries for names no longer referenced by any list, so
    the cache doesn't grow forever and stale/mis-parsed keys don't
    linger. Returns how many entries were dropped.
    """
    keep = {normalize_name(n) for n in names}
    stale = [key for key in cache if key not in keep]
    for key in stale:
        del cache[key]
    return len(stale)


def apply_bulk_prices(
    card_data: dict[str, CardData], bulk_prices: dict[str, float]
) -> int:
    """Set price_eur to the real Cardmarket price for any card present in
    the bulk-mirror price cache (see scripts/fetch-bulk-prices.py).

    This always wins over apply_list_prices - it reflects a card you
    actually own, so it always takes priority regardless of call order.
    A card covered by neither simply has no price (None), which the UI
    shows as "-". Returns how many cards were priced.
    """
    applied = 0
    for key, price in bulk_prices.items():
        data = card_data.get(key)
        if data is not None:
            data.price_eur = price
            applied += 1
    return applied


def apply_list_prices(
    card_data: dict[str, CardData], list_prices: dict[str, float]
) -> int:
    """Fill in a reference Cardmarket price for cards you don't own, from
    one or more reference decks (see scripts/fetch-list-prices.py) - e.g.
    a wishlist mirrored from a public Archidekt decklist, so its "price
    to complete" is real instead of always "-".

    Only fills gaps: never overwrites a price already set by
    apply_bulk_prices, since an owned card's real price always wins.
    Returns how many cards were priced.
    """
    applied = 0
    for key, price in list_prices.items():
        data = card_data.get(key)
        if data is not None and data.price_eur is None:
            data.price_eur = price
            applied += 1
    return applied


def _use_cache_fallback(
    name: str,
    cache: dict[str, dict[str, Any]],
    result: dict[str, CardData],
    warnings: list[str],
    unresolved_name: str | None = None,
) -> None:
    key = normalize_name(name)
    if key in result:
        return
    cached = cache.get(key)
    if cached:
        # Explicit field-by-field extraction (rather than **cached) so a
        # malformed/older cache entry can't crash the build - anything
        # missing just falls back to CardData's own defaults.
        data = CardData(
            name=str(cached.get("name", name)),
            resolved=True,
            mana_cost=str(cached.get("mana_cost", "")),
            mana_value=float(cached.get("mana_value", 0.0)),
            colors=list(cached.get("colors", [])),
            color_identity=list(cached.get("color_identity", [])),
            type_line=str(cached.get("type_line", "")),
            oracle_text=str(cached.get("oracle_text", "")),
            set=str(cached.get("set", "")),
            rarity=str(cached.get("rarity", "")),
            image_uri=cached.get("image_uri"),
            scryfall_uri=cached.get("scryfall_uri"),
            scryfall_id=cached.get("scryfall_id"),
            price_eur=None,
            last_checked=cached.get("last_checked"),
        )
        result[key] = data
    else:
        result[key] = CardData(name=unresolved_name or name, resolved=False)
        if not unresolved_name:
            warnings.append(f"No cached or fresh data available for '{name}'.")
