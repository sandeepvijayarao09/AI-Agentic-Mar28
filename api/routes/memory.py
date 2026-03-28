"""Memory endpoints — the agent's stored knowledge: orders, favourites, bio."""

import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from api.db.base import get_db
from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_favourite import UserFavourite
from api.models.user_bio import UserBio

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("")
def get_all_memory(db: DBSession = Depends(get_db)):
    """Return all agent memory: food orders, shopping, favourites, bio."""
    food = db.query(FoodOrder).order_by(FoodOrder.order_date.desc()).limit(50).all()
    shopping = db.query(Shopping).order_by(Shopping.order_date.desc()).limit(50).all()
    favs = db.query(UserFavourite).order_by(UserFavourite.order_count.desc()).limit(30).all()
    bio = db.query(UserBio).first()

    return {
        "food_orders": [{
            "id": o.id, "platform": o.platform, "restaurant": o.restaurant_name,
            "items": o.items, "total": o.total, "date": str(o.order_date) if o.order_date else "",
            "status": o.status,
        } for o in food],
        "shopping": [{
            "id": o.id, "platform": o.platform, "order_number": o.order_number,
            "items": o.items, "total": o.total, "date": str(o.order_date) if o.order_date else "",
            "status": o.status, "tracking": o.tracking_number,
        } for o in shopping],
        "favourites": [{
            "id": f.id, "category": f.category, "name": f.name,
            "platform": f.platform, "order_count": f.order_count, "rating": f.rating,
        } for f in favs],
        "bio": {
            "full_name": bio.full_name if bio else "",
            "email": bio.email if bio else "",
            "location": bio.location if bio else "",
            "bio": bio.bio if bio else "",
            "preferences": bio.preferences if bio else {},
        },
        "stats": {
            "food_orders": len(food),
            "shopping_orders": len(shopping),
            "favourites": len(favs),
        }
    }
