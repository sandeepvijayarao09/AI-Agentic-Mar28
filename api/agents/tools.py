"""Tool functions for the Second Brain agent — plain Python functions for Google ADK."""

import json
from api.db.base import SessionLocal
from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_favourite import UserFavourite
from api.models.user_bio import UserBio
from api.services.sync import sync_gmail_orders


def get_food_orders(limit: int = 20) -> dict:
    """Get recent food delivery orders. Returns order_id, date, restaurant name, items (with name/qty/price), platform, and total amount for each order."""
    db = SessionLocal()
    try:
        orders = db.query(FoodOrder).order_by(FoodOrder.order_date.desc()).limit(limit).all()
        return {"orders": [{
            "order_id": o.gmail_message_id,
            "date": str(o.order_date) if o.order_date else "",
            "name": o.restaurant_name,
            "items": o.items or [],
            "platform": o.platform,
            "amount": o.total,
            "status": o.status,
        } for o in orders]}
    finally:
        db.close()


def get_shopping_orders(limit: int = 20) -> dict:
    """Get recent shopping orders. Returns order_id, date, order number, items (with name/qty/price), platform, and total amount for each order."""
    db = SessionLocal()
    try:
        orders = db.query(Shopping).order_by(Shopping.order_date.desc()).limit(limit).all()
        return {"orders": [{
            "order_id": o.order_number or o.gmail_message_id,
            "date": str(o.order_date) if o.order_date else "",
            "name": f"Order #{o.order_number}" if o.order_number else "Shopping Order",
            "items": o.items or [],
            "platform": o.platform,
            "amount": o.total,
            "status": o.status,
            "tracking": o.tracking_number,
        } for o in orders]}
    finally:
        db.close()


def get_favourites(category: str = "") -> dict:
    """Get user's favourite items, restaurants, stores, or products. Optionally filter by category: restaurant, food_item, store, product. Sorted by order count."""
    db = SessionLocal()
    try:
        query = db.query(UserFavourite).order_by(UserFavourite.order_count.desc())
        if category:
            query = query.filter(UserFavourite.category == category)
        favs = query.limit(20).all()
        return {"favourites": [{"id": f.id, "category": f.category, "name": f.name, "platform": f.platform, "order_count": f.order_count, "rating": f.rating, "notes": f.notes} for f in favs]}
    finally:
        db.close()


def get_user_bio() -> dict:
    """Get the user's bio/profile information including name, email, phone, location, bio, and preferences."""
    db = SessionLocal()
    try:
        bio = db.query(UserBio).first()
        if not bio:
            return {"message": "No bio set yet"}
        return {"full_name": bio.full_name, "email": bio.email, "phone": bio.phone, "location": bio.location, "bio": bio.bio, "preferences": bio.preferences}
    finally:
        db.close()


def update_user_bio(full_name: str = "", email: str = "", phone: str = "", location: str = "", bio: str = "") -> dict:
    """Update the user's bio/profile. Only updates fields that are provided (non-empty)."""
    db = SessionLocal()
    try:
        existing = db.query(UserBio).first()
        if not existing:
            existing = UserBio()
            db.add(existing)
        if full_name: existing.full_name = full_name
        if email: existing.email = email
        if phone: existing.phone = phone
        if location: existing.location = location
        if bio: existing.bio = bio
        db.commit()
        return {"status": "updated"}
    finally:
        db.close()


def sync_emails_to_db() -> dict:
    """Sync order confirmation emails from Gmail into the database. Searches for food delivery and shopping order emails, parses them, and stores structured data. Also auto-updates favourites based on order frequency."""
    db = SessionLocal()
    try:
        return sync_gmail_orders(db)
    finally:
        db.close()


def search_food_to_order(query: str) -> dict:
    """Search for food to order. Returns personalized recommendations from order history and search links for DoorDash, Uber Eats, Grubhub."""
    db = SessionLocal()
    try:
        favs = db.query(UserFavourite).filter(UserFavourite.category == "restaurant").order_by(UserFavourite.order_count.desc()).limit(5).all()
        recommendations = [{"restaurant": f.name, "platform": f.platform, "times_ordered": f.order_count, "order_link": _get_platform_search_url(f.platform, f.name)} for f in favs]
        search_links = {
            "doordash": f"https://www.doordash.com/search/store/{query.replace(' ', '%20')}/",
            "ubereats": f"https://www.ubereats.com/search?q={query.replace(' ', '+')}",
            "grubhub": f"https://www.grubhub.com/search?queryText={query.replace(' ', '+')}",
        }
        return {"personalized_recommendations": recommendations, "search_links": search_links, "message": f"Top picks and search links for '{query}'"}
    finally:
        db.close()


def search_product_to_buy(query: str) -> dict:
    """Search for products to buy. Returns links to Amazon, Walmart, Target where the user can add items to cart."""
    return {
        "search_links": {
            "amazon": f"https://www.amazon.com/s?k={query.replace(' ', '+')}",
            "walmart": f"https://www.walmart.com/search?q={query.replace(' ', '+')}",
            "target": f"https://www.target.com/s?searchTerm={query.replace(' ', '+')}",
        },
        "message": f"Direct links to search for '{query}'"
    }


def autonomous_shop_amazon(query: str) -> dict:
    """Autonomously open Amazon in a real browser, search for the product, and add it to the user's cart. Opens a visible browser window. Use when the user wants to actually BUY something."""
    import asyncio, threading
    from api.services.autonomous_shop import browser_automation_enabled, shop_amazon
    if not browser_automation_enabled():
        result = search_product_to_buy(query)
        result["status"] = "browser_automation_disabled"
        result["message"] = f"Browser automation is off (set ENABLE_BROWSER_AUTOMATION=1). Here are direct links to search for '{query}'."
        return result
    result = {}
    def run():
        nonlocal result
        result = asyncio.run(shop_amazon(query))
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=45)
    return result or {"status": "timeout", "message": "Shopping took too long, but the browser may still be open."}


def autonomous_order_food(query: str) -> dict:
    """Autonomously open DoorDash in a real browser to find and order food. Opens a visible browser window and navigates to the restaurant."""
    import asyncio, threading
    from api.services.autonomous_shop import browser_automation_enabled, order_doordash
    if not browser_automation_enabled():
        url = f"https://www.doordash.com/search/store/{query.replace(' ', '%20')}/"
        return {"status": "browser_automation_disabled", "url": url, "message": f"Browser automation is off (set ENABLE_BROWSER_AUTOMATION=1). [Search DoorDash for '{query}']({url})"}
    result = {}
    def run():
        nonlocal result
        result = asyncio.run(order_doordash(query))
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=45)
    return result or {"status": "timeout", "message": "Ordering took too long, but the browser may still be open."}


def suggest_food_from_history() -> dict:
    """Suggest a food order based on the user's order history. Prioritizes most-ordered restaurants with weighted random selection. Use when user says 'order food', 'I'm hungry', 'get me something to eat'."""
    import random
    db = SessionLocal()
    try:
        favs = db.query(UserFavourite).filter(UserFavourite.category == "restaurant").order_by(UserFavourite.order_count.desc()).limit(10).all()
        if favs:
            weights = [f.order_count + 1 for f in favs]
            chosen = random.choices(favs, weights=weights, k=1)[0]
            link = _get_platform_search_url(chosen.platform, chosen.name)
            return {"suggestion": chosen.name, "platform": chosen.platform, "times_ordered": chosen.order_count, "order_link": link, "message": f"I recommend **{chosen.name}**! Ordered {chosen.order_count} times. [Order now]({link})"}
        orders = db.query(FoodOrder).order_by(FoodOrder.order_date.desc()).limit(5).all()
        if orders:
            order = random.choice(orders)
            link = _get_platform_search_url(order.platform, order.restaurant_name)
            return {"suggestion": order.restaurant_name, "order_link": link, "message": f"How about **{order.restaurant_name}**? [Order now]({link})"}
        return {"message": "No order history yet. Sync your emails first!"}
    finally:
        db.close()


def suggest_product_from_history(query: str = "") -> dict:
    """Search shopping history for past purchases to rebuy. Use when user mentions a past purchase like 'reorder my headphones' or 'buy that shirt again'."""
    db = SessionLocal()
    try:
        orders = db.query(Shopping).order_by(Shopping.order_date.desc()).all()
        query_lower = query.lower()
        for order in orders:
            for item in (order.items or []):
                item_name = (item.get("name", "") if isinstance(item, dict) else str(item)).lower()
                if query_lower in item_name or any(w in item_name for w in query_lower.split()):
                    name = item.get("name", str(item)) if isinstance(item, dict) else str(item)
                    url = f"https://www.amazon.com/s?k={name.replace(' ', '+')}"
                    return {"found": True, "product": name, "platform": order.platform, "price": item.get("price", "") if isinstance(item, dict) else "", "search_url": url, "message": f"Found **{name}**! [Buy again on Amazon]({url})"}
        return {"found": False, "message": f"Couldn't find '{query}' in shopping history. Try syncing emails."}
    finally:
        db.close()


def find_product_in_gmail(query: str) -> dict:
    """Search Gmail for a specific past purchase order confirmation. Use when user refers to a past purchase like 'my white shirt from last month'."""
    from api.services.gmail import search_emails
    try:
        emails = search_emails(f'subject:(order OR receipt OR shipped) {query}', max_results=5)
        results = [{"subject": e.get("subject", "")[:80], "from": e.get("from", ""), "date": e.get("date", ""), "snippet": e.get("snippet", "")[:200]} for e in emails]
        if results:
            url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
            return {"found": True, "email_matches": results, "search_url": url, "message": f"Found {len(results)} email(s) for '{query}'. [Reorder on Amazon]({url})"}
        return {"found": False, "message": f"No emails found for '{query}'."}
    except Exception as e:
        return {"found": False, "message": f"Gmail search failed: {str(e)}"}


def send_email_for_user(to: str, subject: str, body: str) -> dict:
    """Send an email on behalf of the user via Gmail."""
    from api.services.gmail import send_email
    try:
        result = send_email(to, subject, body, html=False)
        return {"status": "sent", "message_id": result.get("message_id", ""), "message": f"Email sent to {to}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {str(e)}"}


def search_emails_for_user(query: str) -> dict:
    """Search the user's Gmail inbox for specific emails."""
    from api.services.gmail import search_emails
    try:
        emails = search_emails(query, max_results=5)
        results = [{"subject": e.get("subject", "")[:80], "from": e.get("from", ""), "date": e.get("date", ""), "snippet": e.get("snippet", "")[:150]} for e in emails]
        return {"count": len(results), "emails": results}
    except Exception as e:
        return {"count": 0, "message": f"Search failed: {str(e)}"}


def _get_platform_search_url(platform: str, restaurant: str) -> str:
    encoded = restaurant.replace(" ", "%20")
    urls = {
        "doordash": f"https://www.doordash.com/search/store/{encoded}/",
        "ubereats": f"https://www.ubereats.com/search?q={encoded}",
        "grubhub": f"https://www.grubhub.com/search?queryText={encoded}",
    }
    return urls.get(platform, f"https://www.google.com/search?q={encoded}+order+food")
