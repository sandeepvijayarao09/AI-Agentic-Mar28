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


def _get_platform_search_url(platform: str, restaurant: str) -> str:
    encoded = restaurant.replace(" ", "%20")
    urls = {
        "doordash": f"https://www.doordash.com/search/store/{encoded}/",
        "ubereats": f"https://www.ubereats.com/search?q={encoded}",
        "grubhub": f"https://www.grubhub.com/search?queryText={encoded}",
    }
    return urls.get(platform, f"https://www.google.com/search?q={encoded}+order+food")
