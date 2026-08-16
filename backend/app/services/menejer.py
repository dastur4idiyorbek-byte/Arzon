"""Menejer xizmati — do'kon/admin/mahsulot moderatsiyasi va arenda nazorati.

Faqat Menejer Boti (super-admin/menejer) ishlatadi. Boshqaruv Bot bilan
umumiy interfeys yo'q — faqat umumiy ma'lumotlar bazasi (rule 2).
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import vector_store
from ..models import Order, Product, Store, User, _as_aware, _now, admin_identity
from ..models import PickupPoint as _Pickup
from ..models import PromoCode as _Promo
from ..models import UnlockedStore as _Unlocked

ARENDA_MUDDAT_KUN = 30  # bir oy ~ 30 kun


# ---------------------------------------------------------------------------
# Do'kon / mahsulot o'chirish (moderatsiya)
# ---------------------------------------------------------------------------
def delete_store_cascade(db: Session, store_id: int) -> str:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    nomi = store.nomi
    product_ids = [p.id for p in store.products]
    for model in (Order, _Promo, _Unlocked, _Pickup):
        for row in db.scalars(select(model).where(model.store_id == store_id)):
            db.delete(row)
    db.delete(store)  # mahsulotlar cascade bilan
    db.commit()
    for pid in product_ids:
        vector_store.remove_product(pid)
    return nomi


def delete_product_moderation(db: Session, product_id: int) -> str:
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi.")
    nomi = p.nomi
    db.delete(p)
    db.commit()
    vector_store.remove_product(product_id)
    return nomi


# ---------------------------------------------------------------------------
# Adminlarni boshqarish
# ---------------------------------------------------------------------------
def resolve_admin_id(db: Session, telegram_id: int | None, email: str | None) -> int:
    """Admin identifikatorini aniqlaydi — Telegram ID yoki email bo'yicha.

    Email berilsa, o'sha email bilan ro'yxatdan o'tgan hisob topiladi va unga
    manfiy ID beriladi (models.admin_identity). Ya'ni Gmail bilan kirgan odam
    ham do'kon admini bo'la oladi.
    """
    if telegram_id:
        return int(telegram_id)
    if not email or not email.strip():
        raise HTTPException(
            status_code=400, detail="telegram_id yoki email kiriting."
        )
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{email.strip()}' bilan ro'yxatdan o'tgan hisob topilmadi. "
                "Avval o'sha odam ilovaga shu email bilan kirsin."
            ),
        )
    return admin_identity(user)


def add_admin(
    db: Session,
    store_id: int,
    telegram_id: int | None = None,
    email: str | None = None,
) -> list:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    admin_id = resolve_admin_id(db, telegram_id, email)
    ids = list(store.admin_ids or [])
    if admin_id not in ids:
        ids.append(admin_id)
        store.admin_ids = ids
        db.commit()
    return list(store.admin_ids or [])


def remove_admin(db: Session, store_id: int, admin_id: int) -> list:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    ids = [a for a in (store.admin_ids or []) if a != admin_id]
    store.admin_ids = ids
    db.commit()
    return ids


def list_stores_info(db: Session) -> list[dict]:
    """Barcha do'konlar — admin/mahsulot soni + arenda holati bilan."""
    natija = []
    for s in db.scalars(select(Store).order_by(Store.id)):
        cnt = db.scalar(
            select(func.count(Product.id)).where(Product.store_id == s.id)
        ) or 0
        natija.append(
            {
                "id": s.id,
                "nomi": s.nomi,
                "holat": s.holat,
                "admin_ids": list(s.admin_ids or []),
                "mahsulot_soni": int(cnt),
                "mahsulot_limiti": s.mahsulot_limiti,
                "arenda_summasi": float(s.arenda_summasi)
                if s.arenda_summasi is not None
                else None,
                "arenda_muddati_tugashi": (
                    _as_aware(s.arenda_muddati_tugashi).isoformat()
                    if s.arenda_muddati_tugashi
                    else None
                ),
            }
        )
    return natija


def list_store_products(db: Session, store_id: int) -> list[dict]:
    rows = db.scalars(
        select(Product).where(Product.store_id == store_id).order_by(Product.id)
    ).all()
    return [{"id": p.id, "nomi": p.nomi, "narxi": float(p.narxi)} for p in rows]


# ---------------------------------------------------------------------------
# Arenda nazorati
# ---------------------------------------------------------------------------
def block_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    store.holat = "vaqtincha_toxtatilgan"
    db.commit()
    db.refresh(store)
    return store


def unblock_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    store.holat = "faol"
    db.commit()
    db.refresh(store)
    return store


def set_arenda(db: Session, store_id: int, summa, muddat=None) -> Store:
    """Do'kon arendasini o'rnatadi (summa + muddat). Yangi do'kon uchun."""
    from decimal import Decimal

    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    store.arenda_summasi = Decimal(str(summa)) if summa is not None else None
    store.arenda_muddati_tugashi = muddat or (_now() + timedelta(days=ARENDA_MUDDAT_KUN))
    db.commit()
    db.refresh(store)
    return store


def admin_recipients(db: Session) -> list[int]:
    """Barcha do'kon adminlarининг Telegram ID'lari (takrorsiz)."""
    ids: set[int] = set()
    for s in db.scalars(select(Store)):
        for a in s.admin_ids or []:
            ids.add(int(a))
    return list(ids)


def customer_recipients(db: Session) -> list[int]:
    """Barcha mijozlarининг Telegram ID'lari."""
    return [int(t) for t in db.scalars(select(User.telegram_id)) if t]


def extend_arenda(db: Session, store_id: int, oy: int = 1) -> Store:
    """Arendani `oy` oyга uzaytiradi va do'konни blokdan chiqaradi.

    Muddat hozirgi tugash sanasidан (agar kelajakда bo'lsa) yoki hozirdан
    boshlab uzaytiriladi.
    """
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    baza = _now()
    joriy = _as_aware(store.arenda_muddati_tugashi)
    if joriy and joriy > baza:
        baza = joriy
    store.arenda_muddati_tugashi = baza + timedelta(days=ARENDA_MUDDAT_KUN * oy)
    store.holat = "faol"  # to'lov qilindi — blokdan chiqadi
    db.commit()
    db.refresh(store)
    return store
