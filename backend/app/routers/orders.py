"""ARZON 2.0 checkout and order APIs."""
from decimal import Decimal
import secrets
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ai
from ..database import get_db
from ..models import Order, Product, Store, PickupPoint, PromoCode, User, Media, _now, _as_aware
from ..security import get_current_user

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


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _new_order_code(db: Session) -> str:
    # The code is not returned to the buyer until payment approval.
    for _ in range(25):
        code = secrets.token_hex(3).upper()
        if db.scalar(select(Order.id).where(Order.kod == code)) is None:
            return code
    raise HTTPException(503, "Buyurtma kodi yaratilmadi, qayta urinib ko'ring.")


@router.post("/checkout")
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(400, "Savat bo'sh.")
    if payload.yetkazish_turi not in ("kuryer", "pickup"):
        raise HTTPException(400, "yetkazish_turi kuryer yoki pickup bo'lishi kerak.")
    if payload.yetkazish_turi == "kuryer" and not (payload.manzil or "").strip() and payload.lokatsiya_lat is None:
        raise HTTPException(400, "Kuryer uchun manzil yoki lokatsiya majburiy.")

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
    # Validate all stores and calculate every order before adding any rows.
    for store_id, lines in grouped.items():
        store = db.get(Store, store_id)
        if store is None:
            raise HTTPException(404, "Do'kon topilmadi.")
        if store.holat != "faol":
            raise HTTPException(403, "Do'kon sotish uchun faol emas.")

        total = _money(0)
        product_json = []
        for product, item in lines:
            price = _money(product.yakuniy_narx or product.narxi)
            total += price * item.soni
            product_json.append({"product_id": product.id, "nomi": product.nomi,
                                 "narxi": float(price), "soni": item.soni})

        if payload.promo_kod:
            promo = db.scalar(select(PromoCode).where(PromoCode.store_id == store_id,
                                                       PromoCode.kod == payload.promo_kod.strip()))
            if promo and (promo.muddat is None or _as_aware(promo.muddat) >= _now()):
                total = (total * _money(100 - promo.chegirma_foizi) / _money(100)).quantize(Decimal("0.01"))
                promo.ishlatilish_soni += 1

        delivery_type = payload.yetkazish_turi
        pickup_point_id = None
        delivery = Decimal("0")
        if store.turi == "kafe":
            if not store.ochiq:
                raise HTTPException(400, "Kafe hozir yopiq.")
            # Cafes require full prepayment and have no delivery schedule selection.
            delivery_type = "pickup"
            oldindan, qoldiq = total, Decimal("0")
        elif delivery_type == "pickup":
            if store.tarif_turi == "lite":
                pp = db.get(PickupPoint, payload.pickup_point_id) if payload.pickup_point_id else None
                if pp is None or pp.store_id != store_id or not pp.rasm_url or pp.lokatsiya_lat is None or pp.lokatsiya_lng is None:
                    raise HTTPException(400, "Lite do'konida rasm va GPS li punkt majburiy.")
            elif payload.pickup_point_id:
                pp = db.get(PickupPoint, payload.pickup_point_id)
                if pp is None or pp.store_id != store_id:
                    raise HTTPException(400, "Olib ketish punkti noto'g'ri.")
            pickup_point_id = payload.pickup_point_id
            oldindan, qoldiq = total, Decimal("0")
        else:
            delivery = _money(store.kuryer_narxi)
            oldindan = (total * Decimal("0.5") + delivery).quantize(Decimal("0.01"))
            qoldiq = (total - total * Decimal("0.5")).quantize(Decimal("0.01"))

        order = Order(store_id=store_id, user_id=user.id, mahsulotlar=product_json,
                      jami_narx=float(total), holat="tolov_kutilmoqda", kod=_new_order_code(db),
                      yetkazish_turi=delivery_type,
                      manzil=payload.manzil.strip() if payload.manzil else None,
                      pickup_point_id=pickup_point_id, lokatsiya_lat=payload.lokatsiya_lat,
                      lokatsiya_lng=payload.lokatsiya_lng,
                      oldindan_summa=float(oldindan), qoldiq_summa=float(qoldiq),
                      yetkazish_narxi=float(delivery), tolov_holati="kutilmoqda")
        db.add(order)
        created.append(order)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Buyurtma yaratishda to'qnashuv yuz berdi. Qayta urinib ko'ring.")
    for order in created:
        db.refresh(order)
    return {"buyurtmalar": [{"id": o.id, "store_id": o.store_id, "jami_narx": float(o.jami_narx),
                             "oldindan_summa": float(o.oldindan_summa), "qoldiq_summa": float(o.qoldiq_summa),
                             "holat": o.holat, "kod": ""} for o in created],
            "xabar": "To'lov cheki yuklanishi kerak. Buyurtma kodi to'lov tasdiqlangach beriladi."}


@router.get("/orders")
def my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    orders = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.yaratilgan_vaqt.desc())).all()
    return [{"id": o.id, "store_id": o.store_id, "jami_narx": float(o.jami_narx), "holat": o.holat,
             "kod": o.kod if o.tolov_holati == "tasdiqlandi" else "", "mahsulotlar": o.mahsulotlar,
             "yetkazish_turi": o.yetkazish_turi, "oldindan_summa": float(o.oldindan_summa),
             "qoldiq_summa": float(o.qoldiq_summa), "qaytarilgan_summa": float(o.qaytarilgan_summa)} for o in orders]


@router.post("/orders/{order_id}/chek")
async def order_receipt(order_id: int, chek: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(404, "Buyurtma topilmadi.")
    if order.tolov_holati == "tasdiqlandi":
        raise HTTPException(400, "To'lov allaqachon tasdiqlangan.")
    raw = await chek.read()
    if not raw:
        raise HTTPException(400, "Chek bo'sh.")
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, "Chek rasmi 8 MB dan oshmasin.")
    mime = (chek.content_type or "image/jpeg").lower()
    if not mime.startswith("image/"):
        raise HTTPException(400, "Faqat rasm yuklash mumkin.")
    media = Media(mime=mime, data=raw, yuklagan_user_id=user.id, maxfiy=False)
    db.add(media); db.flush()
    result = ai.analyze_receipt(raw, mime, float(order.oldindan_summa))
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
    if order.holat not in ("yolda", "tayyorlanmoqda"):
        raise HTTPException(400, "Bu buyurtmani mijoz rad eta olmaydi.")
    delivery = _money(order.yetkazish_narxi)
    refund = (_money(order.oldindan_summa) - delivery).quantize(Decimal("0.01"))
    order.qaytarilgan_summa = float(max(refund, Decimal("0")))
    order.holat = "mijoz_rad_etdi"
    db.commit()
    return {"qaytarilgan_summa": float(order.qaytarilgan_summa), "holat": order.holat}
