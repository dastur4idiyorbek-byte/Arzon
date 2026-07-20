"""Xabarnomalar: yangi buyurtma -> admin, holat o'zgarishi -> mijoz.

Checkout sinxron (threadpool) kontekstда ishlaydi; xabar yuborish esa async.
run_coroutine_threadsafe orqali backend event loopига topshiramiz — javobni
kutmaymiz (fire-and-forget), checkout sekinlashmaydi.
"""
from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from . import registry

logger = logging.getLogger("arzon.notify")


def _submit(coro) -> None:
    if registry.loop is None or registry.loop.is_closed():
        return
    fut = asyncio.run_coroutine_threadsafe(coro, registry.loop)

    def _log_err(f):
        exc = f.exception()
        if exc:
            logger.warning("Xabarnoma yuborilmadi: %s", exc)

    fut.add_done_callback(_log_err)


async def _send_admin(chat_id: int, text: str, order_id: int) -> None:
    app = registry.get("boshqaruv")
    if app is None:
        return
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Qabul qilish", callback_data=f"qabul_{order_id}"
                ),
                InlineKeyboardButton(
                    "❌ Bekor qilish", callback_data=f"rad_{order_id}"
                ),
            ]
        ]
    )
    await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)


def notify_new_order(
    admin_ids: list[int],
    order_id: int,
    kod: str,
    jami: float,
    mahsulotlar: list,
    mijoz_ism: str | None,
    mijoz_tel: str | None,
    yetkazish_txt: str = "",
) -> None:
    """Yangi buyurtma haqida do'kon adminlariga xabar (spec2 task_1).

    Sync koddан chaqiriladi (checkout) — yuborish fon rejимда bo'ladi.
    """
    items = "\n".join(
        f"  • {m.get('nomi')} x{m.get('soni')} — {m.get('narxi'):,.0f} som"
        for m in (mahsulotlar or [])
    )
    text = (
        f"🆕 Yangi buyurtma!\n\n"
        f"Kod: {kod}\n"
        f"Mijoz: {mijoz_ism or 'nomalum'}"
        + (f" ({mijoz_tel})" if mijoz_tel else "")
        + f"\n\nMahsulotlar:\n{items}\n\n"
        f"Jami: {jami:,.0f} som"
        + (f"\n{yetkazish_txt}" if yetkazish_txt else "")
    )
    for admin_id in admin_ids or []:
        _submit(_send_admin(admin_id, text, order_id))


async def _send_customer(telegram_id: int, text: str) -> None:
    app = registry.get("savdo")
    if app is None:
        return
    await app.bot.send_message(chat_id=telegram_id, text=text)


def notify_customer(telegram_id: int | None, text: str) -> None:
    """Mijozga Savdo Boti orqali xabar (sync yoki async koddан)."""
    if not telegram_id:
        return
    _submit(_send_customer(telegram_id, text))


async def send_customer(telegram_id: int | None, text: str) -> None:
    """Async kontekstдан to'g'ridan-to'g'ri yuborish (bot handlerlari uchun)."""
    if not telegram_id:
        return
    try:
        await _send_customer(telegram_id, text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Mijozga xabar yuborilmadi: %s", e)
