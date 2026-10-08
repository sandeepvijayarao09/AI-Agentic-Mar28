from datetime import datetime

import pytest

from api.services import order_parser as op
from tests import fixture_emails as fx


@pytest.mark.parametrize(
    "email, platform",
    [
        (fx.DOORDASH, "doordash"),
        (fx.UBER_EATS, "ubereats"),
        (fx.GRUBHUB, "grubhub"),
        (fx.AMAZON, "amazon"),
        (fx.AMAZON_SHIPPED, "amazon"),
        (fx.WALMART, "walmart"),
    ],
)
def test_detect_platform(email, platform):
    assert op.detect_platform(email) == platform


def test_detect_platform_unknown_sender():
    assert op.detect_platform({"from": "friend@example.com", "subject": "lunch?", "body": "see you at noon"}) is None


def test_every_fixture_is_an_order_email():
    assert all(op.is_order_email(e) for e in fx.ALL_ORDERS)


def test_promotional_email_is_not_an_order():
    assert not op.is_order_email(fx.NEWSLETTER)
    assert op.parse_shopping_order(fx.NEWSLETTER) is None


def test_doordash_order():
    order = op.parse_food_order(fx.DOORDASH)
    assert order["platform"] == "doordash"
    assert order["restaurant_name"] == "Chipotle Mexican Grill"
    assert order["total"] == 33.87
    assert order["order_date"] == datetime(2026, 3, 21, 19, 42, 10)
    assert order["items"] == [
        {"name": "Chicken Burrito Bowl", "qty": 1, "price": 11.45},
        {"name": "Chips & Guacamole", "qty": 2, "price": 4.95},
        {"name": "Mexican Coca-Cola", "qty": 1, "price": 3.25},
    ]
    assert order["gmail_message_id"] == "msg-doordash-1"


def test_uber_eats_order_uses_date_header():
    order = op.parse_food_order(fx.UBER_EATS)
    assert order["platform"] == "ubereats"
    assert order["restaurant_name"] == "Panda Express"
    assert order["total"] == 17.10
    assert order["order_date"] == datetime(2026, 3, 26, 20, 11)
    assert [i["name"] for i in order["items"]] == ["Orange Chicken Bowl", "Chow Mein"]


def test_grubhub_order_without_qty_prefix_and_without_date_header():
    order = op.parse_food_order(fx.GRUBHUB)
    assert order["restaurant_name"] == "Sweetgreen"
    assert order["total"] == 29.11
    assert order["order_date"] == datetime(2026, 3, 18)
    # Tax line must not be mistaken for an item.
    assert order["items"] == [
        {"name": "Harvest Bowl", "qty": 1, "price": 14.95},
        {"name": "Kale Caesar", "qty": 1, "price": 12.45},
    ]


def test_amazon_order_keeps_digits_in_item_names():
    order = op.parse_shopping_order(fx.AMAZON)
    assert order["platform"] == "amazon"
    assert order["order_number"] == "112-4839201-7765432"
    assert order["total"] == 66.91
    assert order["items"] == [
        {"name": "Anker USB C Charger 65W", "qty": 1, "price": 35.99},
        {"name": "AmazonBasics AA Batteries 24 Pack", "qty": 2, "price": 13.49},
    ]


def test_amazon_shipped_email():
    order = op.parse_shopping_order(fx.AMAZON_SHIPPED)
    assert order["order_number"] == "113-0042817-5521098"
    assert order["items"] == [{"name": "Sony WH-1000XM5 Wireless Headphones", "qty": 1, "price": 328.0}]
    assert order["total"] == 328.0


def test_walmart_order():
    order = op.parse_shopping_order(fx.WALMART)
    assert order["platform"] == "walmart"
    assert order["order_number"] == "2000131-44590"
    assert order["total"] == 5.30
    assert [i["price"] for i in order["items"]] == [3.68, 1.62]


def test_food_and_shopping_parsers_do_not_overlap():
    assert op.parse_shopping_order(fx.DOORDASH) is None
    assert op.parse_food_order(fx.AMAZON) is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Order Total: $1,204.50", 1204.50),
        ("Total: $17.10", 17.10),
        ("You were charged $8.00", 8.00),
        ("Items $3.00 and $12.99, no label", 12.99),
        ("nothing here", 0.0),
    ],
)
def test_extract_total(text, expected):
    assert op.extract_total(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Your order #112-1234567-8901234", "112-1234567-8901234"),
        ("Order # ABC-123456", "ABC-123456"),
        ("Confirmation #: XK29PQ77", "XK29PQ77"),
        ("no id at all", ""),
    ],
)
def test_extract_order_number(text, expected):
    assert op.extract_order_number(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Sat, 21 Mar 2026 19:42:10 -0700", datetime(2026, 3, 21, 19, 42, 10)),
        ("Placed on March 16, 2026", datetime(2026, 3, 16)),
        ("03/18/2026", datetime(2026, 3, 18)),
        ("2026-03-10", datetime(2026, 3, 10)),
        ("", None),
        ("no date", None),
    ],
)
def test_parse_date(text, expected):
    assert op.parse_date(text) == expected


def test_gemini_fallback_fills_missing_fields(monkeypatch):
    sparse = {
        "id": "msg-sparse",
        "from": "DoorDash <no-reply@doordash.com>",
        "subject": "Your order is confirmed",
        "date": "",
        "snippet": "",
        "body": "Your order is confirmed. View receipt in the app.",
    }
    monkeypatch.setattr(
        op,
        "extract_with_gemini",
        lambda email: {
            "order_id": "DD-1",
            "name": "Shake Shack",
            "items": [{"name": "ShackBurger", "qty": 1, "price": 7.89}],
            "total": 9.5,
            "date": "2026-03-20",
        },
    )
    order = op.parse_food_order(sparse)
    assert order["restaurant_name"] == "Shake Shack"
    assert order["total"] == 9.5
    assert order["order_date"] == datetime(2026, 3, 20)


def test_extract_with_gemini_without_key_returns_none(monkeypatch):
    monkeypatch.undo()  # restore the real function; no key is set, so it must not call out
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert op.extract_with_gemini(fx.DOORDASH) is None
