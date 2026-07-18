"""Sodiqlik va referal endpointlari (phase 4, 7.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import LoyaltyStatus
from ..security import get_current_user
from ..services import loyalty as loyalty_service

router = APIRouter(prefix="/api", tags=["sodiqlik"])


@router.get("/loyalty", response_model=LoyaltyStatus)
def get_loyalty(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mijozning sodiqlik holati — barcha do'konlar bo'yicha umumiy (rule 9)."""
    # Savdo bot username'i havola uchun (ixtiyoriy).
    bot_username = ""
    return LoyaltyStatus(**loyalty_service.loyalty_status(db, user, bot_username))
