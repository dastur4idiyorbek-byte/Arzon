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


@router.get("/me")
def bot_me(user: User = Depends(bot_user)):
    """Onboarding uchun foydalanuvchi holati (telefon tasdiqlanganmi)."""
    return {
        "telegram_id": user.telegram_id,
        "ism": user.ism,
        "tel_tasdiqlangan": user.tel_tasdiqlangan,
    }


@router.post("/start-bonus")
def bot_start_bonus(user: User = Depends(bot_user), db: Session = Depends(get_db)):
    """/start uchun bir martalik sodiqlik bonusi (5 ACOM)."""
    bonus = loyalty_service.award_start_bonus(db, user)
    from ..services import coin as coin_service

    return {"bonus": bonus, "coin_balans": float(coin_service.balance(user))}


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


# ---------------------------------------------------------------------------
# ACOM coin — mijoz tomoni (Savdo Boti / Mini App)
# ---------------------------------------------------------------------------
from ..services import coin as coin_service  # noqa: E402


@router.get("/coin/balance")
def bot_coin_balance(
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """Mijoz balansi + platforma karta ma'lumoti (to'ldirish uchun)."""
    hisob = coin_service.get_platforma_hisob(db)
    return {
        "coin_balans": float(coin_service.balance(user)),
        "platforma_hisob": (
            {"karta_raqami": hisob.karta_raqami, "hisob_egasi": hisob.hisob_egasi}
            if hisob
            else None
        ),
    }


class BotTopup(BaseModel):
    summa: float
    chek_rasm_url: str | None = None
    ai_summa: float | None = None
    ai_sana: str | None = None
    ai_xulosa: str | None = None
    tolov_usuli_id: int | None = None


@router.get("/coin/tolov-usullari")
def bot_coin_tolov_usullari(
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """Faol to'lov usullari (Savdo Boti to'ldirish oqimи uchun — task_1)."""
    return [
        coin_service.tolov_usuli_dict(u)
        for u in coin_service.list_active_tolov_usullari(db)
    ]


@router.post("/coin/topup")
def bot_coin_topup(
    payload: BotTopup,
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """To'ldirish so'rovi (rule 2 — coin hali berilmaydi). Moliyaга xabar ketadi."""
    sorov = coin_service.create_topup_request(
        db,
        user,
        payload.summa,
        chek_rasm_url=payload.chek_rasm_url,
        ai_summa=payload.ai_summa,
        ai_sana=payload.ai_sana,
        ai_xulosa=payload.ai_xulosa,
        tolov_usuli_id=payload.tolov_usuli_id,
    )
    usul = (
        coin_service.get_tolov_usuli(db, payload.tolov_usuli_id)
        if payload.tolov_usuli_id
        else None
    )
    try:
        from ..tgbots import notify

        notify.notify_moliya_topup(
            sorov_id=sorov.id,
            ism=user.ism,
            telegram_id=user.telegram_id,
            summa=float(sorov.som_summasi),
            ai_summa=float(sorov.ai_ochigan_summa)
            if sorov.ai_ochigan_summa is not None
            else None,
            ai_sana=sorov.ai_ochigan_sana,
            ai_xulosa=sorov.ai_xulosasi,
            chek_rel_url=sorov.chek_rasm_url,
            usul_nomi=usul.nomi if usul else None,
        )
    except ImportError:
        pass
    return {"sorov_id": sorov.id, "holat": sorov.holat}


class BotDokonSorovi(BaseModel):
    dokon_nomi: str
    admin_telegram_id: int
    mahsulot_soni: int
    tolov_usuli_id: int | None = None
    chek_rasm_url: str | None = None
    ai_summa: float | None = None
    ai_sana: str | None = None
    ai_xulosa: str | None = None


@router.post("/dokon-sorovi")
def bot_dokon_sorovi(
    payload: BotDokonSorovi,
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """Do'kon ochish so'rovi (chek bilan). Hisobchiга (Moliya boti) yuboriladi."""
    from ..services import dokon as dokon_service

    sorov = dokon_service.create_dokon_sorovi(
        db,
        user,
        dokon_nomi=payload.dokon_nomi,
        admin_telegram_id=payload.admin_telegram_id,
        mahsulot_soni=payload.mahsulot_soni,
        tolov_usuli_id=payload.tolov_usuli_id,
        chek_rasm_url=payload.chek_rasm_url,
        ai_summa=payload.ai_summa,
        ai_sana=payload.ai_sana,
        ai_xulosa=payload.ai_xulosa,
    )
    usul = (
        coin_service.get_tolov_usuli(db, payload.tolov_usuli_id)
        if payload.tolov_usuli_id
        else None
    )
    try:
        from ..tgbots import notify

        notify.notify_moliya_dokon_tolov(
            sorov_id=sorov.id,
            ism=user.ism,
            telegram_id=user.telegram_id,
            dokon_nomi=sorov.dokon_nomi,
            admin_tid=sorov.admin_telegram_id,
            mahsulot_soni=sorov.mahsulot_soni,
            summa=float(sorov.summa),
            ai_summa=payload.ai_summa,
            ai_xulosa=payload.ai_xulosa,
            chek_rel_url=sorov.chek_rasm_url,
            usul_nomi=usul.nomi if usul else None,
        )
    except ImportError:
        pass
    return {
        "sorov_id": sorov.id,
        "summa": float(sorov.summa),
        "holat": sorov.holat,
    }


class BotRefund(BaseModel):
    summa: float
    karta_raqami: str


@router.post("/coin/refund")
def bot_coin_refund(
    payload: BotRefund,
    user: User = Depends(bot_user),
    db: Session = Depends(get_db),
):
    """Balansni qaytarib olish so'rovi. Moliyaга xabar ketadi."""
    sorov = coin_service.create_coin_refund(
        db, user, payload.summa, payload.karta_raqami
    )
    try:
        from ..tgbots import notify

        notify.notify_moliya_refund(
            sorov_id=sorov.id,
            ism=user.ism,
            telegram_id=user.telegram_id,
            summa=float(sorov.sorolgan_summa),
            karta=sorov.karta_raqami,
        )
    except ImportError:
        pass
    return {"sorov_id": sorov.id, "holat": sorov.holat}
