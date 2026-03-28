"""User bio endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from api.db.base import get_db
from api.models.user_bio import UserBio

router = APIRouter(prefix="/bio", tags=["bio"])


class BioUpdate(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    bio: str = ""
    preferences: dict = {}


@router.get("")
def get_bio(db: DBSession = Depends(get_db)):
    bio = db.query(UserBio).first()
    if not bio:
        return {"message": "No bio set yet"}
    return {
        "full_name": bio.full_name,
        "email": bio.email,
        "phone": bio.phone,
        "location": bio.location,
        "bio": bio.bio,
        "preferences": bio.preferences,
    }


@router.put("")
def upsert_bio(data: BioUpdate, db: DBSession = Depends(get_db)):
    bio = db.query(UserBio).first()
    if not bio:
        bio = UserBio()
        db.add(bio)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value:
            setattr(bio, field, value)
    db.commit()
    db.refresh(bio)
    return {"status": "updated"}
