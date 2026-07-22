"""Kunlik vazifalar (spec2 task_3 va task_5).

Har kuni mahalliy vaqt 21:00да (LOCAL_TZ, standart Asia/Bishkek):
  1. Muddati o'tgan chegirmalar nolga tushiriladi, adminlarga xabar.
  2. Har do'kon bo'yicha kunlik hisobot adminlarga yuboriladi.

Bot bilan bog'lanmagan sof mantiq — testда soxta bot bilan sinash oson.
Eslatma: bepul Renderда server "uxlab" qolsa job o'tib ketishi mumkin —
UptimeRobot pinger uni uyg'oq tutadi.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ..database import SessionLocal
from ..models import Order, Product, Store, User, _as_aware, _now

logger = logging.getLogger("arzon.daily")

LOCAL_TZ = os.getenv("LOCAL_TZ", "Asia/Bishkek")


def report_time() -> time:
    """Hisobot vaqti — mahalliy 21:00."""
    return time(hour=21, minute=0, tzinfo=ZoneInfo(LOCAL_TZ))


def _today_start_utc() -> datetime:
    """Mahalliy kun boshining UTC ekvivalenti."""
    tz = ZoneInfo(LOCAL_TZ)
    local_now = datetime.now(tz)
    start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc)


def expire_discounts(db) -> dict[int, list[str]]:
    """Muddati o'tgan chegirmalarni nolga tushiradi (spec2 task_5).

    Qaytaradi: {store_id: [xabar, ...]} — adminlarga yuborish uchun.
    """
    xabarlar: dict[int, list[str]] = {}
    products = db.scalars(
        select(Product).where(
            Product.skidka_foizi > 0, Product.skidka_muddati.isnot(None)
        )
    ).all()
    now = _now()
    for p in products:
        if _as_aware(p.skidka_muddati) < now:
            p.skidka_foizi = 0
            p.yakuniy_narx = None
            p.skidka_muddati = None
            xabarlar.setdefault(p.store_id, []).append(
                f"⏰ '{p.nomi}' uchun chegirma muddati tugadi, "
                "narx asl holatiga qaytdi."
            )
    if xabarlar:
        db.commit()
    return xabarlar


def build_store_report(db, store: Store) -> str:
    """Bitta do'kon uchun kunlik hisobot matni (spec2 task_3)."""
    start = _today_start_utc()
    sana = datetime.now(ZoneInfo(LOCAL_TZ)).strftime("%d.%m.%Y")

    orders = db.scalars(
        select(Order).where(
            Order.store_id == store.id, Order.yaratilgan_vaqt >= start
        )
    ).all()
    yangi = len(orders)
    tushum = sum(
        float(o.jami_narx) for o in orders if o.holat != "bekor_qilindi"
    )
    xaridorlar = len({o.user_id for o in orders})

    tally: dict[str, int] = {}
    for o in orders:
        if o.holat == "bekor_qilindi":
            continue
        for m in o.mahsulotlar or []:
            nomi = m.get("nomi") or "?"
            tally[nomi] = tally.get(nomi, 0) + int(m.get("soni", 0))
    if tally:
        top_nomi, top_soni = max(tally.items(), key=lambda kv: kv[1])
        top = f"{top_nomi} ({top_soni} dona)"
    else:
        top = "—"

    return (
        f"📊 Kunlik hisobot — {sana}\n"
        f"Do'kon: {store.nomi}\n\n"
        f"Yangi buyurtmalar: {yangi}\n"
        f"Tushum: {tushum:,.0f} som\n"
        f"Bugungi xaridorlar: {xaridorlar}\n"
        f"Eng ko'p sotilgan: {top}"
    )


def check_arenda(db) -> dict[int, list[str]]:
    """Arenda muddatini tekshiradi (task_5).

    - Tugashiga N kun (settings.arenda_ogohlantirish_kunlar) qolganда — admin(lar)ga
      ogohlantirish.
    - Muddat o'tса va do'kon hali faol bo'lsa — holat 'vaqtincha_toxtatilgan'
      (mahsulotlar bazада saqlanadi, o'chirilmaydi).

    Qaytaradi: {admin_telegram_id: [xabar, ...]}.
    """
    from ..config import settings

    now = _now()
    ogoh_kun = settings.arenda_ogohlantirish_kunlar
    xabarlar: dict[int, list[str]] = {}
    stores = db.scalars(
        select(Store).where(Store.arenda_muddati_tugashi.isnot(None))
    ).all()
    ozgardi = False
    for s in stores:
        muddat = _as_aware(s.arenda_muddati_tugashi)
        if muddat is None:
            continue
        qolgan_kun = (muddat - now).days
        summa = float(s.arenda_summasi or 0)
        if muddat < now:
            # Muddat o'tdi — bloklaymiz (agar hali faol bo'lsa).
            if s.holat == "faol":
                s.holat = "vaqtincha_toxtatilgan"
                ozgardi = True
                for aid in s.admin_ids or []:
                    xabarlar.setdefault(aid, []).append(
                        f"🔴 '{s.nomi}' do'koningiz arenda to'lanmagani uchun "
                        "vaqtincha to'xtatildi. Mahsulotlaringiz sotilib turibdi, "
                        "lekin boshqarish uchun arendani to'lang (Menejer bilan bog'laning)."
                    )
        elif 0 <= qolgan_kun <= ogoh_kun and s.holat == "faol":
            for aid in s.admin_ids or []:
                xabarlar.setdefault(aid, []).append(
                    f"⚠️ '{s.nomi}' do'koningiz arenda muddati {qolgan_kun} kundан "
                    f"keyin tugaydi. Davom etish uchun {summa:,.0f} som to'lang "
                    "(Menejer bilan bog'laning)."
                )
    if ozgardi:
        db.commit()
    return xabarlar


async def daily_tick(bot) -> None:
    """Kunlik ish: chegirma muddati + arenda + hisobotlar. `bot` — Boshqaruv Boti."""
    db = SessionLocal()
    try:
        # 0) Arenda nazorati (ogohlantirish + muddat o'tса bloklash).
        try:
            arenda_xabarlar = check_arenda(db)
            for admin_id, msgs in arenda_xabarlar.items():
                for msg in msgs:
                    try:
                        await bot.send_message(chat_id=admin_id, text=msg)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Arenda xabari ketmadi: %s", e)
        except Exception as e:  # noqa: BLE001
            logger.warning("Arenda tekshiruvида xato: %s", e)

        # 1) Muddati o'tgan chegirmalar.
        xabarlar = expire_discounts(db)
        stores = db.scalars(select(Store).where(Store.holat == "faol")).all()
        store_by_id = {s.id: s for s in stores}
        for store_id, msgs in xabarlar.items():
            store = store_by_id.get(store_id)
            if store is None:
                continue
            for admin_id in store.admin_ids or []:
                for msg in msgs:
                    try:
                        await bot.send_message(chat_id=admin_id, text=msg)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Chegirma xabari ketmadi: %s", e)

        # 2) Kunlik hisobotlar.
        for store in stores:
            text = build_store_report(db, store)
            for admin_id in store.admin_ids or []:
                try:
                    await bot.send_message(chat_id=admin_id, text=text)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Hisobot ketmadi (%s): %s", store.nomi, e)
    finally:
        db.close()
