"""ARZON 2.0 admin router (native users and Expo push)."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, PromoCode, Store, PickupPoint, Order, User
from ..security import require_admin, check_store_access
from ..services.push import push_store_admins, push_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ProductBody(BaseModel):
    nomi: str
    narxi: float = Field(ge=0)
    kategoriya: str | None = None
    holat_turi: str = "yangi"
    holat_izohi: str | None = None
    porsiya: str | None = None
    tayyorlanish_daq: int | None = None
    stop_list: bool = False
    rasm_url: str | None = None
    rasm_urls: list[str] | None = None
    tavsif: str | None = None
    miqdor: int | None = Field(default=None, ge=0)
    skidka_foizi: int = Field(default=0, ge=0, le=100)


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
    kuryer_narxi: float | None = Field(default=None, ge=0)
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
    chegirma_foizi: int = Field(ge=0, le=100)
    muddat: str | None = None


@router.patch("/stores/{store_id}")
def update_store(store_id: int, payload: StoreProfile, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    store = check_store_access(admin_id, store_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return {"id": store.id, "ok": True}


@router.post("/stores/{store_id}/products")
def add_product(store_id: int, payload: ProductBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    store = check_store_access(admin_id, store_id, db)
    if store.holat != "faol":
        raise HTTPException(403, "Do'kon sotish uchun faol emas.")
    if store.mahsulot_limiti is not None:
        count = db.scalar(select(func.count(Product.id)).where(Product.store_id == store_id)) or 0
        if count >= store.mahsulot_limiti:
            raise HTTPException(400, "Mahsulot limiti to'lgan.")
    product = Product(store_id=store_id, **payload.model_dump())
    if product.skidka_foizi:
        product.yakuniy_narx = round(product.narxi * (100 - product.skidka_foizi) / 100, 2)
    db.add(product)
    db.commit()
    db.refresh(product)
    push_store_admins(db, store, "Mahsulot qo'shildi", product.nomi, {"type": "product", "product_id": product.id})
    return {"id": product.id, "nomi": product.nomi}


@router.patch("/products/{product_id}")
def update_product(product_id: int, payload: ProductBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Mahsulot topilmadi.")
    check_store_access(admin_id, product.store_id, db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)
    if product.skidka_foizi:
        product.yakuniy_narx = round(product.narxi * (100 - product.skidka_foizi) / 100, 2)
    else:
        product.yakuniy_narx = None
    db.commit()
    db.refresh(product)
    return {"id": product.id, "ok": True}


@router.delete("/products/{product_id}")
def delete_product(product_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Mahsulot topilmadi.")
    check_store_access(admin_id, product.store_id, db)
    db.delete(product)
    db.commit()
    return {"ochirildi": True}


@router.post("/stores/{store_id}/pickup-points")
def add_pickup(store_id: int, payload: PickupBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    store = check_store_access(admin_id, store_id, db)
    if store.tarif_turi == "lite" and (not payload.rasm_url or payload.lokatsiya_lat is None or payload.lokatsiya_lng is None):
        raise HTTPException(400, "Lite punkt uchun rasm va GPS majburiy.")
    pp = PickupPoint(store_id=store_id, **payload.model_dump())
    db.add(pp)
    db.commit()
    db.refresh(pp)
    return {"id": pp.id, "nomi": pp.nomi}


@router.post("/stores/{store_id}/promo")
def add_promo(store_id: int, payload: PromoBody, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    check_store_access(admin_id, store_id, db)
    muddat = datetime.fromisoformat(payload.muddat) if payload.muddat else None
    promo = PromoCode(store_id=store_id, kod=payload.kod.strip(), chegirma_foizi=payload.chegirma_foizi, muddat=muddat)
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {"id": promo.id, "kod": promo.kod}


@router.get("/stores/{store_id}/promo")
def list_promo(store_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    check_store_access(admin_id, store_id, db)
    promos = db.scalars(select(PromoCode).where(PromoCode.store_id == store_id)).all()
    return [{"id": p.id, "kod": p.kod, "chegirma_foizi": p.chegirma_foizi,
             "muddat": p.muddat.isoformat() if p.muddat else None} for p in promos]


@router.delete("/promo/{promo_id}")
def delete_promo(promo_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    promo = db.get(PromoCode, promo_id)
    if promo is None:
        raise HTTPException(404, "Promo topilmadi.")
    check_store_access(admin_id, promo.store_id, db)
    db.delete(promo)
    db.commit()
    return {"ochirildi": True}


@router.post("/orders/{order_id}/accept")
def accept_order(order_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)
    if order.tolov_holati != "tasdiqlandi":
        raise HTTPException(400, "To'lov avval tasdiqlanishi kerak.")
    if order.holat != "yangi":
        raise HTTPException(400, "Buyurtma allaqachon qabul qilingan yoki yopilgan.")

    for item in order.mahsulotlar or []:
        product = db.get(Product, item.get("product_id"))
        if product and product.miqdor is not None:
            quantity = int(item.get("soni", 0))
            if product.miqdor < quantity:
                raise HTTPException(400, f"'{product.nomi}' omborida yetarli mahsulot yo'q.")

    order.holat = "tayyorlanmoqda"
    order.tasdiqlangan_vaqt = datetime.now(timezone.utc)
    for item in order.mahsulotlar or []:
        product = db.get(Product, item.get("product_id"))
        if product and product.miqdor is not None:
            product.miqdor = max(0, product.miqdor - int(item.get("soni", 0)))
    db.commit()
    push_user(db, db.get(User, order.user_id), "Buyurtma qabul qilindi", "Buyurtmangiz tayyorlanmoqda.", {"type": "order", "order_id": order.id})
    return {"id": order.id, "holat": order.holat}


@router.post("/orders/{order_id}/payment/accept")
def accept_payment(order_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)
    if order.holat != "tolov_kutilmoqda":
        raise HTTPException(400, "Buyurtma to'lov kutish holatida emas.")
    if not order.chek_rasm_url:
        raise HTTPException(400, "To'lov cheki hali yuklanmagan.")
    expected = float(order.oldindan_summa or order.jami_narx)
    if order.ai_ochigan_summa is not None and abs(float(order.ai_ochigan_summa) - expected) <= 1:
        order.ai_xulosasi = "mos_keladi"
    order.tolov_holati = "tasdiqlandi"
    order.holat = "yangi"
    db.commit()
    push_user(db, db.get(User, order.user_id), "To'lov tasdiqlandi", "Buyurtmangiz do'konga yuborildi.", {"type": "order", "order_id": order.id})
    return {"id": order.id, "tolov_holati": order.tolov_holati, "ai_xulosasi": order.ai_xulosasi}


@router.post("/orders/{order_id}/payment/reject")
def reject_receipt(order_id: int, admin_id: int = Depends(require_admin), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    check_store_access(admin_id, order.store_id, db)
    if order.tolov_holati != "kutilmoqda":
        raise HTTPException(400, "Bu to'lov allaqachon yakunlangan.")
    order.tolov_holati = "rad_etildi"
    order.holat = "bekor_qilindi"
    db.commit()
    push_user(db, db.get(User, order.user_id), "To'lov rad etildi", "Buyurtma cheki tasdiqlanmadi.", {"type": "order", "order_id": order.id})
    return {"id": order.id, "tolov_holati": order.tolov_holati}
