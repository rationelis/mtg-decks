from resolve import (
    CardData,
    PinOccurrence,
    PrintingData,
    apply_bulk_prices,
    apply_list_prices,
    fill_printing_prices,
)


def _thranduil():
    """One card, two owned printings (plain + borderless)."""
    return CardData(
        name="Thranduil, the Elvenking",
        set="hob",
        printings={
            "hob/167": PrintingData(set="hob", rarity="rare"),
            "hob/246": PrintingData(set="hob", rarity="rare"),
        },
    )


def _thranduil_prices():
    return {
        "thranduil, the elvenking": [
            {"price_eur": 0.44, "set": "hob", "collector_number": "167"},
            {"price_eur": 6.8, "set": "hob", "collector_number": "246"},
        ]
    }


def test_two_owned_printings_each_keep_their_own_price():
    card = _thranduil()
    card_data = {"thranduil, the elvenking": card}
    pins = {
        "thranduil, the elvenking": PinOccurrence(
            "bulk.txt", 1, "Thranduil, the Elvenking", "HOB", "167", True, True
        )
    }

    applied = apply_bulk_prices(card_data, _thranduil_prices(), pins)

    assert applied == 1
    # Default printing (the 167 pin) is priced as itself, not as 246.
    assert card.price_eur == 0.44
    assert card.price_state == "exact"
    assert card.printings["hob/167"].price_eur == 0.44
    assert card.printings["hob/167"].price_state == "exact"
    assert card.printings["hob/246"].price_eur == 6.8
    assert card.printings["hob/246"].price_state == "exact"


def test_default_price_follows_the_authoritative_pin_regardless_of_row_order():
    card = _thranduil()
    prices = _thranduil_prices()
    prices["thranduil, the elvenking"].reverse()
    pins = {
        "thranduil, the elvenking": PinOccurrence(
            "bulk.txt", 2, "Thranduil, the Elvenking", "HOB", "246", True, True
        )
    }

    apply_bulk_prices({"thranduil, the elvenking": card}, prices, pins)

    assert card.price_eur == 6.8
    assert card.price_state == "exact"


def test_unpinned_card_with_several_priced_printings_uses_the_cheapest():
    card = CardData(name="Thranduil, the Elvenking")

    apply_bulk_prices({"thranduil, the elvenking": card}, _thranduil_prices(), pins={})

    assert card.price_eur == 0.44
    assert card.price_state == "exact"


def test_pinned_printing_without_its_own_price_falls_back_to_cheapest_owned():
    card = CardData(name="Sol Ring")
    prices = {
        "sol ring": [
            {"price_eur": 3.0, "set": "lea", "collector_number": "1"},
            {"price_eur": 1.5, "set": "c21", "collector_number": "263"},
        ]
    }
    pins = {"sol ring": PinOccurrence("bulk.txt", 1, "Sol Ring", "CMM", "400", True, True)}

    apply_bulk_prices({"sol ring": card}, prices, pins)

    assert card.price_eur == 1.5
    assert card.price_state == "fallback"


def test_fill_printing_prices_only_fills_printings_without_their_own_price():
    card = _thranduil()
    card.printings["hob/246"].price_eur = 6.8
    card.printings["hob/246"].price_state = "exact"
    card.price_eur = 0.44
    card.price_state = "exact"

    fill_printing_prices({"thranduil, the elvenking": card})

    assert card.printings["hob/246"].price_eur == 6.8  # untouched
    assert card.printings["hob/167"].price_eur == 0.44
    assert card.printings["hob/167"].price_state == "fallback"


def test_fill_printing_prices_leaves_everything_unavailable_when_card_has_no_price():
    card = _thranduil()

    fill_printing_prices({"thranduil, the elvenking": card})

    assert all(p.price_eur is None and p.price_state == "unavailable" for p in card.printings.values())


def test_apply_bulk_prices_exact_when_no_pin():
    card_data = {"sol ring": CardData(name="Sol Ring")}
    bulk_prices = {"sol ring": {"price_eur": 1.5, "set": "lea", "collector_number": "1"}}

    applied = apply_bulk_prices(card_data, bulk_prices, pins={})

    assert applied == 1
    assert card_data["sol ring"].price_eur == 1.5
    assert card_data["sol ring"].price_state == "exact"


def test_apply_bulk_prices_exact_when_pin_matches():
    card_data = {"sol ring": CardData(name="Sol Ring")}
    bulk_prices = {"sol ring": {"price_eur": 1.5, "set": "lea", "collector_number": "1"}}
    pins = {"sol ring": PinOccurrence("bulk.txt", 1, "Sol Ring", "LEA", "1", True, True)}

    apply_bulk_prices(card_data, bulk_prices, pins)

    assert card_data["sol ring"].price_state == "exact"


def test_apply_bulk_prices_fallback_when_pin_mismatches():
    card_data = {"sol ring": CardData(name="Sol Ring")}
    bulk_prices = {"sol ring": {"price_eur": 1.5, "set": "lea", "collector_number": "1"}}
    pins = {"sol ring": PinOccurrence("bulk.txt", 1, "Sol Ring", "C21", "263", True, True)}

    apply_bulk_prices(card_data, bulk_prices, pins)

    assert card_data["sol ring"].price_state == "fallback"
    assert card_data["sol ring"].price_eur == 1.5  # still applied - it's a real price


def test_apply_bulk_prices_tolerates_previous_single_dict_cache_format():
    card_data = {"sol ring": CardData(name="Sol Ring")}
    bulk_prices = {"sol ring": {"price_eur": 1.5, "set": "lea", "collector_number": "1"}}
    pins = {"sol ring": PinOccurrence("bulk.txt", 1, "Sol Ring", "LEA", "1", True, True)}

    apply_bulk_prices(card_data, bulk_prices, pins)

    assert card_data["sol ring"].price_eur == 1.5
    assert card_data["sol ring"].price_state == "exact"


def test_apply_bulk_prices_tolerates_legacy_flat_float_cache():
    card_data = {"sol ring": CardData(name="Sol Ring")}
    bulk_prices = {"sol ring": 1.5}  # old pre-refactor cache format

    applied = apply_bulk_prices(card_data, bulk_prices, pins={})

    assert applied == 1
    assert card_data["sol ring"].price_eur == 1.5
    assert card_data["sol ring"].price_state == "exact"


def test_apply_list_prices_is_always_fallback_and_only_fills_gaps():
    owned = CardData(name="Sol Ring", price_eur=2.0, price_state="exact")
    missing = CardData(name="Counterspell")
    card_data = {"sol ring": owned, "counterspell": missing}

    applied = apply_list_prices(card_data, {"sol ring": 99.0, "counterspell": 0.5})

    assert applied == 1
    assert owned.price_eur == 2.0  # untouched - owned price always wins
    assert owned.price_state == "exact"
    assert missing.price_eur == 0.5
    assert missing.price_state == "fallback"


def test_price_defaults_to_unavailable():
    data = CardData(name="Unpriced Card")
    assert data.price_eur is None
    assert data.price_state == "unavailable"
