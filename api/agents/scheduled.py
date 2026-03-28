"""Scheduled agents — run autonomously on a schedule."""

import railtracks as rt
from api.agents.tools import sync_emails_to_db, get_favourites, get_food_orders, get_shopping_orders
from api.db.base import SessionLocal
from api.models.user_favourite import UserFavourite
from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from collections import Counter

LLM = rt.llm.GeminiLLM("gemini-2.5-flash-lite")


# ── Email Sync Agent — checks Gmail and updates order lists ──────────────────

EmailSyncAgent = rt.agent_node(
    name="EmailSyncAgent",
    llm=LLM,
    system_message="""You are the Email Sync Agent. Your job is to:
1. Call sync_emails_to_db to pull the latest food and shopping orders from Gmail
2. Report what was synced

Run this autonomously. Just call the tool and report results.""",
    tool_nodes=[sync_emails_to_db],
)


async def run_email_sync():
    """Run the email sync agent."""
    with rt.Session(save_state=False, timeout=60.0):
        result = await rt.call(EmailSyncAgent, "Sync all order emails from Gmail now.")
        return str(result)


# ── Favourites Accuracy Agent — validates and updates favourites ─────────────

def validate_favourites() -> dict:
    """Recompute favourites from actual order data to ensure accuracy."""
    db = SessionLocal()
    try:
        # Recount restaurant frequency
        food_orders = db.query(FoodOrder).all()
        restaurant_counts = Counter()
        platform_map = {}
        for order in food_orders:
            if order.restaurant_name:
                restaurant_counts[order.restaurant_name] += 1
                platform_map[order.restaurant_name] = order.platform

        # Recount item frequency
        item_counts = Counter()
        for order in food_orders:
            for item in (order.items or []):
                name = item.get("name", "") if isinstance(item, dict) else str(item)
                if name:
                    item_counts[name] += item.get("qty", 1) if isinstance(item, dict) else 1

        shopping_orders = db.query(Shopping).all()
        for order in shopping_orders:
            for item in (order.items or []):
                name = item.get("name", "") if isinstance(item, dict) else str(item)
                if name:
                    item_counts[name] += item.get("qty", 1) if isinstance(item, dict) else 1

        updated = 0
        added = 0

        # Update restaurant favourites
        for restaurant, count in restaurant_counts.most_common(15):
            existing = db.query(UserFavourite).filter(
                UserFavourite.name == restaurant,
                UserFavourite.category == "restaurant",
            ).first()
            if existing:
                if existing.order_count != count:
                    existing.order_count = count
                    updated += 1
            else:
                db.add(UserFavourite(
                    category="restaurant",
                    name=restaurant,
                    platform=platform_map.get(restaurant, ""),
                    order_count=count,
                    notes=f"Ordered {count} times",
                ))
                added += 1

        # Update item favourites
        for item_name, count in item_counts.most_common(20):
            existing = db.query(UserFavourite).filter(
                UserFavourite.name == item_name,
                UserFavourite.category == "food_item",
            ).first()
            if existing:
                if existing.order_count != count:
                    existing.order_count = count
                    updated += 1
            else:
                db.add(UserFavourite(
                    category="food_item",
                    name=item_name,
                    order_count=count,
                    notes=f"Ordered {count} times",
                ))
                added += 1

        # Remove favourites that no longer appear in orders
        removed = 0
        all_favs = db.query(UserFavourite).all()
        for fav in all_favs:
            if fav.category == "restaurant" and fav.name not in restaurant_counts:
                db.delete(fav)
                removed += 1
            elif fav.category == "food_item" and fav.name not in item_counts:
                db.delete(fav)
                removed += 1

        db.commit()
        return {
            "status": "validated",
            "restaurants_tracked": len(restaurant_counts),
            "items_tracked": len(item_counts),
            "updated": updated,
            "added": added,
            "removed": removed,
        }
    finally:
        db.close()


async def run_favourites_validation():
    """Validate and update favourites from order data."""
    return validate_favourites()


# ── Daily maintenance — runs both agents ─────────────────────────────────────

async def run_daily_maintenance():
    """Run all scheduled agents: email sync + favourites validation."""
    sync_result = await run_email_sync()
    fav_result = await run_favourites_validation()
    return {
        "email_sync": str(sync_result),
        "favourites_validation": fav_result,
    }
