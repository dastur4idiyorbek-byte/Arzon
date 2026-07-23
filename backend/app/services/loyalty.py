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

# Referal mukofot dasturi (foydalanuvchi so'rovi) — mukofot REFERAL EGASIGA:
#   taklif qilingan do'st /start bossa      -> referal egasiga 5 ACOM
#   taklif qilingan do'st Mini App'ni ochsa -> referal egasiga 10 ACOM
#   taklif qilingan do'st xarid qilsa       -> referal egasiga keyingi xaridiga 5% chegirma
REFERRAL_START_BONUS = 5
REFERRAL_MINIAPP_BONUS = 10
REFERRAL_DISCOUNT_FOIZ = 5


def _referrer_of(db: Session, user: User):
    """Ushbu foydalanuvchini taklif qilgan (referal egasi) — bo'lsa."""
    ref = db.scalar(select(Referral).where(Referral.user_id == user.id))
    return db.get(User, ref.referred_by) if ref else None


def award_miniapp_referral_bonus(db: Session, user: User) -> int:
    """Do'st Mini App'ni birinchi ochganda — referal egasiga 10 ACOM (bir marta).

    Qaytaradi: referal egasiga berilgan ACOM (0 = referal yo'q yoki allaqachon).
    """
    if user.miniapp_bonus_berildi:
        return 0
    user.miniapp_bonus_berildi = True  # takroriy mukofotni oldini olamiz
    referrer = _referrer_of(db, user)
    if referrer is None:
        db.commit()
        return 0
    from . import coin as coin_service

    coin_service.add_bonus(
        db, referrer, REFERRAL_MINIAPP_BONUS, coin_service.T_REFERAL_BONUS
    )
    _notify(
        referrer.telegram_id,
        f"\U0001f389 Taklif qilgan do'stingiz Mini App'ni ochdi! Sizga "
        f"{REFERRAL_MINIAPP_BONUS} ACOM mukofot qo'shildi.",
    )
    db.commit()
    return REFERRAL_MINIAPP_BONUS


def referral_total_earned(db: Session, user: User) -> float:
    """Ushbu foydalanuvchi referal orqali ishlagan jami ACOM."""
    from ..models import CoinHarakati

    val = db.scalar(
        select(func.coalesce(func.sum(CoinHarakati.summa), 0)).where(
            CoinHarakati.user_id == user.id,
            CoinHarakati.turi == "referal_bonus",
        )
    )
    return float(val or 0)


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

    # Taklif qilingan do'stlar: start bosgan (jami) va xarid qilgan.
    taklif_start = (
        db.scalar(
            select(func.count(Referral.id)).where(
                Referral.referred_by == user.id,
            )
        )
        or 0
    )
    taklif_qilganlar = (
        db.scalar(
            select(func.count(Referral.id)).where(
                Referral.referred_by == user.id,
                Referral.holat == "xarid_qilgan",
            )
        )
        or 0
    )

    # Username'ни normallaymiz — to'liq URL yoki @ kiritilган bo'lsa ham faqat
    # username qismини olamiz (aks holда "https://t.me/https://t.me/..." bo'lardi).
    uname = (bot_username or "").strip()
    for pref in ("https://", "http://"):
        if uname.startswith(pref):
            uname = uname[len(pref):]
    for pref in ("t.me/", "telegram.me/", "telegram.dog/"):
        if uname.lower().startswith(pref):
            uname = uname[len(pref):]
    uname = uname.lstrip("@").split("?")[0].split("/")[0]
    havola = (
        f"https://t.me/{uname}?start=ref_{user.telegram_id}"
        if uname
        else f"ref_{user.telegram_id}"
    )

    return {
        "umumiy_xaridlar": total,
        "karta_turi": card.turi if card else None,
        "keyingi_karta_uchun_qolgan": qolgan,
        "referal_havola": havola,
        "taklif_qilganlar": taklif_qilganlar,
        # Referal mukofot dasturi (mukofot referal egasiga).
        "taklif_start": taklif_start,
        "referral_start_bonus": REFERRAL_START_BONUS,
        "referral_miniapp_bonus": REFERRAL_MINIAPP_BONUS,
        "referral_discount_foiz": REFERRAL_DISCOUNT_FOIZ,
        "referral_jami_acom": referral_total_earned(db, user),
        "chegirma_vaucherlar": int(user.chegirma_vaucher or 0),
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
    # Referal egasiga /start mukofoti (do'st link orqali kirib start bosdi).
    from . import coin as coin_service

    coin_service.add_bonus(
        db, referrer, REFERRAL_START_BONUS, coin_service.T_REFERAL_BONUS
    )
    _notify(
        referrer.telegram_id,
        f"\U0001f389 Taklif havolangiz orqali yangi do'st qo'shildi! "
        f"Sizga {REFERRAL_START_BONUS} ACOM mukofot qo'shildi.",
    )
    db.commit()


def mark_referral_purchased(db: Session, user: User, xarid_summasi: float = 0) -> None:
    """Taklif qilingan do'st birinchi xaridini qilganda — referal egasiga 5%."""
    ref = db.scalar(
        select(Referral).where(
            Referral.user_id == user.id, Referral.holat == "start_bosgan"
        )
    )
    if ref:
        ref.holat = "xarid_qilgan"
        from . import coin as coin_service

        referrer = db.get(User, ref.referred_by)
        if referrer:
            # Referal egasiga KEYINGI xaridi uchun 5% chegirma vaucheri (ACOM emas).
            referrer.chegirma_vaucher = (referrer.chegirma_vaucher or 0) + 1
            _notify(
                referrer.telegram_id,
                f"\U0001f389 Taklif qilgan do'stingiz birinchi xaridini qildi! "
                f"Sizga keyingi xaridingizga {REFERRAL_DISCOUNT_FOIZ}% chegirma "
                f"vaucheri berildi.",
            )
        db.commit()
