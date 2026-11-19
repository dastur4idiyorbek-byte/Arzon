"""Guest-friendly product and store catalog endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, Store, YetkazishHudud, PromoCode, _as_aware, _now

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    products = db.scalars(select(Product)).all()
    result = []
    for product in products:
        store = db.get(Store, product.store_id)
        if store is None or store.holat not in ("faol", "vaqtincha_toxtatilgan"):
            continue
        result.append({
            "id": product.id, "store_id": product.store_id, "store_nomi": store.nomi,
            "nomi": product.nomi, "narxi": float(product.narxi),
            "sotuv_narxi": float(product.yakuniy_narx or product.narxi),
            "kategoriya": product.kategoriya, "holat_turi": product.holat_turi,
            "holat_izohi": product.holat_izohi, "porsiya": product.porsiya,
            "tayyorlanish_daq": product.tayyorlanish_daq, "stop_list": product.stop_list,
            "rasm_url": product.rasm_url, "rasm_urls": product.rasm_urls or [],
            "tavsif": product.tavsif, "miqdor": product.miqdor,
            "sotish_toxtatilgan": store.holat == "vaqtincha_toxtatilgan",
        })
    return result


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)):
    stores = db.scalars(select(Store).where(
        Store.holat.in_(["faol", "vaqtincha_toxtatilgan"]),
        Store.tarif_turi.in_(["pro", "kafe"]),
    )).all()
    return [{"id": s.id, "nomi": s.nomi, "turi": s.turi, "tarif_turi": s.tarif_turi,
             "logo": s.logo, "ochiq": s.ochiq, "manzil": s.manzil,
             "lokatsiya_lat": float(s.lokatsiya_lat) if s.lokatsiya_lat is not None else None,
             "lokatsiya_lng": float(s.lokatsiya_lng) if s.lokatsiya_lng is not None else None,
             "sotish_toxtatilgan": s.holat == "vaqtincha_toxtatilgan"} for s in stores]


@router.get("/stores/{store_id}")
def store_detail(store_id: int, db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(404, "Do'kon topilmadi.")
    return {"id": store.id, "nomi": store.nomi, "turi": store.turi, "tarif_turi": store.tarif_turi,
            "logo": store.logo, "boshqaruvchi_ismi": store.boshqaruvchi_ismi, "manzil": store.manzil,
            "tel": store.tel, "ish_vaqti": store.ish_vaqti, "ochiq": store.ochiq,
            "tayyorlanish_vaqti": store.tayyorlanish_vaqti, "yetkazish_rejimi": store.yetkazish_rejimi,
            "kuryer_narxi": float(store.kuryer_narxi or 0),
            "sotish_toxtatilgan": store.holat == "vaqtincha_toxtatilgan"}


@router.get("/hududlar")
def delivery_zones(store_id: int | None = None, db: Session = Depends(get_db)):
    query = select(YetkazishHudud).where(YetkazishHudud.faol.is_(True))
    if store_id is not None:
        query = query.where((YetkazishHudud.store_id == store_id) | YetkazishHudud.store_id.is_(None))
    else:
        query = query.where(YetkazishHudud.store_id.is_(None))
    return [{"id": z.id, "store_id": z.store_id, "hudud_nomi": z.hudud_nomi,
             "vaqt_oraligi": z.vaqt_oraligi, "boshlanish_soati": z.boshlanish_soati,
             "narx": float(z.narx)} for z in db.scalars(query).all()]


class PromoCheck(BaseModel):
    kod: str = Field(min_length=1, max_length=32)
    store_ids: list[int] = Field(default_factory=list)


@router.post("/promo/check")
def promo_check(payload: PromoCheck, db: Session = Depends(get_db)):
    query = select(PromoCode).where(PromoCode.kod == payload.kod.strip())
    if payload.store_ids:
        query = query.where(PromoCode.store_id.in_(payload.store_ids))
    promo = db.scalar(query)
    if promo is None:
        return {"ok": False, "sabab": "Promo kod topilmadi."}
    if promo.muddat and _as_aware(promo.muddat) < _now():
        return {"ok": False, "sabab": "Promo kod muddati tugagan."}
    return {"ok": True, "kod": promo.kod, "chegirma_foizi": promo.chegirma_foizi,
            "store_id": promo.store_id}
