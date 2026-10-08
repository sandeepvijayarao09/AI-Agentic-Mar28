"""Demo data: synthetic order-confirmation emails pushed through the real parser.

Lets the UI and the order/memory endpoints work without connecting Gmail.
Enable with DEMO_MODE=1 (seeds an empty database on startup) or run
`python scripts/seed_demo.py`. Everything here is made up.
"""

from datetime import datetime, timedelta
from email.utils import format_datetime

from sqlalchemy.orm import Session as DBSession

from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_bio import UserBio
from api.services.order_parser import parse_food_order, parse_shopping_order
from api.services.sync import _update_favourites

# (days ago, platform, restaurant, [(qty, item, price)])
FOOD = [
    (1, "doordash", "Chipotle Mexican Grill", [(1, "Chicken Burrito Bowl", 11.45), (1, "Chips & Guacamole", 4.95)]),
    (3, "ubereats", "Panda Express", [(1, "Orange Chicken Bowl", 9.80), (1, "Chow Mein", 5.20)]),
    (5, "doordash", "Chipotle Mexican Grill", [(1, "Steak Burrito", 12.35), (1, "Mexican Coca-Cola", 3.25)]),
    (8, "grubhub", "Sweetgreen", [(1, "Harvest Bowl", 14.95)]),
    (10, "doordash", "Chipotle Mexican Grill", [(1, "Chicken Burrito Bowl", 11.45)]),
    (13, "doordash", "Shake Shack", [(1, "ShackBurger", 7.89), (1, "Crinkle Cut Fries", 4.29)]),
    (17, "ubereats", "Panda Express", [(1, "Orange Chicken Bowl", 9.80)]),
    (21, "doordash", "Chipotle Mexican Grill", [(2, "Chicken Burrito Bowl", 11.45)]),
]

SHOPPING = [
    (2, "amazon", "112-4839201-7765432", [(1, "Anker USB C Charger 65W", 35.99), (2, "AmazonBasics AA Batteries 24 Pack", 13.49)]),
    (9, "amazon", "113-0042817-5521098", [(1, "Sony WH-1000XM5 Wireless Headphones", 328.00)]),
    (15, "walmart", "2000131-44590", [(1, "Great Value Whole Milk 1 Gallon", 3.68), (1, "Bananas 3 lb", 1.62)]),
    (24, "amazon", "114-7710032-0098812", [(1, "Hydro Flask 32 oz Wide Mouth", 44.95)]),
]

SENDERS = {
    "doordash": "DoorDash <no-reply@doordash.com>",
    "ubereats": "Uber Receipts <noreply@uber.com>",
    "grubhub": "Grubhub <orders@eat.grubhub.com>",
    "amazon": "Amazon.com <auto-confirm@amazon.com>",
    "walmart": "Walmart.com <help@walmart.com>",
}


def _lines(items):
    return "\n".join(f"{qty}x {name} ${price:.2f}" for qty, name, price in items)


def _total(items):
    return round(sum(q * p for q, _, p in items) * 1.08, 2)


def demo_emails(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now().replace(hour=19, minute=30, second=0, microsecond=0)
    emails = []
    for i, (days, platform, restaurant, items) in enumerate(FOOD):
        emails.append({
            "id": f"demo-food-{i}",
            "from": SENDERS[platform],
            "subject": f"Your order from {restaurant} is confirmed",
            "date": format_datetime(now - timedelta(days=days)),
            "snippet": f"Your order from {restaurant} is on its way.",
            "body": f"Order from {restaurant} - Estimated arrival 25 min\nOrder #DEMO-F{i:04d}\n{_lines(items)}\nOrder Total: ${_total(items):.2f}\n",
        })
    for i, (days, platform, order_no, items) in enumerate(SHOPPING):
        emails.append({
            "id": f"demo-shop-{i}",
            "from": SENDERS[platform],
            "subject": f"Your {platform.title()} order #{order_no}",
            "date": format_datetime((now - timedelta(days=days)).replace(hour=9)),
            "snippet": "Thanks for your order.",
            "body": f"Your order has been placed.\nOrder #{order_no}\n{_lines(items)}\nOrder Total: ${_total(items):.2f}\n",
        })
    return emails


def seed_demo_data(db: DBSession, only_if_empty: bool = True) -> dict:
    """Insert demo orders, favourites and a profile. Returns counts."""
    if only_if_empty and (db.query(FoodOrder).count() or db.query(Shopping).count()):
        return {"seeded": False, "reason": "database already has orders"}

    food = shopping = 0
    for email in demo_emails():
        if db.query(FoodOrder).filter_by(gmail_message_id=email["id"]).first() or \
           db.query(Shopping).filter_by(gmail_message_id=email["id"]).first():
            continue
        if parsed := parse_food_order(email):
            db.add(FoodOrder(**parsed))
            food += 1
        elif parsed := parse_shopping_order(email):
            db.add(Shopping(**parsed))
            shopping += 1

    if not db.query(UserBio).first():
        db.add(UserBio(full_name="Demo User", location="Boston, MA",
                       bio="Sample profile created by demo mode.",
                       preferences={"diet": "no restrictions", "delivery": "DoorDash"}))
    db.commit()
    _update_favourites(db)
    return {"seeded": True, "food_orders": food, "shopping_orders": shopping}
