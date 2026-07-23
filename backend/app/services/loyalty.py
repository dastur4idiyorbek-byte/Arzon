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

# ACOM coin bonuslari (task_6) — jismoniy sovg'a o'rniga coin (KGS bilan 1:1).
KUMUSH_BONUS = 500
OLTIN_BONUS = 1000
REFERAL_BONUS = 500

# Sodiqlik dasturi (foydalanuvchi so'rovi):
#   /start bosganга — 5 ACOM (bir marta)
#   Mini App'ni ochганга — 10 ACOM (bir marta)
#   kamida 1 marta xarid qilган mijozга — har xaridда 5% chegirma
START_BONUS = 5
MINIAPP_BONUS = 10
SODIQLIK_CHEGIRMA_FOIZ = 5


def award_start_bonus(db: Session, user: User) -> int:
    """/start uchun bir martalik bonus. Qaytaradi: berilган ACOM (0 = allaqachon)."""
    if user.start_bonus_berildi:
        return 0
    from . import coin as coin_service

    coin_service.add_bonus(db, user, START_BONUS, coin_service.T_SODIQLIK_BONUS)
    user.start_bonus_berildi = True
    db.commit()
    return START_BONUS


def award_miniapp_bonus(db: Session, user: User) -> int:
    """Mini App'ni birinchi ochган uchun bir martalik bonus (ACOM)."""
    if user.miniapp_bonus_berildi:
        return 0
    from . import coin as coin_service

    coin_service.add_bonus(db, user, MINIAPP_BONUS, coin_service.T_SODIQLIK_BONUS)
    user.miniapp_bonus_berildi = True
    db.commit()
    return MINIAPP_BONUS


def sodiqlik_chegirma_foizi(db: Session, user: User) -> int:
    """Xarid qilган mijozга chegirma foizi (aks holда 0)."""
    return SODIQLIK_CHEGIRMA_FOIZ if count_purchases(db, user) >= 1 else 0


def _notify(telegram_id: int | None, text: str) -> None:
    if not telegram_id:
        return
    try:
        from ..tgbots import notify

        notify.notify_customer(telegram_id, text)
    except Exception:  # noqa: BLE001
        pass


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
        # task_6: yangi kartaга yetganда coin bonusi (jismoniy sovg'a o'rniga).
        from . import coin as coin_service

        bonus = OLTIN_BONUS if yangi.turi == "oltin" else KUMUSH_BONUS
        coin_service.add_bonus(db, user, bonus, coin_service.T_SODIQLIK_BONUS)
        db.commit()
        db.refresh(yangi)
        _notify(
            user.telegram_id,
            f"🎁 Tabriklaymiz! Siz '{yangi.turi}' kartaga ega bo'ldingiz va "
            f"{bonus:,.0f} ACOM ({bonus:,.0f} som) bonus oldingiz!",
        )
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
        # Sodiqlik dasturi holati (foydalanuvchi so'rovi).
        "start_bonus": START_BONUS,
        "miniapp_bonus": MINIAPP_BONUS,
        "start_bonus_olindi": bool(user.start_bonus_berildi),
        "miniapp_bonus_olindi": bool(user.miniapp_bonus_berildi),
        "chegirma_foizi": sodiqlik_chegirma_foizi(db, user),
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
        # task_6: taklif qilgan mijozga coin bonusi.
        from . import coin as coin_service

        referrer = db.get(User, ref.referred_by)
        if referrer:
            coin_service.add_bonus(
                db, referrer, REFERAL_BONUS, coin_service.T_REFERAL_BONUS
            )
            _notify(
                referrer.telegram_id,
                f"🎉 Sizning taklifingiz bilan kelgan do'stingiz birinchi "
                f"xaridini qildi! Sizga {REFERAL_BONUS:,.0f} ACOM "
                f"({REFERAL_BONUS:,.0f} som) bonus qo'shildi.",
            )
        db.commit()
