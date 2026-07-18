"""Mijoz katalogi va mahfiy kod endpointlari (phase 2.3, 7.2, 7.3)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import ProductOut, UnlockRequest, UnlockResponse
from ..security import enforce_code_rate_limit, get_current_user
from ..services import catalog as catalog_service

router = APIRouter(prefix="/api", tags=["katalog"])


@router.get("/products", response_model=List[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Bitta umumiy katalog (rule 1).

    Barcha do'konlarning ommaviy mahsulotlari + mijozga ochiq bo'lgan mahfiy
    mahsulotlar bitta ro'yxatda. Do'kon tanlash YO'Q.
    """
    return catalog_service.get_catalog(db, user)


@router.post("/unlock", response_model=UnlockResponse)
def unlock_store(
    payload: UnlockRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mahfiy kodni kiritish (rule 3, 4). Kod YARATISH bu yerda yo'q.

    Rate-limit (phase 3.6): bir daqiqada cheklangan urinish.
    """
    # Brute-force'dan himoya — foydalanuvchi bo'yicha cheklov.
    enforce_code_rate_limit(f"unlock:{user.telegram_id}")
    return catalog_service.try_unlock(db, user, payload.kod)
