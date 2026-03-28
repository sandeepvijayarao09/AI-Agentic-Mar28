from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from api.db.base import Base


class UserBio(Base):
    __tablename__ = "user_bio"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    location = Column(String, default="")
    bio = Column(Text, default="")
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
