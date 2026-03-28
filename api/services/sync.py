"""Sync Gmail order emails to database."""

from collections import Counter
from sqlalchemy.orm import Session as DBSession

from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_favourite import UserFavourite
from api.services.gmail import search_emails
from api.services.order_parser import (
    parse_food_order,
    parse_shopping_order,
    FOOD_PLATFORMS,
    SHOPPING_PLATFORMS,
)


FOOD_QUERIES = [
    'from:doordash subject:order',
    'from:uber.com subject:receipt OR subject:order',
    'from:grubhub subject:order',
    'from:instacart subject:order OR subject:receipt',
]

SHOPPING_QUERIES = [
    'from:amazon subject:order OR subject:"your order"',
    'from:walmart subject:order',
    'from:target.com subject:order',
]


def sync_gmail_orders(db: DBSession) -> dict:
    """Sync food and shopping orders from Gmail to database."""
    stats = {"food_synced": 0, "shopping_synced": 0, "skipped": 0, "errors": []}

    # Sync food orders
    for query in FOOD_QUERIES:
        try:
            emails = search_emails(query, max_results=50)
        except Exception as e:
            stats["errors"].append(f"Query failed: {query} - {str(e)}")
            continue

        for email in emails:
            msg_id = email.get("id", "")
            if not msg_id:
                continue
            if db.query(FoodOrder).filter(FoodOrder.gmail_message_id == msg_id).first():
                stats["skipped"] += 1
                continue

            parsed = parse_food_order(email)
            if parsed:
                db.add(FoodOrder(**parsed))
                stats["food_synced"] += 1

    # Sync shopping orders
    for query in SHOPPING_QUERIES:
        try:
            emails = search_emails(query, max_results=50)
        except Exception as e:
            stats["errors"].append(f"Query failed: {query} - {str(e)}")
            continue

        for email in emails:
            msg_id = email.get("id", "")
            if not msg_id:
                continue
            if db.query(Shopping).filter(Shopping.gmail_message_id == msg_id).first():
                stats["skipped"] += 1
                continue

            parsed = parse_shopping_order(email)
            if parsed:
                db.add(Shopping(**parsed))
                stats["shopping_synced"] += 1

    db.commit()

    # Auto-populate favourites from order history
    _update_favourites(db)

    return stats


def _update_favourites(db: DBSession):
    """Analyze order history and update favourites with most ordered items."""
    # Count restaurant frequency from food orders
    food_orders = db.query(FoodOrder).all()
    restaurant_counts = Counter()
    platform_map = {}
    for order in food_orders:
        if order.restaurant_name:
            restaurant_counts[order.restaurant_name] += 1
            platform_map[order.restaurant_name] = order.platform

    # Add top restaurants as favourites
    for restaurant, count in restaurant_counts.most_common(10):
        existing = db.query(UserFavourite).filter(
            UserFavourite.name == restaurant,
            UserFavourite.category == "restaurant",
        ).first()
        if existing:
            existing.order_count = count
        else:
            db.add(UserFavourite(
                category="restaurant",
                name=restaurant,
                platform=platform_map.get(restaurant, ""),
                order_count=count,
                notes=f"Ordered {count} times",
            ))

    # Count item frequency from all orders
    item_counts = Counter()
    for order in food_orders:
        for item in (order.items or []):
            name = item.get("name", "")
            if name:
                item_counts[name] += item.get("qty", 1)

    shopping_orders = db.query(Shopping).all()
    for order in shopping_orders:
        for item in (order.items or []):
            name = item.get("name", "")
            if name:
                item_counts[name] += item.get("qty", 1)

    for item_name, count in item_counts.most_common(15):
        existing = db.query(UserFavourite).filter(
            UserFavourite.name == item_name,
            UserFavourite.category == "food_item",
        ).first()
        if existing:
            existing.order_count = count
        else:
            db.add(UserFavourite(
                category="food_item",
                name=item_name,
                order_count=count,
                notes=f"Ordered {count} times",
            ))

    db.commit()
