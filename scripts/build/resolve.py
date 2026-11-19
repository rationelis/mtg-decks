"""Resolve card names into normalized identity metadata via the Scryfall API.

Scryfall is used for identity only (name, mana cost/value, colors, type,
oracle text, set, rarity, image, scryfall page link) - never for price.
Pricing comes exclusively from cache/bulk-prices.json / cache/list-prices.json
(real Cardmarket prices fetched via Archidekt, see build.py). A card with
no entry there simply has no price; that's a signal to mirror it into
your Archidekt bulk deck and re-run the build, not something this module
tries to guess at.

Identity fields are cached indefinitely in cache/card-data.json, keyed by
a normalized name, and re-fetched over the network on every build in
batches of up to 75 names via Scryfall's /cards/collection endpoint. If
the network is unavailable, previously-confidently-resolved cached
identity data is reused (never a fuzzy-matched guess) - the build degrades
gracefully rather than failing; anything that was never confidently
resolved before is a hard error (see REFACTOR.md §6.2).

A name can optionally be pinned to a specific printing (e.g. "Mystical
Tutor (DMR) 289" in a source file, see parse.py). Every such pin is
verified directly via /cards/{set}/{number} and must both exist and
actually be a printing of that same card - a mismatch is always a hard
error. A conflicting pin (one that disagrees with what bulk.txt records
as owned) is only a hard error when it comes from bulk.txt itself or a
real active deck (see parse.is_real_active_deck) - collections,
wishlists, proxy decks, and archived decks are exempt, since their pins
are aspirational/informational, not a claim about a physical card you
own (see REFACTOR.md §6.1/§9.3). This never changes the lookup key,
which stays the bare oracle name, so ownership diffing is unaffected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from net import get_json, post_json
from parse import BuildError, CardList, is_real_active_deck, normalize_name, printing_key

COLLECTION_URL = "https://api.scryfall.com/cards/collection"
NAMED_FUZZY_URL = "https://api.scryfall.com/cards/named"
CARD_BY_SET_NUMBER_URL = "https://api.scryfall.com/cards/{set}/{number}"
BATCH_SIZE = 75


@dataclass
class PrintingData:
    """The per-printing slice of a card: everything that can differ
    between two printings of the same oracle card (art, set, rarity,
    and - crucially - price). Keyed by parse.printing_key in
    CardData.printings."""

    set: str = ""
    set_name: str = ""
    rarity: str = ""
    image_uri: str | None = None
    scryfall_uri: str | None = None
    released_at: str | None = None
    price_eur: float | None = None
    price_state: str = "unavailable"  # "exact" | "fallback" | "unavailable"


@dataclass
class CardData:
    name: str
    mana_cost: str = ""
    mana_value: float = 0.0
    colors: list[str] = field(default_factory=list)
    color_identity: list[str] = field(default_factory=list)
    type_line: str = ""
    oracle_text: str = ""
    set: str = ""
    set_name: str = ""
    rarity: str = ""
    image_uri: str | None = None
    scryfall_uri: str | None = None
    scryfall_id: str | None = None
    price_eur: float | None = None
    price_state: str = "unavailable"  # "exact" | "fallback" | "unavailable"
    released_at: str | None = None
    last_checked: str | None = None
    fuzzy_matched_from: str | None = None
    # Every verified printing pin for this card across bulk + lists. The
    # top-level fields above describe the *default* printing (the
    # authoritative pin); a list entry that pins a different printing is
    # shown using its own entry here instead.
    printings: dict[str, PrintingData] = field(default_factory=dict)


@dataclass(frozen=True)
class PinOccurrence:
    """One "(SET) NUM" printing pin found in a source file."""

    path: str
    line: int
    name: str
    set: str
    collector_number: str
    is_bulk: bool
    binding: bool  # must agree with bulk.txt's pin, or it's a conflict (see §9.3)


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
        mana_cost=_mana_cost(card),
        mana_value=card.get("cmc", 0.0),
        colors=_face_colors(card),
        color_identity=card.get("color_identity", []),
        type_line=card.get("type_line", ""),
        oracle_text=_oracle_text(card),
        set=card.get("set", ""),
        set_name=card.get("set_name", ""),
        rarity=card.get("rarity", ""),
        image_uri=_image_uri(card),
        scryfall_uri=card.get("scryfall_uri"),
        scryfall_id=card.get("id"),
        released_at=card.get("released_at"),
        last_checked=now,
    )


def _printing_of(data: CardData) -> PrintingData:
    """The per-printing slice of a freshly resolved CardData (no price -
    prices are applied separately, see apply_bulk_prices)."""
    return PrintingData(
        set=data.set,
        set_name=data.set_name,
        rarity=data.rarity,
        image_uri=data.image_uri,
        scryfall_uri=data.scryfall_uri,
        released_at=data.released_at,
    )


def _cached_printing(cached: dict[str, Any]) -> PrintingData:
    return PrintingData(
        set=str(cached.get("set", "")),
        set_name=str(cached.get("set_name", "")),
        rarity=str(cached.get("rarity", "")),
        image_uri=cached.get("image_uri"),
        scryfall_uri=cached.get("scryfall_uri"),
        released_at=cached.get("released_at"),
    )


def _cached_card_data(name: str, cached: dict[str, Any]) -> CardData:
    """Explicit field-by-field extraction (rather than **cached) so a
    malformed/older cache entry can't crash the build - anything missing
    just falls back to CardData's own defaults."""
    return CardData(
        name=str(cached.get("name", name)),
        mana_cost=str(cached.get("mana_cost", "")),
        mana_value=float(cached.get("mana_value", 0.0)),
        colors=list(cached.get("colors", [])),
        color_identity=list(cached.get("color_identity", [])),
        type_line=str(cached.get("type_line", "")),
        oracle_text=str(cached.get("oracle_text", "")),
        set=str(cached.get("set", "")),
        set_name=str(cached.get("set_name", "")),
        rarity=str(cached.get("rarity", "")),
        image_uri=cached.get("image_uri"),
        scryfall_uri=cached.get("scryfall_uri"),
        scryfall_id=cached.get("scryfall_id"),
        price_eur=None,
        released_at=cached.get("released_at"),
        last_checked=cached.get("last_checked"),
        printings={
            str(k): _cached_printing(v)
            for k, v in (cached.get("printings") or {}).items()
            if isinstance(v, dict)
        },
    )


def load_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    import json

    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text(encoding="utf-8"))


def save_cache(cache_path: Path, cache: dict[str, dict[str, Any]]) -> None:
    import json

    cache_path.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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


def collect_pins(bulk: CardList, lists: list[CardList]) -> dict[str, list[PinOccurrence]]:
    """Every "(SET) NUM" printing pin found across bulk + every list,
    grouped by normalized card name key."""
    pins: dict[str, list[PinOccurrence]] = {}
    for card_list in [bulk, *lists]:
        is_bulk = card_list.kind == "bulk"
        binding = is_bulk or is_real_active_deck(card_list)
        for entry in card_list.entries:
            if not (entry.set and entry.collector_number):
                continue
            key = normalize_name(entry.name)
            pins.setdefault(key, []).append(
                PinOccurrence(
                    path=card_list.source_path,
                    line=entry.line,
                    name=entry.name,
                    set=entry.set,
                    collector_number=entry.collector_number,
                    is_bulk=is_bulk,
                    binding=binding,
                )
            )
    return pins


def resolve_pin_conflicts(
    pins: dict[str, list[PinOccurrence]],
) -> tuple[dict[str, PinOccurrence], list[BuildError]]:
    """For each key with one or more pins, pick the authoritative pin for
    identity/price-matching purposes, and flag any *binding* pin outside
    bulk.txt that disagrees with it as a BuildError (see REFACTOR.md
    §6.1/§9.3).

    bulk.txt is the sole source of truth for "what you physically have" -
    its own pin(s) are authoritative, and never conflict with each other
    even when there's more than one (owning two different printings of
    the same card is normal; that's two lines in bulk.txt, not a
    conflict). A pin in a real active deck (see parse.is_real_active_deck)
    is only flagged when bulk.txt has at least one pin for that name and
    this one matches none of them - i.e. it claims a printing you don't
    have recorded as owned. Non-binding pins (collections/wishlists,
    proxy decks, archived decks) never conflict with anything - a
    wishlist pin records a printing you'd like to acquire, not one you
    already own, so it has nothing to disagree with. When bulk.txt has no
    pin for a name at all (e.g. a basic land, or simply never pinned),
    there is no physical truth to disagree with, so every file's choice
    of pin for that name is treated as a non-binding display preference -
    including when two non-bulk files disagree with each other.

    Returns (authoritative pin per key - used to pick a display printing
    and to judge price exactness, errors).
    """
    authoritative: dict[str, PinOccurrence] = {}
    errors: list[BuildError] = []

    for key, occurrences in pins.items():
        bulk_occs = [o for o in occurrences if o.is_bulk]
        if not bulk_occs:
            # No physical truth recorded for this name - nothing to
            # arbitrate; still pick a deterministic representative for
            # display purposes.
            authoritative[key] = min(occurrences, key=lambda o: (o.path, o.line))
            continue

        chosen = min(bulk_occs, key=lambda o: o.line)
        authoritative[key] = chosen
        owned_pins = {(o.set.lower(), o.collector_number.lower()) for o in bulk_occs}

        for occ in occurrences:
            if occ.is_bulk:
                continue  # bulk's own multiple pins never conflict with each other
            if not occ.binding:
                continue  # collection/proxy/archived pin - never a conflict
            if (occ.set.lower(), occ.collector_number.lower()) in owned_pins:
                continue  # matches a printing actually recorded as owned
            errors.append(
                BuildError(
                    path=occ.path,
                    line=occ.line,
                    message=(
                        f'Conflicting printing pin for "{occ.name}": '
                        f"({occ.set}) {occ.collector_number} here, but bulk.txt has "
                        f"({chosen.set}) {chosen.collector_number} at "
                        f"{chosen.path}:{chosen.line}."
                    ),
                )
            )

    return authoritative, errors


def _collection_identifier(name: str) -> str:
    """The name text to send to Scryfall's /cards/collection endpoint.

    That endpoint - unlike /cards/named?exact= - does not match a
    split/DFC/adventure card's combined "Front // Back" name; only its
    front face resolves. The canonical card is still found (and its
    `name` field in the response is the full combined name, matching
    what source files write), so this only affects what text is sent,
    never what key the result is stored/looked up under.
    """
    return name.partition(" // ")[0].strip()


def _occurrences_by_key(bulk: CardList, lists: list[CardList]) -> dict[str, list[tuple[str, int]]]:
    occurrences: dict[str, list[tuple[str, int]]] = {}
    for card_list in [bulk, *lists]:
        for entry in card_list.entries:
            key = normalize_name(entry.name)
            occurrences.setdefault(key, []).append((card_list.source_path, entry.line))
    return occurrences


def _name_by_key(bulk: CardList, lists: list[CardList]) -> dict[str, str]:
    """First-seen raw name text per normalized key (bulk checked first,
    since it best represents what's physically written on the card)."""
    names: dict[str, str] = {}
    for card_list in [bulk, *lists]:
        for entry in card_list.entries:
            key = normalize_name(entry.name)
            names.setdefault(key, entry.name)
    return names


def resolve_identity(
    bulk: CardList,
    lists: list[CardList],
    cache: dict[str, dict[str, Any]],
) -> tuple[dict[str, CardData], dict[str, PinOccurrence], list[BuildError], list[str]]:
    """Resolve every unique card name referenced by bulk + lists into a
    CardData, updating `cache` in place. Returns (card_data keyed by
    normalized name, authoritative pins keyed by normalized name, hard
    errors, warnings).
    """
    errors: list[BuildError] = []
    warnings: list[str] = []
    result: dict[str, CardData] = {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    name_by_key = _name_by_key(bulk, lists)
    occurrences_by_key = _occurrences_by_key(bulk, lists)
    all_keys = set(name_by_key)

    pins_by_key = collect_pins(bulk, lists)
    authoritative_pins, pin_errors = resolve_pin_conflicts(pins_by_key)
    errors.extend(pin_errors)

    pending_keys = sorted(all_keys)
    batches = [pending_keys[i : i + BATCH_SIZE] for i in range(0, len(pending_keys), BATCH_SIZE)]

    not_found_keys: list[str] = []

    for batch_keys in batches:
        identifiers = [{"name": _collection_identifier(name_by_key[k])} for k in batch_keys]
        try:
            response = post_json(COLLECTION_URL, {"identifiers": identifiers})
        except requests.RequestException as e:
            warnings.append(
                f"Scryfall unreachable ({e}); falling back to cached data for this batch."
            )
            for key in batch_keys:
                _use_cache_or_error(key, name_by_key, occurrences_by_key, cache, result, errors, warnings)
            continue

        found_keys: set[str] = set()
        for card in response.get("data", []):
            data = _card_to_data(card, now)
            # Scryfall's /cards/collection only returns a card in `data`
            # when the requested identifier was an exact (case-insensitive)
            # name match, so the normalized requested name and the
            # normalized canonical name are the same key.
            key = normalize_name(data.name)
            result[key] = data
            cache[key] = asdict(data)
            found_keys.add(key)

        for key in batch_keys:
            if key not in found_keys:
                not_found_keys.append(key)

    # Fuzzy lookup for anything not found - suggestion only, never
    # auto-accepted into `result` (see REFACTOR.md §6.2).
    for key in not_found_keys:
        name = name_by_key[key]
        suggestion: str | None = None
        try:
            card = get_json(NAMED_FUZZY_URL, {"fuzzy": name})
            if card is not None:
                suggestion = card.get("name")
        except requests.RequestException:
            pass  # suggestion is best-effort only; absence doesn't change anything

        message = f'Unknown card name: "{name}"'
        if suggestion and normalize_name(suggestion) != key:
            message += f' (did you mean "{suggestion}"?)'

        if _use_cache_or_error(
            key, name_by_key, occurrences_by_key, cache, result, errors, warnings, force_error_message=message
        ):
            continue

    # Pin verification: every distinct pinned printing (not just the
    # authoritative one per name) must exist on Scryfall and actually be a
    # printing of the pinned name. Each verified printing is recorded on
    # the card's `printings`; the authoritative one also becomes the
    # card's default printing.
    for key in sorted(pins_by_key):
        if key not in result:
            continue  # the name itself already errored above

        authoritative = authoritative_pins[key]
        # One representative occurrence per distinct printing, used for
        # error attribution and messages. The authoritative pin always
        # represents its own printing.
        representatives: dict[str, PinOccurrence] = {
            printing_key(authoritative.set, authoritative.collector_number): authoritative
        }
        for occ in sorted(pins_by_key[key], key=lambda o: (o.path, o.line)):
            representatives.setdefault(printing_key(occ.set, occ.collector_number), occ)

        default_data: CardData | None = None
        verified: dict[str, PrintingData] = {}

        for pkey, pin in representatives.items():
            try:
                card = get_json(
                    CARD_BY_SET_NUMBER_URL.format(
                        set=pin.set.lower(), number=pin.collector_number
                    )
                )
            except requests.RequestException as e:
                warnings.append(
                    f"Could not verify pinned printing '({pin.set}) {pin.collector_number}' for "
                    f"'{result[key].name}' ({e}); keeping its default printing."
                )
                continue

            if card is None:
                errors.append(
                    BuildError(
                        path=pin.path,
                        line=pin.line,
                        message=(
                            f"Pinned printing ({pin.set}) {pin.collector_number} was not found "
                            "on Scryfall."
                        ),
                    )
                )
                continue

            pinned_key = normalize_name(card.get("name", ""))
            if pinned_key != key:
                errors.append(
                    BuildError(
                        path=pin.path,
                        line=pin.line,
                        message=(
                            f"Pinned printing ({pin.set}) {pin.collector_number} does not match "
                            f'"{pin.name}" - that printing is a different card '
                            f'("{card.get("name", "")}").'
                        ),
                    )
                )
                continue

            printing = _card_to_data(card, now)
            verified[pkey] = _printing_of(printing)
            if pin is authoritative:
                default_data = printing

        if default_data is not None:
            default_data.printings = dict(result[key].printings)
            result[key] = default_data
        result[key].printings.update(verified)
        cache[key] = asdict(result[key])

    return result, authoritative_pins, errors, warnings


def _use_cache_or_error(
    key: str,
    name_by_key: dict[str, str],
    occurrences_by_key: dict[str, list[tuple[str, int]]],
    cache: dict[str, dict[str, Any]],
    result: dict[str, CardData],
    errors: list[BuildError],
    warnings: list[str],
    force_error_message: str | None = None,
) -> bool:
    """Try to satisfy `key` from a confidently-resolved cache entry;
    otherwise append a BuildError per occurrence of that name and return
    True (signalling "this key failed"). A cache entry only counts as
    confidently resolved if it was previously resolved exactly (never a
    fuzzy guess) - see REFACTOR.md §6.2.
    """
    if key in result:
        return False

    name = name_by_key[key]
    cached = cache.get(key)
    if force_error_message is None and cached and not cached.get("fuzzy_matched_from"):
        result[key] = _cached_card_data(name, cached)
        warnings.append(f"Scryfall unreachable for '{name}'; reused previously-resolved cache entry.")
        return False

    message = force_error_message or (
        f"Scryfall unreachable and \"{name}\" was never confidently resolved before."
    )
    for path, line in occurrences_by_key.get(key, []):
        errors.append(BuildError(path=path, line=line, message=message))
    return True


def _priced_printings(entry: Any) -> list[tuple[str, str, float]]:
    """Normalize one bulk-prices.json value into (set, collector_number,
    price) tuples, skipping unpriced rows. Accepts the current format (a
    list of {price_eur, set, collector_number}), the previous
    one-printing-per-name dict, and the original flat-float format (no
    printing info available).
    """
    if isinstance(entry, list):
        rows = [r for r in entry if isinstance(r, dict)]
    elif isinstance(entry, dict):
        rows = [entry]
    else:
        rows = [{"price_eur": entry}]

    priced: list[tuple[str, str, float]] = []
    for row in rows:
        price = row.get("price_eur")
        if price is None:
            continue
        priced.append((str(row.get("set", "")), str(row.get("collector_number", "")), price))
    return priced


def apply_bulk_prices(
    card_data: dict[str, CardData],
    bulk_prices: dict[str, Any],
    pins: dict[str, PinOccurrence],
) -> int:
    """Set real Cardmarket prices from the bulk-mirror price cache.

    Every priced row whose (set, number) is one of the card's pinned
    printings prices that printing exactly, so two owned printings of
    one card each keep their own price. The card's own (default)
    price_eur/price_state describes its default printing, i.e. the
    authoritative pin: "exact" when that printing has its own price,
    otherwise the cheapest priced printing of the same name marked
    "fallback" (a real price for a copy you own, but not for the printing
    currently displayed). With no pin at all there's no way to tell
    which printing is displayed, so the cheapest priced one is used and
    called "exact". Always wins over apply_list_prices - it reflects a
    card you actually own. Returns how many cards were priced.
    """
    applied = 0
    for key, entry in bulk_prices.items():
        data = card_data.get(key)
        if data is None:
            continue
        priced = _priced_printings(entry)
        if not priced:
            continue

        by_printing: dict[str, float] = {}
        for set_code, number, price in priced:
            if set_code and number:
                by_printing[printing_key(set_code, number)] = price

        for pkey, printing in data.printings.items():
            if pkey in by_printing:
                printing.price_eur = by_printing[pkey]
                printing.price_state = "exact"

        pin = pins.get(key)
        pin_price = (
            by_printing.get(printing_key(pin.set, pin.collector_number)) if pin is not None else None
        )
        if pin_price is not None:
            data.price_eur = pin_price
            data.price_state = "exact"
        else:
            data.price_eur = min(price for _, _, price in priced)
            data.price_state = "exact" if pin is None else "fallback"
        applied += 1
    return applied


def apply_list_prices(
    card_data: dict[str, CardData], list_prices: dict[str, float]
) -> int:
    """Fill in a reference Cardmarket price for cards you don't own, from
    one or more reference decks - e.g. a wishlist mirrored from a public
    Archidekt decklist, so its "price to complete" is real instead of
    always "-". Always "fallback": a list price is a reference/wishlist
    estimate, never "your" copy, regardless of whether it happens to
    match a pinned printing. Only fills gaps: never overwrites a price
    already set by apply_bulk_prices. Returns how many cards were priced.
    """
    applied = 0
    for key, price in list_prices.items():
        data = card_data.get(key)
        if data is not None and data.price_eur is None:
            data.price_eur = price
            data.price_state = "fallback"
            applied += 1
    return applied


def fill_printing_prices(card_data: dict[str, CardData]) -> None:
    """Give every pinned printing that has no price of its own the
    card's default price, marked "fallback" - e.g. a wishlist pins a
    printing you don't own, or one the bulk-mirror deck doesn't cover.
    Run after apply_bulk_prices and apply_list_prices so printings with
    their own exact price are never overwritten.
    """
    for data in card_data.values():
        if data.price_eur is None:
            continue
        for printing in data.printings.values():
            if printing.price_eur is None:
                printing.price_eur = data.price_eur
                printing.price_state = "fallback"
