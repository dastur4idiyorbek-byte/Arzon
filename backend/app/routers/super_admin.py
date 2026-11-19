"""Unified super-admin router replacing old moliya/menejer roles."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (SotuvchiSorovi, ObunaTarif, Store, User, PlatformaTolovUsuli,
                      YetkazishHudud, PlatformaSozlama, Shikoyat, Order, Product, Media)
from ..security import require_super_admin
from ..services.push import push_user, push_admin_ids

router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


class TarifBody(BaseModel):
    turi: str
    nomi: str
    mahsulot_limiti: int | None = None
    oylik_narx: float = 0
    faol: bool = True


class SotuvchiDecision(BaseModel):
    holat: str


class PaymentMethodBody(BaseModel):
    turi: str
    nomi: str
    qiymat: str | None = None
    egasi: str | None = None
    qr_rasm_url: str | None = None
    faol: bool = True


class ZoneBody(BaseModel):
    store_id: int | None = None
    hudud_nomi: str
    vaqt_oraligi: str | None = None
    boshlanish_soati: str | None = None
    narx: float = 0
    faol: bool = True


class ComplaintAnswer(BaseModel):
    holat: str = "javob_berildi"
    admin_javobi: str


class AssignUserBody(BaseModel):
    user_id: int


@router.get("/seller-requests")
def seller_requests(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return [{"id": r.id, "user_id": r.user_id, "sorov_turi": r.sorov_turi, "tarif_turi": r.tarif_turi,
             "dokon_turi": r.dokon_turi, "fish": r.fish, "tel": r.tel, "dokon_nomi": r.dokon_nomi,
             "chek_rasm_url": r.chek_rasm_url, "ai_ochigan_summa": float(r.ai_ochigan_summa or 0),
             "ai_xulosasi": r.ai_xulosasi, "holat": r.holat,
             "pasport_oldi_url": r.pasport_oldi_url, "pasport_orqa_url": r.pasport_orqa_url,
             "selfi_pasport_url": r.selfi_pasport_url} for r in db.scalars(select(SotuvchiSorovi).order_by(SotuvchiSorovi.yaratilgan_vaqt.desc())).all()]


@router.post("/seller-requests/{request_id}/decision")
def seller_decision(request_id: int, payload: SotuvchiDecision, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    request = db.get(SotuvchiSorovi, request_id)
    if request is None:
        raise HTTPException(404, "Ariza topilmadi.")
    if payload.holat not in ("tasdiqlandi", "rad_etildi"):
        raise HTTPException(400, "holat tasdiqlandi yoki rad_etildi bo'lishi kerak.")
    request.holat = payload.holat
    if payload.holat == "tasdiqlandi":
        store = Store(nomi=request.dokon_nomi, turi=request.dokon_turi, tarif_turi=request.tarif_turi,
                      admin_ids=[request.user_id], manzil=request.manzil, tel=request.tel,
                      ish_vaqti=request.ish_vaqti, lokatsiya_lat=request.lokatsiya_lat,
                      lokatsiya_lng=request.lokatsiya_lng, logo=request.dokon_rasm_url,
                      pasport_oldi_url=request.pasport_oldi_url, pasport_orqa_url=request.pasport_orqa_url,
                      selfi_pasport_url=request.selfi_pasport_url, holat="faol")
        tarif = db.get(ObunaTarif, request.tarif_id) if request.tarif_id else None
        store.mahsulot_limiti = tarif.mahsulot_limiti if tarif else None
        db.add(store); db.flush()
        user = db.get(User, request.user_id)
        if user:
            push_user(db, user, "Do'kon ochildi", f"{store.nomi} do'koningiz tasdiqlandi.", {"type": "store", "store_id": store.id})
    db.commit()
    return {"id": request.id, "holat": request.holat}


@router.get("/tariffs")
@router.post("/tariffs")
def tariffs(body: TarifBody | None = None, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    if body is not None:
        tarif = ObunaTarif(turi=body.turi, nomi=body.nomi, mahsulot_limiti=body.mahsulot_limiti, oylik_narx=body.oylik_narx, faol=body.faol)
        db.add(tarif); db.commit(); db.refresh(tarif)
        return {"id": tarif.id, "turi": tarif.turi}
    return [{"id": t.id, "turi": t.turi, "nomi": t.nomi, "mahsulot_limiti": t.mahsulot_limiti,
             "oylik_narx": float(t.oylik_narx), "faol": t.faol} for t in db.scalars(select(ObunaTarif)).all()]


@router.patch("/tariffs/{tarif_id}")
def update_tariff(tarif_id: int, body: TarifBody, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    tarif = db.get(ObunaTarif, tarif_id)
    if tarif is None:
        raise HTTPException(404, "Tarif topilmadi.")
    for field, value in body.model_dump(exclude_unset=True).items(): setattr(tarif, field, value)
    db.commit(); db.refresh(tarif)
    return {"id": tarif.id, "ok": True}


@router.delete("/tariffs/{tarif_id}")
def delete_tariff(tarif_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    tarif = db.get(ObunaTarif, tarif_id)
    if tarif is None:
        raise HTTPException(404, "Tarif topilmadi.")
    db.delete(tarif); db.commit()
    return {"ochirildi": True}


@router.get("/payment-methods")
@router.post("/payment-methods")
def payment_methods(body: PaymentMethodBody | None = None, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    if body is not None:
        item = PlatformaTolovUsuli(**body.model_dump())
        db.add(item); db.commit(); db.refresh(item)
        return {"id": item.id}
    return [{"id": x.id, "turi": x.turi, "nomi": x.nomi, "qiymat": x.qiymat,
             "egasi": x.egasi, "qr_rasm_url": x.qr_rasm_url, "faol": x.faol}
            for x in db.scalars(select(PlatformaTolovUsuli)).all()]


@router.get("/zones")
@router.post("/zones")
def zones(body: ZoneBody | None = None, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    if body is not None:
        zone = YetkazishHudud(**body.model_dump())
        db.add(zone); db.commit(); db.refresh(zone)
        return {"id": zone.id}
    return [{"id": z.id, "store_id": z.store_id, "hudud_nomi": z.hudud_nomi,
             "vaqt_oraligi": z.vaqt_oraligi, "boshlanish_soati": z.boshlanish_soati,
             "narx": float(z.narx), "faol": z.faol} for z in db.scalars(select(YetkazishHudud)).all()]


@router.get("/complaints")
def complaints(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return [{"id": c.id, "order_id": c.order_id, "user_id": c.user_id, "store_id": c.store_id,
             "matn": c.matn, "rasm_url": c.rasm_url, "holat": c.holat, "admin_javobi": c.admin_javobi}
            for c in db.scalars(select(Shikoyat).order_by(Shikoyat.id.desc())).all()]


@router.post("/complaints/{complaint_id}/answer")
def answer_complaint(complaint_id: int, body: ComplaintAnswer, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    complaint = db.get(Shikoyat, complaint_id)
    if complaint is None:
        raise HTTPException(404, "Shikoyat topilmadi.")
    complaint.holat = body.holat; complaint.admin_javobi = body.admin_javobi
    db.commit()
    u = db.get(User, complaint.user_id)
    if u:
        push_user(db, u, "Shikoyatga javob", body.admin_javobi, {"type": "complaint", "complaint_id": complaint.id})
    return {"id": complaint.id, "ok": True}


@router.post("/couriers/{user_id}")
def make_courier(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Foydalanuvchi topilmadi.")
    user.is_kuryer = True
    db.commit()
    push_user(db, user, "Kuryer huquqi", "Sizga kuryer huquqi berildi.", {"type": "courier"})
    return {"id": user.id, "is_kuryer": True}


@router.post("/stores/{store_id}/admins")
def assign_admin(store_id: int, body: AssignUserBody, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(404, "Do'kon topilmadi.")
    ids = list(store.admin_ids or [])
    if body.user_id not in ids:
        ids.append(body.user_id)
        store.admin_ids = ids
    db.commit()
    push_user(db, db.get(User, body.user_id), "Do'kon admini", f"Siz {store.nomi} do'koniga admin qilib tayinlandingiz.", {"type": "admin", "store_id": store.id})
    return {"store_id": store.id, "admin_ids": ids}


@router.post("/broadcast")
def broadcast(title: str, body: str, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    sent = 0
    for user in db.scalars(select(User).where(User.expo_push_token.isnot(None))).all():
        sent += int(push_user(db, user, title, body, {"type": "broadcast"}))
    return {"yuborildi": sent}


@router.post("/platform-setting")
def platform_setting(faqat_platforma_kuryeri: bool, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    setting = db.scalar(select(PlatformaSozlama).limit(1))
    if setting is None:
        setting = PlatformaSozlama(faqat_platforma_kuryeri=faqat_platforma_kuryeri); db.add(setting)
    else:
        setting.faqat_platforma_kuryeri = faqat_platforma_kuryeri
    db.commit()
    return {"faqat_platforma_kuryeri": faqat_platforma_kuryeri}


@router.get("/reports")
def reports(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return {"users": db.scalar(select(func.count(User.id))) or 0,
            "stores": db.scalar(select(func.count(Store.id))) or 0,
            "orders": db.scalar(select(func.count(Order.id))) or 0,
            "products": db.scalar(select(func.count(Product.id))) or 0,
            "complaints": db.scalar(select(func.count(Shikoyat.id))) or 0,
            "seller_requests": db.scalar(select(func.count(SotuvchiSorovi.id))) or 0}
