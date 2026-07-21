"""Moliya Boti — faqat super-admin (ACOM coin so'rovlarini tasdiqlaydi).

Menyu:
    🔔 To'ldirish so'rovlari    💸 Pul yechish so'rovlari
    ↩️ Qaytarish so'rovlari      📊 Umumiy hisobot
    💳 Platforma karta

Rule 2: yakuniy qaror HAR DOIM shu yerда super-admin tugma bosishи bilan
beriladi — AI xulosasidan qat'i nazar. Barcha summalar KGS (Qirg'iziston somi).
"""
from __future__ import annotations

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..config import settings
from .client import api

logger = logging.getLogger("arzon.moliya")

BTN_TOPUPS = "🔔 To'ldirish so'rovlari"
BTN_WITHDRAWS = "💸 Pul yechish so'rovlari"
BTN_REFUNDS = "↩️ Qaytarish so'rovlari"
BTN_REPORT = "📊 Umumiy hisobot"
BTN_CARD = "💳 Platforma karta"
BTN_HOME = "🏠 Bosh menyu"

# Conversation holatlari.
R_SABAB, C_KARTA, C_EGASI = range(3)


def _is_super(uid: int) -> bool:
    return uid in settings.super_admin_id_list


def menu_markup() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_TOPUPS), KeyboardButton(BTN_WITHDRAWS)],
            [KeyboardButton(BTN_REFUNDS), KeyboardButton(BTN_REPORT)],
            [KeyboardButton(BTN_CARD)],
        ],
        resize_keyboard=True,
    )


async def _guard(update: Update) -> bool:
    if not _is_super(update.effective_user.id):
        await update.effective_message.reply_text(
            "⛔️ Bu bot faqat super-admin (loyiha egasi) uchun."
        )
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.effective_message.reply_text(
        "💰 ARZON Moliya Boti\n\nACOM coin so'rovlarini boshqaring 👇",
        reply_markup=menu_markup(),
    )


# ---------------------------------------------------------------------------
# To'ldirish so'rovlari
# ---------------------------------------------------------------------------
def _topup_kb(sorov_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mt_ok_{sorov_id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"mt_no_{sorov_id}"),
            ]
        ]
    )


async def topups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    uid = update.effective_user.id
    rows = await api.moliya_topups(uid)
    if not rows:
        await update.message.reply_text("Kutilayotgan to'ldirish so'rovi yo'q. ✅")
        return
    xulosa_map = {
        "mos_keladi": "✅ Mos keladi",
        "mos_kelmaydi": "⚠️ Mos kelmaydi",
        "aniq_emas": "❓ Aniq emas",
    }
    for s in rows[:20]:
        ai_txt = (
            f"🤖 Gemini: {s['ai_summa']:,.0f} som"
            + (f", {s['ai_sana']}" if s.get("ai_sana") else "")
            if s.get("ai_summa") is not None
            else "🤖 Gemini: o'qilmadi"
        )
        text = (
            f"🔔 So'rov #{s['id']}\n"
            f"👤 {s.get('ism') or 'nomalum'}, {s.get('telegram_id')}\n"
            f"💰 Kiritgan: {s['summa']:,.0f} som\n"
            f"{ai_txt}\n"
            f"AI xulosasi: {xulosa_map.get(s.get('ai_xulosa'), '❓')}"
        )
        base = _base_url()
        if s.get("chek_rasm_url") and base:
            try:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=f"{base}{s['chek_rasm_url']}",
                    caption=text,
                    reply_markup=_topup_kb(s["id"]),
                )
                continue
            except Exception:  # noqa: BLE001
                pass
        await update.message.reply_text(text, reply_markup=_topup_kb(s["id"]))


async def topup_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("mt_ok_", ""))
    r = await api.moliya_topup_approve(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        yangi = r.json().get("yangi_balans")
        await _edit(query, f"✅ Tasdiqlandi. Mijoz balansi: {yangi:,.0f} ACOM")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Pul yechish so'rovlari
# ---------------------------------------------------------------------------
async def withdraws(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.moliya_withdraws(update.effective_user.id)
    if not rows:
        await update.message.reply_text("Kutilayotgan pul yechish so'rovi yo'q. ✅")
        return
    for s in rows[:20]:
        text = (
            f"💸 So'rov #{s['id']}\n"
            f"🏪 {s.get('store_nomi')}\n"
            f"💰 {s['summa']:,.0f} som\n"
            f"💳 {s['karta_raqami']}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ To'landi", callback_data=f"mw_ok_{s['id']}")]]
        )
        await update.message.reply_text(text, reply_markup=kb)


async def withdraw_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("mw_ok_", ""))
    r = await api.moliya_withdraw_paid(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        await _edit(query, "✅ To'landi deb belgilandi.")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Qaytarish so'rovlari
# ---------------------------------------------------------------------------
async def refunds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    rows = await api.moliya_refunds(update.effective_user.id)
    if not rows:
        await update.message.reply_text("Kutilayotgan qaytarish so'rovi yo'q. ✅")
        return
    for s in rows[:20]:
        text = (
            f"↩️ So'rov #{s['id']}\n"
            f"👤 {s.get('ism') or 'nomalum'}, {s.get('telegram_id')}\n"
            f"💰 {s['summa']:,.0f} som\n"
            f"💳 {s['karta_raqami']}"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"mr_ok_{s['id']}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"mr_no_{s['id']}"),
                ]
            ]
        )
        await update.message.reply_text(text, reply_markup=kb)


async def refund_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return
    await query.answer()
    sorov_id = int(query.data.replace("mr_ok_", ""))
    r = await api.moliya_refund_approve(update.effective_user.id, sorov_id)
    if r.status_code == 200:
        await _edit(query, "✅ Qaytarish tasdiqlandi.")
    else:
        await _edit(query, f"❌ Xatolik: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Rad etish (sabab bilan) — to'ldirish va qaytarish uchun umumiy conversation
# ---------------------------------------------------------------------------
async def reject_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not _is_super(update.effective_user.id):
        await query.answer("Faqat super-admin.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    data = query.data
    if data.startswith("mt_no_"):
        context.user_data["reject"] = ("topup", int(data.replace("mt_no_", "")))
    else:
        context.user_data["reject"] = ("refund", int(data.replace("mr_no_", "")))
    await _edit(query, "❌ Rad etish sababini yozing (mijozga yuboriladi):")
    return R_SABAB


async def reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    turi_id = context.user_data.pop("reject", None)
    if not turi_id:
        return ConversationHandler.END
    turi, sorov_id = turi_id
    sabab = update.message.text.strip()
    uid = update.effective_user.id
    if turi == "topup":
        r = await api.moliya_topup_reject(uid, sorov_id, sabab)
    else:
        r = await api.moliya_refund_reject(uid, sorov_id, sabab)
    msg = "✅ Rad etildi, mijozga xabar berildi." if r.status_code == 200 else f"❌ {r.text[:200]}"
    await update.message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Umumiy hisobot
# ---------------------------------------------------------------------------
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    from datetime import datetime

    d = await api.moliya_report(update.effective_user.id)
    if not d:
        await update.message.reply_text("Hisobot olinmadi.")
        return
    sana = datetime.now().strftime("%d.%m.%Y")
    text = (
        f"📊 Umumiy holat — {sana}\n\n"
        f"💰 Jami mijozlar balansi: {d['jami_mijozlar_balansi']:,.0f} som\n"
        f"🏪 Jami adminlar kutilayotgan balansi: {d['jami_adminlar_balansi']:,.0f} som\n"
        f"🏦 Platforma hisobida (real pul) bo'lishi kerak: "
        f"~{d['platforma_hisobida']:,.0f} som\n\n"
        f"Bugungi harakatlar:\n"
        f"+ To'ldirishlar: {d['bugun_toldirish_summa']:,.0f} som "
        f"({d['bugun_toldirish_soni']} ta so'rov)\n"
        f"- Xaridlar: {d['bugun_xarid_summa']:,.0f} som "
        f"({d['bugun_xarid_soni']} ta buyurtma)\n"
        f"- Pul yechishlar: {d['bugun_yechish_summa']:,.0f} som "
        f"({d['bugun_yechish_soni']} ta so'rov)\n"
        f"- Komissiya yig'ildi: {d['bugun_komissiya']:,.0f} som"
    )
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Platforma karta sozlash
# ---------------------------------------------------------------------------
async def card_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _guard(update):
        return ConversationHandler.END
    joriy = await api.moliya_get_platforma(update.effective_user.id)
    joriy_txt = (
        f"\n\nJoriy: {joriy['karta_raqami']} — {joriy['hisob_egasi']}"
        if joriy
        else ""
    )
    await update.message.reply_text(
        "💳 Platforma karta raqamini kiriting (mijozlar shunga pul o'tkazadi):"
        + joriy_txt,
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_HOME)]], resize_keyboard=True
        ),
    )
    return C_KARTA


async def card_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _to_menu(update)
    context.user_data["p_karta"] = update.message.text.strip()
    await update.message.reply_text("Hisob egasining to'liq ismini kiriting:")
    return C_EGASI


async def card_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _to_menu(update)
    egasi = update.message.text.strip()
    karta = context.user_data.pop("p_karta", "")
    r = await api.moliya_set_platforma(update.effective_user.id, karta, egasi)
    msg = "✅ Platforma karta saqlandi." if r.status_code == 200 else f"❌ {r.text[:200]}"
    await update.message.reply_text(msg, reply_markup=menu_markup())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------
def _base_url() -> str:
    import os

    return (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")


async def _edit(query, text: str) -> None:
    try:
        if query.message and query.message.photo:
            await query.edit_message_caption(caption=text)
        else:
            await query.edit_message_text(text)
    except Exception:  # noqa: BLE001
        await query.message.reply_text(text)


async def _to_menu(update: Update) -> int:
    await update.message.reply_text("Bosh menyu 👇", reply_markup=menu_markup())
    return ConversationHandler.END


def build_application(token: str) -> Application:
    app = Application.builder().token(token).updater(None).build()

    TXT = filters.TEXT & ~filters.COMMAND

    # Rad etish sababi (to'ldirish/qaytarish) — callbackдан kiradi.
    reject_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(reject_start, pattern="^mt_no_"),
            CallbackQueryHandler(reject_start, pattern="^mr_no_"),
        ],
        states={R_SABAB: [MessageHandler(TXT, reject_reason)]},
        fallbacks=[CommandHandler("start", start)],
        name="moliya_reject",
        persistent=False,
    )
    # Platforma karta sozlash.
    card_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{BTN_CARD}$"), card_start),
        ],
        states={
            C_KARTA: [MessageHandler(TXT, card_number)],
            C_EGASI: [MessageHandler(TXT, card_owner)],
        },
        fallbacks=[CommandHandler("start", start)],
        name="moliya_card",
        persistent=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_HOME}$"), start))
    app.add_handler(reject_conv)
    app.add_handler(card_conv)
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_TOPUPS}$"), topups))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_WITHDRAWS}$"), withdraws))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_REFUNDS}$"), refunds))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_REPORT}$"), report))

    # Inline callbacklar (menyu ro'yxati va push xabarlaridан).
    app.add_handler(CallbackQueryHandler(topup_approve, pattern="^mt_ok_"))
    app.add_handler(CallbackQueryHandler(withdraw_paid, pattern="^mw_ok_"))
    app.add_handler(CallbackQueryHandler(refund_approve, pattern="^mr_ok_"))
    return app
