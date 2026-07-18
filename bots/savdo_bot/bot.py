"""Savdo Boti — mijozlar uchun (phase 5).

Imkoniyatlar:
  * /start — referal havolani qayta ishlash (ref_<id>), Mini App tugmasi.
  * Oddiy matn — AI chat-yordamchi (/api/bot/chat orqali).
  * "Kontaktni ulashish" — telefonni tasdiqlash (rule 8, 2-bosqich).
  * /holat — buyurtmalar tarixi.
  * /sodiqlik — karta va referal havola.

Bu bot mijozga faqat KOD KIRITISH imkonini beradi (Mini App'da), kod YARATISH
emas (rule 4). Kod yaratish faqat Boshqaruv Botida.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram import (  # noqa: E402
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (  # noqa: E402
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from common import MINIAPP_URL, SAVDO_BOT_TOKEN, backend  # noqa: E402


def _main_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    if MINIAPP_URL:
        rows.append(
            [KeyboardButton("🛍 Do'kon (katalog)", web_app=WebAppInfo(url=MINIAPP_URL))]
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
                    await backend.bot_register_referral(user.id, referrer_id)
            except ValueError:
                pass

    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "ARZON'ga xush kelibsiz — bu yerda ko'plab do'konlarning mahsulotlari "
        "bitta katalogda.\n\n"
        "🛍 Katalogni ochish uchun quyidagi tugmadan foydalaning.\n"
        "💬 Yoki menga savolingizni yozing — mahsulot tanlashда yordam beraman.",
        reply_markup=_main_keyboard(),
    )


async def holat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    orders = await backend.bot_orders(update.effective_user.id)
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
    data = await backend.bot_loyalty(update.effective_user.id)
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
    ok = await backend.bot_confirm_phone(
        update.effective_user.id, c.phone_number, update.effective_user.first_name
    )
    msg = (
        "✅ Telefon raqamingiz tasdiqlandi! Endi buyurtma bera olasiz."
        if ok
        else "Telefonni tasdiqlab bo'lmadi, qaytadan urinib ko'ring."
    )
    await update.message.reply_text(msg, reply_markup=_main_keyboard())


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Oddiy matn — AI chat (phase 5.2)."""
    txt = update.message.text
    if txt == "📦 Buyurtmalarim":
        return await holat(update, context)
    if txt == "🎁 Sodiqlik":
        return await sodiqlik(update, context)

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    javob = await backend.bot_chat(update.effective_user.id, txt)
    await update.message.reply_text(javob)


def main() -> None:
    if not SAVDO_BOT_TOKEN:
        raise SystemExit("SAVDO_BOT_TOKEN sozlanmagan (.env).")
    app = Application.builder().token(SAVDO_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("holat", holat))
    app.add_handler(CommandHandler("sodiqlik", sodiqlik))
    app.add_handler(MessageHandler(filters.CONTACT, contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    print("Savdo Boti ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
