from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from api.db.base import Base


class FoodOrder(Base):
    __tablename__ = "food_orders"

    id = Column(Integer, primary_key=True, index=True)
    gmail_message_id = Column(String, unique=True, nullable=False)
    platform = Column(String, nullable=False)  # doordash, ubereats, grubhub
    restaurant_name = Column(String, default="")
    order_date = Column(DateTime, nullable=True)
    items = Column(JSON, default=[])  # [{name, qty, price}]
    subtotal = Column(Float, default=0)
    tax = Column(Float, default=0)
    tip = Column(Float, default=0)
    delivery_fee = Column(Float, default=0)
    total = Column(Float, default=0)
    delivery_address = Column(Text, default="")
    status = Column(String, default="confirmed")
    raw_snippet = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
