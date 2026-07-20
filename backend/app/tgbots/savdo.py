"""Savdo Boti — onboarding + tugmali menyu (yangi spec).

Onboarding tartibi (rule 1, hech qadam o'tkazilmaydi):
  1. Kanalga a'zolik (majburiy, NEWS_CHANNEL_ID) — getChatMember bilan
  2. Telefon raqamini ulashish (majburiy, request_contact)
  3. Bosh ekran taqdimoti (WELCOME_TEXT + "Do'konga kirish")
  4. To'liq Bosh menyu (Katalog, Buyurtmalarim, Sodiqlik, Sevimlilar, ...)

1 va 2 faqat birinchi marta (rule 2). Mijoz kanaldan chiqsa — istalgan
funksiyaда qayta 1-qadamга qaytariladi (rule 3).
"""
from __future__ import annotations

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..config import settings
from .client import api

logger = logging.getLogger("arzon.savdo")

# --- Bosh ekran taqdimoti (osongina tahrirlanadigan matn) ---
WELCOME_TEXT = (
    "Sifatli mahsulotlar — hamyonbop narxlarda!\n\n"
    "🛍 Bizda siz kundalik ehtiyoj uchun kerak bo'lgan mahsulotlarni qulay "
    "narxlarda topasiz.\n\n"
    "✨ Siz uchun:\n"
    "• 🛒 Hamyonbop narxlar\n"
    "• ✅ Sifat kafolati\n"
    "• 🚚 Tezkor yetkazib berish\n"
    "• 📦 Doimiy yangilanib boradigan mahsulotlar\n"
    "• 💬 Buyurtma: Telegram va Instagram orqali\n\n"
    "📢 Kanalimizni kuzatib boring va eng foydali chegirmalarni "
    "birinchilardan bo'lib qo'lga kiriting!\n\n"
    "ARZON ONLINE SAVDO\n"
    "Arzon narx, sifatli tanlov!"
)
WELCOME_SHORT = "🛍 ARZON ONLINE SAVDO — Xush kelibsiz!"

# --- Menyu tugmalari ---
BTN_CATALOG = "🛍 Katalog"
BTN_ORDERS = "📦 Buyurtmalarim"
BTN_LOYALTY = "🎁 Sodiqlik kartam"
BTN_FAV = "❤️ Sevimlilar"
BTN_HELP = "❓ Yordam"
BTN_ASK = "💬 Savol berish"


def main_menu(miniapp_url: str) -> ReplyKeyboardMarkup:
    catalog_btn = (
        KeyboardButton(BTN_CATALOG, web_app=WebAppInfo(url=miniapp_url))
        if miniapp_url
        else KeyboardButton(BTN_CATALOG)
    )
    rows = [
        [catalog_btn, KeyboardButton(BTN_ORDERS)],
        [KeyboardButton(BTN_LOYALTY), KeyboardButton(BTN_FAV)],
        [KeyboardButton(BTN_HELP), KeyboardButton(BTN_ASK)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ---------------------------------------------------------------------------
# Kanalga a'zolik tekshiruvi (task_1, rule 3)
# ---------------------------------------------------------------------------
async def is_channel_member(bot, user_id: int) -> bool:
    """Mijoz rasmiy kanalга a'zomi? NEWS_CHANNEL_ID bo'sh bo'lса — True (o'chiq).

    Xatolik (bot kanalда admin emas va h.k.) bo'lса — fail-open (True) + log,
    aks holda noto'g'ri sozlash barcha mijozlarni bloklab qo'yardi.
    """
    channel = settings.news_channel_id.strip()
    if not channel:
        return True
    chat_id = int(channel) if channel.lstrip("-").isdigit() else channel
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ("member", "administrator", "creator", "owner")
    except Exception as e:  # noqa: BLE001
        logger.warning("Kanal a'zoligini tekshirib bo'lmadi: %s", e)
        return True  # fail-open


def _join_markup() -> InlineKeyboardMarkup:
    rows = []
    if settings.news_channel_link.strip():
        rows.append(
            [InlineKeyboardButton("🔗 Kanalga o'tish", url=settings.news_channel_link)]
        )
    rows.append(
        [InlineKeyboardButton("✅ Men qo'shildim, tekshirish", callback_data="join_check")]
    )
    return InlineKeyboardMarkup(rows)


async def _ask_join(update: Update) -> None:
    await update.effective_message.reply_text(
        "📢 Botdan foydalanish uchun avval rasmiy kanalimizga qo'shiling:",
        reply_markup=_join_markup(),
    )


async def _ask_phone(update: Update) -> None:
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
    )
    await update.effective_message.reply_text(
        "📱 Davom etish uchun telefon raqamingizni ulashing:",
        reply_markup=kb,
    )


async def _show_welcome(update: Update, short: bool = False) -> None:
    text = WELCOME_SHORT if short else WELCOME_TEXT
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒 Do'konga kirish", callback_data="enter_shop")]]
    )
    await update.effective_message.reply_text(text, reply_markup=kb)


async def _gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Onboarding "eshigi": a'zolik + telefonни tekshiradi.

    True — mijoz to'liq o'tган, davom etsa bo'ladi. False — kerakli qadam
    ko'rsatildi (join yoki phone), chaqiruvchi to'xtashi kerak.
    """
    uid = update.effective_user.id
    if not await is_channel_member(context.bot, uid):
        await _ask_join(update)
        return False
    me = await api.me(uid)
    if not me.get("tel_tasdiqlangan"):
        await _ask_phone(update)
        return False
    return True


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # Referal: /start ref_<telegram_id>
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                ref = int(arg[4:])
                if ref != user.id:
                    await api.register_referral(user.id, ref)
            except ValueError:
                pass

    # 1-qadam: kanal.
    if not await is_channel_member(context.bot, user.id):
        await _ask_join(update)
        return
    # 2-qadam: telefon.
    me = await api.me(user.id)
    if not me.get("tel_tasdiqlangan"):
        await _ask_phone(update)
        return
    # 3-qadam: taqdimot (qaytган mijozга qisqasi).
    await _show_welcome(update, short=bool(me.get("tel_tasdiqlangan")))


async def join_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if await is_channel_member(context.bot, update.effective_user.id):
        await query.answer("Rahmat! ✅")
        await query.edit_message_text("✅ A'zolik tasdiqlandi.")
        # Keyingi qadam: telefon yoki taqdimot.
        me = await api.me(update.effective_user.id)
        if not me.get("tel_tasdiqlangan"):
            await _ask_phone(update)
        else:
            await _show_welcome(update)
    else:
        await query.answer("Hali a'zo bo'lmadingiz.", show_alert=True)
        await query.message.reply_text(
            "Hali a'zo bo'lmadingiz, iltimos kanalga qo'shiling.",
            reply_markup=_join_markup(),
        )


async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telefonni ulashish (task_2, rule 8 2-bosqich)."""
    # Onboardingда telefon so'ralganда kanal allaqachon tasdiqlangan.
    c = update.message.contact
    ok = await api.confirm_phone(
        update.effective_user.id, c.phone_number, update.effective_user.first_name
    )
    if ok:
        await update.message.reply_text("✅ Telefon tasdiqlandi!")
        await _show_welcome(update)
    else:
        await update.message.reply_text(
            "Telefonni tasdiqlab bo'lmadi, qayta urinib ko'ring."
        )


async def enter_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """"Do'konga kirish" — to'liq bosh menyuni ochadi (task_3)."""
    query = update.callback_query
    await query.answer()
    if not await _gate(update, context):
        return
    await query.message.reply_text(
        "Bosh menyu 👇 Kerakli bo'limни tanlang:",
        reply_markup=main_menu(context.bot_data.get("miniapp_url", "")),
    )


# ---------------------------------------------------------------------------
# Menyu tugmalari (har birida onboarding eshigi tekshiriladi — rule 3)
# ---------------------------------------------------------------------------
async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _gate(update, context):
        return
    rows = await api.my_orders(update.effective_user.id)
    if not rows:
        await update.message.reply_text("Sizда hali buyurtmalar yo'q.")
        return
    lines = ["📦 *Buyurtmalaringiz:*\n"]
    for o in rows[:10]:
        yetk = (
            "🚚 Kuryer" if o.get("yetkazish_turi") == "kuryer" else "🏬 Punktdan"
        )
        lines.append(
            f"• `{o['kod']}` — {o['jami_narx']:,.0f} som — _{o['holat']}_ — {yetk}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def loyalty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _gate(update, context):
        return
    data = await api.loyalty(
        update.effective_user.id, context.bot.username or ""
    )
    if not data:
        await update.message.reply_text("Ma'lumot olinmadi.")
        return
    karta = data.get("karta_turi") or "yo'q"
    qolgan = data.get("keyingi_karta_uchun_qolgan")
    qolgan_txt = (
        f"\nKeyingi karta uchun yana {qolgan} ta xarid kerak." if qolgan else ""
    )
    await update.message.reply_text(
        f"🎁 *Sodiqlik kartam*\n\n"
        f"Umumiy xaridlar: *{data.get('umumiy_xaridlar', 0)}*\n"
        f"Karta: *{karta}*{qolgan_txt}\n\n"
        f"👥 Referal havolangiz:\n{data.get('referal_havola', '')}\n"
        f"Taklif qilganlaringiz: {data.get('taklif_qilganlar', 0)}",
        parse_mode="Markdown",
    )


async def favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _gate(update, context):
        return
    await update.message.reply_text(
        "❤️ Sevimlilar bo'limi tez orada qo'shiladi.\n"
        "Hozircha katalogда yoqqan mahsulotni savatga qo'shib qo'ying. 🙂"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _gate(update, context):
        return
    await update.message.reply_text(
        "❓ *Yordam*\n\n"
        "🛍 Katalog — mahsulotlarni ko'rish va buyurtma berish\n"
        "📦 Buyurtmalarim — buyurtmalaringiz holati\n"
        "🎁 Sodiqlik kartam — chegirma va referal\n"
        "💬 Savol berish — menга yozing, javob beraman\n\n"
        "Savolingiz bo'lsa — shu yerга yozing!",
        parse_mode="Markdown",
    )


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _gate(update, context):
        return
    await update.message.reply_text(
        "💬 Savolingizni yozing — mahsulot tanlashда yordam beraman."
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Oddiy matn — AI chat (onboarding eshigidan keyin)."""
    if not await _gate(update, context):
        return
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    javob = await api.chat(update.effective_user.id, update.message.text)
    await update.message.reply_text(javob)


def build_application(token: str, miniapp_url: str) -> Application:
    app = Application.builder().token(token).updater(None).build()
    app.bot_data["miniapp_url"] = miniapp_url

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("holat", orders))
    app.add_handler(CallbackQueryHandler(join_check, pattern="^join_check$"))
    app.add_handler(CallbackQueryHandler(enter_shop, pattern="^enter_shop$"))
    app.add_handler(MessageHandler(filters.CONTACT, contact))

    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_ORDERS}$"), orders))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_LOYALTY}$"), loyalty))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_FAV}$"), favorites))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_HELP}$"), help_cmd))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_ASK}$"), ask))
    # Katalog tugmasi WebApp bo'lса Telegram o'zi ochadi; matn kelса — eslatma.
    app.add_handler(
        MessageHandler(filters.Regex(f"^{BTN_CATALOG}$"), _catalog_hint)
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)
    )
    return app


async def _catalog_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _gate(update, context):
        return
    url = context.bot_data.get("miniapp_url", "")
    if url:
        await update.message.reply_text(
            "🛍 Katalogni ochish uchun tugmani bosing 👆 (Mini App)."
        )
    else:
        await update.message.reply_text("Katalog hozircha sozlanmoqda.")
