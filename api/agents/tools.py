"""Tool functions that Railtracks agents can call."""

import json
from railtracks import function_node
from api.db.base import SessionLocal
from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_favourite import UserFavourite
from api.models.user_bio import UserBio
from api.services.sync import sync_gmail_orders


@function_node
def get_food_orders(limit: int = 20) -> str:
    """Get recent food delivery orders from the database. Returns a JSON list of food orders including restaurant name, items, total, platform, and date."""
    db = SessionLocal()
    try:
        orders = db.query(FoodOrder).order_by(FoodOrder.order_date.desc()).limit(limit).all()
        result = []
        for o in orders:
            result.append({
                "id": o.id,
                "platform": o.platform,
                "restaurant": o.restaurant_name,
                "items": o.items,
                "total": o.total,
                "date": str(o.order_date) if o.order_date else "",
                "status": o.status,
            })
        return json.dumps(result)
    finally:
        db.close()


@function_node
def get_shopping_orders(limit: int = 20) -> str:
    """Get recent shopping orders from the database. Returns a JSON list of shopping orders including items, total, platform, order number, and date."""
    db = SessionLocal()
    try:
        orders = db.query(Shopping).order_by(Shopping.order_date.desc()).limit(limit).all()
        result = []
        for o in orders:
            result.append({
                "id": o.id,
                "platform": o.platform,
                "order_number": o.order_number,
                "items": o.items,
                "total": o.total,
                "date": str(o.order_date) if o.order_date else "",
                "status": o.status,
                "tracking": o.tracking_number,
            })
        return json.dumps(result)
    finally:
        db.close()


@function_node
def get_favourites(category: str = "") -> str:
    """Get user's favourite items, restaurants, stores, or products. Optionally filter by category (restaurant, food_item, store, product). Returns JSON list sorted by order count."""
    db = SessionLocal()
    try:
        query = db.query(UserFavourite).order_by(UserFavourite.order_count.desc())
        if category:
            query = query.filter(UserFavourite.category == category)
        favs = query.limit(20).all()
        result = []
        for f in favs:
            result.append({
                "id": f.id,
                "category": f.category,
                "name": f.name,
                "platform": f.platform,
                "order_count": f.order_count,
                "rating": f.rating,
                "notes": f.notes,
            })
        return json.dumps(result)
    finally:
        db.close()


@function_node
def get_user_bio() -> str:
    """Get the user's bio/profile information. Returns JSON with name, email, phone, location, bio, and preferences."""
    db = SessionLocal()
    try:
        bio = db.query(UserBio).first()
        if not bio:
            return json.dumps({"message": "No bio set yet"})
        return json.dumps({
            "full_name": bio.full_name,
            "email": bio.email,
            "phone": bio.phone,
            "location": bio.location,
            "bio": bio.bio,
            "preferences": bio.preferences,
        })
    finally:
        db.close()


@function_node
def update_user_bio(full_name: str = "", email: str = "", phone: str = "", location: str = "", bio: str = "") -> str:
    """Update the user's bio/profile. Only updates fields that are provided (non-empty)."""
    db = SessionLocal()
    try:
        existing = db.query(UserBio).first()
        if not existing:
            existing = UserBio()
            db.add(existing)
        if full_name:
            existing.full_name = full_name
        if email:
            existing.email = email
        if phone:
            existing.phone = phone
        if location:
            existing.location = location
        if bio:
            existing.bio = bio
        db.commit()
        return json.dumps({"status": "updated"})
    finally:
        db.close()


@function_node
def sync_emails_to_db() -> str:
    """Sync order confirmation emails from Gmail into the database. Searches for food delivery and shopping order emails, parses them, and stores structured data. Also auto-updates favourites based on order frequency."""
    db = SessionLocal()
    try:
        result = sync_gmail_orders(db)
        return json.dumps(result)
    finally:
        db.close()


@function_node
def search_food_to_order(query: str) -> str:
    """Search for food to order based on user query. Returns recommendation links to popular food delivery platforms. Use the user's favourites and order history to make personalized recommendations."""
    db = SessionLocal()
    try:
        # Get user's top restaurants
        favs = db.query(UserFavourite).filter(
            UserFavourite.category == "restaurant"
        ).order_by(UserFavourite.order_count.desc()).limit(5).all()

        recommendations = []
        for f in favs:
            recommendations.append({
                "restaurant": f.name,
                "platform": f.platform,
                "times_ordered": f.order_count,
                "order_link": _get_platform_search_url(f.platform, f.name),
            })

        # Add general search links
        search_links = {
            "doordash": f"https://www.doordash.com/search/store/{query.replace(' ', '%20')}/",
            "ubereats": f"https://www.ubereats.com/search?q={query.replace(' ', '+')}",
            "grubhub": f"https://www.grubhub.com/search?queryText={query.replace(' ', '+')}",
        }

        return json.dumps({
            "personalized_recommendations": recommendations,
            "search_links": search_links,
            "message": f"Based on your order history, here are your top picks and search links for '{query}'"
        })
    finally:
        db.close()


@function_node
def search_product_to_buy(query: str) -> str:
    """Search for products to buy based on user query. Returns links to popular shopping platforms where the user can add items to cart."""
    search_links = {
        "amazon": f"https://www.amazon.com/s?k={query.replace(' ', '+')}",
        "walmart": f"https://www.walmart.com/search?q={query.replace(' ', '+')}",
        "target": f"https://www.target.com/s?searchTerm={query.replace(' ', '+')}",
    }
    return json.dumps({
        "search_links": search_links,
        "message": f"Here are direct links to search for '{query}' — click to add to cart and pay!"
    })


@function_node
def autonomous_shop_amazon(query: str) -> str:
    """Autonomously open Amazon in a real browser, search for the product, and add it to the user's cart. Use this when the user wants to actually BUY something, not just browse. This opens a visible browser window, searches Amazon, clicks the first result, and adds to cart.

    Args:
        query (str): The product to search for and add to cart.
    """
    import asyncio, threading
    from api.services.autonomous_shop import shop_amazon
    # Run in a new thread with its own event loop (can't nest asyncio.run in FastAPI)
    result = {}
    def run():
        nonlocal result
        result = asyncio.run(shop_amazon(query))
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=45)
    return json.dumps(result or {"status": "timeout", "message": "Shopping took too long, but the browser may still be open."})


@function_node
def autonomous_order_food(query: str) -> str:
    """Autonomously open DoorDash in a real browser to find and order food. Use this when the user wants to actually ORDER food, not just get links. This opens a visible browser window and navigates to the restaurant.

    Args:
        query (str): The restaurant name or food type to search for.
    """
    import asyncio, threading
    from api.services.autonomous_shop import order_doordash
    result = {}
    def run():
        nonlocal result
        result = asyncio.run(order_doordash(query))
    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=45)
    return json.dumps(result or {"status": "timeout", "message": "Ordering took too long, but the browser may still be open."})


@function_node
def suggest_food_from_history() -> str:
    """Suggest a random food order based on the user's order history. Prioritizes most-ordered restaurants. Use this when the user says something vague like 'order some food', 'I'm hungry', 'get me something to eat'. Returns a specific restaurant recommendation with direct ordering link.
    """
    import random
    db = SessionLocal()
    try:
        # Get favourites sorted by order count (highest first)
        favs = db.query(UserFavourite).filter(
            UserFavourite.category == "restaurant"
        ).order_by(UserFavourite.order_count.desc()).limit(10).all()

        if favs:
            # Weighted random — higher order count = higher chance
            weights = [f.order_count + 1 for f in favs]
            chosen = random.choices(favs, weights=weights, k=1)[0]
            link = _get_platform_search_url(chosen.platform, chosen.name)
            return json.dumps({
                "suggestion": chosen.name,
                "platform": chosen.platform,
                "times_ordered": chosen.order_count,
                "order_link": link,
                "message": f"Based on your order history, I recommend **{chosen.name}**! You've ordered from there {chosen.order_count} times. [Order now on {chosen.platform}]({link})"
            })

        # Fallback: check food orders directly
        orders = db.query(FoodOrder).order_by(FoodOrder.order_date.desc()).limit(20).all()
        if orders:
            order = random.choice(orders[:5])  # pick from recent 5
            link = _get_platform_search_url(order.platform, order.restaurant_name)
            return json.dumps({
                "suggestion": order.restaurant_name,
                "platform": order.platform,
                "order_link": link,
                "message": f"How about **{order.restaurant_name}**? You ordered from there recently. [Order now]({link})"
            })

        return json.dumps({"message": "I don't have any order history yet. Try syncing your emails first, or tell me what kind of food you'd like!"})
    finally:
        db.close()


@function_node
def suggest_product_from_history(query: str = "") -> str:
    """Suggest a product to buy based on the user's shopping history. Use this when the user mentions a past purchase like 'I want to buy that shirt again' or 'reorder my headphones'. Searches shopping history for matching items.

    Args:
        query (str): Description of the product the user wants to rebuy (e.g., 'white shirt', 'headphones').
    """
    db = SessionLocal()
    try:
        orders = db.query(Shopping).order_by(Shopping.order_date.desc()).all()
        matches = []
        query_lower = query.lower()

        for order in orders:
            for item in (order.items or []):
                item_name = (item.get("name", "") if isinstance(item, dict) else str(item)).lower()
                if query_lower in item_name or any(w in item_name for w in query_lower.split()):
                    matches.append({
                        "name": item.get("name", str(item)) if isinstance(item, dict) else str(item),
                        "price": item.get("price", "") if isinstance(item, dict) else "",
                        "platform": order.platform,
                        "order_date": str(order.order_date),
                        "order_number": order.order_number,
                    })

        if matches:
            best = matches[0]
            search_url = f"https://www.amazon.com/s?k={best['name'].replace(' ', '+')}"
            return json.dumps({
                "found": True,
                "product": best["name"],
                "platform": best["platform"],
                "price": best["price"],
                "order_date": best["order_date"],
                "search_url": search_url,
                "message": f"Found it! You bought **{best['name']}** on {best['platform']} ({best['order_date']}). [Buy again on Amazon]({search_url})"
            })

        return json.dumps({"found": False, "message": f"I couldn't find '{query}' in your shopping history. Try syncing your emails or give me more details."})
    finally:
        db.close()


@function_node
def find_product_in_gmail(query: str) -> str:
    """Search Gmail for a specific past purchase to find product details and reorder it. Use this when the user refers to a past purchase like 'my white shirt from last month' or 'the headphones I bought'. Searches Gmail for order confirmation emails matching the query.

    Args:
        query (str): Description of the product to find in email (e.g., 'white shirt', 'sony headphones').
    """
    from api.services.gmail import search_emails
    try:
        # Search Gmail for order-related emails matching the query
        gmail_query = f'subject:(order OR receipt OR confirmation) {query}'
        emails = search_emails(gmail_query, max_results=5)

        results = []
        for email in emails:
            results.append({
                "subject": email.get("subject", ""),
                "from": email.get("from", ""),
                "date": email.get("date", ""),
                "snippet": email.get("snippet", "")[:200],
            })

        if results:
            # Build a search URL from the best match
            best = results[0]
            search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
            return json.dumps({
                "found": True,
                "email_matches": results,
                "search_url": search_url,
                "message": f"Found {len(results)} email(s) about '{query}'. Latest: **{best['subject']}** from {best['from']} on {best['date']}. [Reorder on Amazon]({search_url})"
            })

        return json.dumps({"found": False, "message": f"No emails found for '{query}'. Make sure Gmail is connected and try again."})
    except Exception as e:
        return json.dumps({"found": False, "message": f"Couldn't search Gmail: {str(e)}. Make sure Gmail is connected."})


def _get_platform_search_url(platform: str, restaurant: str) -> str:
    encoded = restaurant.replace(" ", "%20")
    urls = {
        "doordash": f"https://www.doordash.com/search/store/{encoded}/",
        "ubereats": f"https://www.ubereats.com/search?q={encoded}",
        "grubhub": f"https://www.grubhub.com/search?queryText={encoded}",
    }
    return urls.get(platform, f"https://www.google.com/search?q={encoded}+order+food")
