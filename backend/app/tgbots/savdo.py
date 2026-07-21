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
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..config import settings
from . import confirm
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
BTN_BALANCE = "💰 Balansim"
BTN_FAV = "❤️ Sevimlilar"
BTN_HELP = "❓ Yordam"
BTN_ASK = "💬 Savol berish"
BTN_HOME = "🏠 Bosh menyu"

# ACOM coin balans oqimi holatlari.
(TOPUP_SUMMA, TOPUP_CODE, TOPUP_CHEK, REFUND_SUMMA, REFUND_KARTA, REFUND_CODE) = range(6)


def main_menu(miniapp_url: str) -> ReplyKeyboardMarkup:
    catalog_btn = (
        KeyboardButton(BTN_CATALOG, web_app=WebAppInfo(url=miniapp_url))
        if miniapp_url
        else KeyboardButton(BTN_CATALOG)
    )
    rows = [
        [catalog_btn, KeyboardButton(BTN_ORDERS)],
        [KeyboardButton(BTN_BALANCE), KeyboardButton(BTN_LOYALTY)],
        [KeyboardButton(BTN_FAV), KeyboardButton(BTN_HELP)],
        [KeyboardButton(BTN_ASK)],
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


# ---------------------------------------------------------------------------
# 💰 Balansim — ACOM coin (1 ACOM = 1 som, KGS)
# ---------------------------------------------------------------------------
def _menu_kb(context) -> ReplyKeyboardMarkup:
    return main_menu(context.bot_data.get("miniapp_url", ""))


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _gate(update, context):
        return
    data = await api.coin_balance(update.effective_user.id)
    bal = data.get("coin_balans", 0) or 0
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Hisobni to'ldirish", callback_data="bal_topup")],
            [InlineKeyboardButton("↩️ Balansni qaytarish", callback_data="bal_refund")],
        ]
    )
    await update.message.reply_text(
        f"🪙 ACOM balansingiz: <b>{bal:,.0f}</b> ACOM ({bal:,.0f} som)\n\n"
        "1 ACOM = 1 som. Xaridlar shu balansdan amalga oshadi.",
        reply_markup=kb,
        parse_mode="HTML",
    )


def _home_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_HOME)]], resize_keyboard=True)


# --- To'ldirish oqimi (task_1 + task_8) ---
async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await _gate(update, context):
        return ConversationHandler.END
    await query.message.reply_text(
        "➕ To'ldirmoqchi bo'lgan summani <b>somda (KGS)</b> kiriting (masalan 10000):",
        reply_markup=_home_kb(),
        parse_mode="HTML",
    )
    return TOPUP_SUMMA


async def topup_summa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    try:
        summa = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        assert summa > 0
    except (ValueError, AssertionError):
        await update.message.reply_text("Iltimos, musbat raqam kiriting (masalan 10000):")
        return TOPUP_SUMMA
    limit = settings.bir_martalik_toldirish_limit
    if summa > limit:
        await update.message.reply_text(
            f"Bir martalik to'ldirish chegarasi: {limit:,.0f} som. "
            "Kichikroq summa kiriting:"
        )
        return TOPUP_SUMMA
    context.user_data["topup_summa"] = summa
    kod = confirm.issue_code(context.user_data)
    await update.message.reply_text(confirm.prompt_text(kod), parse_mode="HTML")
    return TOPUP_CODE


async def topup_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    natija = confirm.check_code(context.user_data, update.message.text)
    if natija == "wrong":
        await update.message.reply_text("Kod noto'g'ri, qaytadan urinib ko'ring:")
        return TOPUP_CODE
    if natija == "expired":
        await update.message.reply_text(
            "Kodning muddati tugadi. To'ldirishni boshidan boshlang (💰 Balansim).",
            reply_markup=_menu_kb(context),
        )
        return ConversationHandler.END
    if natija in ("toomany", "yoq"):
        await update.message.reply_text(
            "Juda ko'p noto'g'ri urinish. So'rov bekor qilindi.",
            reply_markup=_menu_kb(context),
        )
        return ConversationHandler.END
    # ok — platforma karta ko'rsatiladi.
    summa = context.user_data.get("topup_summa", 0)
    data = await api.coin_balance(update.effective_user.id)
    hisob = data.get("platforma_hisob")
    if hisob:
        karta_txt = (
            f"💳 <b>{hisob['karta_raqami']}</b> — {hisob['hisob_egasi']} nomiga\n"
            f"<b>{summa:,.0f} som</b> o'tkazing va chekni (rasm) yuboring."
        )
    else:
        karta_txt = (
            "⚠️ Platforma karta hali sozlanmagan. Iltimos, administrator bilan "
            "bog'laning. Chekni baribir yuborishingiz mumkin."
        )
    await update.message.reply_text(karta_txt, parse_mode="HTML", reply_markup=_home_kb())
    await update.message.reply_text("📸 To'lov chekini (rasm) yuboring:")
    return TOPUP_CHEK


async def topup_chek(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text and update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    if not update.message.photo:
        await update.message.reply_text("Iltimos, chek RASMINI yuboring:")
        return TOPUP_CHEK

    summa = context.user_data.pop("topup_summa", 0)
    photo = update.message.photo[-1]
    file_id = photo.file_id
    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    # Chekni yuklab, Gemini bilan tahlil qilamiz (rule 2 — faqat taklif).
    ai_summa = ai_sana = ai_xulosa = None
    try:
        import asyncio

        from .. import ai as ai_module

        tg_file = await photo.get_file()
        raw = bytes(await tg_file.download_as_bytearray())
        loop = asyncio.get_running_loop()
        natija = await loop.run_in_executor(
            None, ai_module.analyze_receipt, raw, "image/jpeg", summa
        )
        ai_summa = natija.get("summa")
        ai_sana = natija.get("sana")
        ai_xulosa = natija.get("xulosa")
    except Exception as e:  # noqa: BLE001
        logger.warning("Chek tahlilида xato: %s", e)

    r = await api.coin_topup(
        update.effective_user.id,
        summa,
        chek_rasm_url=f"/media/{file_id}",
        ai_summa=ai_summa,
        ai_sana=ai_sana,
        ai_xulosa=ai_xulosa,
    )
    confirm.clear(context.user_data)
    if r.status_code == 200:
        await update.message.reply_text(
            "✅ So'rovingiz qabul qilindi! Super-admin chekni tekshirib "
            "tasdiqlaydi. Tasdiqlangач balansingizga coin qo'shiladi.",
            reply_markup=_menu_kb(context),
        )
    else:
        try:
            xato = r.json().get("detail", "Xatolik")
        except Exception:  # noqa: BLE001
            xato = "Xatolik"
        await update.message.reply_text(f"❌ {xato}", reply_markup=_menu_kb(context))
    return ConversationHandler.END


# --- Qaytarish oqimi (task_8) ---
async def refund_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await _gate(update, context):
        return ConversationHandler.END
    data = await api.coin_balance(update.effective_user.id)
    bal = data.get("coin_balans", 0) or 0
    await query.message.reply_text(
        f"↩️ Joriy balans: {bal:,.0f} som.\n"
        "Qaytarib olmoqchi bo'lgan summani kiriting:",
        reply_markup=_home_kb(),
    )
    return REFUND_SUMMA


async def refund_summa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    try:
        summa = float(update.message.text.strip().replace(" ", "").replace(",", ""))
        assert summa > 0
    except (ValueError, AssertionError):
        await update.message.reply_text("Iltimos, musbat raqam kiriting:")
        return REFUND_SUMMA
    data = await api.coin_balance(update.effective_user.id)
    bal = data.get("coin_balans", 0) or 0
    if summa > bal:
        await update.message.reply_text(
            f"Balansingiz yetarli emas (joriy: {bal:,.0f} som). Kichikroq summa kiriting:"
        )
        return REFUND_SUMMA
    context.user_data["refund_summa"] = summa
    await update.message.reply_text("💳 Pul qaytariladigan karta raqamini kiriting:")
    return REFUND_KARTA


async def refund_karta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    context.user_data["refund_karta"] = update.message.text.strip()
    kod = confirm.issue_code(context.user_data)
    await update.message.reply_text(confirm.prompt_text(kod), parse_mode="HTML")
    return REFUND_CODE


async def refund_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    natija = confirm.check_code(context.user_data, update.message.text)
    if natija == "wrong":
        await update.message.reply_text("Kod noto'g'ri, qaytadan urinib ko'ring:")
        return REFUND_CODE
    if natija in ("expired", "toomany", "yoq"):
        await update.message.reply_text(
            "So'rov bekor qilindi (kod xato yoki muddati o'tdi). Qaytadan urinib ko'ring.",
            reply_markup=_menu_kb(context),
        )
        return ConversationHandler.END
    summa = context.user_data.pop("refund_summa", 0)
    karta = context.user_data.pop("refund_karta", "")
    r = await api.coin_refund(update.effective_user.id, summa, karta)
    if r.status_code == 200:
        await update.message.reply_text(
            "✅ Qaytarish so'rovingiz yuborildi! Super-admin tasdiqlagach "
            "kartangizga o'tkaziladi.",
            reply_markup=_menu_kb(context),
        )
    else:
        try:
            xato = r.json().get("detail", "Xatolik")
        except Exception:  # noqa: BLE001
            xato = "Xatolik"
        await update.message.reply_text(f"❌ {xato}", reply_markup=_menu_kb(context))
    return ConversationHandler.END


async def _cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    confirm.clear(context.user_data)
    for k in ("topup_summa", "refund_summa", "refund_karta"):
        context.user_data.pop(k, None)
    await update.message.reply_text("Bosh menyu 👇", reply_markup=_menu_kb(context))
    return ConversationHandler.END


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

    # 💰 Balansim — coin balansi va to'ldirish/qaytarish oqimlari (ACOM coin).
    TXT = filters.TEXT & ~filters.COMMAND
    balance_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(topup_start, pattern="^bal_topup$"),
            CallbackQueryHandler(refund_start, pattern="^bal_refund$"),
        ],
        states={
            TOPUP_SUMMA: [MessageHandler(TXT, topup_summa)],
            TOPUP_CODE: [MessageHandler(TXT, topup_code)],
            TOPUP_CHEK: [
                MessageHandler(filters.PHOTO, topup_chek),
                MessageHandler(TXT, topup_chek),
            ],
            REFUND_SUMMA: [MessageHandler(TXT, refund_summa)],
            REFUND_KARTA: [MessageHandler(TXT, refund_karta)],
            REFUND_CODE: [MessageHandler(TXT, refund_code)],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(f"^{BTN_HOME}$"), _cancel_to_menu),
        ],
        name="balance_flow",
        persistent=False,
    )
    app.add_handler(balance_conv)
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_BALANCE}$"), balance))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_HOME}$"), start))

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
