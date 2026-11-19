"""ARZON 2.0 admin router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, PromoCode, Store, PickupPoint, YetkazishHudud, Order, Shikoyat, Media, _now
from ..security import require_admin, check_store_access
from ..services.push import push_store_admins

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ProductBody(BaseModel):
    nomi: str
    narxi: float
    kategoriya: str | None = None
    holat_turi: str = "yangi"
    holat_izohi: str | None = None
    porsiya: str | None = None
    tayyorlanish_daq: int | None = None
    stop_list: bool = False
    rasm_url: str | None = None
    rasm_urls: list[str] | None = None
    tavsif: str | None = None
    miqdor: int | None = None
    skidka_foizi: int = 0


class StoreProfile(BaseModel):
    nomi: str | None = None
    boshqaruvchi_ismi: str | None = None
    logo: str | None = None
    manzil: str | None = None
    tel: str | None = None
    ish_vaqti: str | None = None
    lokatsiya_lat: float | None = None
    lokatsiya_lng: float | None = None
    ochiq: bool | None = None
    tayyorlanish_vaqti: int | None = None
    yetkazish_rejimi: str | None = None
    kuryer_narxi: float | None = None
    tolov_usullari: list[dict] | None = None


class PickupBody(BaseModel):
    nomi: str
    manzil: str
    ish_vaqti: str | None = None
    rasm_url: str | None = None
    lokatsiya_lat: float | None = None
    lokatsiya_lng: float | None = None
    google_maps_link: str | None = None


class PromoBody(BaseModel):
    kod: str
    chegirma_foizi: int
    muddat: str | None = None


@router.patch("/stores/{store_id}")
def update_store(store_id: int, payload: StoreProfile, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    store = check_store_access(admin_id, store_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    if store.tarif_turi == "lite" and payload.yetkazish_rejimi == "ozi":
        store.yetkazish_rejimi = "ozi"
    db.commit(); db.refresh(store)
    return {"id": store.id, "ok": True}


@router.post("/stores/{store_id}/products")
def add_product(store_id: int, payload: ProductBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    store = check_store_access(admin_id, store_id, db)
    if store.holat == "vaqtincha_toxtatilgan":
        raise HTTPException(403, "Do'kon vaqtincha to'xtatilgan.")
    if store.mahsulot_limiti is not None:
        count = db.scalar(select(__import__('sqlalchemy').func.count(Product.id)).where(Product.store_id == store_id)) or 0
        if count >= store.mahsulot_limiti:
            raise HTTPException(400, "Mahsulot limiti to'lgan.")
    p = Product(store_id=store_id, **payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    push_store_admins(db, store, "Mahsulot qo'shildi", p.nomi, {"type": "product", "product_id": p.id})
    return {"id": p.id, "nomi": p.nomi}


@router.patch("/products/{product_id}")
def update_product(product_id: int, payload: ProductBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(404, "Mahsulot topilmadi.")
    check_store_access(admin_id, p.store_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit(); db.refresh(p)
    return {"id": p.id, "ok": True}


@router.delete("/products/{product_id}")
def delete_product(product_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(404, "Mahsulot topilmadi.")
    check_store_access(admin_id, p.store_id, db)
    db.delete(p); db.commit()
    return {"ochirildi": True}


@router.post("/stores/{store_id}/pickup-points")
def add_pickup(store_id: int, payload: PickupBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    store = check_store_access(admin_id, store_id, db)
    if store.tarif_turi == "lite" and (not payload.rasm_url or payload.lokatsiya_lat is None or payload.lokatsiya_lng is None):
        raise HTTPException(400, "Lite punkt uchun rasm va GPS majburiy.")
    pp = PickupPoint(store_id=store_id, **payload.model_dump())
    db.add(pp); db.commit(); db.refresh(pp)
    return {"id": pp.id, "nomi": pp.nomi}


@router.post("/stores/{store_id}/promo")
def add_promo(store_id: int, payload: PromoBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    check_store_access(admin_id, store_id, db)
    muddat = None
    if payload.muddat:
        from datetime import datetime
        muddat = datetime.fromisoformat(payload.muddat)
    promo = PromoCode(store_id=store_id, kod=payload.kod.strip(), chegirma_foizi=payload.chegirma_foizi, muddat=muddat)
    db.add(promo); db.commit(); db.refresh(promo)
    return {"id": promo.id, "kod": promo.kod}


@router.get("/stores/{store_id}/promo")
def list_promo(store_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    check_store_access(admin_id, store_id, db)
    return [{"id": p.id, "kod": p.kod, "chegirma_foizi": p.chegirma_foizi, "muddat": p.muddat.isoformat() if p.muddat else None}
            for p in db.scalars(select(PromoCode).where(PromoCode.store_id == store_id)).all()]


@router.delete("/promo/{promo_id}")
def delete_promo(promo_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    promo = db.get(PromoCode, promo_id)
    if promo is None:
        raise HTTPException(404, "Promo topilmadi.")
    check_store_access(admin_id, promo.store_id, db)
    db.delete(promo); db.commit()
    return {"ochirildi": True}


@router.post("/orders/{order_id}/accept")
def accept_order(order_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)
    if order.tolov_holati != "tasdiqlandi":
        raise Exception("To'lov avval tasdiqlanishi kerak")
    order.holat = "tayyorlanmoqda"
    for item in order.mahsulotlar or []:
        p = db.get(Product, item.get("product_id"))
        if p and p.miqdor is not None:
            p.miqdor = max(0, p.miqdor - int(item.get("soni", 0)))
    db.commit()
    user = db.get(__import__('backend.app.models', fromlist=['User']).User, order.user_id) if False else None
    return {"id": order.id, "holat": order.holat}


@router.post("/orders/{order_id}/payment/reject")
def reject_receipt(order_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)
    order.tolov_holati = "rad_etildi"; order.holat = "bekor_qilindi"
    db.commit()
    return {"id": order.id, "tolov_holati": order.tolov_holati}
