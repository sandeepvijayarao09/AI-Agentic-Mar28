"""Memory endpoints — the agent's long-term memory."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from api.db.base import get_db
from api.models.memory import Memory

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    category: str = "note"
    content: str
    source: str = "manual"


@router.get("")
def get_memories(category: str = "", db: DBSession = Depends(get_db)):
    query = db.query(Memory).order_by(Memory.created_at.desc())
    if category:
        query = query.filter(Memory.category == category)
    memories = query.limit(100).all()
    return [{"id": m.id, "category": m.category, "content": m.content, "source": m.source, "created_at": str(m.created_at)} for m in memories]


@router.post("")
def add_memory(data: MemoryCreate, db: DBSession = Depends(get_db)):
    mem = Memory(category=data.category, content=data.content, source=data.source)
    db.add(mem)
    db.commit()
    return {"status": "saved", "id": mem.id}


@router.delete("/{memory_id}")
def delete_memory(memory_id: int, db: DBSession = Depends(get_db)):
    db.query(Memory).filter(Memory.id == memory_id).delete()
    db.commit()
    return {"status": "deleted"}
