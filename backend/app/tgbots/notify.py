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


async def _send_customer(telegram_id: int, text: str, parse_mode=None) -> None:
    app = registry.get("savdo")
    if app is None:
        return
    await app.bot.send_message(chat_id=telegram_id, text=text, parse_mode=parse_mode)


# ===========================================================================
# Moliya Boti xabarnomalari (ACOM coin — super-adminга)
# ===========================================================================
def _base_url() -> str:
    import os

    return (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")


async def _send_moliya(
    text: str,
    reply_markup=None,
    photo_rel_url: str | None = None,
    photo_bytes: bytes | None = None,
) -> None:
    """Barcha super-adminlarга Moliya Boti orqali xabar.

    photo_bytes — Mini App'дан yuklangan chek (Telegram file_id yo'q). Birinchi
    super-adminга baytlar bilan yuboriladi va olingan file_id qolganlarга
    ishlatiladi (samarali).
    """
    from ..config import settings

    app = registry.get("moliya")
    if app is None:
        return
    base = _base_url()
    file_id = None
    for sid in settings.super_admin_id_list:
        try:
            if photo_bytes is not None:
                photo = file_id if file_id else photo_bytes
                msg = await app.bot.send_photo(
                    chat_id=sid, photo=photo, caption=text, reply_markup=reply_markup
                )
                if file_id is None and msg and msg.photo:
                    file_id = msg.photo[-1].file_id
            elif photo_rel_url and base:
                await app.bot.send_photo(
                    chat_id=sid,
                    photo=f"{base}{photo_rel_url}",
                    caption=text,
                    reply_markup=reply_markup,
                )
            else:
                await app.bot.send_message(
                    chat_id=sid, text=text, reply_markup=reply_markup
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Moliya xabari yuborilmadi (%s): %s", sid, e)


def notify_moliya_topup(
    sorov_id: int,
    ism: str | None,
    telegram_id: int | None,
    summa: float,
    ai_summa: float | None,
    ai_sana: str | None,
    ai_xulosa: str | None,
    chek_rel_url: str | None,
    usul_nomi: str | None = None,
    image_bytes: bytes | None = None,
) -> None:
    """Yangi to'ldirish so'rovi — chek + AI taklifи bilan (task_1, task_2)."""
    xulosa_emoji = {
        "mos_keladi": "✅ Mos keladi",
        "mos_kelmaydi": "⚠️ Mos kelmaydi",
        "aniq_emas": "❓ Aniq emas",
    }.get(ai_xulosa or "aniq_emas", "❓ Aniq emas")
    ai_qator = (
        f"🤖 Gemini o'qigani: {ai_summa:,.0f} som"
        + (f", {ai_sana}" if ai_sana else "")
        if ai_summa is not None
        else "🤖 Gemini: o'qib bo'lmadi"
    )
    text = (
        f"🔔 Yangi to'ldirish so'rovi #{sorov_id}\n\n"
        f"👤 Mijoz: {ism or 'nomalum'}"
        + (f", {telegram_id}" if telegram_id else "")
        + f"\n💰 Kiritgan summa: {summa:,.0f} som\n"
        + (f"💳 To'lov usuli: {usul_nomi}\n" if usul_nomi else "")
        + f"{ai_qator}\n"
        f"AI xulosasi: {xulosa_emoji}\n\n"
        "⚠️ Yakuniy qaror sizniki — chekni ko'rib tasdiqlang."
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mt_ok_{sorov_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"mt_no_{sorov_id}"),
            ]
        ]
    )
    _submit(
        _send_moliya(text, kb, photo_rel_url=chek_rel_url, photo_bytes=image_bytes)
    )


async def _send_menejer(text, reply_markup=None, photo_rel_url=None, photo_bytes=None):
    """Barcha menejerlarга Menejer Boti orqali xabar."""
    from ..config import settings

    app = registry.get("menejer")
    if app is None:
        return
    base = _base_url()
    file_id = None
    for mid in settings.menejer_id_list:
        try:
            if photo_bytes is not None:
                photo = file_id if file_id else photo_bytes
                msg = await app.bot.send_photo(
                    chat_id=mid, photo=photo, caption=text, reply_markup=reply_markup
                )
                if file_id is None and msg and msg.photo:
                    file_id = msg.photo[-1].file_id
            elif photo_rel_url and base:
                await app.bot.send_photo(
                    chat_id=mid, photo=f"{base}{photo_rel_url}",
                    caption=text, reply_markup=reply_markup,
                )
            else:
                await app.bot.send_message(
                    chat_id=mid, text=text, reply_markup=reply_markup
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("Menejer xabari yuborilmadi (%s): %s", mid, e)


def notify_moliya_dokon_tolov(
    sorov_id: int,
    ism: str | None,
    telegram_id: int | None,
    dokon_nomi: str,
    admin_tid: int,
    mahsulot_soni: int,
    summa: float,
    ai_summa: float | None,
    ai_xulosa: str | None,
    chek_rel_url: str | None,
    usul_nomi: str | None = None,
    image_bytes: bytes | None = None,
) -> None:
    """1-bosqich: do'kon ochish TO'LOVI — hisobchiга (Moliya) tekshirishга."""
    xulosa_emoji = {
        "mos_keladi": "✅ Mos keladi",
        "mos_kelmaydi": "⚠️ Mos kelmaydi",
        "aniq_emas": "❓ Aniq emas",
    }.get(ai_xulosa or "aniq_emas", "❓ Aniq emas")
    ai_qator = (
        f"🤖 Gemini: {ai_summa:,.0f} som" if ai_summa is not None else "🤖 Gemini: o'qilmadi"
    )
    text = (
        f"🏪 Do'kon ochish TO'LOVI #{sorov_id}\n\n"
        f"👤 So'rovchi: {ism or 'nomalum'}"
        + (f", {telegram_id}" if telegram_id else "")
        + f"\n🏷 Do'kon: {dokon_nomi}\n"
        f"📦 Mahsulot soni: {mahsulot_soni} ta\n"
        f"💰 To'lov: {summa:,.0f} som\n"
        + (f"💳 Usul: {usul_nomi}\n" if usul_nomi else "")
        + f"{ai_qator}\nAI xulosasi: {xulosa_emoji}\n\n"
        "To'lov to'g'ri bo'lsa — tasdiqlang. So'rov Menejerга uzatiladi."
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ To'lov tasdiqlash", callback_data=f"dt_ok_{sorov_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"dt_no_{sorov_id}"),
            ]
        ]
    )
    _submit(
        _send_moliya(text, kb, photo_rel_url=chek_rel_url, photo_bytes=image_bytes)
    )


def notify_menejer_dokon(
    sorov_id: int,
    ism: str | None,
    telegram_id: int | None,
    dokon_nomi: str,
    admin_tid: int,
    mahsulot_soni: int,
    summa: float,
    ai_summa: float | None,
    ai_xulosa: str | None,
    chek_rel_url: str | None,
    usul_nomi: str | None = None,
    image_bytes: bytes | None = None,
) -> None:
    """2-bosqich: hisobchi to'lovni tasdiqladi — Menejerга (biznes qarori)."""
    xulosa_emoji = {
        "mos_keladi": "✅ Mos keladi",
        "mos_kelmaydi": "⚠️ Mos kelmaydi",
        "aniq_emas": "❓ Aniq emas",
    }.get(ai_xulosa or "aniq_emas", "❓ Aniq emas")
    ai_qator = (
        f"🤖 Gemini: {ai_summa:,.0f} som" if ai_summa is not None else "🤖 Gemini: o'qilmadi"
    )
    text = (
        f"🏪 Do'kon ochish so'rovi #{sorov_id}\n"
        "💳 To'lov hisobchi tomonidan TASDIQLANDI ✅\n\n"
        f"👤 So'rovchi: {ism or 'nomalum'}"
        + (f", {telegram_id}" if telegram_id else "")
        + f"\n🏷 Do'kon nomi: {dokon_nomi}\n"
        f"🆔 Admin Telegram ID: {admin_tid}\n"
        f"📦 Mahsulot limiti: {mahsulot_soni} ta\n"
        f"💰 To'lov: {summa:,.0f} som\n\n"
        "Shu do'kon ochilsinmi? Tasdiqласангиз — do'kon ochiladi va "
        "so'rovchiga mahfiy kod + admin bot havolasi yuboriladi."
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"md_ok_{sorov_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"md_no_{sorov_id}"),
            ]
        ]
    )
    _submit(
        _send_menejer(text, kb, photo_rel_url=chek_rel_url, photo_bytes=image_bytes)
    )


def notify_moliya_withdraw(
    sorov_id: int, store_nomi: str, summa: float, karta: str
) -> None:
    """Yangi pul yechish so'rovi (task_2, task_5)."""
    text = (
        f"💸 Pul yechish so'rovi #{sorov_id}\n\n"
        f"🏪 Do'kon: {store_nomi}\n"
        f"💰 Summa: {summa:,.0f} som\n"
        f"💳 Karta: {karta}\n\n"
        "Real pulni o'tkazgach 'To'landi' deb belgilang."
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ To'landi deb belgilash", callback_data=f"mw_ok_{sorov_id}")]]
    )
    _submit(_send_moliya(text, kb))


def notify_moliya_refund(
    sorov_id: int,
    ism: str | None,
    telegram_id: int | None,
    summa: float,
    karta: str,
) -> None:
    """Yangi balans qaytarish so'rovi (task_2)."""
    text = (
        f"↩️ Balans qaytarish so'rovi #{sorov_id}\n\n"
        f"👤 Mijoz: {ism or 'nomalum'}"
        + (f", {telegram_id}" if telegram_id else "")
        + f"\n💰 Summa: {summa:,.0f} som\n"
        f"💳 Karta: {karta}"
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mr_ok_{sorov_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"mr_no_{sorov_id}"),
            ]
        ]
    )
    _submit(_send_moliya(text, kb))


def notify_customer(telegram_id: int | None, text: str, parse_mode=None) -> None:
    """Mijozga Savdo Boti orqali xabar (sync yoki async koddан)."""
    if not telegram_id:
        return
    _submit(_send_customer(telegram_id, text, parse_mode))


async def send_customer(telegram_id: int | None, text: str) -> None:
    """Async kontekstдан to'g'ridan-to'g'ri yuborish (bot handlerlari uchun)."""
    if not telegram_id:
        return
    try:
        await _send_customer(telegram_id, text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Mijozga xabar yuborilmadi: %s", e)
