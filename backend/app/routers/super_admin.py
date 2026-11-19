"""Unified super-admin router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (SotuvchiSorovi, ObunaTarif, Store, User, PlatformaTolovUsuli,
                      YetkazishHudud, PlatformaSozlama, Shikoyat, Order, Product)
from ..security import get_current_user, require_super_admin
from ..services.push import push_user

router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


class TarifBody(BaseModel):
    turi: str
    nomi: str
    mahsulot_limiti: int | None = None
    oylik_narx: float = 0
    faol: bool = True


class SellerRequestBody(BaseModel):
    sorov_turi: str = "yangi"
    tarif_id: int | None = None
    tarif_turi: str = "lite"
    dokon_turi: str = "magazin"
    fish: str
    tel: str
    dokon_nomi: str
    manzil: str | None = None
    ish_vaqti: str | None = None
    dokon_rasm_url: str | None = None
    lokatsiya_lat: float | None = None
    lokatsiya_lng: float | None = None
    pasport_oldi_url: str | None = None
    pasport_orqa_url: str | None = None
    selfi_pasport_url: str | None = None
    chek_rasm_url: str | None = None


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


@router.post("/seller-requests")
def create_seller_request(payload: SellerRequestBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.dokon_turi not in ("magazin", "kafe"):
        raise HTTPException(400, "dokon_turi magazin yoki kafe bo'lishi kerak.")
    if payload.sorov_turi not in ("yangi", "yangilash", "pro_otish"):
        raise HTTPException(400, "Noto'g'ri sorov_turi.")
    if not payload.pasport_oldi_url or not payload.pasport_orqa_url or not payload.selfi_pasport_url:
        raise HTTPException(400, "Pasport oldi, pasport orqa va selfi-pasport rasmlari majburiy.")
    request = SotuvchiSorovi(user_id=user.id, **payload.model_dump())
    db.add(request); db.commit(); db.refresh(request)
    return {"id": request.id, "holat": request.holat}


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
        existing = db.scalar(select(Store).where(Store.admin_ids.contains([request.user_id])))
        if existing:
            existing.nomi = request.dokon_nomi
            existing.turi = request.dokon_turi
            existing.tarif_turi = request.tarif_turi
            existing.manzil = request.manzil
            existing.tel = request.tel
            existing.ish_vaqti = request.ish_vaqti
            existing.logo = request.dokon_rasm_url
            existing.lokatsiya_lat = request.lokatsiya_lat
            existing.lokatsiya_lng = request.lokatsiya_lng
            existing.pasport_oldi_url = request.pasport_oldi_url
            existing.pasport_orqa_url = request.pasport_orqa_url
            existing.selfi_pasport_url = request.selfi_pasport_url
            existing.holat = "faol"
            store = existing
        else:
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
            push_user(db, user, "Do'kon tasdiqlandi", f"{store.nomi} do'koningiz tasdiqlandi.", {"type": "store", "store_id": store.id})
    db.commit()
    return {"id": request.id, "holat": request.holat}


@router.post("/tariffs")
def create_tariff(body: TarifBody, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    tarif = ObunaTarif(turi=body.turi, nomi=body.nomi, mahsulot_limiti=body.mahsulot_limiti, oylik_narx=body.oylik_narx, faol=body.faol)
    db.add(tarif); db.commit(); db.refresh(tarif)
    return {"id": tarif.id}


@router.get("/tariffs")
def list_tariffs(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return [{"id": t.id, "turi": t.turi, "nomi": t.nomi, "mahsulot_limiti": t.mahsulot_limiti,
             "oylik_narx": float(t.oylik_narx), "faol": t.faol} for t in db.scalars(select(ObunaTarif)).all()]


@router.post("/payment-methods")
def create_payment_method(body: PaymentMethodBody, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    item = PlatformaTolovUsuli(**body.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id}


@router.post("/zones")
def create_zone(body: ZoneBody, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    zone = YetkazishHudud(**body.model_dump())
    db.add(zone); db.commit(); db.refresh(zone)
    return {"id": zone.id}


@router.post("/couriers/{user_id}")
def make_courier(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Foydalanuvchi topilmadi.")
    user.is_kuryer = True
    db.commit()
    push_user(db, user, "Kuryer huquqi", "Sizga kuryer huquqi berildi.", {"type": "courier"})
    return {"id": user.id, "is_kuryer": True}


@router.post("/platform-setting")
def platform_setting(faqat_platforma_kuryeri: bool, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    setting = db.scalar(select(PlatformaSozlama).limit(1))
    if setting is None:
        setting = PlatformaSozlama(faqat_platforma_kuryeri=faqat_platforma_kuryeri)
        db.add(setting)
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
            "seller_requests": db.scalar(select(func.count(SotuvchiSorovi.id))) or 0}
