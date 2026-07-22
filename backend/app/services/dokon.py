"""Do'kon ochish so'rovi xizmati.

Mijoz Savdo botида do'kon ochish uchun so'rov yuboradi (nom, admin ID, mahsulot
soni, to'lov cheki). Hisobchi (Moliya boti) chekni tasdiqlasa — do'kon avtomatik
ochiladi va so'rovchiга admin bot havolasi + mahfiy kod yuboriladi.

Narx: har 10 mahsulot uchun settings.dokon_ontalik_narxi (100 som).
Hozircha 10..100 mahsulotgacha.
"""
from __future__ import annotations

import secrets
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import DokonSorovi, Store, User

# Ruxsat etilgan mahsulot sonlari (o'ntalik, 100 gacha).
RUXSAT_SONLAR = list(range(10, 101, 10))  # [10, 20, ..., 100]


def _generate_secret_code() -> str:
    return secrets.token_hex(3).upper()  # 6 belgili


def hisobla_summa(mahsulot_soni: int) -> Decimal:
    """Do'kon ochish narxi: (mahsulot_soni / 10) * o'ntalik narxi."""
    ontalik = mahsulot_soni // 10
    return Decimal(str(ontalik * settings.dokon_ontalik_narxi))


def create_dokon_sorovi(
    db: Session,
    user: User,
    *,
    dokon_nomi: str,
    admin_telegram_id: int,
    mahsulot_soni: int,
    tolov_usuli_id: Optional[int] = None,
    chek_rasm_url: Optional[str] = None,
    ai_summa=None,
    ai_sana: Optional[str] = None,
    ai_xulosa: Optional[str] = None,
) -> DokonSorovi:
    if mahsulot_soni not in RUXSAT_SONLAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mahsulot_soni 10 dan 100 gacha (o'ntalik) bo'lishi kerak.",
        )
    if not (dokon_nomi or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Do'kon nomi bo'sh."
        )
    sorov = DokonSorovi(
        user_id=user.id,
        dokon_nomi=dokon_nomi.strip()[:255],
        admin_telegram_id=admin_telegram_id,
        mahsulot_soni=mahsulot_soni,
        summa=hisobla_summa(mahsulot_soni),
        tolov_usuli_id=tolov_usuli_id,
        chek_rasm_url=chek_rasm_url,
        ai_ochigan_summa=Decimal(str(ai_summa)) if ai_summa is not None else None,
        ai_ochigan_sana=ai_sana,
        ai_xulosasi=ai_xulosa,
        holat="kutilmoqda",
    )
    db.add(sorov)
    db.commit()
    db.refresh(sorov)
    return sorov


def approve_dokon_sorovi(db: Session, sorov: DokonSorovi, admin_id: int) -> Store:
    """Hisobchi tasdiqlaydi — do'kon avtomatik ochiladi (mahfiy kod bilan)."""
    if sorov.holat != "kutilmoqda":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"So'rov allaqachon '{sorov.holat}' holatida.",
        )
    store = Store(
        nomi=sorov.dokon_nomi,
        admin_ids=[sorov.admin_telegram_id],
        mahfiy_kirish_kodi=_generate_secret_code(),
        holat="faol",
        mahsulot_limiti=sorov.mahsulot_soni,
    )
    db.add(store)
    db.flush()  # store.id
    sorov.holat = "tasdiqlandi"
    sorov.tasdiqlagan_admin = admin_id
    sorov.created_store_id = store.id
    db.commit()
    db.refresh(store)
    return store


def reject_dokon_sorovi(
    db: Session, sorov: DokonSorovi, admin_id: int, sabab: str
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


def list_pending(db: Session) -> list[DokonSorovi]:
    return db.scalars(
        select(DokonSorovi)
        .where(DokonSorovi.holat == "kutilmoqda")
        .order_by(DokonSorovi.id.desc())
    ).all()
