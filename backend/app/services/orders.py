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
from ..models import Order, Product, PromoCode, Store, User
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
    # tayyorlanmoqda -> topshirildi: punktdan olishда to'g'ridan-to'g'ri topshirish.
    "yangi": ["tayyorlanmoqda", "bekor_qilindi"],
    "tayyorlanmoqda": ["yolda", "topshirildi", "bekor_qilindi"],
    "yolda": ["topshirildi", "bekor_qilindi"],
    "topshirildi": [],
    "bekor_qilindi": [],
}


# Buyurtma kodi belgilari — harf + raqam aralash. Chalkash belgilar
# (O/0, I/1) olib tashlangan, o'qish oson bo'lishi uchun.
_KOD_HARFLAR = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_KOD_RAQAMLAR = "23456789"
_KOD_BELGILAR = _KOD_HARFLAR + _KOD_RAQAMLAR


def generate_order_code(db: Session, *, max_tries: int = 50) -> str:
    """Takrorlanmaydigan 6 belgili kod (harf+raqam aralash).

    Harflar va raqamlar aralashtiriladi (kamida bittadan). Bazada UNIQUE
    cheklovi bor, ammo poyga holatini kamaytirish uchun oldindan tekshiramiz.
    """
    for _ in range(max_tries):
        # Kamida 1 harf + 1 raqam kafolatlanadi, qolgani aralash.
        belgilar = [
            secrets.choice(_KOD_HARFLAR),
            secrets.choice(_KOD_RAQAMLAR),
        ] + [secrets.choice(_KOD_BELGILAR) for _ in range(4)]
        # Aralashtiramiz (harf/raqam pozitsiyasi tasodifiy bo'lsin).
        for i in range(len(belgilar) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            belgilar[i], belgilar[j] = belgilar[j], belgilar[i]
        kod = "".join(belgilar)
        exists = db.scalar(select(Order.id).where(Order.kod == kod))
        if not exists:
            return kod
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Buyurtma kodi generatsiya qilib bo'lmadi, qayta urinib ko'ring.",
    )


def hisobla_yetkazish_narxi(
    manzil: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
) -> Decimal:
    """Yetkazib berish narxini hisoblaydi (som).

    Hozircha qat'iy bazaviy narx (settings.yetkazish_baza_narxi = 100 som).
    Keyinchalik bu yerда manzil/lokatsiyaga (masofaga) qarab hisoblanadi —
    interfeys shu funksiya orqali tayyor turibdi, faqat mantiq almashtiriladi.
    """
    return Decimal(str(settings.yetkazish_baza_narxi))


def create_orders_from_cart(
    db: Session,
    user: User,
    items: list,
    accessible_store_ids: set[int],
    promo_kod: str | None = None,
    yetkazish_turi: str = "kuryer",
    manzil: str | None = None,
    pickup_points: dict | None = None,
    lokatsiya_lat: float | None = None,
    lokatsiya_lng: float | None = None,
) -> List[Order]:
    """Savatdan buyurtma(lar) yaratadi — do'kon bo'yicha guruhlab (rule 10).

    `accessible_store_ids` — mijoz ko'ra oladigan do'konlar (ommaviy + ochilgan
    mahfiy). Bu ro'yxatdan tashqari do'kon mahsuloti savatga tushmasligi kerak.

    Yetkazib berish (spec task_4):
      * 'kuryer' — manzil talab qilinadi.
      * 'pickup' — har do'kon uchun o'sha do'konга tegishli punkt talab qilinadi.
    """
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Savat bo'sh."
        )
    if yetkazish_turi not in ("kuryer", "pickup"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="yetkazish_turi 'kuryer' yoki 'pickup' bo'lsin.",
        )
    if yetkazish_turi == "kuryer" and not (manzil or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kuryer uchun manzil kiritilishi shart.",
        )
    pickup_points = pickup_points or {}

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
        grouped.setdefault(product.store_id, []).append((product, it))

    # Ombor tekshiruvi (task_2): tugagan yoki yetarli bo'lmagan mahsulot
    # savatdan o'tmaydi.
    from .catalog import sotuv_narxi as _sotuv_narxi

    for store_id, line_items in grouped.items():
        for product, it in line_items:
            soni = it.soni
            if product.miqdor is not None:
                if product.miqdor <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"'{product.nomi}' tugagan (omborда yo'q).",
                    )
                if soni > product.miqdor:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"'{product.nomi}'дан faqat {product.miqdor} dona "
                            "qolgan."
                        ),
                    )

    # Sodiqlik chegirmasi — kamida 1 marta xarid qilган mijozга 5% (bu xariddан oldin).
    from . import loyalty as loyalty_service

    sodiqlik_foiz = loyalty_service.sodiqlik_chegirma_foizi(db, user)

    orders: List[Order] = []
    for store_id, line_items in grouped.items():
        jami = Decimal("0")
        mahsulotlar_json = []
        for product, it in line_items:
            soni = it.soni
            # Chegirma faol bo'lса chegirmali narx bilan sotiladi.
            narx = Decimal(str(_sotuv_narxi(product)))
            jami += narx * soni
            mahsulotlar_json.append(
                {
                    "product_id": product.id,
                    "nomi": product.nomi,
                    "narxi": float(narx),
                    "soni": soni,
                    # Mijoz tanlagan variant ustun; bo'lmasa mahsulotdagi qiymat.
                    "olcham": getattr(it, "olcham", None) or product.olcham,
                    "rang": getattr(it, "rang", None) or product.rang,
                }
            )

        # Promo kod — faqat shu do'konga tegishli bo'lsa qo'llanadi.
        if promo_kod:
            jami = _apply_promo(db, store_id, promo_kod, jami)

        # Sodiqlik chegirmasi (xarid qilган mijozга 5%).
        if sodiqlik_foiz:
            jami = (jami * Decimal(100 - sodiqlik_foiz) / Decimal(100)).quantize(
                Decimal("0.01")
            )

        # Yetkazib berish tekshiruvi (do'kon darajasида).
        order_pickup_id = None
        if yetkazish_turi == "pickup":
            pid = pickup_points.get(str(store_id)) or pickup_points.get(store_id)
            from ..models import PickupPoint

            pp = db.get(PickupPoint, pid) if pid else None
            if pp is None or pp.store_id != store_id:
                store = db.get(Store, store_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"'{store.nomi if store else store_id}' do'koni uchun "
                        "olib ketish punktini tanlang."
                    ),
                )
            order_pickup_id = pp.id

        # Yetkazib berish narxi — faqat kuryer uchun (punktdan olish bepul).
        yetkazish = (
            hisobla_yetkazish_narxi(manzil, lokatsiya_lat, lokatsiya_lng)
            if yetkazish_turi == "kuryer"
            else Decimal("0")
        )
        order = Order(
            store_id=store_id,
            user_id=user.id,
            mahsulotlar=mahsulotlar_json,
            # Jami = mahsulotlar + yetkazib berish narxi.
            jami_narx=float(jami + yetkazish),
            holat="yangi",
            kod=generate_order_code(db),
            amal_qilish_muddati=_now()
            + timedelta(days=settings.order_code_ttl_days),
            yetkazish_turi=yetkazish_turi,
            manzil=manzil.strip() if (yetkazish_turi == "kuryer" and manzil) else None,
            pickup_point_id=order_pickup_id,
            yetkazish_narxi=float(yetkazish),
            lokatsiya_lat=lokatsiya_lat,
            lokatsiya_lng=lokatsiya_lng,
        )
        db.add(order)
        orders.append(order)

    # ACOM coin bilan to'lash (rule 1: naqd yo'q; rule 3: balans yetsa darhol).
    from . import coin as coin_service

    db.flush()  # order.id larini olamiz (harakat yozuvlari uchun)
    grand_total = sum((coin_service._dec(o.jami_narx) for o in orders), coin_service._dec(0))
    mavjud = coin_service.balance(user)
    if mavjud < grand_total:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Balansingiz yetarli emas (joriy: {mavjud:,.0f} som, "
                f"kerak: {grand_total:,.0f} som). Hisobingizni to'ldiring."
            ),
        )
    # Rule 4: har buyurtma uchun darhol hisob-kitob (yechish + komissiya + admin).
    # Komissiya faqat mahsulot narxidan olinadi; yetkazish narxi platformaники.
    for o in orders:
        store = db.get(Store, o.store_id)
        yetk = coin_service._dec(o.yetkazish_narxi)
        mahsulot_base = coin_service._dec(o.jami_narx) - yetk
        coin_service.settle_purchase(
            db, user, store, mahsulot_base, o.id, yetkazish=yetk
        )

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


def accept_order(db: Session, order: Order, admin_id: int) -> dict:
    """Buyurtmani tezkor qabul qilish (spec2 task_1 + task_2).

    Holat: yangi -> tayyorlanmoqda. Mahsulotlar miqdori kamaytiriladi;
    tugagan/kamaygan mahsulotlar bo'yicha ogohlantirishlar qaytariladi.
    """
    if order.holat != "yangi":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Buyurtma allaqachon '{order.holat}' holatida.",
        )
    order.holat = "tayyorlanmoqda"

    ogohlantirishlar: List[str] = []
    for item in order.mahsulotlar or []:
        product = db.get(Product, item.get("product_id"))
        if product is None or product.miqdor is None:
            continue  # cheksiz ombor — kamaytirilmaydi
        product.miqdor = max(0, product.miqdor - int(item.get("soni", 0)))
        if product.miqdor == 0:
            ogohlantirishlar.append(
                f"⚠️ '{product.nomi}' tugadi, miqdorni yangilang."
            )
        elif product.miqdor <= 3:
            ogohlantirishlar.append(
                f"🟡 '{product.nomi}' kamaymoqda — {product.miqdor} dona qoldi."
            )
    db.commit()
    db.refresh(order)

    user = db.get(User, order.user_id)
    return {
        "order": order,
        "ogohlantirishlar": ogohlantirishlar,
        "user_telegram_id": user.telegram_id if user else None,
    }


def cancel_order(
    db: Session, order: Order, admin_id: int, sabab: str
) -> dict:
    """Buyurtmani bekor qilish — sabab bilan (spec2 task_1)."""
    if order.holat in ("topshirildi", "bekor_qilindi"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{order.holat}' holatidagi buyurtmani bekor qilib bo'lmaydi.",
        )
    order.holat = "bekor_qilindi"
    order.bekor_sababi = (sabab or "").strip()[:255] or None

    # Rule 5 / task_4: coin darhol qaytariladi (mijozга to'liq, adminдан sof).
    from . import coin as coin_service

    user = db.get(User, order.user_id)
    store = db.get(Store, order.store_id)
    if user and store:
        yetk = coin_service._dec(order.yetkazish_narxi)
        mahsulot_base = coin_service._dec(order.jami_narx) - yetk
        coin_service.refund_purchase(
            db, user, store, mahsulot_base, order.id, yetkazish=yetk
        )

    db.commit()
    db.refresh(order)
    return {
        "order": order,
        "user_telegram_id": user.telegram_id if user else None,
    }


def delete_order_for_user(db: Session, order: Order, user: User) -> None:
    """Mijoz o'z buyurtmasini tarixidan o'chiradi (faqat tugagan buyurtma).

    Faqat egasi va faqat yakuniy holatдаги (topshirildi/bekor_qilindi)
    buyurtмани o'chira oladi — faol buyurtмани o'chirib bo'lmaydi (avval
    bekor qilinishi kerak, coin qaytarilishi uchun).
    """
    if order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu buyurtma sizniki emas.",
        )
    if order.holat not in ("topshirildi", "bekor_qilindi"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Faol buyurtмани o'chirib bo'lmaydi. Avval uni bekor qiling."
            ),
        )
    db.delete(order)
    db.commit()


def confirm_order_code(db: Session, kod: str, admin_id: int) -> Order:
    """Buyurtma kodini tasdiqlaydi (phase 3.3).

    Kim va qachon tasdiqlagani saqlanadi. Muddati o'tган kod rad etiladi.
    """
    kod = (kod or "").strip().upper()
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
