"""ARZON 2.0 daily tasks, scheduled for 21:00 Asia/Bishkek."""
from __future__ import annotations
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from ..database import SessionLocal
from ..models import Product, Store, User, _as_aware, _now
from .push import push_user

logger = logging.getLogger("arzon.daily")
_scheduler: BackgroundScheduler | None = None


def daily_maintenance() -> dict:
    now = _now()
    soon = now + timedelta(days=2)
    discounts = suspended = reminders = 0
    with SessionLocal() as db:
        for product in db.scalars(select(Product).where(Product.skidka_foizi > 0, Product.skidka_muddati.is_not(None))).all():
            if _as_aware(product.skidka_muddati) < now:
                product.skidka_foizi = 0
                product.yakuniy_narx = None
                discounts += 1
        for store in db.scalars(select(Store).where(Store.holat == "faol")).all():
            expiry = _as_aware(store.obuna_muddati_tugashi or store.arenda_muddati_tugashi)
            if expiry is None:
                continue
            recipients = [db.get(User, uid) for uid in (store.admin_ids or [])]
            if now < expiry <= soon:
                for user in recipients:
                    if user:
                        reminders += int(push_user(db, user, "Obuna tugayapti", f"{store.nomi} do'koni obunasi 2 kun ichida tugaydi.", {"type": "subscription", "store_id": store.id}))
            elif expiry <= now:
                store.holat = "vaqtincha_toxtatilgan"
                suspended += 1
                for user in recipients:
                    if user:
                        push_user(db, user, "Do'kon vaqtincha to'xtatildi", f"{store.nomi} do'koni obunasi tugadi.", {"type": "store_suspended", "store_id": store.id})
        db.commit()
    logger.info("Daily maintenance discounts=%s suspended=%s reminders=%s", discounts, suspended, reminders)
    return {"expired_discounts": discounts, "suspended_stores": suspended, "reminders": reminders}


def start_daily_jobs() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone=ZoneInfo("Asia/Bishkek"))
    _scheduler.add_job(daily_maintenance, "cron", hour=21, minute=0, id="arzon-daily", replace_existing=True)
    _scheduler.start()


def stop_daily_jobs() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
