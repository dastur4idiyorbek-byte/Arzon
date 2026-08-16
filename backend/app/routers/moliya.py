"""Moliya endpointlari — faqat super-admin (Moliya Boti orqali).

ACOM coin so'rovlarини tasdiqlaydi/rad etadi va umumiy hisobotни beradi.
Barcha summalar Qirg'iziston somida (KGS). Har endpoint super-admin ekanini
tekshiradi (rule 2 — yakuniy qaror faqat super-adminники).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CoinQaytarishSorovi,
    CoinToldirishSorovi,
    PulYechishSorovi,
    Store,
    User,
)
from ..security import _verify_internal_admin, is_super_admin, native_user_or_none
from ..services import auth as auth_service
from ..services import coin as coin_service

router = APIRouter(prefix="/api/moliya", tags=["moliya"])


def require_super(
    authorization: str = Header(default=""),
    x_admin_id: str = Header(default="", alias="X-Admin-Id"),
    x_internal_token: str = Header(default="", alias="X-Internal-Token"),
    db: Session = Depends(get_db),
) -> int:
    """Faqat super-admin (loyiha egasi) — Native ilova (JWT) yoki Moliya Boti."""
    user = native_user_or_none(authorization, db)
    if user is not None:
        if "moliya" not in auth_service.roles(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Faqat super-admin uchun.",
            )
        return int(user.telegram_id or 0)
    admin_id = _verify_internal_admin(x_admin_id, x_internal_token)
    if not is_super_admin(admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat super-admin uchun.",
        )
    return admin_id


# ---------------------------------------------------------------------------
# To'ldirish so'rovlari
# ---------------------------------------------------------------------------
@router.get("/topups")
def list_topups(
    holat: str = "kutilmoqda",
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(CoinToldirishSorovi)
        .where(CoinToldirishSorovi.holat == holat)
        .order_by(CoinToldirishSorovi.id.desc())
    ).all()
    natija = []
    for s in rows:
        u = db.get(User, s.user_id)
        natija.append(
            {
                "id": s.id,
                "ism": u.ism if u else None,
                "telegram_id": u.telegram_id if u else None,
                "summa": float(s.som_summasi),
                "ai_summa": float(s.ai_ochigan_summa)
                if s.ai_ochigan_summa is not None
                else None,
                "ai_sana": s.ai_ochigan_sana,
                "ai_xulosa": s.ai_xulosasi,
                "chek_rasm_url": s.chek_rasm_url,
                "holat": s.holat,
            }
        )
    return natija


class RejectBody(BaseModel):
    sabab: str = Field(default="", max_length=255)


@router.post("/topups/{sorov_id}/approve")
def approve_topup(
    sorov_id: int,
    admin_id: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    sorov = db.get(CoinToldirishSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    user = coin_service.approve_topup(db, sorov, admin_id)
    _notify(
        user.telegram_id,
        f"✅ Hisobingiz to'ldi: {float(sorov.som_summasi):,.0f} ACOM "
        f"({float(sorov.som_summasi):,.0f} som)!",
    )
    _push(
        db, user, "✅ Hisobingiz to'ldi",
        f"{float(sorov.som_summasi):,.0f} ACOM qo'shildi.",
        {"type": "balance"},
    )
    return {"holat": sorov.holat, "yangi_balans": float(coin_service.balance(user))}


@router.post("/topups/{sorov_id}/reject")
def reject_topup(
    sorov_id: int,
    payload: RejectBody,
    admin_id: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    sorov = db.get(CoinToldirishSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    coin_service.reject_topup(db, sorov, admin_id, payload.sabab)
    u = db.get(User, sorov.user_id)
    sabab_txt = f"\nSabab: {payload.sabab}" if payload.sabab else ""
    _notify(
        u.telegram_id if u else None,
        f"❌ To'ldirish so'rovingiz ({float(sorov.som_summasi):,.0f} som) "
        f"rad etildi.{sabab_txt}",
    )
    _push(
        db, u, "❌ To'ldirish rad etildi",
        f"{float(sorov.som_summasi):,.0f} som so'rovi rad etildi."
        + (f" Sabab: {payload.sabab}" if payload.sabab else ""),
        {"type": "balance"},
    )
    return {"holat": sorov.holat}


# ---------------------------------------------------------------------------
# Pul yechish so'rovlari
# ---------------------------------------------------------------------------
@router.get("/withdraws")
def list_withdraws(
    holat: str = "kutilmoqda",
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(PulYechishSorovi)
        .where(PulYechishSorovi.holat == holat)
        .order_by(PulYechishSorovi.id.desc())
    ).all()
    natija = []
    for s in rows:
        store = db.get(Store, s.store_id)
        natija.append(
            {
                "id": s.id,
                "store_nomi": store.nomi if store else None,
                "summa": float(s.sorolgan_summa),
                "karta_raqami": s.karta_raqami,
                "holat": s.holat,
            }
        )
    return natija


@router.post("/withdraws/{sorov_id}/paid")
def mark_withdraw_paid(
    sorov_id: int,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    sorov = db.get(PulYechishSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    coin_service.mark_withdraw_paid(db, sorov)
    # Do'kon adminlariга xabar.
    store = db.get(Store, sorov.store_id)
    for aid in (store.admin_ids or []) if store else []:
        _notify(
            aid,
            f"✅ Pul yechish so'rovingiz ({float(sorov.sorolgan_summa):,.0f} som) "
            "to'landi deb belgilandi.",
        )
    return {"holat": sorov.holat}


# ---------------------------------------------------------------------------
# Balans qaytarish so'rovlari
# ---------------------------------------------------------------------------
@router.get("/refunds")
def list_refunds(
    holat: str = "kutilmoqda",
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(CoinQaytarishSorovi)
        .where(CoinQaytarishSorovi.holat == holat)
        .order_by(CoinQaytarishSorovi.id.desc())
    ).all()
    natija = []
    for s in rows:
        u = db.get(User, s.user_id)
        natija.append(
            {
                "id": s.id,
                "ism": u.ism if u else None,
                "telegram_id": u.telegram_id if u else None,
                "summa": float(s.sorolgan_summa),
                "karta_raqami": s.karta_raqami,
                "holat": s.holat,
            }
        )
    return natija


@router.post("/refunds/{sorov_id}/approve")
def approve_refund(
    sorov_id: int,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    sorov = db.get(CoinQaytarishSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    coin_service.approve_coin_refund(db, sorov)
    u = db.get(User, sorov.user_id)
    _notify(
        u.telegram_id if u else None,
        f"✅ Balans qaytarish so'rovingiz ({float(sorov.sorolgan_summa):,.0f} som) "
        "tasdiqlandi. Tez orada kartangizga o'tkaziladi.",
    )
    _push(
        db, u, "✅ Qaytarish tasdiqlandi",
        f"{float(sorov.sorolgan_summa):,.0f} som kartangizga o'tkaziladi.",
        {"type": "balance"},
    )
    return {"holat": sorov.holat}


@router.post("/refunds/{sorov_id}/reject")
def reject_refund(
    sorov_id: int,
    payload: RejectBody,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    sorov = db.get(CoinQaytarishSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    coin_service.reject_coin_refund(db, sorov, payload.sabab)
    u = db.get(User, sorov.user_id)
    _notify(
        u.telegram_id if u else None,
        f"❌ Balans qaytarish so'rovingiz ({float(sorov.sorolgan_summa):,.0f} som) "
        "rad etildi.",
    )
    _push(
        db, u, "❌ Qaytarish rad etildi",
        f"{float(sorov.sorolgan_summa):,.0f} som so'rovi rad etildi."
        + (f" Sabab: {payload.sabab}" if payload.sabab else ""),
        {"type": "balance"},
    )
    return {"holat": sorov.holat}


# ---------------------------------------------------------------------------
# Umumiy hisobot + platforma hisob
# ---------------------------------------------------------------------------
@router.get("/report")
def report(
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    return coin_service.overall_report(db)


class PlatformaHisobBody(BaseModel):
    karta_raqami: str = Field(min_length=4, max_length=32)
    hisob_egasi: str = Field(min_length=1, max_length=255)


@router.get("/platforma-hisob")
def get_platforma_hisob(
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    h = coin_service.get_platforma_hisob(db)
    if h is None:
        return None
    return {"karta_raqami": h.karta_raqami, "hisob_egasi": h.hisob_egasi}


@router.post("/platforma-hisob")
def set_platforma_hisob(
    payload: PlatformaHisobBody,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    h = coin_service.set_platforma_hisob(
        db, payload.karta_raqami, payload.hisob_egasi
    )
    return {"karta_raqami": h.karta_raqami, "hisob_egasi": h.hisob_egasi}


def _notify(telegram_id: int | None, text: str) -> None:
    if not telegram_id:
        return
    try:
        from ..tgbots import notify

        notify.notify_customer(telegram_id, text)
    except ImportError:
        pass


def _push(db: Session, user, title: str, body: str, data: dict | None = None) -> None:
    """Native ilova foydalanuvchisiga push (Phase 5)."""
    from ..services import push as push_service

    push_service.push_user(db, user, title, body, data)


# ---------------------------------------------------------------------------
# Do'kon ochish TO'LOVLARI (1-bosqich — hisobchi to'lovni tasdiqlaydi)
# ---------------------------------------------------------------------------
@router.get("/dokon-tolovlari")
def list_dokon_tolovlari(
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    from ..models import DokonSorovi  # noqa: F401
    from ..services import dokon as dokon_service

    natija = []
    for s in dokon_service.list_kutilmoqda(db):
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


@router.post("/dokon-tolovlari/{sorov_id}/confirm")
def confirm_dokon_tolov(
    sorov_id: int,
    admin_id: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    """Hisobchi to'lovni tasdiqlaydi -> so'rov Menejerга uzatiladi."""
    from ..models import DokonSorovi
    from ..services import dokon as dokon_service

    sorov = db.get(DokonSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    dokon_service.confirm_tolov(db, sorov, admin_id)
    # 2-bosqich: Menejerга xabar.
    try:
        from ..tgbots import notify

        u = db.get(User, sorov.user_id)
        notify.notify_menejer_dokon(
            sorov_id=sorov.id,
            ism=u.ism if u else None,
            telegram_id=u.telegram_id if u else None,
            dokon_nomi=sorov.dokon_nomi,
            admin_tid=sorov.admin_telegram_id,
            mahsulot_soni=sorov.mahsulot_soni,
            summa=float(sorov.summa),
            ai_summa=float(sorov.ai_ochigan_summa)
            if sorov.ai_ochigan_summa is not None
            else None,
            ai_xulosa=sorov.ai_xulosasi,
            chek_rel_url=sorov.chek_rasm_url,
        )
    except ImportError:
        pass
    return {"holat": sorov.holat}


@router.post("/dokon-tolovlari/{sorov_id}/reject")
def reject_dokon_tolov(
    sorov_id: int,
    payload: RejectBody,
    admin_id: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    from ..models import DokonSorovi
    from ..services import dokon as dokon_service

    sorov = db.get(DokonSorovi, sorov_id)
    if sorov is None:
        raise HTTPException(status_code=404, detail="So'rov topilmadi.")
    dokon_service.reject_dokon_sorovi(db, sorov, admin_id, payload.sabab)
    u = db.get(User, sorov.user_id)
    sabab_txt = f"\nSabab: {payload.sabab}" if payload.sabab else ""
    _notify(
        u.telegram_id if u else None,
        f"❌ Do'kon ochish to'lovingiz ('{sorov.dokon_nomi}') tasdiqlanmadi.{sabab_txt}",
    )
    return {"holat": sorov.holat}


# ---------------------------------------------------------------------------
# To'lov usullari boshqaruvi (task_2)
# ---------------------------------------------------------------------------
@router.get("/tolov-usullari")
def list_tolov_usullari(
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    return [
        coin_service.tolov_usuli_dict(u)
        for u in coin_service.list_all_tolov_usullari(db)
    ]


class TolovUsuliBody(BaseModel):
    turi: str
    nomi: str = Field(min_length=1, max_length=50)
    qiymat: str | None = None
    egasi: str | None = None
    qr_rasm_url: str | None = None
    izoh: str | None = None


@router.post("/tolov-usullari")
def create_tolov_usuli(
    payload: TolovUsuliBody,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    u = coin_service.create_tolov_usuli(
        db,
        payload.turi,
        payload.nomi,
        qiymat=payload.qiymat,
        egasi=payload.egasi,
        qr_rasm_url=payload.qr_rasm_url,
        izoh=payload.izoh,
    )
    return coin_service.tolov_usuli_dict(u)


class TolovUsuliUpdate(BaseModel):
    nomi: str | None = None
    qiymat: str | None = None
    egasi: str | None = None
    qr_rasm_url: str | None = None
    izoh: str | None = None


@router.patch("/tolov-usullari/{usul_id}")
def update_tolov_usuli(
    usul_id: int,
    payload: TolovUsuliUpdate,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    u = coin_service.update_tolov_usuli(
        db, usul_id, **payload.model_dump(exclude_none=True)
    )
    return coin_service.tolov_usuli_dict(u)


@router.post("/tolov-usullari/{usul_id}/toggle")
def toggle_tolov_usuli(
    usul_id: int,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    u = coin_service.toggle_tolov_usuli(db, usul_id)
    return coin_service.tolov_usuli_dict(u)


@router.delete("/tolov-usullari/{usul_id}")
def delete_tolov_usuli(
    usul_id: int,
    _: int = Depends(require_super),
    db: Session = Depends(get_db),
):
    coin_service.delete_tolov_usuli(db, usul_id)
    return {"status": "ok"}
