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

import html as _html
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
BTN_ORDERS = "📦 Buyurtmalarim"
BTN_LOYALTY = "👥 Do'stlarni taklif qilish"
BTN_BALANCE = "💰 Balansim"
BTN_DOKON = "🏪 Do'kon ochish"
BTN_FAV = "❤️ Sevimlilar"
BTN_HELP = "❓ Yordam"
BTN_ASK = "💬 Savol berish"
BTN_HOME = "🏠 Bosh menyu"

# ACOM coin balans + do'kon ochish oqimi holatlari.
(
    TOPUP_SUMMA, TOPUP_METHOD, TOPUP_CODE, TOPUP_CHEK,
    REFUND_SUMMA, REFUND_KARTA, REFUND_CODE,
    D_NOMI, D_ADMIN_ID, D_SONI, D_METHOD, D_CODE, D_CHEK,
) = range(13)

# To'lov usuli turlari uchun emoji.
_USUL_EMOJI = {"karta": "💳", "telefon": "📱", "qr_kod": "🔳", "crypto": "₿"}


def _base_url() -> str:
    import os

    return (
        os.getenv("WEBHOOK_BASE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")


def _usul_detail(usul: dict, summa: float) -> str:
    """Tanlangan to'lov usuli bo'yicha to'lov ko'rsatmasi matni (task_1)."""
    turi = usul.get("turi")
    nomi = usul.get("nomi", "")
    qiymat = usul.get("qiymat") or ""
    egasi = usul.get("egasi") or ""
    izoh = usul.get("izoh") or ""
    if turi == "karta":
        return (
            f"💳 <b>{qiymat}</b> — {egasi} nomiga\n"
            f"<b>{summa:,.0f} som</b> o'tkazing va chekni (rasm) yuboring."
        )
    if turi == "telefon":
        return (
            f"📱 <b>{qiymat}</b> raqamiga {nomi} orqali\n"
            f"<b>{summa:,.0f} som</b> o'tkazing va chekni (rasm) yuboring."
        )
    if turi == "qr_kod":
        return (
            f"🔳 Yuqoridagi QR kodni ({nomi}) skanerlab,\n"
            f"<b>{summa:,.0f} som</b> o'tkazing va chekni (rasm) yuboring."
        )
    if turi == "crypto":
        base = (
            f"₿ <b>{qiymat}</b> manziliga\n"
            f"<b>{summa:,.0f} som</b>ga teng miqdorda o'tkazing."
        )
        if izoh:
            base += f"\n⚠️ {izoh}"
        base += "\nSo'ng chekni (skrinshot) yuboring."
        return base
    return f"<b>{summa:,.0f} som</b> o'tkazing va chekni yuboring."


def main_menu(miniapp_url: str = "") -> InlineKeyboardMarkup:
    # Inline menyu (Menyu_Inline_Prompt) — tugmalar xabarга biriktiriladi,
    # doimiy pastki klaviatura emas. Do'konga kirish pastdagi ko'k menyu
    # tugmasi (BotFather MenuButtonWebApp) orqali.
    rows = [
        [InlineKeyboardButton(BTN_ORDERS, callback_data="m:orders"),
         InlineKeyboardButton(BTN_BALANCE, callback_data="m:balance")],
        [InlineKeyboardButton(BTN_LOYALTY, callback_data="m:loyalty"),
         InlineKeyboardButton(BTN_FAV, callback_data="m:fav")],
        [InlineKeyboardButton(BTN_DOKON, callback_data="m:dokon")],
        [InlineKeyboardButton(BTN_HELP, callback_data="m:help"),
         InlineKeyboardButton(BTN_ASK, callback_data="m:ask")],
    ]
    return InlineKeyboardMarkup(rows)


def back_home() -> InlineKeyboardMarkup:
    """Har natijadan keyin asosiy menyuга qaytish tugmasi (Menyu_Inline_Prompt)."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Bosh menyu", callback_data="m:home")]]
    )


# ---------------------------------------------------------------------------
# Kanalga a'zolik tekshiruvi (task_1, rule 3)
# ---------------------------------------------------------------------------
async def is_channel_member(bot, user_id: int) -> bool:
    """Mijoz rasmiy kanalга a'zomi? NEWS_CHANNEL_ID bo'sh bo'lса — True (o'chiq).

    Tekshirib bo'lmasа (masalan bot kanalда admin emas): standart holatда
    fail-open (True) — noto'g'ri sozlash barcha mijozlarni bloklab qo'ymasin.
    NEWS_CHANNEL_STRICT=true bo'lса — fail-closed (False), obuna qat'iy majburiy.
    """
    channel = settings.news_channel_id.strip()
    if not channel:
        return True
    chat_id = int(channel) if channel.lstrip("-").isdigit() else channel
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        # "left"/"kicked" — a'zo emas; "restricted" — is_member bo'yicha.
        if m.status in ("member", "administrator", "creator", "owner"):
            return True
        if m.status == "restricted":
            return bool(getattr(m, "is_member", False))
        return False  # left / kicked
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Kanal a'zoligini tekshirib bo'lmadi (bot '%s' kanalда ADMIN "
            "ekanini tekshiring): %s", channel, e,
        )
        # Strict rejimда — tekshirib bo'lmasа kirgizmaymiz (obuna majburiy).
        return not settings.news_channel_strict


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
    # Inline asosiy menyu xabarга biriktiriladi (Menyu_Inline_Prompt).
    await update.effective_message.reply_text(text, reply_markup=main_menu())


async def menu_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⬅️ Bosh menyu — mavjud xabarni tahrirlab asosiy menyuга qaytaradi."""
    q = update.callback_query
    await q.answer()
    try:
        await q.edit_message_text(
            "🏠 Bosh menyu 👇 Kerakli bo'limни tanlang:", reply_markup=main_menu()
        )
    except Exception:  # noqa: BLE001
        await update.effective_message.reply_text(
            "🏠 Bosh menyu 👇", reply_markup=main_menu()
        )


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
    # Referal mukofoti register_referral ichida beriladi (referal egasiga).
    # 3-qadam: taqdimot (qaytgan mijozga qisqasi).
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
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return
    rows = await api.my_orders(update.effective_user.id)
    if not rows:
        await update.effective_message.reply_text(
            "Sizда hali buyurtmalar yo'q.", reply_markup=back_home()
        )
        return
    lines = ["📦 *Buyurtmalaringiz:*\n"]
    for o in rows[:10]:
        yetk = (
            "🚚 Kuryer" if o.get("yetkazish_turi") == "kuryer" else "🏬 Punktdan"
        )
        lines.append(
            f"• `{o['kod']}` — {o['jami_narx']:,.0f} som — _{o['holat']}_ — {yetk}"
        )
    await update.effective_message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=back_home()
    )


async def loyalty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return
    # Havola uchun sozlamadagi username afzal (noto'g'ri link bo'lmasligi uchun).
    data = await api.loyalty(
        update.effective_user.id,
        settings.savdo_bot_username or context.bot.username or "",
    )
    if not data:
        await update.effective_message.reply_text(
            "Ma'lumot olinmadi.", reply_markup=back_home()
        )
        return
    karta = data.get("karta_turi") or "yo'q"
    qolgan = data.get("keyingi_karta_uchun_qolgan")
    qolgan_txt = (
        f"\nKeyingi karta uchun yana {qolgan} ta xarid kerak." if qolgan else ""
    )
    s = data.get("referral_start_bonus", 5)
    m = data.get("referral_miniapp_bonus", 10)
    f = data.get("referral_discount_foiz", 5)
    vau = data.get("chegirma_vaucherlar", 0)
    havola = data.get("referal_havola", "")
    # HTML rejimi — havoladagi "_" belgilari Markdownда kursivга aylanmasligi uchun.
    karta_h = _html.escape(str(karta))
    havola_h = _html.escape(havola)
    vau_txt = (
        f"\n🏷 Sizda <b>{vau} ta {f}% chegirma</b> bor — keyingi xaridingizda ishlatiladi."
        if vau else ""
    )
    await update.message.reply_text(
        f"👥 <b>Do'stlarni taklif qilish</b>\n\n"
        f"🛍 Umumiy xaridlar: <b>{data.get('umumiy_xaridlar', 0)}</b>\n"
        f"💳 Karta: <b>{karta_h}</b>{qolgan_txt}\n\n"
        f"<b>Do'stingiz havolangiz orqali kirsa, mukofot sizga:</b>\n"
        f"• Do'st /start bossa → <b>+{s} ACOM</b>\n"
        f"• Do'st Mini App'ni ochsa → <b>+{m} ACOM</b>\n"
        f"• Do'st xarid qilsa → <b>keyingi xaridingizga {f}% chegirma</b>\n\n"
        f"🔗 Taklif havolangiz:\n{havola_h}\n\n"
        f"👤 Taklif qilinganlar: <b>{data.get('taklif_start', 0)}</b> "
        f"(xarid qilgan: <b>{data.get('taklif_qilganlar', 0)}</b>)\n"
        f"🪙 Referaldan ishlagan: <b>{data.get('referral_jami_acom', 0):,.0f} ACOM</b>"
        f"{vau_txt}",
        parse_mode="HTML",
        reply_markup=back_home(),
    )


async def favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return
    await update.effective_message.reply_text(
        "❤️ Sevimlilar bo'limi tez orada qo'shiladi.\n"
        "Hozircha katalogда yoqqan mahsulotni savatga qo'shib qo'ying. 🙂",
        reply_markup=back_home(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return
    await update.effective_message.reply_text(
        "❓ *Yordam*\n\n"
        "🛒 Do'kon — pastdagi ko'k menyu tugmasi orqali oching (mahsulotlarni "
        "ko'rish va buyurtma berish)\n"
        "📦 Buyurtmalarim — buyurtmalaringiz holati\n"
        "💰 Balansim — ACOM hisobingiz\n"
        "👥 Do'stlarni taklif qilish — do'st taklif qiling, ACOM va chegirma yutib oling\n"
        "💬 Savol berish — menга yozing, javob beraman\n\n"
        "Savolingiz bo'lsa — shu yerга yozing!",
        parse_mode="Markdown",
        reply_markup=back_home(),
    )


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return
    await update.effective_message.reply_text(
        "💬 Savolingizni yozing — mahsulot tanlashда yordam beraman.",
        reply_markup=back_home(),
    )


# ---------------------------------------------------------------------------
# 💰 Balansim — ACOM coin (1 ACOM = 1 som, KGS)
# ---------------------------------------------------------------------------
def _menu_kb(context) -> InlineKeyboardMarkup:
    return main_menu(context.bot_data.get("miniapp_url", ""))


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return
    data = await api.coin_balance(update.effective_user.id)
    bal = data.get("coin_balans", 0) or 0
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Hisobni to'ldirish", callback_data="bal_topup")],
            [InlineKeyboardButton("↩️ Balansni qaytarish", callback_data="bal_refund")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="m:home")],
        ]
    )
    await update.effective_message.reply_text(
        f"🪙 ACOM balansingiz: <b>{bal:,.0f}</b> ACOM ({bal:,.0f} som)\n\n"
        "1 ACOM = 1 som. Xaridlar shu balansdan amalga oshadi.",
        reply_markup=kb,
        parse_mode="HTML",
    )


def _home_kb() -> InlineKeyboardMarkup:
    # Jarayonning har qadamida "Bekor qilish" inline tugmasi (Menyu_Inline_Prompt task_2).
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Bekor qilish", callback_data="conv:cancel")]]
    )


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

    # task_1: to'lov usulini tanlash. Faqat bitta bo'lsa — o'tkazib yuboriladi.
    usullar = await api.coin_tolov_usullari(update.effective_user.id)
    context.user_data["topup_usullar"] = usullar
    if len(usullar) > 1:
        rows = [
            [InlineKeyboardButton(
                f"{_USUL_EMOJI.get(u['turi'], '💰')} {u['nomi']}",
                callback_data=f"tu_{u['id']}",
            )]
            for u in usullar
        ]
        await update.message.reply_text(
            "To'lov usulini tanlang:", reply_markup=InlineKeyboardMarkup(rows)
        )
        return TOPUP_METHOD
    # 0 yoki 1 ta usul — to'g'ridan-to'g'ri kodга o'tamiz.
    context.user_data["topup_usul"] = usullar[0] if usullar else None
    kod = confirm.issue_code(context.user_data)
    await update.message.reply_text(confirm.prompt_text(kod), parse_mode="HTML")
    return TOPUP_CODE


async def topup_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    usul_id = int(query.data.replace("tu_", ""))
    usullar = context.user_data.get("topup_usullar", [])
    context.user_data["topup_usul"] = next(
        (u for u in usullar if u["id"] == usul_id), None
    )
    kod = confirm.issue_code(context.user_data)
    await query.message.reply_text(confirm.prompt_text(kod), parse_mode="HTML")
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
    # ok — tanlangan to'lov usuli tafsilotlarini ko'rsatamiz.
    summa = context.user_data.get("topup_summa", 0)
    usul = context.user_data.get("topup_usul")
    if usul:
        # QR kod bo'lsa — rasmni yuboramiz.
        if usul.get("turi") == "qr_kod" and usul.get("qr_rasm_url"):
            base = _base_url()
            url = usul["qr_rasm_url"]
            if url.startswith("/media/") and base:
                url = f"{base}{url}"
            try:
                await context.bot.send_photo(update.effective_chat.id, url)
            except Exception:  # noqa: BLE001
                pass
        await update.message.reply_text(
            _usul_detail(usul, summa), parse_mode="HTML", reply_markup=_home_kb()
        )
    else:
        await update.message.reply_text(
            "⚠️ To'lov usuli hali sozlanmagan. Administrator bilan bog'laning. "
            "Chekni baribir yuborishingiz mumkin.",
            reply_markup=_home_kb(),
        )
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

    usul = context.user_data.get("topup_usul")
    r = await api.coin_topup(
        update.effective_user.id,
        summa,
        chek_rasm_url=f"/media/{file_id}",
        ai_summa=ai_summa,
        ai_sana=ai_sana,
        ai_xulosa=ai_xulosa,
        tolov_usuli_id=usul["id"] if usul else None,
    )
    confirm.clear(context.user_data)
    for k in ("topup_usul", "topup_usullar"):
        context.user_data.pop(k, None)
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


# ---------------------------------------------------------------------------
# 🏪 Do'kon ochish — pullik so'rov (nom -> ID -> mahsulot soni -> to'lov -> chek)
# ---------------------------------------------------------------------------
DOKON_ONTALIK = 100  # har 10 mahsulot uchun (som) — backend bilan mos


async def dokon_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not await _gate(update, context):
        return ConversationHandler.END
    context.user_data["d"] = {}
    await update.effective_message.reply_text(
        "🏪 <b>Do'kon ochish</b>\n\n"
        "ARZON platformasida o'z do'koningizni oching!\n\n"
        "Avval do'koningiz nomini kiriting (masalan: Diyorbek Shop):",
        parse_mode="HTML",
        reply_markup=_home_kb(),
    )
    return D_NOMI


async def dokon_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    context.user_data["d"]["nomi"] = update.message.text.strip()[:255]
    await update.message.reply_text(
        "🆔 Endi do'kon egasining <b>Telegram ID</b> raqamini kiriting.\n\n"
        "❓ <b>ID'ni qanday bilaman?</b>\n"
        "1) @userinfobot ni oching\n"
        "2) unga /start yozing\n"
        "3) u sizga raqamli ID beradi (masalan 123456789)\n"
        "Odatda bu — sizning o'z ID'ingiz. O'sha raqamni shu yerga yuboring:",
        parse_mode="HTML",
    )
    return D_ADMIN_ID


async def dokon_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    matn = update.message.text.strip()
    if not matn.isdigit():
        await update.message.reply_text(
            "Iltimos, faqat raqamli ID kiriting (masalan 123456789):"
        )
        return D_ADMIN_ID
    context.user_data["d"]["admin_id"] = int(matn)
    # Mahsulot soni tanlash (10..100, o'ntalik).
    rows, qator = [], []
    for n in range(10, 101, 10):
        qator.append(InlineKeyboardButton(str(n), callback_data=f"ds_{n}"))
        if len(qator) == 5:
            rows.append(qator)
            qator = []
    if qator:
        rows.append(qator)
    await update.message.reply_text(
        f"📦 Do'koningizда nechта mahsulot bo'ladi?\n\n"
        f"Har 10 ta mahsulot uchun <b>{DOKON_ONTALIK} som</b> "
        f"(masalan 50 ta = {5 * DOKON_ONTALIK} som).\n"
        "Quyidan tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return D_SONI


async def dokon_soni(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    soni = int(query.data.replace("ds_", ""))
    context.user_data["d"]["soni"] = soni
    summa = (soni // 10) * DOKON_ONTALIK
    context.user_data["d"]["summa"] = summa
    await query.edit_message_text(
        f"✅ {soni} ta mahsulot — <b>{summa:,.0f} som</b>",
        parse_mode="HTML",
    )
    # To'lov usulini tanlash (yoki bitta bo'lsa avto).
    usullar = await api.coin_tolov_usullari(update.effective_user.id)
    context.user_data["d"]["usullar"] = usullar
    if len(usullar) > 1:
        rows = [
            [InlineKeyboardButton(
                f"{_USUL_EMOJI.get(u['turi'], '💰')} {u['nomi']}",
                callback_data=f"dtu_{u['id']}",
            )]
            for u in usullar
        ]
        await query.message.reply_text(
            "To'lov usulini tanlang:", reply_markup=InlineKeyboardMarkup(rows)
        )
        return D_METHOD
    context.user_data["d"]["usul"] = usullar[0] if usullar else None
    kod = confirm.issue_code(context.user_data)
    await query.message.reply_text(confirm.prompt_text(kod), parse_mode="HTML")
    return D_CODE


async def dokon_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    usul_id = int(query.data.replace("dtu_", ""))
    usullar = context.user_data["d"].get("usullar", [])
    context.user_data["d"]["usul"] = next(
        (u for u in usullar if u["id"] == usul_id), None
    )
    kod = confirm.issue_code(context.user_data)
    await query.message.reply_text(confirm.prompt_text(kod), parse_mode="HTML")
    return D_CODE


async def dokon_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    natija = confirm.check_code(context.user_data, update.message.text)
    if natija == "wrong":
        await update.message.reply_text("Kod noto'g'ri, qaytadan urinib ko'ring:")
        return D_CODE
    if natija in ("expired", "toomany", "yoq"):
        await update.message.reply_text(
            "So'rov bekor qilindi (kod xato yoki muddati o'tdi). Qaytadan boshlang.",
            reply_markup=_menu_kb(context),
        )
        return ConversationHandler.END
    d = context.user_data["d"]
    usul = d.get("usul")
    summa = d.get("summa", 0)
    if usul:
        if usul.get("turi") == "qr_kod" and usul.get("qr_rasm_url"):
            base = _base_url()
            url = usul["qr_rasm_url"]
            if url.startswith("/media/") and base:
                url = f"{base}{url}"
            try:
                await context.bot.send_photo(update.effective_chat.id, url)
            except Exception:  # noqa: BLE001
                pass
        await update.message.reply_text(
            _usul_detail(usul, summa), parse_mode="HTML", reply_markup=_home_kb()
        )
    else:
        await update.message.reply_text(
            f"<b>{summa:,.0f} som</b> to'lang va chekni yuboring.\n"
            "⚠️ To'lov usuli sozlanmagan — administrator bilan bog'laning.",
            parse_mode="HTML",
            reply_markup=_home_kb(),
        )
    await update.message.reply_text("📸 To'lov chekini (rasm) yuboring:")
    return D_CHEK


async def dokon_chek(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text and update.message.text == BTN_HOME:
        return await _cancel_to_menu(update, context)
    if not update.message.photo:
        await update.message.reply_text("Iltimos, chek RASMINI yuboring:")
        return D_CHEK
    d = context.user_data.get("d", {})
    summa = d.get("summa", 0)
    photo = update.message.photo[-1]
    file_id = photo.file_id
    await context.bot.send_chat_action(update.effective_chat.id, "typing")

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
        logger.warning("Do'kon cheki tahlilида xato: %s", e)

    usul = d.get("usul")
    r = await api.dokon_sorovi(
        update.effective_user.id,
        {
            "dokon_nomi": d.get("nomi", ""),
            "admin_telegram_id": d.get("admin_id"),
            "mahsulot_soni": d.get("soni"),
            "tolov_usuli_id": usul["id"] if usul else None,
            "chek_rasm_url": f"/media/{file_id}",
            "ai_summa": ai_summa,
            "ai_sana": ai_sana,
            "ai_xulosa": ai_xulosa,
        },
    )
    confirm.clear(context.user_data)
    context.user_data.pop("d", None)
    if r.status_code == 200:
        await update.message.reply_text(
            "✅ <b>So'rovingiz qabul qilindi!</b>\n\n"
            "Hisobchi to'lovni tekshiradi. Tasdiqлангандан so'ng do'koningiz "
            "ochiladi va sizga <b>mahfiy kod</b> hamda admin bot havolasi "
            "yuboriladi. 🚀",
            parse_mode="HTML",
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
    if update.callback_query:
        await update.callback_query.answer()
    confirm.clear(context.user_data)
    for k in ("topup_summa", "refund_summa", "refund_karta", "d"):
        context.user_data.pop(k, None)
    await update.effective_message.reply_text(
        "❌ Bekor qilindi. Bosh menyu 👇", reply_markup=main_menu()
    )
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

    # Inline menyu tugmalari (Menyu_Inline_Prompt) — callback orqali.
    app.add_handler(CallbackQueryHandler(menu_home, pattern="^m:home$"))
    app.add_handler(CallbackQueryHandler(orders, pattern="^m:orders$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^m:balance$"))
    app.add_handler(CallbackQueryHandler(loyalty, pattern="^m:loyalty$"))
    app.add_handler(CallbackQueryHandler(favorites, pattern="^m:fav$"))
    app.add_handler(CallbackQueryHandler(help_cmd, pattern="^m:help$"))
    app.add_handler(CallbackQueryHandler(ask, pattern="^m:ask$"))

    # 💰 Balansim — coin balansi va to'ldirish/qaytarish oqimlari (ACOM coin).
    TXT = filters.TEXT & ~filters.COMMAND
    balance_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(topup_start, pattern="^bal_topup$"),
            CallbackQueryHandler(refund_start, pattern="^bal_refund$"),
        ],
        states={
            TOPUP_SUMMA: [MessageHandler(TXT, topup_summa)],
            TOPUP_METHOD: [CallbackQueryHandler(topup_method, pattern="^tu_")],
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
            CallbackQueryHandler(_cancel_to_menu, pattern="^conv:cancel$"),
        ],
        name="balance_flow",
        persistent=False,
    )
    app.add_handler(balance_conv)

    # 🏪 Do'kon ochish (pullik so'rov).
    dokon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(dokon_start, pattern="^m:dokon$")],
        states={
            D_NOMI: [MessageHandler(TXT, dokon_nomi)],
            D_ADMIN_ID: [MessageHandler(TXT, dokon_admin_id)],
            D_SONI: [CallbackQueryHandler(dokon_soni, pattern="^ds_")],
            D_METHOD: [CallbackQueryHandler(dokon_method, pattern="^dtu_")],
            D_CODE: [MessageHandler(TXT, dokon_code)],
            D_CHEK: [
                MessageHandler(filters.PHOTO, dokon_chek),
                MessageHandler(TXT, dokon_chek),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(_cancel_to_menu, pattern="^conv:cancel$"),
        ],
        name="dokon_flow",
        persistent=False,
    )
    app.add_handler(dokon_conv)

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)
    )
    return app
