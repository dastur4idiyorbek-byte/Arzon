"""Menejer endpointlari — faqat menejer(lar) (MENEJER_ID).

Do'kon so'rovlarini tasdiqlash, admin boshqaruvi, do'kon/mahsulot moderatsiyasi,
arenda nazorati va Moliyadan hisobot. Boshqaruv Bot bilan umumiy kod yo'q,
faqat umumiy baza (rule 2).
"""
from __future__ import annotations

import html as _html

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import DokonSorovi, User
from ..security import require_manager
from ..services import coin as coin_service
from ..services import dokon as dokon_service
from ..services import menejer as menejer_service

router = APIRouter(prefix="/api/menejer", tags=["menejer"])


# ---------------------------------------------------------------------------
# Do'kon ochish so'rovlari (task_2)
# ---------------------------------------------------------------------------
@router.get("/dokon-sorovlari")
def list_dokon_sorovlari(
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    natija = []
    # Faqat hisobchi to'lovni tasdiqlagan so'rovlar (2-bosqich).
    for s in dokon_service.list_tolov_tasdiqlangan(db):
        u = db.get(User, s.user_id)
        natija.append(
            {
                "id": s.id,
                "ism": u.ism if u else None,
                "telegram_id": u.telegram_id if u else None,
                "dokon_nomi": s.dokon_nomi,
                "admin_telegram_id": s.admin_telegram_id,
                "mahsulot_soni": s.mahsulot_soni,
                "summa": float(s.summa),
                "ai_summa": float(s.ai_ochigan_summa)
                if s.ai_ochigan_summa is not None
                else None,
                "ai_xulosa": s.ai_xulosasi,
                "chek_rasm_url": s.chek_rasm_url,
            }
        )
    return natija


@router.post("/dokon-sorovlari/{sorov_id}/approve")
def approve_dokon(
    sorov_id: int,
    admin_id: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    sorov = db.get(DokonSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    # Oylik arenda avtomatik (mahsulot soniга qarab) — approve_dokon_sorovi ичида.
    store = dokon_service.approve_dokon_sorovi(db, sorov, admin_id)

    bot_uname = settings.admin_bot_username.lstrip("@")
    bot_link = f"https://t.me/{bot_uname}"
    arenda_qator = (
        f"📅 Oylik arenda: <b>{float(store.arenda_summasi):,.0f} som</b> "
        "(1 oy to'landi)\n"
        if store.arenda_summasi
        else ""
    )
    xabar = (
        "🎉 <b>Tabriklaymiz! Do'koningiz ochildi!</b>\n\n"
        f"🏪 Do'kon: <b>{_html.escape(store.nomi)}</b>\n"
        f"📦 Mahsulot limiti: <b>{store.mahsulot_limiti} ta</b>\n"
        f"{arenda_qator}\n"
        f"🔑 Do'koningiz mahfiy kodi:\n<code>{_html.escape(store.mahfiy_kirish_kodi or '')}</code>\n\n"
        f"👉 Boshqaruv botiga o'ting va /start bosing:\n"
        f'<a href="{bot_link}">@{_html.escape(bot_uname)}</a>\n\n'
        "Omad tilaymiz! 🚀"
    )
    u = db.get(User, sorov.user_id)
    _notify_html(u.telegram_id if u else None, xabar)
    if sorov.admin_telegram_id and (not u or sorov.admin_telegram_id != u.telegram_id):
        _notify_html(sorov.admin_telegram_id, xabar)
    return {
        "store_id": store.id,
        "nomi": store.nomi,
        "mahfiy_kirish_kodi": store.mahfiy_kirish_kodi,
    }


class RejectBody(BaseModel):
    sabab: str = Field(default="", max_length=255)


@router.post("/dokon-sorovlari/{sorov_id}/reject")
def reject_dokon(
    sorov_id: int,
    payload: RejectBody,
    admin_id: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    sorov = db.get(DokonSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    dokon_service.reject_dokon_sorovi(db, sorov, admin_id, payload.sabab)
    u = db.get(User, sorov.user_id)
    sabab_txt = f"\nSabab: {payload.sabab}" if payload.sabab else ""
    _notify_plain(
        u.telegram_id if u else None,
        f"❌ Do'kon ochish so'rovingiz ('{sorov.dokon_nomi}') rad etildi.{sabab_txt}",
    )
    return {"holat": sorov.holat}


# ---------------------------------------------------------------------------
# Adminlar
# ---------------------------------------------------------------------------
@router.get("/adminlar")
def adminlar(
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return menejer_service.list_stores_info(db)


class AdminBody(BaseModel):
    """Admin qo'shish. Uchtadan biri yetarli (arzon_id — tavsiya etiladi)."""

    arzon_id: int | None = None  # ARZON foydalanuvchi ID (#42) — asosiy usul
    email: str | None = None  # ilovaga shu email bilan kirgan hisob
    telegram_id: int | None = None  # eski usul (botlar bilan moslik uchun)


@router.post("/stores/{store_id}/admins")
def add_admin(
    store_id: int,
    payload: AdminBody,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return {
        "admin_ids": menejer_service.add_admin(
            db, store_id, payload.telegram_id, payload.email, payload.arzon_id
        )
    }


@router.delete("/stores/{store_id}/admins/{admin_id}")
def remove_admin(
    store_id: int,
    admin_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """admin_id — Telegram ID (musbat) yoki native hisob ID'si (manfiy)."""
    return {"admin_ids": menejer_service.remove_admin(db, store_id, admin_id)}


# ---------------------------------------------------------------------------
# Do'kon / mahsulot moderatsiyasi
# ---------------------------------------------------------------------------
@router.get("/stores")
def stores(
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return menejer_service.list_stores_info(db)


@router.delete("/stores/{store_id}")
def delete_store(
    store_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    nomi = menejer_service.delete_store_cascade(db, store_id)
    return {"ochirildi": True, "nomi": nomi}


@router.get("/stores/{store_id}/products")
def store_products(
    store_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return menejer_service.list_store_products(db, store_id)


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    nomi = menejer_service.delete_product_moderation(db, product_id)
    return {"ochirildi": True, "nomi": nomi}


# ---------------------------------------------------------------------------
# Arenda nazorati (task_5)
# ---------------------------------------------------------------------------
@router.get("/arenda")
def arenda(
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return menejer_service.list_stores_info(db)


@router.post("/stores/{store_id}/block")
def block(
    store_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    s = menejer_service.block_store(db, store_id)
    return {"holat": s.holat}


@router.post("/stores/{store_id}/unblock")
def unblock(
    store_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    s = menejer_service.unblock_store(db, store_id)
    return {"holat": s.holat}


@router.post("/stores/{store_id}/arenda-uzaytir")
def arenda_uzaytir(
    store_id: int,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Arenda to'landi — 1 oyga uzaytiriladi va do'kon blokdan chiqadi."""
    s = menejer_service.extend_arenda(db, store_id, oy=1)
    # Do'kon adminlariга xabar.
    for aid in s.admin_ids or []:
        _notify_plain(
            aid,
            f"✅ '{s.nomi}' arendasi 1 oyga uzaytirildi. Do'koningiz faol.",
        )
    return {
        "holat": s.holat,
        "arenda_muddati_tugashi": (
            s.arenda_muddati_tugashi.isoformat()
            if s.arenda_muddati_tugashi
            else None
        ),
    }


# ---------------------------------------------------------------------------
# 📢 E'lon / yangilik yuborish (adminlarга yoki mijozларга)
# ---------------------------------------------------------------------------
class BroadcastBody(BaseModel):
    target: str  # 'admin' | 'customer'
    matn: str = Field(min_length=1, max_length=4000)


@router.post("/broadcast")
def broadcast(
    payload: BroadcastBody,
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """E'lonni barcha adminlarга (Boshqaruv boti) yoki mijozларга (Savdo boti)."""
    if payload.target not in ("admin", "customer"):
        raise HTTPException(status_code=400, detail="target 'admin' yoki 'customer'.")
    if payload.target == "admin":
        ids = menejer_service.admin_recipients(db)
    else:
        ids = menejer_service.customer_recipients(db)

    matn = payload.matn
    try:
        from ..tgbots import notify

        for tid in ids:
            if payload.target == "admin":
                notify.notify_admin_plain(tid, matn)
            else:
                notify.notify_customer(tid, matn)
    except ImportError:
        pass
    return {"yuborildi": len(ids), "target": payload.target}


# ---------------------------------------------------------------------------
# Hisobot (Moliyadan — bir xil backend, ikki marta yozilmaydi)
# ---------------------------------------------------------------------------
@router.get("/report")
def report(
    _: int = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return coin_service.overall_report(db)


# ---------------------------------------------------------------------------
# Xabar yordamchilari
# ---------------------------------------------------------------------------
def _notify_html(telegram_id: int | None, text: str) -> None:
    if not telegram_id:
        return
    try:
        from ..tgbots import notify

        notify.notify_customer(telegram_id, text, parse_mode="HTML")
    except ImportError:
        pass


def _notify_plain(telegram_id: int | None, text: str) -> None:
    if not telegram_id:
        return
    try:
        from ..tgbots import notify

        notify.notify_customer(telegram_id, text)
    except ImportError:
        pass
