"""Push-token ro'yxatga olish endpointi (Phase 5).

Native ilova qurilma push tokenини (Expo) shu yerда saqlaydi. Keyin backend
buyurtma holati / balans / arenda hodisalarida shu token orqali bildirishnoma
yuboradi (services/push.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix="/api/push", tags=["push"])


class RegisterBody(BaseModel):
    token: str = Field(min_length=1, max_length=255)


@router.post("/register")
def register(
    payload: RegisterBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Joriy foydalanuvchiga Expo push tokenини biriktiradi."""
    user.expo_push_token = payload.token.strip()
    db.commit()
    return {"ok": True}


@router.delete("/register")
def unregister(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tokenни o'chiradi (chiqishда yoki push o'chirilganda)."""
    user.expo_push_token = None
    db.commit()
    return {"ok": True}
