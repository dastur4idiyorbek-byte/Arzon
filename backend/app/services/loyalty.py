"""Sodiqlik va referal xizmati.

Rule 9: Kumush/Oltin karta va referal user_id'ga bog'lanadi — barcha
do'konlar bo'yicha xaridlar BIRGALIKDA hisoblanadi (store_id'ga emas).
"""
from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import LoyaltyCard, Order, Referral, User

# Karta chegaralari (phase 4.2).
KUMUSH_THRESHOLD = 5
OLTIN_THRESHOLD = 10
# Maxsus referal sovg'asi (phase 4.4).
REFERAL_SOVGA_THRESHOLD = 100


def count_purchases(db: Session, user: User) -> int:
    """Mijozning barcha do'konlar bo'yicha tasdiqlangan xaridlari (rule 9).

    'topshirildi' holatidagi yoki tasdiqlangan buyurtmalar hisoblanadi.
    """
    return (
        db.scalar(
            select(func.count(Order.id)).where(
                Order.user_id == user.id,
                Order.tasdiqlangan_vaqt.isnot(None),
            )
        )
        or 0
    )


def _generate_card_code() -> str:
    return secrets.token_hex(4).upper()


def evaluate_loyalty(db: Session, user: User) -> LoyaltyCard | None:
    """Xaridlar soniga qarab karta beradi (agar hali berilmagan bo'lsa).

    10 xaridda Oltin, 5 xaridda Kumush. Eng yuqori darajadagi karta qaytadi.
    """
    total = count_purchases(db, user)

    mavjud = {
        c.turi: c
        for c in db.scalars(
            select(LoyaltyCard).where(LoyaltyCard.user_id == user.id)
        )
    }

    yangi = None
    if total >= OLTIN_THRESHOLD and "oltin" not in mavjud:
        yangi = LoyaltyCard(
            user_id=user.id, turi="oltin", kod=_generate_card_code()
        )
    elif (
        total >= KUMUSH_THRESHOLD
        and "kumush" not in mavjud
        and "oltin" not in mavjud
    ):
        yangi = LoyaltyCard(
            user_id=user.id, turi="kumush", kod=_generate_card_code()
        )

    if yangi:
        db.add(yangi)
        db.commit()
        db.refresh(yangi)
        return yangi

    # Mavjud eng yuqori karta.
    if "oltin" in mavjud:
        return mavjud["oltin"]
    if "kumush" in mavjud:
        return mavjud["kumush"]
    return None


def loyalty_status(db: Session, user: User, bot_username: str = "") -> dict:
    total = count_purchases(db, user)
    card = evaluate_loyalty(db, user)

    if total < KUMUSH_THRESHOLD:
        qolgan = KUMUSH_THRESHOLD - total
    elif total < OLTIN_THRESHOLD:
        qolgan = OLTIN_THRESHOLD - total
    else:
        qolgan = None

    taklif_qilganlar = (
        db.scalar(
            select(func.count(Referral.id)).where(
                Referral.referred_by == user.id,
                Referral.holat == "xarid_qilgan",
            )
        )
        or 0
    )

    havola = (
        f"https://t.me/{bot_username}?start=ref_{user.telegram_id}"
        if bot_username
        else f"ref_{user.telegram_id}"
    )

    return {
        "umumiy_xaridlar": total,
        "karta_turi": card.turi if card else None,
        "keyingi_karta_uchun_qolgan": qolgan,
        "referal_havola": havola,
        "taklif_qilganlar": taklif_qilganlar,
    }


def register_referral(
    db: Session, new_user: User, referrer_telegram_id: int
) -> None:
    """Yangi foydalanuvchi referal havola orqali kelganda (phase 4.4).

    O'zini-o'zi taklif qilish va takroriy yozuvlar bloklanadi.
    """
    referrer = db.scalar(
        select(User).where(User.telegram_id == referrer_telegram_id)
    )
    if referrer is None or referrer.id == new_user.id:
        return
    exists = db.scalar(
        select(Referral).where(Referral.user_id == new_user.id)
    )
    if exists:
        return
    db.add(
        Referral(
            user_id=new_user.id,
            referred_by=referrer.id,
            holat="start_bosgan",
        )
    )
    db.commit()


def mark_referral_purchased(db: Session, user: User) -> None:
    """Taklif qilingan mijoz birinchi xaridini qilganda holatni yangilaydi."""
    ref = db.scalar(
        select(Referral).where(
            Referral.user_id == user.id, Referral.holat == "start_bosgan"
        )
    )
    if ref:
        ref.holat = "xarid_qilgan"
        db.commit()
