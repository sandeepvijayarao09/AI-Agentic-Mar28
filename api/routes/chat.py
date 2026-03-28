"""Chat endpoint with session management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.agents.brain import chat
from api.db.base import SessionLocal
from api.models.chat_history import ChatMessage, ChatSession

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: int = 0  # 0 = create new session
    history: list[dict] = []


class ChatResponse(BaseModel):
    response: str
    session_id: int


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        response = await chat(req.message, req.history)
        text = str(response)
        if text.startswith("LLMResponse(") and text.endswith(")"):
            text = text[len("LLMResponse("):-1]

        db = SessionLocal()
        try:
            # Create or get session
            session_id = req.session_id
            if session_id == 0:
                session = ChatSession(title=req.message[:50])
                db.add(session)
                db.commit()
                db.refresh(session)
                session_id = session.id
            else:
                session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if session:
                    from datetime import datetime
                    session.updated_at = datetime.utcnow()

            db.add(ChatMessage(session_id=session_id, role="user", content=req.message))
            db.add(ChatMessage(session_id=session_id, role="assistant", content=text))
            db.commit()
        finally:
            db.close()

        return ChatResponse(response=text, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
