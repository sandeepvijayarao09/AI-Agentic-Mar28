"""Chat endpoint — main interface for the Second Brain agent."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.agents.brain import chat
from api.db.base import SessionLocal
from api.models.chat_history import ChatMessage
from api.models.memory import Memory

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Send a message to the Second Brain agent."""
    try:
        response = await chat(req.message, req.history)
        text = str(response)
        if text.startswith("LLMResponse(") and text.endswith(")"):
            text = text[len("LLMResponse("):-1]

        # Save to chat history
        db = SessionLocal()
        try:
            db.add(ChatMessage(role="user", content=req.message))
            db.add(ChatMessage(role="assistant", content=text))

            # Auto-extract memories from conversation
            _extract_memories(req.message, text, db)

            db.commit()
        finally:
            db.close()

        return ChatResponse(response=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _extract_memories(user_msg: str, assistant_msg: str, db):
    """Auto-extract key facts as memories from conversation."""
    keywords = {
        "preference": ["i love", "i like", "i prefer", "my favorite", "my favourite", "i hate", "i don't like"],
        "fact": ["i am", "i'm", "my name is", "i live in", "i work at", "i study"],
        "habit": ["i usually", "i always", "i often", "every day", "every week"],
    }
    msg_lower = user_msg.lower()
    for category, triggers in keywords.items():
        for trigger in triggers:
            if trigger in msg_lower:
                existing = db.query(Memory).filter(Memory.content == user_msg).first()
                if not existing:
                    db.add(Memory(category=category, content=user_msg, source="chat"))
                break
