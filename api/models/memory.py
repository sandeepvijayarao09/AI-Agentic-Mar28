from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from api.db.base import Base


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)  # preference, fact, habit, note
    content = Column(Text, nullable=False)
    source = Column(String, default="chat")  # chat, gmail, manual
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
