"""Savat/checkout, buyurtmalar tarixi, kontakt tasdiqlash (phase 2.3, 3.5)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, User
from ..schemas import (
    CheckoutRequest,
    CheckoutResponse,
    OrderOut,
    PhoneConfirmRequest,
)
from ..security import get_current_user
from ..services import catalog as catalog_service
from ..services import loyalty as loyalty_service
from ..services import orders as order_service

router = APIRouter(prefix="/api", tags=["buyurtma"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Savatni buyurtmaga aylantiradi — do'kon bo'yicha ajratib (rule 10).

    2-bosqich tasdiqlash (rule 8): telefon tasdiqlanmagan bo'lsa, checkout
    rad etiladi va mijoz "Kontaktni ulashish"ga yo'naltiriladi.
    """
    if not user.tel_tasdiqlangan:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=(
                "Birinchi buyurtma uchun telefon raqamingizni tasdiqlang "
                "('Kontaktni ulashish')."
            ),
        )

    accessible = catalog_service.accessible_store_ids(db, user)
    orders = order_service.create_orders_from_cart(
        db, user, payload.items, accessible, payload.promo_kod
    )

    # Referal: birinchi xaridni belgilash (phase 4.4).
    loyalty_service.mark_referral_purchased(db, user)

    # Yangi buyurtma haqida do'kon adminlariga xabar (spec2 task_1).
    # PTB o'rnatilmagan yoki botlar faol bo'lmagan muhitда jimgina o'tadi.
    try:
        from ..models import Store
        from ..tgbots import notify

        for o in orders:
            store = db.get(Store, o.store_id)
            notify.notify_new_order(
                admin_ids=list(store.admin_ids or []) if store else [],
                order_id=o.id,
                kod=o.kod,
                jami=float(o.jami_narx),
                mahsulotlar=o.mahsulotlar,
                mijoz_ism=user.ism,
                mijoz_tel=user.tel,
            )
    except ImportError:
        pass

    return CheckoutResponse(
        buyurtmalar=[OrderOut.model_validate(o) for o in orders],
        xabar=(
            f"{len(orders)} ta buyurtma yaratildi. Har biriga alohida kod "
            "berildi."
        ),
    )


@router.get("/orders", response_model=List[OrderOut])
def my_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mijozning buyurtmalar tarixi (phase 7.5)."""
    rows = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.yaratilgan_vaqt.desc())
    ).all()
    return [OrderOut.model_validate(o) for o in rows]


@router.post("/confirm-phone")
def confirm_phone(
    payload: PhoneConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Kontaktni ulashish — telefonni tasdiqlash (rule 8, 2-bosqich).

    Telegram "Kontaktni ulashish" tugmasi orqali yuborilgan raqam bot
    tomonidan backendga uzatiladi. SMS-OTP kerak emas (rule 8 notogri).
    """
    user.tel = payload.tel
    user.tel_tasdiqlangan = True
    db.commit()
    return {"tel_tasdiqlangan": True, "xabar": "Telefon tasdiqlandi."}
