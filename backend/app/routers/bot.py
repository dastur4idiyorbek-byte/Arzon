"""Savdo Boti uchun ichki endpointlar (phase 5).

Oddiy Telegram chat'ida Mini App initData bo'lmaydi. Savdo Boti server tomonда
ishlaydigan ishonchli komponent — u ichki token bilan autentifikatsiya qiladi
va foydalanuvchi telegram_id'sini X-Telegram-User-Id sarlavhasида uzatadi.

initData (rule 8, 1-bosqich) Mini App uchun; bu endpointlar bot uchun. Ikkalasi
ham bir xil xizmat qatlamini (services) chaqiradi.
"""
from __future__ import annotations

from typing import List

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ai
from ..config import settings
from ..database import get_db
from ..models import Order, User
from ..schemas import ChatReply, OrderOut
from ..services import catalog as catalog_service
from ..services import loyalty as loyalty_service

router = APIRouter(prefix="/api/bot", tags=["savdo-bot"])


def bot_user(
    x_internal_token: str = Header(default="", alias="X-Internal-Token"),
    x_telegram_user_id: str = Header(default="", alias="X-Telegram-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Ichki token + telegram_id orqali foydalanuvchini oladi/yaratadi."""
    if not settings.internal_api_token or not hmac.compare_digest(
        x_internal_token, settings.internal_api_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ichki token noto'g'ri.",
        )
    if not x_telegram_user_id.lstrip("-").isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Telegram-User-Id noto'g'ri.",
        )
    tid = int(x_telegram_user_id)
    user = db.scalar(select(User).where(User.telegram_id == tid))
    if user is None:
        user = User(telegram_id=tid)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


class BotChat(BaseModel):
    matn: str


@router.post("/chat", response_model=ChatReply)
def bot_chat(
    payload: BotChat,
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    return ChatReply(javob=ai.chat_reply(db, user, payload.matn))


class BotContact(BaseModel):
    tel: str
    ism: str | None = None


@router.post("/confirm-phone")
def bot_confirm_phone(
    payload: BotContact,
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """Kontaktni ulashish orqali telefon tasdiqlash (rule 8, 2-bosqich)."""
    user.tel = payload.tel
    if payload.ism:
        user.ism = payload.ism
    user.tel_tasdiqlangan = True
    db.commit()
    return {"tel_tasdiqlangan": True}


@router.get("/orders", response_model=List[OrderOut])
def bot_orders(
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """/holat buyrug'i uchun buyurtmalar tarixi (phase 5.3)."""
    rows = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.yaratilgan_vaqt.desc())
    ).all()
    return [OrderOut.model_validate(o) for o in rows]


@router.post("/loyalty")
def bot_loyalty(
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
    bot_username: str = "",
):
    return loyalty_service.loyalty_status(db, user, bot_username)


class BotReferral(BaseModel):
    referrer_telegram_id: int


@router.post("/register-referral")
def bot_register_referral(
    payload: BotReferral,
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """Referal havola orqali kelgan foydalanuvchini ro'yxatga olish (phase 4.4)."""
    loyalty_service.register_referral(db, user, payload.referrer_telegram_id)
    return {"status": "ok"}
