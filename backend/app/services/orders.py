"""Buyurtma xizmati: 6 xonali kod, do'kon bo'yicha guruhlash, holat tizimi.

Rule 10: turli adminlarning mahsulotlari savatga qo'shilsa, checkout paytida
har bir store_id uchun alohida buyurtma (alohida 6 xonali kod) yaratiladi.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Order, Product, PromoCode, User
from ..models import _as_aware, _now

# Buyurtma holati tizimi (phase 3.2).
ORDER_STATES = [
    "yangi",
    "tayyorlanmoqda",
    "yolda",
    "topshirildi",
    "bekor_qilindi",
]
# Ruxsat etilgan o'tishlar.
ORDER_TRANSITIONS: Dict[str, List[str]] = {
    "yangi": ["tayyorlanmoqda", "bekor_qilindi"],
    "tayyorlanmoqda": ["yolda", "bekor_qilindi"],
    "yolda": ["topshirildi", "bekor_qilindi"],
    "topshirildi": [],
    "bekor_qilindi": [],
}


def generate_order_code(db: Session, *, max_tries: int = 50) -> str:
    """Takrorlanmaydigan 6 xonali kod generatsiya qiladi (phase 3.1).

    secrets moduli — kriptografik jihatdan xavfsiz. Bazada UNIQUE cheklovi
    bor, ammo poyga holatini kamaytirish uchun oldindan tekshiramiz.
    """
    for _ in range(max_tries):
        kod = f"{secrets.randbelow(1_000_000):06d}"
        exists = db.scalar(select(Order.id).where(Order.kod == kod))
        if not exists:
            return kod
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Buyurtma kodi generatsiya qilib bo'lmadi, qayta urinib ko'ring.",
    )


def create_orders_from_cart(
    db: Session,
    user: User,
    items: list,
    accessible_store_ids: set[int],
    promo_kod: str | None = None,
) -> List[Order]:
    """Savatdan buyurtma(lar) yaratadi — do'kon bo'yicha guruhlab (rule 10).

    `accessible_store_ids` — mijoz ko'ra oladigan do'konlar (ommaviy + ochilgan
    mahfiy). Bu ro'yxatdan tashqari do'kon mahsuloti savatga tushmasligi kerak.
    """
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Savat bo'sh."
        )

    # Mahsulotlarni yuklash.
    product_ids = [it.product_id for it in items]
    products = {
        p.id: p
        for p in db.scalars(select(Product).where(Product.id.in_(product_ids)))
    }

    # Do'kon bo'yicha guruhlash.
    grouped: Dict[int, list] = {}
    for it in items:
        product = products.get(it.product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mahsulot topilmadi: {it.product_id}",
            )
        # Mahfiy mahsulot ochilmagan bo'lsa — savatga qo'shib bo'lmaydi.
        if product.store_id not in accessible_store_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"'{product.nomi}' mahsuloti sizga ochilmagan "
                    "(mahfiy kod kerak)."
                ),
            )
        grouped.setdefault(product.store_id, []).append((product, it.soni))

    orders: List[Order] = []
    for store_id, line_items in grouped.items():
        jami = Decimal("0")
        mahsulotlar_json = []
        for product, soni in line_items:
            narx = Decimal(str(product.narxi))
            jami += narx * soni
            mahsulotlar_json.append(
                {
                    "product_id": product.id,
                    "nomi": product.nomi,
                    "narxi": float(narx),
                    "soni": soni,
                    "olcham": product.olcham,
                    "rang": product.rang,
                }
            )

        # Promo kod — faqat shu do'konga tegishli bo'lsa qo'llanadi.
        if promo_kod:
            jami = _apply_promo(db, store_id, promo_kod, jami)

        order = Order(
            store_id=store_id,
            user_id=user.id,
            mahsulotlar=mahsulotlar_json,
            jami_narx=float(jami),
            holat="yangi",
            kod=generate_order_code(db),
            amal_qilish_muddati=_now()
            + timedelta(days=settings.order_code_ttl_days),
        )
        db.add(order)
        orders.append(order)

    db.commit()
    for o in orders:
        db.refresh(o)
    return orders


def _apply_promo(
    db: Session, store_id: int, kod: str, jami: Decimal
) -> Decimal:
    promo = db.scalar(
        select(PromoCode).where(
            PromoCode.store_id == store_id, PromoCode.kod == kod
        )
    )
    if promo is None:
        return jami  # Boshqa do'kon promokodi — jim o'tkazib yuboriladi.
    if promo.muddat and _as_aware(promo.muddat) < _now():
        return jami
    chegirma = jami * Decimal(promo.chegirma_foizi) / Decimal(100)
    promo.ishlatilish_soni += 1
    return (jami - chegirma).quantize(Decimal("0.01"))


def change_order_status(
    db: Session, order: Order, yangi_holat: str, admin_id: int
) -> Order:
    """Buyurtma holatini o'zgartiradi (ruxsat etilgan o'tishlar bo'yicha)."""
    if yangi_holat not in ORDER_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Noma'lum holat: {yangi_holat}",
        )
    allowed = ORDER_TRANSITIONS.get(order.holat, [])
    if yangi_holat not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{order.holat}' holatidan '{yangi_holat}' holatiga "
                "o'tib bo'lmaydi."
            ),
        )
    order.holat = yangi_holat
    db.commit()
    db.refresh(order)
    return order


def confirm_order_code(db: Session, kod: str, admin_id: int) -> Order:
    """Buyurtma kodini tasdiqlaydi (phase 3.3).

    Kim va qachon tasdiqlagani saqlanadi. Muddati o'tган kod rad etiladi.
    """
    order = db.scalar(select(Order).where(Order.kod == kod))
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bunday kodli buyurtma topilmadi.",
        )
    if order.amal_qilish_muddati and _as_aware(order.amal_qilish_muddati) < _now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buyurtma kodi muddati o'tgan.",
        )
    if order.tasdiqlangan_vaqt is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu buyurtma allaqachon tasdiqlangan.",
        )
    order.tasdiqlangan_vaqt = _now()
    order.tasdiqlagan_kim = admin_id
    if order.holat == "yolda":
        order.holat = "topshirildi"
    db.commit()
    db.refresh(order)
    return order
