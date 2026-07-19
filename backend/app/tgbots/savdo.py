"""Savdo Boti handlerlari — webhook rejimi (mijozlar uchun, phase 5).

bots/savdo_bot/bot.py bilan bir xil mantiq, lekin bulutда (backend ichida)
ishlaydi va API'ни localhost orqali chaqiradi.
"""
from __future__ import annotations

from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .client import api


def _main_keyboard(miniapp_url: str) -> ReplyKeyboardMarkup:
    rows = []
    if miniapp_url:
        rows.append(
            [KeyboardButton("🛍 Do'kon (katalog)", web_app=WebAppInfo(url=miniapp_url))]
        )
    rows.append([KeyboardButton("📦 Buyurtmalarim"), KeyboardButton("🎁 Sodiqlik")])
    rows.append([KeyboardButton("📱 Kontaktni ulashish", request_contact=True)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # Referal: /start ref_<telegram_id> (phase 4.4).
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referrer_id = int(arg[4:])
                if referrer_id != user.id:
                    await api.register_referral(user.id, referrer_id)
            except ValueError:
                pass

    miniapp_url = context.bot_data.get("miniapp_url", "")
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "ARZON'ga xush kelibsiz — bu yerda ko'plab do'konlarning mahsulotlari "
        "bitta katalogda.\n\n"
        "🛍 Katalogni ochish uchun quyidagi tugmadan foydalaning.\n"
        "💬 Yoki menga savolingizni yozing — mahsulot tanlashда yordam beraman.",
        reply_markup=_main_keyboard(miniapp_url),
    )


async def holat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    orders = await api.my_orders(update.effective_user.id)
    if not orders:
        await update.message.reply_text("Sizда hali buyurtmalar yo'q.")
        return
    lines = ["📦 *Buyurtmalaringiz:*\n"]
    for o in orders[:10]:
        lines.append(
            f"• Kod: `{o['kod']}` — {o['jami_narx']:,.0f} so'm — _{o['holat']}_"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def sodiqlik(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = await api.loyalty(
        update.effective_user.id, context.bot.username or ""
    )
    if not data:
        await update.message.reply_text("Ma'lumot olinmadi.")
        return
    karta = data.get("karta_turi") or "yo'q"
    qolgan = data.get("keyingi_karta_uchun_qolgan")
    qolgan_txt = (
        f"\nKeyingi karta uchun yana {qolgan} ta xarid kerak."
        if qolgan
        else ""
    )
    await update.message.reply_text(
        f"🎁 *Sodiqlik dasturi*\n\n"
        f"Umumiy xaridlar: *{data.get('umumiy_xaridlar', 0)}*\n"
        f"Karta: *{karta}*{qolgan_txt}\n\n"
        f"👥 Do'stlaringizni taklif qiling:\n{data.get('referal_havola', '')}\n"
        f"Taklif qilganlaringiz: {data.get('taklif_qilganlar', 0)}",
        parse_mode="Markdown",
    )


async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kontaktni ulashish — telefonni tasdiqlash (rule 8, 2-bosqich)."""
    c = update.message.contact
    ok = await api.confirm_phone(
        update.effective_user.id, c.phone_number, update.effective_user.first_name
    )
    msg = (
        "✅ Telefon raqamingiz tasdiqlandi! Endi buyurtma bera olasiz."
        if ok
        else "Telefonni tasdiqlab bo'lmadi, qaytadan urinib ko'ring."
    )
    miniapp_url = context.bot_data.get("miniapp_url", "")
    await update.message.reply_text(
        msg, reply_markup=_main_keyboard(miniapp_url)
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Oddiy matn — AI chat (phase 5.2)."""
    txt = update.message.text
    if txt == "📦 Buyurtmalarim":
        return await holat(update, context)
    if txt == "🎁 Sodiqlik":
        return await sodiqlik(update, context)

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    javob = await api.chat(update.effective_user.id, txt)
    await update.message.reply_text(javob)


def build_application(token: str, miniapp_url: str) -> Application:
    app = Application.builder().token(token).updater(None).build()
    app.bot_data["miniapp_url"] = miniapp_url
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("holat", holat))
    app.add_handler(CommandHandler("sodiqlik", sodiqlik))
    app.add_handler(MessageHandler(filters.CONTACT, contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    return app
