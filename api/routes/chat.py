"""Chat endpoint — main interface for the Second Brain agent."""

import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.agents.brain import chat

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
        # Clean up LLMResponse wrapper if present
        text = str(response)
        if text.startswith("LLMResponse(") and text.endswith(")"):
            text = text[len("LLMResponse("):-1]
        return ChatResponse(response=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
