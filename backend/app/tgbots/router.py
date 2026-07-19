"""Telegram webhook endpointlari va bot hayot sikli boshqaruvi.

Ishlash sharti: WEBHOOK_BASE_URL (yoki Render avtomatik beradigan
RENDER_EXTERNAL_URL) mavjud bo'lishi kerak. Lokalда bu o'zgaruvchi yo'q —
webhook o'rnatilmaydi va lokal polling skriptlari ishlashда davom etadi.

Xavfsizlik: har webhook so'rovда Telegram `X-Telegram-Bot-Api-Secret-Token`
sarlavhasini yuboradi (set_webhook'да berganimiz) — INTERNAL_API_TOKEN bilan
solishtiramiz. Mos kelmasa 403.
"""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request, status
from telegram import Update
from telegram.ext import Application

from ..config import settings
from . import boshqaruv, savdo

logger = logging.getLogger("arzon.tgbots")

router = APIRouter(prefix="/webhook/telegram", tags=["telegram-webhook"])

# Faol bot ilovalari: {"savdo": Application, "boshqaruv": Application}
_apps: dict[str, Application] = {}


def _base_url() -> str:
    return (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")


def _miniapp_url(base: str) -> str:
    return os.getenv("MINIAPP_URL", "").strip() or (f"{base}/app/" if base else "")


async def _setup_one(name: str, app: Application, base: str) -> None:
    """Bitta botni initsializatsiya qilib, webhook o'rnatadi."""
    await app.initialize()
    await app.bot.set_webhook(
        url=f"{base}/webhook/telegram/{name}",
        secret_token=settings.internal_api_token,
        drop_pending_updates=True,
    )
    _apps[name] = app
    logger.info("Telegram webhook o'rnatildi: %s", name)


async def startup() -> None:
    """FastAPI lifespan'дан chaqiriladi — botlarni webhook rejimда yoqadi."""
    base = _base_url()
    if not base:
        logger.info(
            "WEBHOOK_BASE_URL/RENDER_EXTERNAL_URL yo'q — webhook rejimi o'chiq "
            "(lokal polling ishlatilishi mumkin)."
        )
        return
    if not settings.internal_api_token:
        logger.warning("INTERNAL_API_TOKEN yo'q — webhook o'rnatilmaydi.")
        return

    if settings.savdo_bot_token:
        try:
            await _setup_one(
                "savdo",
                savdo.build_application(
                    settings.savdo_bot_token, _miniapp_url(base)
                ),
                base,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Savdo boti webhook o'rnatilmadi.")
    else:
        logger.info("SAVDO_BOT_TOKEN yo'q — savdo boti o'chiq.")

    if settings.boshqaruv_bot_token:
        try:
            await _setup_one(
                "boshqaruv",
                boshqaruv.build_application(settings.boshqaruv_bot_token),
                base,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Boshqaruv boti webhook o'rnatilmadi.")
    else:
        logger.info("BOSHQARUV_BOT_TOKEN yo'q — boshqaruv boti o'chiq.")


async def shutdown() -> None:
    """Bot resurslarini yopadi (webhook Telegram'да saqlanib qoladi)."""
    for name, app in list(_apps.items()):
        try:
            await app.shutdown()
        except Exception:  # noqa: BLE001
            logger.exception("Bot yopishда xato: %s", name)
    _apps.clear()


@router.post("/{bot_name}")
async def telegram_webhook(
    bot_name: str,
    request: Request,
    x_secret: str = Header(default="", alias="X-Telegram-Bot-Api-Secret-Token"),
):
    app = _apps.get(bot_name)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bot faol emas."
        )
    if not hmac.compare_digest(x_secret, settings.internal_api_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Secret noto'g'ri."
        )
    data = await request.json()
    try:
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    except Exception:  # noqa: BLE001
        # Handler xatosi Telegram'ga 500 qaytarmasin — aks holda Telegram
        # o'sha update'ни qayta-qayta yuboraveradi.
        logger.exception("Update qayta ishlashда xato (%s)", bot_name)
    return {"ok": True}


def active_bots() -> list[str]:
    return sorted(_apps.keys())
