"""ARZON 2.0 checkout and order APIs."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ai
from ..database import get_db
from ..models import Order, Product, Store, PickupPoint, PromoCode, User, Media, _now, _as_aware
from ..security import get_current_user
from ..services.push import push_user

router = APIRouter(prefix="/api", tags=["orders"])


class CartItem(BaseModel):
    product_id: int
    soni: int = Field(ge=1)


class CheckoutRequest(BaseModel):
    items: list[CartItem]
    promo_kod: str | None = None
    yetkazish_turi: str = "kuryer"
    manzil: str | None = None
    lokatsiya_lat: float | None = None
    lokatsiya_lng: float | None = None
    pickup_point_id: int | None = None


def _money(v):
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


@router.post("/checkout")
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(400, "Savat bo'sh.")
    if payload.yetkazish_turi not in ("kuryer", "pickup"):
        raise HTTPException(400, "yetkazish_turi kuryer yoki pickup bo'lishi kerak.")

    grouped: dict[int, list[tuple[Product, CartItem]]] = {}
    for item in payload.items:
        product = db.get(Product, item.product_id)
        if product is None:
            raise HTTPException(404, f"Mahsulot topilmadi: {item.product_id}")
        if product.stop_list:
            raise HTTPException(400, f"'{product.nomi}' stop-listda.")
        if product.miqdor is not None and (product.miqdor <= 0 or item.soni > product.miqdor):
            raise HTTPException(400, f"'{product.nomi}' yetarli miqdorda emas.")
        grouped.setdefault(product.store_id, []).append((product, item))

    created = []
    for store_id, lines in grouped.items():
        store = db.get(Store, store_id)
        if store is None:
            raise HTTPException(404, "Do'kon topilmadi.")
        if store.holat == "vaqtincha_toxtatilgan":
            raise HTTPException(403, "Do'kon sotish to'xtatilgan.")

        total = _money(0)
        product_json = []
        for product, item in lines:
            price = _money(product.yakuniy_narx or product.narxi)
            total += price * item.soni
            product_json.append({"product_id": product.id, "nomi": product.nomi,
                                 "narxi": float(price), "soni": item.soni})

        if payload.promo_kod:
            promo = db.scalar(select(PromoCode).where(PromoCode.store_id == store_id, PromoCode.kod == payload.promo_kod.strip()))
            if promo and (promo.muddat is None or _as_aware(promo.muddat) >= _now()):
                total = (total * _money(100 - promo.chegirma_foizi) / _money(100)).quantize(Decimal("0.01"))
                promo.ishlatilish_soni += 1

        if store.turi == "kafe":
            if not store.ochiq:
                raise HTTPException(400, "Kafe hozir yopiq.")
            oldindan = total
            qoldiq = Decimal("0")
            if payload.yetkazish_turi != "pickup":
                payload.yetkazish_turi = "pickup"
            pickup_point_id = None
        elif payload.yetkazish_turi == "pickup":
            if store.tarif_turi == "lite":
                pp = db.get(PickupPoint, payload.pickup_point_id) if payload.pickup_point_id else None
                if pp is None or pp.store_id != store_id or not pp.rasm_url or pp.lokatsiya_lat is None or pp.lokatsiya_lng is None:
                    raise HTTPException(400, "Lite do'konida rasm va GPS li punkt majburiy.")
            elif payload.pickup_point_id:
                pp = db.get(PickupPoint, payload.pickup_point_id)
                if pp is None or pp.store_id != store_id:
                    raise HTTPException(400, "Olib ketish punkti noto'g'ri.")
            else:
                pp = None
            oldindan = total
            qoldiq = Decimal("0")
            pickup_point_id = payload.pickup_point_id
        else:
            delivery = _money(store.kuryer_narxi)
            oldindan = (total * Decimal("0.5") + delivery).quantize(Decimal("0.01"))
            qoldiq = (total - total * Decimal("0.5")).quantize(Decimal("0.01"))
            pickup_point_id = None

        order = Order(store_id=store_id, user_id=user.id, mahsulotlar=product_json,
                      jami_narx=float(total), holat="tolov_kutilmoqda", kod="",
                      yetkazish_turi=payload.yetkazish_turi, manzil=payload.manzil,
                      pickup_point_id=pickup_point_id, lokatsiya_lat=payload.lokatsiya_lat,
                      lokatsiya_lng=payload.lokatsiya_lng,
                      oldindan_summa=float(oldindan), qoldiq_summa=float(qoldiq),
                      yetkazish_narxi=float(store.kuryer_narxi if payload.yetkazish_turi == "kuryer" else 0),
                      tolov_holati="kutilmoqda")
        db.add(order); db.flush()
        # Code is issued only after payment acceptance.
        import secrets
        order.kod = secrets.token_hex(3).upper()[:6]
        created.append(order)

    db.commit()
    for o in created:
        db.refresh(o)
    return {"buyurtmalar": [{"id": o.id, "store_id": o.store_id, "jami_narx": float(o.jami_narx),
                             "oldindan_summa": float(o.oldindan_summa), "qoldiq_summa": float(o.qoldiq_summa),
                             "holat": o.holat, "kod": ""} for o in created],
            "xabar": "To'lov cheki yuklanishi kerak. Buyurtma kodi faqat to'lov tasdiqlangach beriladi."}


@router.get("/orders")
def my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": o.id, "store_id": o.store_id, "jami_narx": float(o.jami_narx), "holat": o.holat,
             "kod": o.kod if o.tolov_holati == "tasdiqlandi" else "", "mahsulotlar": o.mahsulotlar,
             "yetkazish_turi": o.yetkazish_turi, "oldindan_summa": float(o.oldindan_summa),
             "qoldiq_summa": float(o.qoldiq_summa), "qaytarilgan_summa": float(o.qaytarilgan_summa)}
            for o in db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.yaratilgan_vaqt.desc())).all()]


@router.post("/orders/{order_id}/chek")
async def order_receipt(order_id: int, chek: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(404, "Buyurtma topilmadi.")
    raw = await chek.read()
    if not raw:
        raise HTTPException(400, "Chek bo'sh.")
    media = Media(mime=chek.content_type or "image/jpeg", data=raw, yuklagan_user_id=user.id, maxfiy=False)
    db.add(media); db.flush()
    result = ai.analyze_receipt(raw, chek.content_type or "image/jpeg", float(order.oldindan_summa))
    order.chek_rasm_url = f"/media/db/{media.id}"
    order.ai_ochigan_summa = result.get("summa")
    order.ai_xulosasi = result.get("xulosa")
    db.commit()
    return {"ok": True, "tolov_holati": order.tolov_holati, "ai_xulosasi": order.ai_xulosasi}


@router.post("/orders/{order_id}/mijoz-rad-etdi")
def customer_rejected(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(404, "Buyurtma topilmadi.")
    if order.yetkazish_turi != "kuryer":
        raise HTTPException(400, "Bu holat faqat kuryerli buyurtma uchun.")
    delivery = _money(order.yetkazish_narxi)
    refund = (_money(order.oldindan_summa) - delivery).quantize(Decimal("0.01"))
    order.qaytarilgan_summa = float(max(refund, Decimal("0")))
    order.holat = "mijoz_rad_etdi"
    db.commit()
    return {"qaytarilgan_summa": float(order.qaytarilgan_summa), "holat": order.holat}
