"""Katalog xizmati — bitta umumiy katalog + mahfiy kod mantig'i.

Bu modul critical_architecture_rules'ning eng nozik qismini (rule 1-6)
amalga oshiradi. Har o'zgartirishdan oldin o'sha qoidalarni qayta o'qing.

  rule 1: Bitta umumiy katalog — barcha do'konlarning ommaviy mahsulotlari
          bitta ro'yxatda. Do'kon tanlash ekrani YO'Q.
  rule 3: Do'kon darajasidagi bitta kod butun mahfiy to'plamni ochadi.
  rule 5: Ochilgan do'kon unlocked_stores'da saqlanadi, qayta so'ralmaydi.
  rule 6: Admin kodni yangilasa — "hammani tozalash" funksiyasi YO'Q.
          Buning o'rniga har katalog ko'rsatilганда:
          saqlangan ishlatilgan_kod == do'konning joriy mahfiy_kirish_kodi?
          mos kelmasa — yopiq hisoblanadi.
"""
from __future__ import annotations

from typing import List, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Product, Store, UnlockedStore, User


def get_unlocked_store_ids(db: Session, user: User) -> Set[int]:
    """Mijoz uchun HOZIR ochiq bo'lgan mahfiy do'konlar (rule 6).

    unlocked_stores'dagi har yozuv uchun ishlatilgan_kod do'konning joriy
    mahfiy_kirish_kodi bilan solishtiriladi. Mos kelmasa — yopiq (kod
    yangilangan). Bu yerda hech narsa o'chirilmaydi; taqqoslash o'qish
    paytida amalga oshiriladi.
    """
    rows = db.execute(
        select(UnlockedStore, Store)
        .join(Store, Store.id == UnlockedStore.store_id)
        .where(UnlockedStore.user_id == user.id)
    ).all()

    valid: Set[int] = set()
    for unlocked, store in rows:
        if (
            store.mahfiy_kirish_kodi
            and unlocked.ishlatilgan_kod == store.mahfiy_kirish_kodi
            and store.holat == "faol"
        ):
            valid.add(store.id)
    return valid


def get_catalog(db: Session, user: User) -> List[dict]:
    """Mijoz uchun to'liq katalog — bitta ro'yxat (rule 1).

    Tarkibi:
      * barcha faol do'konlarning ommaviy mahsulotlari;
      * mijozga hozir ochiq bo'lgan do'konlarning mahfiy mahsulotlari.
    """
    unlocked_ids = get_unlocked_store_ids(db, user)

    # Faol do'kon nomlarini oldindan yuklaymiz (javobda store_nomi uchun).
    stores = {s.id: s for s in db.scalars(select(Store)) if s.holat == "faol"}
    active_ids = set(stores.keys())

    products = db.scalars(
        select(Product).where(Product.store_id.in_(active_ids or {-1}))
    ).all()

    catalog: List[dict] = []
    for p in products:
        if p.korinish == "ommaviy" or p.store_id in unlocked_ids:
            store = stores.get(p.store_id)
            catalog.append(
                {
                    "id": p.id,
                    "store_id": p.store_id,
                    "store_nomi": store.nomi if store else None,
                    "nomi": p.nomi,
                    "narxi": float(p.narxi),
                    "olcham": p.olcham,
                    "rang": p.rang,
                    "rasm_url": p.rasm_url,
                    "tavsif": p.tavsif,
                    "korinish": p.korinish,
                }
            )
    return catalog


def accessible_store_ids(db: Session, user: User) -> Set[int]:
    """Checkout uchun: mijoz xarid qila oladigan do'konlar to'plami.

    Barcha faol do'konlar (ommaviy tovar uchun) + ochilgan mahfiy do'konlar.
    """
    active = {
        s.id for s in db.scalars(select(Store)) if s.holat == "faol"
    }
    return active  # Ommaviy tovar har qanday faol do'kondan olinishi mumkin;
    # mahfiy tovar tekshiruvi orders.create_orders_from_cart ichida
    # product.korinish bo'yicha alohida amalga oshiriladi.


def try_unlock(db: Session, user: User, kod: str) -> dict:
    """Kiritilgan kodni BARCHA do'konlar bilan solishtiradi (rule 3, phase 7.3).

    Mos do'kon topilsa:
      * unlocked_stores'ga yoziladi (yoki mavjud yozuv yangilanadi — rule 5/6);
      * o'sha adminning mahfiy mahsulotlari soni qaytariladi.
    Mos kelmasa — ochilmadi.

    Diqqat: kod mahsulotga emas, do'konning butun mahfiy to'plamiga tegishli
    (rule 3). Kod YARATISH bu yerda YO'Q — faqat KIRITISH (rule 4).
    """
    kod = kod.strip()
    store = db.scalar(
        select(Store).where(
            Store.mahfiy_kirish_kodi == kod, Store.holat == "faol"
        )
    )
    if store is None:
        return {
            "ochildi": False,
            "xabar": "Kod noto'g'ri yoki bunday do'kon topilmadi.",
        }

    # Mavjud yozuvni yangilaymiz yoki yangi yaratamiz (rule 5).
    existing = db.scalar(
        select(UnlockedStore).where(
            UnlockedStore.user_id == user.id,
            UnlockedStore.store_id == store.id,
        )
    )
    if existing:
        existing.ishlatilgan_kod = kod
    else:
        db.add(
            UnlockedStore(
                user_id=user.id, store_id=store.id, ishlatilgan_kod=kod
            )
        )
    db.commit()

    count = len(
        db.scalars(
            select(Product.id).where(
                Product.store_id == store.id, Product.korinish == "mahfiy"
            )
        ).all()
    )

    return {
        "ochildi": True,
        "store_id": store.id,
        "store_nomi": store.nomi,
        "qoshilgan_mahsulotlar": count,
        "xabar": f"'{store.nomi}' do'konining mahfiy mahsulotlari ochildi.",
    }
