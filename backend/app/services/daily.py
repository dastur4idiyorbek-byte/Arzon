"""Daily subscription/discount maintenance at 21:00 Asia/Bishkek."""
from __future__ import annotations
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from ..database import SessionLocal
from ..models import Product, Store, User, _as_aware, _now
from . import push
logger=logging.getLogger("arzon.daily")
_scheduler: BackgroundScheduler|None=None

def daily_maintenance() -> dict:
    now=_now(); soon=now+timedelta(days=2); expired_discounts=0; suspended=0; reminders=0
    with SessionLocal() as db:
        for p in db.scalars(select(Product).where(Product.skidka_foizi>0,Product.skidka_muddati.isnot(None))).all():
            if _as_aware(p.skidka_muddati)<now:
                p.skidka_foizi=0;p.yakuniy_narx=None;expired_discounts+=1
        for store in db.scalars(select(Store).where(Store.holat=="faol")).all():
            expiry=_as_aware(store.obuna_muddati_tugashi or store.arenda_muddati_tugashi)
            if expiry is None: continue
            recipients=[db.get(User,uid) for uid in (store.admin_ids or [])]
            if now < expiry <= soon:
                for u in recipients:
                    if u: reminders+=int(push.push_user(db,u,"Obuna tugayapti",f"{store.nomi} do'koni obunasi 2 kun ichida tugaydi.",{"type":"subscription"}))
            elif expiry<=now:
                store.holat="vaqtincha_toxtatilgan";suspended+=1
                for u in recipients:
                    if u: push.push_user(db,u,"Do'kon vaqtincha to'xtatildi",f"{store.nomi} do'koni obunasi tugadi.",{"type":"store_suspended","store_id":store.id})
        db.commit()
    logger.info("Daily maintenance: discounts=%s suspended=%s reminders=%s",expired_discounts,suspended,reminders)
    return {"expired_discounts":expired_discounts,"suspended_stores":suspended,"reminders":reminders}

def start_daily_jobs() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:return
    _scheduler=BackgroundScheduler(timezone=ZoneInfo("Asia/Bishkek"))
    _scheduler.add_job(daily_maintenance,"cron",hour=21,minute=0,id="arzon-daily",replace_existing=True)
    _scheduler.start()
def stop_daily_jobs() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:_scheduler.shutdown(wait=False)
    _scheduler=None
