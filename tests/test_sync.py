"""Gmail -> SQLite sync with the Gmail API stubbed out."""

from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_favourite import UserFavourite
from api.services import sync
from tests import fixture_emails as fx


def _fake_search(emails):
    # Every query returns the whole mailbox, like an overly broad Gmail search would.
    return lambda query, max_results=50: list(emails)


def test_sync_stores_orders_once(db, monkeypatch):
    mailbox = fx.ALL_ORDERS + [fx.NEWSLETTER]
    monkeypatch.setattr(sync, "search_emails", _fake_search(mailbox))

    first = sync.sync_gmail_orders(db)
    assert first["food_synced"] == 3
    assert first["shopping_synced"] == 3
    assert first["errors"] == []
    assert db.query(FoodOrder).count() == 3
    assert db.query(Shopping).count() == 3

    second = sync.sync_gmail_orders(db)
    assert second["food_synced"] == 0
    assert second["shopping_synced"] == 0
    assert db.query(FoodOrder).count() == 3


def test_sync_reports_gmail_errors(db, monkeypatch):
    def broken(query, max_results=50):
        raise RuntimeError("Not authenticated")

    monkeypatch.setattr(sync, "search_emails", broken)
    stats = sync.sync_gmail_orders(db)
    assert stats["food_synced"] == stats["shopping_synced"] == 0
    assert len(stats["errors"]) == len(sync.FOOD_QUERIES) + len(sync.SHOPPING_QUERIES)


def test_favourites_rank_by_order_count(db, monkeypatch):
    repeat = [dict(fx.DOORDASH, id=f"dd-{i}") for i in range(3)]
    monkeypatch.setattr(sync, "search_emails", _fake_search(repeat + [fx.UBER_EATS]))
    sync.sync_gmail_orders(db)

    restaurants = (
        db.query(UserFavourite)
        .filter(UserFavourite.category == "restaurant")
        .order_by(UserFavourite.order_count.desc())
        .all()
    )
    assert [(r.name, r.order_count) for r in restaurants] == [
        ("Chipotle Mexican Grill", 3),
        ("Panda Express", 1),
    ]
    guac = db.query(UserFavourite).filter(UserFavourite.name == "Chips & Guacamole").one()
    assert guac.order_count == 6  # qty 2 across three orders
