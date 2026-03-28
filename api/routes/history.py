"""Chat history endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from api.db.base import get_db
from api.models.chat_history import ChatMessage

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def get_history(limit: int = 50, db: DBSession = Depends(get_db)):
    messages = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": str(m.created_at)} for m in reversed(messages)]


@router.delete("")
def clear_history(db: DBSession = Depends(get_db)):
    db.query(ChatMessage).delete()
    db.commit()
    return {"status": "cleared"}
