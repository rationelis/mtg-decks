"""Emit static JSON consumed by the web app.

Only the fields the UI actually needs are written - the build is the
place where we decide what "normalized card data" means, so the
frontend never has to deal with raw Scryfall shapes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parse import CardList
from resolve import CardData

# Fields kept in cards.json. Deliberately excludes bookkeeping fields
# (last_checked, fuzzy_matched_from) that only matter for the build itself.
_CARD_FIELDS = (
    "name",
    "resolved",
    "mana_cost",
    "mana_value",
    "colors",
    "color_identity",
    "type_line",
    "oracle_text",
    "set",
    "rarity",
    "image_uri",
    "scryfall_uri",
    "price_eur",
)


def _card_json(data: CardData) -> dict[str, Any]:
    return {field: getattr(data, field) for field in _CARD_FIELDS}


def _list_json(card_list: CardList) -> dict[str, Any]:
    return {
        "id": card_list.id,
        "kind": card_list.kind,
        "status": card_list.status,
        "name": card_list.name,
        "commander": card_list.commander,
        "archidektId": card_list.archidekt_id,
        "proxy": card_list.proxy,
        "collection": card_list.collection,
        "sourcePath": card_list.source_path,
        "entries": [{"name": e.name, "qty": e.qty} for e in card_list.entries],
    }


def _index_entry(card_list: CardList) -> dict[str, Any]:
    return {
        "id": card_list.id,
        "kind": card_list.kind,
        "status": card_list.status,
        "name": card_list.name,
        "commander": card_list.commander,
        "proxy": card_list.proxy,
        "collection": card_list.collection,
        "sourcePath": card_list.source_path,
        "entryCount": len(card_list.entries),
        "totalQty": sum(e.qty for e in card_list.entries),
    }


def emit_all(
    data_dir: Path,
    bulk: CardList,
    lists: list[CardList],
    card_data: dict[str, CardData],
    warnings: list[str],
    generated_at: str,
    bulk_prices_meta: dict[str, Any] | None = None,
    list_prices_meta: dict[str, Any] | None = None,
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    lists_dir = data_dir / "lists"
    lists_dir.mkdir(parents=True, exist_ok=True)

    cards_json = {key: _card_json(data) for key, data in card_data.items()}
    _write(data_dir / "cards.json", cards_json)

    _write(data_dir / "bulk.json", _list_json(bulk))

    for card_list in lists:
        _write(lists_dir / f"{card_list.kind}-{card_list.id}.json", _list_json(card_list))

    index = [_index_entry(cl) for cl in lists]
    _write(data_dir / "index.json", index)

    unresolved = sorted(
        {data.name for data in card_data.values() if not data.resolved}
    )
    _write(
        data_dir / "meta.json",
        {
            "generatedAt": generated_at,
            "uniqueCardCount": len(card_data),
            "unresolvedCount": len(unresolved),
            "warnings": warnings,
            "bulkPrices": bulk_prices_meta,
            "listPrices": list_prices_meta,
        },
    )


def _write(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
