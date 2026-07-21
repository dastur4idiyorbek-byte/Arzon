"""ACOM coin hisob-kitob xizmati — ichki hisob birligi (1 ACOM = 1 KGS).

Bu modul ACOM_Coin_Tizimi spec'ining yuragi: darhol hisoblash (rule 4),
darhol qaytarish (rule 5), komissiya, to'ldirish/yechish/qaytarish so'rovlari
va real vaqtli hisobot (coin_harakatlari jadvalidan SUM() bilan).

DIQQAT (rule 0): barcha summalar Qirg'iziston somida (KGS). O'zbekiston so'mi
(UZS) EMAS. Naqd to'lov yo'q (rule 1) — hamma narsa coin balansi orqali.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    CoinHarakati,
    CoinQaytarishSorovi,
    CoinToldirishSorovi,
    Order,
    PlatformaHisob,
    PulYechishSorovi,
    Store,
    User,
    _now,
)

# Movement turlari.
T_TOLDIRISH = "toldirish"
T_XARID = "xarid"
T_QAYTARISH = "bekor_qilish_qaytarish"
T_PUL_YECHISH = "pul_yechish"
T_QAYTARIB_OLISH = "qaytarib_olish"
T_REFERAL_BONUS = "referal_bonus"
T_SODIQLIK_BONUS = "sodiqlik_bonus"


def _dec(x) -> Decimal:
    """Har qanday qiymatni (None ham) 2 kasrli Decimalga aylantiradi."""
    return Decimal(str(x or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def komissiya(narx) -> Decimal:
    """Xarid komissiyasi (KGS) — KOMISSIYA_FOIZI foiz."""
    return (_dec(narx) * Decimal(settings.komissiya_foizi) / Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def sof_summa(narx) -> Decimal:
    """Adminга tushadigan sof summa (narx - komissiya)."""
    return _dec(narx) - komissiya(narx)


def balance(user: User) -> Decimal:
    return _dec(user.coin_balans)


def store_balance(store: Store) -> Decimal:
    return _dec(store.kutilayotgan_balans)


def _record(
    db: Session,
    turi: str,
    summa,
    *,
    user_id: Optional[int] = None,
    store_id: Optional[int] = None,
    order_id: Optional[int] = None,
) -> None:
    """coin_harakatlari jadvaliga yozuv qo'shadi (commit chaqiruvchida)."""
    db.add(
        CoinHarakati(
            user_id=user_id,
            store_id=store_id,
            turi=turi,
            summa=_dec(summa),
            order_id=order_id,
        )
    )


# ---------------------------------------------------------------------------
# Xarid / bekor qilish — darhol hisob-kitob (rule 4, 5)
# ---------------------------------------------------------------------------
def settle_purchase(
    db: Session, user: User, store: Store, narx, order_id: int
) -> None:
    """Xarid darhol hisob-kitobi (rule 4). Commit chaqiruvchida.

    Bitta amalда: mijozdan to'liq narx yechiladi, komissiya hisoblanadi,
    adminга sof summa (narx - komissiya) qo'shiladi.
    """
    narx = _dec(narx)
    user.coin_balans = balance(user) - narx
    store.kutilayotgan_balans = store_balance(store) + sof_summa(narx)
    _record(
        db, T_XARID, narx, user_id=user.id, store_id=store.id, order_id=order_id
    )


def refund_purchase(
    db: Session, user: User, store: Store, narx, order_id: int
) -> None:
    """Bekor qilishда darhol teskari amal (rule 5). Commit chaqiruvchida.

    Mijozга to'liq narx qaytadi, admin balansidan sof summa ayiriladi.
    """
    narx = _dec(narx)
    user.coin_balans = balance(user) + narx
    store.kutilayotgan_balans = store_balance(store) - sof_summa(narx)
    _record(
        db, T_QAYTARISH, narx, user_id=user.id, store_id=store.id, order_id=order_id
    )


# ---------------------------------------------------------------------------
# Bonuslar (sodiqlik / referal) — coin sifatida (task_6)
# ---------------------------------------------------------------------------
def add_bonus(db: Session, user: User, summa, turi: str) -> None:
    """Mijoz balansiga bonus qo'shadi (referal_bonus / sodiqlik_bonus)."""
    user.coin_balans = balance(user) + _dec(summa)
    _record(db, turi, summa, user_id=user.id)


# ---------------------------------------------------------------------------
# Platforma hisob (super-admin karta ma'lumotlari)
# ---------------------------------------------------------------------------
def get_platforma_hisob(db: Session) -> Optional[PlatformaHisob]:
    return db.scalar(
        select(PlatformaHisob).order_by(PlatformaHisob.id.desc())
    )


def set_platforma_hisob(db: Session, karta: str, egasi: str) -> PlatformaHisob:
    row = get_platforma_hisob(db)
    if row is None:
        row = PlatformaHisob(karta_raqami=karta, hisob_egasi=egasi)
        db.add(row)
    else:
        row.karta_raqami = karta
        row.hisob_egasi = egasi
        row.yangilangan_vaqt = _now()
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Balansni to'ldirish so'rovlari (task_1, task_2)
# ---------------------------------------------------------------------------
def _today_start() -> datetime:
    from ..tgbots.daily import LOCAL_TZ
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(LOCAL_TZ)
    now_local = datetime.now(tz)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def check_topup_limits(db: Session, user: User, summa) -> Optional[str]:
    """To'ldirish chegaralarини tekshiradi. Xato matni yoki None qaytaradi."""
    summa = _dec(summa)
    if summa <= 0:
        return "Summa 0 dan katta bo'lishi kerak."
    if summa > _dec(settings.bir_martalik_toldirish_limit):
        return (
            f"Bir martalik to'ldirish chegarasi: "
            f"{_dec(settings.bir_martalik_toldirish_limit):,.0f} som. "
            "Kichikroq summa kiriting."
        )
    # Kunlik so'rovlar soni.
    bugun = _today_start()
    soni = (
        db.scalar(
            select(func.count(CoinToldirishSorovi.id)).where(
                CoinToldirishSorovi.user_id == user.id,
                CoinToldirishSorovi.yaratilgan_vaqt >= bugun,
            )
        )
        or 0
    )
    if soni >= settings.kunlik_toldirish_soni_limit:
        return (
            f"Kunlik to'ldirish so'rovlari chegarasi ({settings.kunlik_toldirish_soni_limit} ta) "
            "tugadi. Ertaga qayta urinib ko'ring."
        )
    return None


def create_topup_request(
    db: Session,
    user: User,
    summa,
    *,
    chek_rasm_url: Optional[str] = None,
    ai_summa=None,
    ai_sana: Optional[str] = None,
    ai_xulosa: Optional[str] = None,
) -> CoinToldirishSorovi:
    """To'ldirish so'rovini yaratadi (rule 2 — coin hali BERILMAYDI)."""
    xato = check_topup_limits(db, user, summa)
    if xato:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=xato)
    sorov = CoinToldirishSorovi(
        user_id=user.id,
        som_summasi=_dec(summa),
        chek_rasm_url=chek_rasm_url,
        ai_ochigan_summa=_dec(ai_summa) if ai_summa is not None else None,
        ai_ochigan_sana=ai_sana,
        ai_xulosasi=ai_xulosa,
        holat="kutilmoqda",
    )
    db.add(sorov)
    db.commit()
    db.refresh(sorov)
    return sorov


def approve_topup(db: Session, sorov: CoinToldirishSorovi, admin_id: int) -> User:
    """Super-admin tasdiqlaydi — coin BERILADI (rule 2, task_2)."""
    if sorov.holat != "kutilmoqda":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"So'rov allaqachon '{sorov.holat}' holatida.",
        )
    user = db.get(User, sorov.user_id)
    user.coin_balans = balance(user) + _dec(sorov.som_summasi)
    sorov.holat = "tasdiqlandi"
    sorov.tasdiqlagan_admin = admin_id
    _record(db, T_TOLDIRISH, sorov.som_summasi, user_id=user.id)
    db.commit()
    db.refresh(user)
    return user


def reject_topup(
    db: Session, sorov: CoinToldirishSorovi, admin_id: int, sabab: str
) -> None:
    if sorov.holat != "kutilmoqda":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"So'rov allaqachon '{sorov.holat}' holatida.",
        )
    sorov.holat = "rad_etildi"
    sorov.tasdiqlagan_admin = admin_id
    sorov.rad_sababi = (sabab or "").strip()[:255] or None
    db.commit()


# ---------------------------------------------------------------------------
# Pul yechish so'rovlari (task_5, task_2)
# ---------------------------------------------------------------------------
def pending_withdraw_total(db: Session, store_id: int) -> Decimal:
    rows = db.scalars(
        select(PulYechishSorovi.sorolgan_summa).where(
            PulYechishSorovi.store_id == store_id,
            PulYechishSorovi.holat == "kutilmoqda",
        )
    ).all()
    return sum((_dec(r) for r in rows), Decimal("0"))


def create_withdraw(
    db: Session, store: Store, summa, karta: str, admin_id: int
) -> PulYechishSorovi:
    """Admin pul yechish so'rovi (minimal chegara yo'q — rule 6)."""
    summa = _dec(summa)
    if summa <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summa 0 dan katta bo'lishi kerak.",
        )
    mavjud = store_balance(store) - pending_withdraw_total(db, store.id)
    if summa > mavjud:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Balansingiz yetarli emas. Yechish mumkin: {mavjud:,.0f} som "
                f"(kutilayotgan so'rovlar hisobga olindi)."
            ),
        )
    sorov = PulYechishSorovi(
        store_id=store.id,
        sorolgan_summa=summa,
        karta_raqami=(karta or "").strip()[:32],
        holat="kutilmoqda",
        soragan_admin=admin_id,
    )
    db.add(sorov)
    db.commit()
    db.refresh(sorov)
    return sorov


def mark_withdraw_paid(db: Session, sorov: PulYechishSorovi) -> None:
    """Super-admin real pulni o'tkazgach — balansdan ayiriladi (task_2)."""
    if sorov.holat != "kutilmoqda":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"So'rov allaqachon '{sorov.holat}' holatida.",
        )
    store = db.get(Store, sorov.store_id)
    store.kutilayotgan_balans = store_balance(store) - _dec(sorov.sorolgan_summa)
    sorov.holat = "yopildi"
    sorov.yopilgan_vaqt = _now()
    _record(db, T_PUL_YECHISH, sorov.sorolgan_summa, store_id=store.id)
    db.commit()


# ---------------------------------------------------------------------------
# Balansni qaytarib olish so'rovlari (task_2, task_8)
# ---------------------------------------------------------------------------
def pending_refund_total(db: Session, user_id: int) -> Decimal:
    rows = db.scalars(
        select(CoinQaytarishSorovi.sorolgan_summa).where(
            CoinQaytarishSorovi.user_id == user_id,
            CoinQaytarishSorovi.holat == "kutilmoqda",
        )
    ).all()
    return sum((_dec(r) for r in rows), Decimal("0"))


def create_coin_refund(
    db: Session, user: User, summa, karta: str
) -> CoinQaytarishSorovi:
    summa = _dec(summa)
    if summa <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summa 0 dan katta bo'lishi kerak.",
        )
    mavjud = balance(user) - pending_refund_total(db, user.id)
    if summa > mavjud:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Balansingiz yetarli emas. Qaytarish mumkin: {mavjud:,.0f} som.",
        )
    sorov = CoinQaytarishSorovi(
        user_id=user.id,
        sorolgan_summa=summa,
        karta_raqami=(karta or "").strip()[:32],
        holat="kutilmoqda",
    )
    db.add(sorov)
    db.commit()
    db.refresh(sorov)
    return sorov


def approve_coin_refund(db: Session, sorov: CoinQaytarishSorovi) -> None:
    """Qaytarishни tasdiqlaydi — balansdan ayiriladi (komissiya YO'Q)."""
    if sorov.holat != "kutilmoqda":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"So'rov allaqachon '{sorov.holat}' holatida.",
        )
    user = db.get(User, sorov.user_id)
    user.coin_balans = balance(user) - _dec(sorov.sorolgan_summa)
    sorov.holat = "yopildi"
    sorov.yopilgan_vaqt = _now()
    _record(db, T_QAYTARIB_OLISH, sorov.sorolgan_summa, user_id=user.id)
    db.commit()


def reject_coin_refund(db: Session, sorov: CoinQaytarishSorovi, sabab: str) -> None:
    if sorov.holat != "kutilmoqda":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"So'rov allaqachon '{sorov.holat}' holatida.",
        )
    sorov.holat = "rad_etildi"
    sorov.yopilgan_vaqt = _now()
    db.commit()


# ---------------------------------------------------------------------------
# Umumiy hisobot (task_2) — coin_harakatlari'дан real vaqtда SUM()
# ---------------------------------------------------------------------------
def _sum_count_today(db: Session, turi: str) -> tuple[Decimal, int]:
    bugun = _today_start()
    row = db.execute(
        select(func.coalesce(func.sum(CoinHarakati.summa), 0), func.count(CoinHarakati.id))
        .where(CoinHarakati.turi == turi, CoinHarakati.vaqt >= bugun)
    ).one()
    return _dec(row[0]), int(row[1])


def overall_report(db: Session) -> dict:
    """Umumiy holat + bugungi harakatlar (barchasi KGS)."""
    jami_mijoz = _dec(
        db.scalar(select(func.coalesce(func.sum(User.coin_balans), 0)))
    )
    jami_admin = _dec(
        db.scalar(select(func.coalesce(func.sum(Store.kutilayotgan_balans), 0)))
    )
    toldirish_sum, toldirish_cnt = _sum_count_today(db, T_TOLDIRISH)
    xarid_sum, xarid_cnt = _sum_count_today(db, T_XARID)
    yechish_sum, yechish_cnt = _sum_count_today(db, T_PUL_YECHISH)
    komissiya_bugun = komissiya(xarid_sum)

    return {
        "jami_mijozlar_balansi": float(jami_mijoz),
        "jami_adminlar_balansi": float(jami_admin),
        "platforma_hisobida": float(jami_mijoz + jami_admin),
        "bugun_toldirish_summa": float(toldirish_sum),
        "bugun_toldirish_soni": toldirish_cnt,
        "bugun_xarid_summa": float(xarid_sum),
        "bugun_xarid_soni": xarid_cnt,
        "bugun_yechish_summa": float(yechish_sum),
        "bugun_yechish_soni": yechish_cnt,
        "bugun_komissiya": float(komissiya_bugun),
    }
