"""Chat history with session management."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from api.db.base import get_db
from api.models.chat_history import ChatSession, ChatMessage

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/sessions")
def get_sessions(db: DBSession = Depends(get_db)):
    """List all chat sessions, newest first."""
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).limit(50).all()
    result = []
    for s in sessions:
        msg_count = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).count()
        last_msg = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at.desc()).first()
        result.append({
            "id": s.id,
            "title": s.title,
            "message_count": msg_count,
            "preview": last_msg.content[:80] if last_msg else "",
            "created_at": str(s.created_at),
            "updated_at": str(s.updated_at),
        })
    return result


@router.post("/sessions")
def create_session(db: DBSession = Depends(get_db)):
    """Create a new chat session."""
    session = ChatSession(title="New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title}


@router.get("/sessions/{session_id}")
def get_session_messages(session_id: int, db: DBSession = Depends(get_db)):
    """Get all messages for a session."""
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": str(m.created_at)} for m in messages]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.query(ChatSession).filter(ChatSession.id == session_id).delete()
    db.commit()
    return {"status": "deleted"}


@router.delete("")
def clear_all(db: DBSession = Depends(get_db)):
    db.query(ChatMessage).delete()
    db.query(ChatSession).delete()
    db.commit()
    return {"status": "cleared"}
