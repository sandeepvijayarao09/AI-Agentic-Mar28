from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from api.db.base import Base


class Shopping(Base):
    __tablename__ = "shopping"

    id = Column(Integer, primary_key=True, index=True)
    gmail_message_id = Column(String, unique=True, nullable=False)
    platform = Column(String, nullable=False)  # amazon, walmart, target
    order_number = Column(String, default="")
    order_date = Column(DateTime, nullable=True)
    items = Column(JSON, default=[])  # [{name, qty, price}]
    subtotal = Column(Float, default=0)
    tax = Column(Float, default=0)
    shipping_cost = Column(Float, default=0)
    total = Column(Float, default=0)
    shipping_address = Column(Text, default="")
    estimated_delivery = Column(String, default="")
    status = Column(String, default="confirmed")
    tracking_number = Column(String, default="")
    raw_snippet = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
