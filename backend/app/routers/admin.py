"""Admin endpointlari — Boshqaruv Boti orqali ishlatiladi (phase 8).

Har bir endpoint check_store_access(admin_id, store_id) orqali izolyatsiyani
tekshiradi (rule 7). Mahfiy kod faqat shu yerda yaratiladi/yangilanadi
(rule 4). Yangi do'kon faqat super-admin tomonidan qo'shiladi (rule 11).
"""
from __future__ import annotations

import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import vector_store
from ..database import get_db
from ..models import Order, Product, PromoCode, Store
from ..schemas import OrderOut, ProductCreate, ProductOut, ProductUpdate
from ..security import (
    check_store_access,
    get_admin_store_ids,
    is_super_admin,
    require_admin,
)
from ..services import orders as order_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _generate_secret_code() -> str:
    """Do'kon uchun mahfiy kirish kodi (rule 3, 4)."""
    return secrets.token_hex(3).upper()  # 6 belgili, masalan 'A1B2C3'


# ---------------------------------------------------------------------------
# Mahsulot boshqaruvi (phase 8.2) — faqat shu admin store_id doirasida (rule 7)
# ---------------------------------------------------------------------------
ALLOWED_RATIOS = {"1:1", "4:3", "3:4", "9:16", "16:9"}


def _check_ratio(nisbat: str | None) -> None:
    if nisbat is not None and nisbat not in ALLOWED_RATIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"rasm_nisbati quyidagilardan biri bo'lsin: {ALLOWED_RATIOS}",
        )


def _hisobla_yakuniy(narxi: float, skidka_foizi: int | None) -> float | None:
    """Chegirmali yakuniy narx: narx - (narx * foiz / 100)."""
    sk = skidka_foizi or 0
    if sk <= 0:
        return None
    from decimal import Decimal

    return float(
        (Decimal(str(narxi)) * (100 - sk) / 100).quantize(Decimal("0.01"))
    )


@router.post("/stores/{store_id}/products", response_model=ProductOut)
def add_product(
    store_id: int,
    payload: ProductCreate,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    check_store_access(admin_id, store_id, db)  # rule 7
    if payload.korinish not in ("ommaviy", "mahfiy"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="korinish 'ommaviy' yoki 'mahfiy' bo'lishi kerak.",
        )
    if payload.rasm_urls and len(payload.rasm_urls) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maksimal 10 ta rasm.",
        )
    _check_ratio(payload.rasm_nisbati)
    data = payload.model_dump()
    data["yakuniy_narx"] = _hisobla_yakuniy(
        payload.narxi, payload.skidka_foizi
    )
    if data.get("rasm_urls") and not data.get("rasm_url"):
        data["rasm_url"] = data["rasm_urls"][0]
    product = Product(store_id=store_id, **data)
    db.add(product)
    db.commit()
    db.refresh(product)
    vector_store.index_product(
        product.id,
        store_id,
        product.nomi,
        product.tavsif,
        product.rang,
        product.korinish,
    )
    return ProductOut.model_validate(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi.")
    check_store_access(admin_id, product.store_id, db)  # rule 7
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("rasm_urls") and len(updates["rasm_urls"]) > 10:
        raise HTTPException(status_code=400, detail="Maksimal 10 ta rasm.")
    if "rasm_nisbati" in updates:
        _check_ratio(updates["rasm_nisbati"])
    for field, value in updates.items():
        setattr(product, field, value)
    if updates.get("rasm_urls"):
        product.rasm_url = updates["rasm_urls"][0]
    # Narx yoki chegirma o'zgarган bo'lса — yakuniy narxni qayta hisoblaymiz.
    if "narxi" in updates or "skidka_foizi" in updates:
        product.yakuniy_narx = _hisobla_yakuniy(
            float(product.narxi), product.skidka_foizi
        )
    db.commit()
    db.refresh(product)
    vector_store.index_product(
        product.id,
        product.store_id,
        product.nomi,
        product.tavsif,
        product.rang,
        product.korinish,
    )
    return ProductOut.model_validate(product)


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi.")
    check_store_access(admin_id, product.store_id, db)  # rule 7
    db.delete(product)
    db.commit()
    vector_store.remove_product(product_id)
    return {"ochirildi": True}


@router.get("/stores/{store_id}/products", response_model=List[ProductOut])
def admin_list_products(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    check_store_access(admin_id, store_id, db)  # rule 7
    rows = db.scalars(
        select(Product).where(Product.store_id == store_id)
    ).all()
    return [ProductOut.model_validate(p) for p in rows]


# ---------------------------------------------------------------------------
# Buyurtma boshqaruvi (phase 8.3)
# ---------------------------------------------------------------------------
@router.get("/stores/{store_id}/orders", response_model=List[OrderOut])
def admin_orders(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    check_store_access(admin_id, store_id, db)  # rule 7
    rows = db.scalars(
        select(Order)
        .where(Order.store_id == store_id)
        .order_by(Order.yaratilgan_vaqt.desc())
    ).all()
    return [OrderOut.model_validate(o) for o in rows]


class StatusChange(BaseModel):
    holat: str


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def change_status(
    order_id: int,
    payload: StatusChange,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)  # rule 7
    order = order_service.change_order_status(
        db, order, payload.holat, admin_id
    )
    return OrderOut.model_validate(order)


class OrderActionOut(BaseModel):
    model_config = {"from_attributes": True}

    order: OrderOut
    ogohlantirishlar: List[str] = []
    user_telegram_id: Optional[int] = None


@router.post("/orders/{order_id}/accept", response_model=OrderActionOut)
def accept_order_endpoint(
    order_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Buyurtmani tezkor qabul qilish (spec2 task_1).

    Faqat shu do'kon admini (rule 7). Ombor miqdori kamaytiriladi (task_2).
    """
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)  # rule 7
    natija = order_service.accept_order(db, order, admin_id)
    return OrderActionOut(
        order=OrderOut.model_validate(natija["order"]),
        ogohlantirishlar=natija["ogohlantirishlar"],
        user_telegram_id=natija["user_telegram_id"],
    )


class CancelRequest(BaseModel):
    sabab: str = Field(min_length=1, max_length=255)


@router.post("/orders/{order_id}/cancel", response_model=OrderActionOut)
def cancel_order_endpoint(
    order_id: int,
    payload: CancelRequest,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)  # rule 7
    natija = order_service.cancel_order(db, order, admin_id, payload.sabab)
    return OrderActionOut(
        order=OrderOut.model_validate(natija["order"]),
        user_telegram_id=natija["user_telegram_id"],
    )


@router.get("/stores/{store_id}/orders/search")
def search_orders(
    store_id: int,
    q: str,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Buyurtma qidirish (spec2 task_4): kod, mijoz telefoni yoki ismi bo'yicha.

    Faqat shu adminning store_id doirasida (rule 7).
    """
    check_store_access(admin_id, store_id, db)  # rule 7
    q = q.strip()
    if not q:
        return []
    from ..models import User as _User

    rows = db.execute(
        select(Order, _User)
        .join(_User, _User.id == Order.user_id)
        .where(
            Order.store_id == store_id,
            (
                (Order.kod == q)
                | _User.tel.ilike(f"%{q}%")
                | _User.ism.ilike(f"%{q}%")
            ),
        )
        .order_by(Order.yaratilgan_vaqt.desc())
        .limit(20)
    ).all()
    return [
        {
            "id": o.id,
            "kod": o.kod,
            "holat": o.holat,
            "jami_narx": float(o.jami_narx),
            "mahsulotlar": [
                f"{m.get('nomi')} x{m.get('soni')}" for m in (o.mahsulotlar or [])
            ],
            "mijoz_ism": u.ism,
            "mijoz_tel": u.tel,
            "yaratilgan_vaqt": o.yaratilgan_vaqt.isoformat()
            if o.yaratilgan_vaqt
            else None,
        }
        for o, u in rows
    ]


class CodeConfirm(BaseModel):
    kod: str = Field(min_length=6, max_length=6)


@router.post("/orders/confirm-code", response_model=OrderOut)
def confirm_code(
    payload: CodeConfirm,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Buyurtma kodini tasdiqlash (phase 3.3).

    Avval kodga tegishli buyurtma topiladi, keyin do'kon ruxsati tekshiriladi.
    """
    order = db.scalar(select(Order).where(Order.kod == payload.kod))
    if order is None:
        raise HTTPException(
            status_code=404, detail="Bunday kodli buyurtma topilmadi."
        )
    check_store_access(admin_id, order.store_id, db)  # rule 7
    order = order_service.confirm_order_code(db, payload.kod, admin_id)
    return OrderOut.model_validate(order)


# ---------------------------------------------------------------------------
# Promo (phase 8.4)
# ---------------------------------------------------------------------------
class PromoCreate(BaseModel):
    kod: str
    chegirma_foizi: int = Field(ge=1, le=100)
    muddat: Optional[datetime] = None


@router.post("/stores/{store_id}/promo")
def create_promo(
    store_id: int,
    payload: PromoCreate,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    check_store_access(admin_id, store_id, db)  # rule 7
    promo = PromoCode(
        store_id=store_id,
        kod=payload.kod,
        chegirma_foizi=payload.chegirma_foizi,
        muddat=payload.muddat,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {"id": promo.id, "kod": promo.kod, "xabar": "Promo yaratildi."}


# ---------------------------------------------------------------------------
# Statistika (phase 8.4) — faqat o'z do'koni bo'yicha (rule 7)
# ---------------------------------------------------------------------------
@router.get("/stores/{store_id}/stats")
def store_stats(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    check_store_access(admin_id, store_id, db)  # rule 7

    umumiy_buyurtma = db.scalar(
        select(func.count(Order.id)).where(Order.store_id == store_id)
    )
    tasdiqlangan = db.scalar(
        select(func.count(Order.id)).where(
            Order.store_id == store_id,
            Order.tasdiqlangan_vaqt.isnot(None),
        )
    )
    tushum = db.scalar(
        select(func.coalesce(func.sum(Order.jami_narx), 0)).where(
            Order.store_id == store_id,
            Order.tasdiqlangan_vaqt.isnot(None),
        )
    )
    mahsulot_soni = db.scalar(
        select(func.count(Product.id)).where(Product.store_id == store_id)
    )
    return {
        "store_id": store_id,
        "umumiy_buyurtma": umumiy_buyurtma or 0,
        "tasdiqlangan_buyurtma": tasdiqlangan or 0,
        "umumiy_tushum": float(tushum or 0),
        "mahsulot_soni": mahsulot_soni or 0,
    }


@router.get("/stores/{store_id}/top-products")
def top_products(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = 10,
):
    """Eng ko'p sotilgan tovarlar (phase 8.4).

    mahsulotlar JSONB ichidagi 'soni' bo'yicha jamlanadi (dastur tomonida,
    baza-agnostik bo'lishi uchun).
    """
    check_store_access(admin_id, store_id, db)  # rule 7
    orders = db.scalars(
        select(Order).where(
            Order.store_id == store_id,
            Order.tasdiqlangan_vaqt.isnot(None),
        )
    ).all()
    tally: dict[str, dict] = {}
    for o in orders:
        for item in o.mahsulotlar or []:
            key = str(item.get("product_id"))
            entry = tally.setdefault(
                key, {"nomi": item.get("nomi"), "soni": 0}
            )
            entry["soni"] += item.get("soni", 0)
    top = sorted(tally.values(), key=lambda x: x["soni"], reverse=True)
    return top[:limit]


# ---------------------------------------------------------------------------
# Mahfiy kod (phase 8.5) — YARATISH/YANGILASH faqat shu yerda (rule 4)
# ---------------------------------------------------------------------------
@router.get("/stores/{store_id}/secret-code")
def get_secret_code(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Joriy mahfiy kodni ko'rsatish (rule 4).

    Faqat shu do'kon admini ko'ra oladi — boshqa admin ko'ra olmaydi (rule 7).
    """
    store = check_store_access(admin_id, store_id, db)
    return {"store_id": store_id, "mahfiy_kirish_kodi": store.mahfiy_kirish_kodi}


@router.post("/stores/{store_id}/secret-code/refresh")
def refresh_secret_code(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Mahfiy kodni yangilash (rule 4, 6).

    Yangilangach, eski kod bilan ochgan mijozlar uchun mahfiy mahsulotlar
    avtomatik qayta yopiladi — chunki katalog har safar ishlatilgan_kod'ni
    joriy kod bilan solishtiradi (rule 6). Alohida "tozalash" YO'Q.
    """
    store = check_store_access(admin_id, store_id, db)
    store.mahfiy_kirish_kodi = _generate_secret_code()
    db.commit()
    return {
        "store_id": store_id,
        "mahfiy_kirish_kodi": store.mahfiy_kirish_kodi,
        "xabar": (
            "Kod yangilandi. Eski kod bilan ochgan barcha mijozlar uchun "
            "mahfiy mahsulotlar avtomatik yopildi."
        ),
    }


# ---------------------------------------------------------------------------
# Super-admin: yangi do'kon/admin (phase 8.6, rule 11)
# ---------------------------------------------------------------------------
class NewStoreRequest(BaseModel):
    nomi: str
    admin_telegram_id: int
    logo: Optional[str] = None


@router.post("/stores")
def create_store(
    payload: NewStoreRequest,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Yangi do'kon + birinchi admin (rule 11).

    Faqat super-admin. Bir martalik mahfiy kod generatsiya qilinadi. admin_ids
    bazada saqlanadi — .env'da EMAS, shuning uchun server qayta ishga
    tushirilmaydi (rule 11 notogri).
    """
    if not is_super_admin(admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat super-admin yangi do'kon qo'sha oladi.",
        )
    store = Store(
        nomi=payload.nomi,
        logo=payload.logo,
        admin_ids=[payload.admin_telegram_id],
        mahfiy_kirish_kodi=_generate_secret_code(),
        holat="faol",
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return {
        "store_id": store.id,
        "nomi": store.nomi,
        "admin_ids": store.admin_ids,
        "mahfiy_kirish_kodi": store.mahfiy_kirish_kodi,
        "xabar": "Yangi do'kon yaratildi.",
    }


@router.delete("/stores/{store_id}")
def delete_store(
    store_id: int,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Do'konni butunlay o'chirish (phase 8.6) — faqat super-admin.

    Mahsulotlar ORM cascade orqali, buyurtma/promo/unlocked yozuvlari esa
    aniq (explicit) o'chiriladi — SQLite'да FK cascade majburiy emasligi uchun.
    """
    if not is_super_admin(admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat super-admin do'kon o'chira oladi.",
        )
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")

    nomi = store.nomi
    product_ids = [p.id for p in store.products]

    from ..models import PromoCode as _Promo
    from ..models import UnlockedStore as _Unlocked

    for model in (Order, _Promo, _Unlocked):
        for row in db.scalars(select(model).where(model.store_id == store_id)):
            db.delete(row)
    db.delete(store)  # mahsulotlar relationship cascade bilan o'chadi
    db.commit()
    for pid in product_ids:
        vector_store.remove_product(pid)
    return {"ochirildi": True, "store_id": store_id, "nomi": nomi}


class AddAdminRequest(BaseModel):
    admin_telegram_id: int


@router.post("/stores/{store_id}/admins")
def add_admin(
    store_id: int,
    payload: AddAdminRequest,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Mavjud do'konga qo'shimcha admin biriktirish (rule 11).

    Faqat super-admin. admin_ids massiviga qo'shiladi (bazada, real vaqtda).
    """
    if not is_super_admin(admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat super-admin admin qo'sha oladi.",
        )
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    ids = list(store.admin_ids or [])
    if payload.admin_telegram_id not in ids:
        ids.append(payload.admin_telegram_id)
        store.admin_ids = ids
        db.commit()
    return {"store_id": store_id, "admin_ids": store.admin_ids}


class SelfStoreRequest(BaseModel):
    nomi: str = Field(min_length=1, max_length=255)


@router.post("/stores/self")
def create_self_store(
    payload: SelfStoreRequest,
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """O'ziga do'kon ochish (spec1 task_3).

    Do'koni bo'lmagan foydalanuvchi o'z do'konини yaratadi va uning admini
    bo'ladi. Allaqachon do'koni bo'lса — 400.
    Eslatma: bu eski rule 11 (faqat super-admin) dan farq qiladi — yangi spec
    talabi bo'yicha o'z-o'ziga xizmat (self-service) rejimi.
    """
    mavjud = get_admin_store_ids(admin_id, db)
    if not is_super_admin(admin_id) and mavjud:
        stores = db.scalars(
            select(Store).where(Store.id.in_(mavjud))
        ).all()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Sizда allaqachon do'kon bor: "
                + ", ".join(s.nomi for s in stores)
            ),
        )
    store = Store(
        nomi=payload.nomi,
        admin_ids=[admin_id],
        mahfiy_kirish_kodi=_generate_secret_code(),
        holat="faol",
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return {
        "store_id": store.id,
        "nomi": store.nomi,
        "mahfiy_kirish_kodi": store.mahfiy_kirish_kodi,
        "xabar": "Do'koningiz yaratildi.",
    }


@router.get("/my-stores")
def my_stores(
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin tegishli bo'lgan do'konlar (Boshqaruv Boti menyusi uchun)."""
    ids = get_admin_store_ids(admin_id, db)
    stores = db.scalars(select(Store).where(Store.id.in_(ids or {-1}))).all()
    return [
        {"id": s.id, "nomi": s.nomi, "holat": s.holat}
        for s in stores
    ]
