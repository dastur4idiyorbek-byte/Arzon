"""Savat/checkout, buyurtmalar tarixi, kontakt tasdiqlash (phase 2.3, 3.5)."""
from __future__ import annotations

from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, User
from ..models import PickupPoint
from ..schemas import (
    CheckoutRequest,
    CheckoutResponse,
    OrderOut,
    PhoneConfirmRequest,
    PickupPointOut,
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
        db,
        user,
        payload.items,
        accessible,
        payload.promo_kod,
        yetkazish_turi=payload.yetkazish_turi,
        manzil=payload.manzil,
        pickup_points=payload.pickup_points,
        lokatsiya_lat=payload.lokatsiya_lat,
        lokatsiya_lng=payload.lokatsiya_lng,
    )

    # Referal: birinchi xaridni belgilash + referal egasiga 5% mukofot (phase 4.4).
    jami_xarid = sum(float(o.jami_narx) for o in orders)
    loyalty_service.mark_referral_purchased(db, user, jami_xarid)

    # Yangi buyurtma haqida do'kon adminlariga xabar (spec2 task_1).
    # PTB o'rnatilmagan yoki botlar faol bo'lmagan muhitда jimgina o'tadi.
    try:
        from ..models import PickupPoint, Store
        from ..tgbots import notify

        import html as _h

        for o in orders:
            store = db.get(Store, o.store_id)
            if o.yetkazish_turi == "pickup" and o.pickup_point_id:
                pp = db.get(PickupPoint, o.pickup_point_id)
                yetk = (
                    f"🏬 Olib ketish: <b>{_h.escape(pp.nomi)}</b>, "
                    f"{_h.escape(pp.manzil)}"
                    if pp
                    else "🏬 Olib ketish"
                )
            else:
                yetk = f"🚚 Kuryer: <b>{_h.escape(o.manzil or '-')}</b>"
                if o.yetkazish_narxi:
                    yetk += f"\n💵 Yetkazish: {float(o.yetkazish_narxi):,.0f} som"
            # Lokatsiya bo'lsa — Google Maps havolasi (inline tugma, task_3).
            maps_link = None
            if o.lokatsiya_lat is not None and o.lokatsiya_lng is not None:
                maps_link = (
                    f"https://www.google.com/maps?q="
                    f"{o.lokatsiya_lat},{o.lokatsiya_lng}"
                )
            notify.notify_new_order(
                admin_ids=list(store.admin_ids or []) if store else [],
                order_id=o.id,
                kod=o.kod,
                jami=float(o.jami_narx),
                mahsulotlar=o.mahsulotlar,
                mijoz_ism=user.ism,
                mijoz_tel=user.tel,
                yetkazish_txt=yetk,
                maps_link=maps_link,
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


@router.delete("/orders/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mijoz eski (tugagan) buyurtмани tarixidan o'chiradi."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
    order_service.delete_order_for_user(db, order, user)
    return {"ochirildi": True}


@router.get("/pickup-points", response_model=List[PickupPointOut])
def pickup_points(
    store_ids: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Berilgan do'konlar uchun olib ketish punktlari (Mini App checkout).

    store_ids — vergul bilan ajratilган (masalan "1,3"). Faqat faol punktlar.
    """
    ids = [int(x) for x in store_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return []
    rows = db.scalars(
        select(PickupPoint).where(
            PickupPoint.store_id.in_(ids), PickupPoint.holat == "faol"
        )
    ).all()
    return [PickupPointOut.model_validate(p) for p in rows]


@router.get("/balance")
def balance(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mini App uchun mijoz ACOM coin balansi (header'да ko'rsatiladi)."""
    from ..services import coin as coin_service

    return {"coin_balans": float(coin_service.balance(user))}


@router.post("/miniapp-opened")
def miniapp_opened(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mini App'ni birinchi ochган uchun bir martalik bonus (10 ACOM)."""
    from ..services import coin as coin_service
    from ..services import loyalty as loyalty_service

    # Mukofot referal egasiga beriladi (do'st Mini App'ni ochdi).
    bonus = loyalty_service.award_miniapp_referral_bonus(db, user)
    return {"bonus": bonus, "coin_balans": float(coin_service.balance(user))}


@router.get("/reverse-geocode")
def reverse_geocode(
    lat: float,
    lng: float,
    user: User = Depends(get_current_user),
):
    """Koordinatani qisqa manzil nomiga aylantiradi (OpenStreetMap Nominatim).

    Mijoz lokatsiya yuborganда manzil maydoni avtomatik to'ldirilsin — qo'lда
    yozish shart bo'lmaydi. Xizmat javob bermasa — koordinata qaytadi (zaxira).
    """
    import httpx

    fallback = f"{lat:.5f}, {lng:.5f}"
    try:
        r = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "jsonv2",
                "lat": lat,
                "lon": lng,
                "zoom": 18,
                "addressdetails": 1,
            },
            headers={
                "User-Agent": "ARZON-Shop/1.0 (telegram mini app)",
                "Accept-Language": "ru,uz",
            },
            timeout=8,
        )
        if r.status_code != 200:
            return {"nomi": fallback}
        data = r.json()
        adr = data.get("address", {}) or {}
        # Qisqa nom: ko'cha/mahalla + shahar.
        koча = (
            adr.get("road")
            or adr.get("pedestrian")
            or adr.get("neighbourhood")
            or adr.get("suburb")
            or adr.get("city_district")
        )
        shahar = (
            adr.get("city")
            or adr.get("town")
            or adr.get("village")
            or adr.get("county")
        )
        uy = adr.get("house_number")
        qismlar = []
        if koча:
            qismlar.append(f"{koча} {uy}" if uy else koча)
        if shahar and shahar != koча:
            qismlar.append(shahar)
        nomi = ", ".join(qismlar) if qismlar else (data.get("display_name") or fallback)
        # Juda uzun bo'lsa qisqartiramiz.
        if len(nomi) > 120:
            nomi = nomi[:117] + "..."
        return {"nomi": nomi}
    except Exception:  # noqa: BLE001
        return {"nomi": fallback}


def _tolov_usuli_public(usul, base: str) -> dict:
    """To'lov usulini Mini App uchun formatlaydi (QR uchun to'liq URL)."""
    from ..services import coin as coin_service

    d = coin_service.tolov_usuli_dict(usul)
    if d.get("qr_rasm_url") and d["qr_rasm_url"].startswith("/media/") and base:
        d["qr_rasm_url"] = f"{base}{d['qr_rasm_url']}"
    return d


@router.get("/tolov-usullari")
def tolov_usullari(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mini App to'ldirish oynasi uchun faol to'lov usullari (task_1, task_3)."""
    import os

    from ..services import coin as coin_service

    base = (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")
    usullar = coin_service.list_active_tolov_usullari(db)
    return [_tolov_usuli_public(u, base) for u in usullar]


@router.post("/topup-request")
def topup_request(
    summa: float = Form(...),
    tolov_usuli_id: int | None = Form(None),
    chek: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mini App ichida balans to'ldirish so'rovi (task_3).

    Chek rasmi yuklanadi -> Gemini tahlil -> so'rov yaratiladi -> Moliya Botiga
    (chek rasmi bilan) yuboriladi. Backend mantig'i bot oqimi bilan bir xil.
    """
    from .. import ai as ai_module
    from ..services import coin as coin_service

    raw = chek.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Chek rasmi bo'sh.")
    mime = chek.content_type or "image/jpeg"
    natija = ai_module.analyze_receipt(raw, mime, summa)

    sorov = coin_service.create_topup_request(
        db,
        user,
        summa,
        ai_summa=natija.get("summa"),
        ai_sana=natija.get("sana"),
        ai_xulosa=natija.get("xulosa"),
        tolov_usuli_id=tolov_usuli_id,
    )
    usul = (
        coin_service.get_tolov_usuli(db, tolov_usuli_id)
        if tolov_usuli_id
        else None
    )
    try:
        from ..tgbots import notify

        notify.notify_moliya_topup(
            sorov_id=sorov.id,
            ism=user.ism,
            telegram_id=user.telegram_id,
            summa=float(sorov.som_summasi),
            ai_summa=natija.get("summa"),
            ai_sana=natija.get("sana"),
            ai_xulosa=natija.get("xulosa"),
            chek_rel_url=None,
            usul_nomi=usul.nomi if usul else None,
            image_bytes=raw,
        )
    except ImportError:
        pass
    return {"sorov_id": sorov.id, "holat": sorov.holat}


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
