from resolve import CardData, PinOccurrence, apply_bulk_prices, apply_list_prices


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
    pins = {"sol ring": PinOccurrence("bulk.txt", 1, "Sol Ring", "LEA", "1", True)}

    apply_bulk_prices(card_data, bulk_prices, pins)

    assert card_data["sol ring"].price_state == "exact"


def test_apply_bulk_prices_fallback_when_pin_mismatches():
    card_data = {"sol ring": CardData(name="Sol Ring")}
    bulk_prices = {"sol ring": {"price_eur": 1.5, "set": "lea", "collector_number": "1"}}
    pins = {"sol ring": PinOccurrence("bulk.txt", 1, "Sol Ring", "C21", "263", True)}

    apply_bulk_prices(card_data, bulk_prices, pins)

    assert card_data["sol ring"].price_state == "fallback"
    assert card_data["sol ring"].price_eur == 1.5  # still applied - it's a real price


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
