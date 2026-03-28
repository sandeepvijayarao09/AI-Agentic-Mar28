from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, SmallInteger
from api.db.base import Base


class UserFavourite(Base):
    __tablename__ = "user_favourites"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)  # restaurant, food_item, store, product
    name = Column(String, nullable=False)
    platform = Column(String, default="")
    notes = Column(Text, default="")
    rating = Column(SmallInteger, nullable=True)
    order_count = Column(Integer, default=0)  # how many times ordered
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
