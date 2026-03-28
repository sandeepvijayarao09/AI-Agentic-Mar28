"""Sync endpoint — trigger Gmail to DB sync."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from api.db.base import get_db
from api.services.sync import sync_gmail_orders
from api.models.food_order import FoodOrder
from api.models.shopping import Shopping
from api.models.user_favourite import UserFavourite

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/gmail")
def sync_gmail(db: DBSession = Depends(get_db)):
    """Sync food and shopping orders from Gmail emails to database."""
    result = sync_gmail_orders(db)
    return result


@router.get("/stats")
def sync_stats(db: DBSession = Depends(get_db)):
    """Get database stats — how many orders and favourites are stored."""
    return {
        "food_orders": db.query(FoodOrder).count(),
        "shopping_orders": db.query(Shopping).count(),
        "favourites": db.query(UserFavourite).count(),
    }
