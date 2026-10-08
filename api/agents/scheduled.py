"""Scheduled agents — run autonomously using Google ADK."""

from collections import Counter
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from api.agents.tools import sync_emails_to_db
from api.db.base import SessionLocal
from api.models.user_favourite import UserFavourite
from api.models.food_order import FoodOrder
from api.models.shopping import Shopping


# ── Email Sync Agent ─────────────────────────────────────────────────────────

email_sync_agent = Agent(
    name="EmailSyncAgent",
    model="gemini-2.5-flash-lite",
    description="Syncs Gmail order emails to database.",
    instruction="Call sync_emails_to_db to pull the latest food and shopping orders from Gmail. Report what was synced.",
    tools=[sync_emails_to_db],
)

_sync_session_service = InMemorySessionService()
_sync_runner = Runner(agent=email_sync_agent, app_name="EmailSync", session_service=_sync_session_service)


async def run_email_sync():
    """Run the email sync agent."""
    session = await _sync_session_service.create_session(app_name="EmailSync", user_id="system", session_id="sync")
    content = types.Content(role="user", parts=[types.Part.from_text(text="Sync all order emails from Gmail now.")])
    result = ""
    async for event in _sync_runner.run_async(user_id="system", session_id="sync", new_message=content):
        if event.is_final_response() and event.content and event.content.parts:
            result = event.content.parts[0].text or ""
    return result


# ── Favourites Validator (pure Python, no LLM needed) ────────────────────────

def validate_favourites() -> dict:
    """Recompute favourites from actual order data to ensure accuracy."""
    db = SessionLocal()
    try:
        food_orders = db.query(FoodOrder).all()
        restaurant_counts = Counter()
        platform_map = {}
        for order in food_orders:
            if order.restaurant_name:
                restaurant_counts[order.restaurant_name] += 1
                platform_map[order.restaurant_name] = order.platform

        def count_items(orders):
            counts = Counter()
            for order in orders:
                for item in (order.items or []):
                    name = item.get("name", "") if isinstance(item, dict) else str(item)
                    if name:
                        counts[name] += item.get("qty", 1) if isinstance(item, dict) else 1
            return counts

        item_counts = count_items(food_orders)
        product_counts = count_items(db.query(Shopping).all())

        updated, added, removed = 0, 0, 0

        for restaurant, count in restaurant_counts.most_common(15):
            existing = db.query(UserFavourite).filter(UserFavourite.name == restaurant, UserFavourite.category == "restaurant").first()
            if existing:
                if existing.order_count != count:
                    existing.order_count = count
                    updated += 1
            else:
                db.add(UserFavourite(category="restaurant", name=restaurant, platform=platform_map.get(restaurant, ""), order_count=count))
                added += 1

        for category, counts in (("food_item", item_counts), ("product", product_counts)):
            for item_name, count in counts.most_common(20):
                existing = db.query(UserFavourite).filter(UserFavourite.name == item_name, UserFavourite.category == category).first()
                if existing:
                    if existing.order_count != count:
                        existing.order_count = count
                        updated += 1
                else:
                    db.add(UserFavourite(category=category, name=item_name, order_count=count))
                    added += 1

        all_favs = db.query(UserFavourite).all()
        for fav in all_favs:
            if fav.category == "restaurant" and fav.name not in restaurant_counts:
                db.delete(fav); removed += 1
            elif fav.category == "food_item" and fav.name not in item_counts:
                db.delete(fav); removed += 1
            elif fav.category == "product" and fav.name not in product_counts:
                db.delete(fav); removed += 1

        db.commit()
        return {"status": "validated", "updated": updated, "added": added, "removed": removed}
    finally:
        db.close()


async def run_favourites_validation():
    return validate_favourites()


async def run_daily_maintenance():
    sync_result = await run_email_sync()
    fav_result = await run_favourites_validation()
    return {"email_sync": str(sync_result), "favourites_validation": fav_result}
