"""Courier APIs based on native User.is_kuryer."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, YetkazishHudud, User
from ..security import require_kuryer
from ..services.push import push_user

router = APIRouter(prefix="/api/courier", tags=["courier"])


@router.get("/zones")
def my_zones(db: Session = Depends(get_db), courier: User = Depends(require_kuryer)):
    return [{"id": z.id, "hudud_nomi": z.hudud_nomi, "vaqt_oraligi": z.vaqt_oraligi,
             "boshlanish_soati": z.boshlanish_soati, "narx": float(z.narx), "faol": z.faol}
            for z in db.scalars(select(YetkazishHudud).where(YetkazishHudud.faol == True)).all()]


@router.get("/orders")
def available_orders(db: Session = Depends(get_db), courier: User = Depends(require_kuryer)):
    return [{"id": o.id, "store_id": o.store_id, "user_id": o.user_id, "jami_narx": float(o.jami_narx),
             "manzil": o.manzil, "lokatsiya_lat": float(o.lokatsiya_lat) if o.lokatsiya_lat is not None else None,
             "lokatsiya_lng": float(o.lokatsiya_lng) if o.lokatsiya_lng is not None else None,
             "holat": o.holat, "oldindan_summa": float(o.oldindan_summa)}
            for o in db.scalars(select(Order).where(Order.yetkazish_turi == "kuryer", Order.holat.in(["yangi", "tayyorlanmoqda", "yolda"]), Order.kuryer_user_id.is_(None))).all()]


@router.post("/orders/{order_id}/take")
def take_order(order_id: int, db: Session = Depends(get_db), courier: User = Depends(require_kuryer)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    if order.kuryer_user_id is not None:
        raise HTTPException(400, "Buyurtma boshqa kuryerga biriktirilgan.")
    order.kuryer_user_id = courier.id
    order.holat = "yolda"
    db.commit()
    customer = db.get(User, order.user_id)
    push_user(db, customer, "Buyurtma yo'lda", "Kuryer buyurtmangizni qabul qildi.", {"type": "order", "order_id": order.id})
    return {"id": order.id, "holat": order.holat}


@router.post("/orders/{order_id}/delivered")
def delivered(order_id: int, db: Session = Depends(get_db), courier: User = Depends(require_kuryer)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    if order.kuryer_user_id != courier.id:
        raise HTTPException(403, "Bu buyurtma sizga biriktirilmagan.")
    order.holat = "topshirildi"; order.tasdiqlangan_vaqt = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    db.commit()
    push_user(db, db.get(User, order.user_id), "Buyurtma topshirildi", "Buyurtmangiz topshirildi. Xaridingiz uchun rahmat!", {"type": "order", "order_id": order.id})
    return {"id": order.id, "holat": order.holat}


@router.post("/orders/{order_id}/mijoz-rad-etdi")
def customer_rejected(order_id: int, db: Session = Depends(get_db), courier: User = Depends(require_kuryer)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi.")
    if order.kuryer_user_id != courier.id:
        raise HTTPException(403, "Bu buyurtma sizga biriktirilmagan.")
    from decimal import Decimal
    delivery = Decimal(str(order.yetkazish_narxi or 0))
    refund = (Decimal(str(order.oldindan_summa or 0)) - delivery).quantize(Decimal("0.01"))
    order.qaytarilgan_summa = float(max(refund, Decimal("0")))
    order.holat = "mijoz_rad_etdi"
    db.commit()
    push_user(db, db.get(User, order.user_id), "Buyurtma rad etildi", f"Qaytariladigan summa: {order.qaytarilgan_summa}", {"type": "order", "order_id": order.id})
    return {"id": order.id, "qaytarilgan_summa": float(order.qaytarilgan_summa), "holat": order.holat}
