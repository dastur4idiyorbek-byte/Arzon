"""Boshqaruv Boti — tugmali interfeys (spec1) + yangi funksiyalar (spec2).

Bosh menyu ReplyKeyboardMarkup orqali doimiy ko'rinadi (spec1 rule 1).
Eski /buyruqlar ham saqlanadi (spec1 rule 3) — faqat kirish nuqtalari
tugmalarga bog'landi. Har amal backend'да check_store_access orqali
tekshiriladi (admin izolyatsiyasi).
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

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
from . import daily, notify
from .client import api

# ---------------------------------------------------------------------------
# Bosh menyu tugmalari (spec1 task_1)
# ---------------------------------------------------------------------------
BTN_ADD = "📦 Mahsulot qo'shish"
BTN_DEL = "🗑 Mahsulotni o'chirish"
BTN_EDIT = "🔄 Mahsulotni tahrirlash"
BTN_PROMO = "🎟 Promo kod"
BTN_SECRET = "🔑 Mahfiy kod"
BTN_STATS = "📊 Statistika"
BTN_ORDERS = "📋 Buyurtmalar"
BTN_SEARCH = "🔍 Buyurtma qidirish"
# Faqat super-admin (do'kon/admin boshqaruvi)
BTN_NEWSTORE = "🏪 Yangi do'kon"
BTN_NEWADMIN = "➕ Yangi admin qo'shish"
BTN_DELSTORE = "🗑 Do'kon o'chirish"
# Navigatsiya
BTN_CANCEL = "❌ Bekor qilish"  # eski (fallbackда saqlanadi)
BTN_HOME = "🏠 Bosh menyu"
BTN_BACK = "⬅️ Orqaga"
BTN_DONE = "✅ Tayyor"
BTN_SKIP = "⏭ O'tkazib yuborish"

# Bosh menyu tugmalari — jarayon ichida bosilса "avval yakunlang" deyiladi.
MENU_BUTTONS = {
    BTN_ADD, BTN_DEL, BTN_EDIT, BTN_PROMO, BTN_SECRET,
    BTN_STATS, BTN_ORDERS, BTN_SEARCH,
    BTN_NEWSTORE, BTN_NEWADMIN, BTN_DELSTORE,
}

# Conversation holatlari.
(
    P_NOMI, P_RASM, P_NISBAT, P_NARX, P_SKIDKA, P_MUDDAT, P_MIQDOR, P_TAVSIF,
    P_KORINISH, P_TASDIQ,
    E_FIELD, E_VALUE, E_MUDDAT,
    PR_KOD, PR_FOIZ,
    Q_KIRITISH,
    DO_NOMI,
    NA_ID,
    S_NOMI, S_ADMIN_ID,
    RAD_SABAB,
) = range(21)

# Ruxsat etilgan rasm nisbatlari.
RATIOS = ["1:1", "4:3", "3:4", "9:16", "16:9"]


def _is_super(uid: int) -> bool:
    return uid in settings.super_admin_id_list


def menu_markup(uid: int) -> ReplyKeyboardMarkup:
    """Bosh menyu — doimiy tugmalar qatori (spec1 rule 1).

    Do'kon/admin boshqaruvi (yangi do'kon, yangi admin, do'kon o'chirish)
    faqat super-adminга ko'rinadi. Oddiy admin do'kon ocholmaydi.
    """
    rows = [
        [KeyboardButton(BTN_ADD), KeyboardButton(BTN_EDIT)],
        [KeyboardButton(BTN_DEL), KeyboardButton(BTN_SECRET)],
        [KeyboardButton(BTN_PROMO), KeyboardButton(BTN_STATS)],
        [KeyboardButton(BTN_ORDERS), KeyboardButton(BTN_SEARCH)],
    ]
    if _is_super(uid):
        rows.append(
            [KeyboardButton(BTN_NEWSTORE), KeyboardButton(BTN_NEWADMIN)]
        )
        rows.append([KeyboardButton(BTN_DELSTORE)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def nav_markup(*extra_rows: list[str], back: bool = False) -> ReplyKeyboardMarkup:
    """Jarayon klaviaturasi: qo'shimcha tugmalar + [⬅️ Orqaga] [🏠 Bosh menyu]."""
    rows = [[KeyboardButton(b) for b in row] for row in extra_rows]
    bottom = []
    if back:
        bottom.append(KeyboardButton(BTN_BACK))
    bottom.append(KeyboardButton(BTN_HOME))
    rows.append(bottom)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# Eski nomni saqlaymiz (qisqa flowlar cancel_markup ishlatadi) — endi 🏠 beradi.
def cancel_markup(*extra_rows: list[str]) -> ReplyKeyboardMarkup:
    return nav_markup(*extra_rows, back=False)


def _menu_notice(text: str) -> str:
    return text


async def _back_to_menu(update: Update, text: str) -> None:
    await update.effective_message.reply_text(
        text, reply_markup=menu_markup(update.effective_user.id)
    )


def _is_menu_press(text: str | None) -> bool:
    return (text or "").strip() in MENU_BUTTONS


async def _warn_finish_first(update: Update) -> None:
    await update.message.reply_text(
        f"Avval joriy jarayonni yakunlang yoki '{BTN_CANCEL}' tugmasini bosing."
    )


async def _resolve_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminning do'konini aniqlaydi; ruxsat yo'q bo'lsa xabar beradi."""
    admin_id = update.effective_user.id
    stores = await api.my_stores(admin_id)
    if not stores:
        await update.effective_message.reply_text(
            "⛔️ Sizga hali do'kon biriktirilmagan.\n"
            "Do'kon faqat super-admin tomonidan ochiladi/biriktiriladi — "
            "super-admin bilan bog'laning.",
            reply_markup=menu_markup(admin_id),
        )
        return None
    return stores[0]["id"]


# ---------------------------------------------------------------------------
# /start — bosh menyu
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    stores = await api.my_stores(uid)
    if stores:
        lines = ["✅ Xush kelibsiz, admin!\n\nSizning do'konlaringiz:"]
        for s in stores:
            lines.append(f"• {s['nomi']} (ID: {s['id']}, holat: {s['holat']})")
        lines.append("\nQuyidagi tugmalardан foydalaning 👇")
        text = "\n".join(lines)
    elif _is_super(uid):
        text = (
            "Assalomu alaykum, super-admin! 👋\n\n"
            f"'{BTN_NEWSTORE}' tugmasi bilan do'kon oching va admin tayinlang."
        )
    else:
        text = (
            "Assalomu alaykum! 👋\n\n"
            "Sizga hali do'kon biriktirilmagan. Do'kon super-admin tomonidan "
            "ochiladi — super-admin bilan bog'laning."
        )
    await update.message.reply_text(text, reply_markup=menu_markup(uid))


async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await _back_to_menu(update, "Bekor qilindi. Bosh menyu 👇")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 📦 Mahsulot qo'shish — kengaytirilgan jarayon (spec1 task_2)
# ---------------------------------------------------------------------------
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["p"] = {"store_id": store_id, "rasmlar": []}
    return await _ask_nomi(update)


# --- Har qadam uchun "so'rash" funksiyalari (orqaga navigatsiya uchun) ---
async def _ask_nomi(update: Update):
    await update.effective_message.reply_text(
        "1/8 — Mahsulot nomini kiriting:", reply_markup=nav_markup(back=False)
    )
    return P_NOMI


async def _ask_rasm(update: Update):
    await update.effective_message.reply_text(
        "2/8 — Mahsulot rasmlarini yuboring (maksimal 10 ta).\n"
        f"Tugatgach '{BTN_DONE}' bosing, rasm bo'lmasa '{BTN_SKIP}' bosing.",
        reply_markup=nav_markup([BTN_DONE], [BTN_SKIP], back=True),
    )
    return P_RASM


async def _ask_nisbat(update: Update):
    rows = [
        [
            InlineKeyboardButton("⬜️ 1:1", callback_data="nis_1:1"),
            InlineKeyboardButton("🖼 4:3", callback_data="nis_4:3"),
            InlineKeyboardButton("📱 3:4", callback_data="nis_3:4"),
        ],
        [
            InlineKeyboardButton("📲 9:16", callback_data="nis_9:16"),
            InlineKeyboardButton("🖥 16:9", callback_data="nis_16:9"),
        ],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="nis_back")],
    ]
    await update.effective_message.reply_text(
        "Rasm nisbatini tanlang (rasmingiz shakliga mos keladiganini):\n"
        "⬜️ 1:1 — kvadrat\n"
        "🖼 4:3 — yotiq\n"
        "📱 3:4 — tik\n"
        "📲 9:16 — baland (story)\n"
        "🖥 16:9 — keng",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return P_NISBAT


async def _ask_narx(update: Update):
    await update.effective_message.reply_text(
        "3/8 — Narxini kiriting (som), masalan: 3200",
        reply_markup=nav_markup(back=True),
    )
    return P_NARX


async def _ask_skidka(update: Update):
    await update.effective_message.reply_text(
        "4/8 — Chegirma bormi? Foizni kiriting (masalan 20), "
        "yo'q bo'lsa 0 yozing:",
        reply_markup=nav_markup(back=True),
    )
    return P_SKIDKA


async def _ask_muddat(update: Update):
    await update.effective_message.reply_text(
        "Chegirma qachongacha amal qiladi? Sana kiriting "
        "(masalan 31.07.2026), muddatsiz bo'lsa 'yo'q' deb yozing:",
        reply_markup=nav_markup(back=True),
    )
    return P_MUDDAT


async def _ask_miqdor(update: Update):
    await update.effective_message.reply_text(
        "5/8 — Omborда nechta bor? Sonini kiriting (dona), "
        "cheksiz bo'lsa 'yo'q' deb yozing:",
        reply_markup=nav_markup(back=True),
    )
    return P_MIQDOR


async def _ask_tavsif(update: Update):
    await update.effective_message.reply_text(
        "6/8 — Tavsif (opisaniya) yozing: o'lcham, rang, material va h.k. "
        f"Bo'lmasa '{BTN_SKIP}' bosing.",
        reply_markup=nav_markup([BTN_SKIP], back=True),
    )
    return P_TAVSIF


async def _ask_korinish(update: Update):
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌐 Ommaviy", callback_data="pkor_ommaviy"),
                InlineKeyboardButton("🔒 Mahfiy", callback_data="pkor_mahfiy"),
            ],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="pkor_back")],
        ]
    )
    await update.effective_message.reply_text(
        "7/8 — Ko'rinishini tanlang:\n"
        "🌐 Ommaviy — hamma ko'radi.\n"
        "🔒 Mahfiy — faqat do'kon mahfiy kodi bilan ochiladi.",
        reply_markup=kb,
    )
    return P_KORINISH


# --- Qadam ishlovchilari ---
async def p_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return P_NOMI
    context.user_data["p"]["nomi"] = update.message.text.strip()
    return await _ask_rasm(update)


async def p_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rasmlar = context.user_data["p"]["rasmlar"]
    if len(rasmlar) >= 10:
        await update.message.reply_text(
            f"Maksimal 10 ta rasm. Ortiqcha qabul qilinmadi — '{BTN_DONE}' bosing."
        )
        return P_RASM
    rasmlar.append(update.message.photo[-1].file_id)
    if len(rasmlar) == 10:
        await update.message.reply_text("10/10 rasm qabul qilindi (maksimal).")
        return await _ask_nisbat(update)
    await update.message.reply_text(
        f"{len(rasmlar)}/10 rasm qabul qilindi. Yana yuboring yoki "
        f"'{BTN_DONE}' bosing."
    )
    return P_RASM


async def p_back_to_nomi(update, context):
    return await _ask_nomi(update)


async def p_rasm_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data["p"]["rasmlar"]:
        await update.message.reply_text(
            f"Hali rasm yubormadingiz. Rasm yuboring yoki '{BTN_SKIP}' bosing."
        )
        return P_RASM
    return await _ask_nisbat(update)


async def p_rasm_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p"]["rasmlar"] = []
    context.user_data["p"]["rasm_nisbati"] = "1:1"
    return await _ask_narx(update)


async def p_nisbat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "nis_back":
        await query.edit_message_reply_markup(reply_markup=None)
        return await _ask_rasm(update)
    context.user_data["p"]["rasm_nisbati"] = query.data.replace("nis_", "")
    await query.edit_message_text(
        f"Rasm nisbati: {context.user_data['p']['rasm_nisbati']} ✅"
    )
    return await _ask_narx(update)


async def p_stray_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Maksimal 10 ta rasm qabul qilindi.")
    return None


async def p_narx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return P_NARX
    try:
        narx = float(update.message.text.replace(" ", "").replace(",", "."))
        assert narx >= 0
    except (ValueError, AssertionError):
        await update.message.reply_text(
            "Narx noto'g'ri. Faqat raqam kiriting (som), masalan: 3200"
        )
        return P_NARX
    context.user_data["p"]["narxi"] = narx
    return await _ask_skidka(update)


async def p_back_from_narx(update, context):
    """Narxдан orqaga: rasm bo'lsa nisbatга, aks holda rasmга."""
    if context.user_data["p"].get("rasmlar"):
        return await _ask_nisbat(update)
    return await _ask_rasm(update)


async def p_skidka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return P_SKIDKA
    try:
        foiz = int(update.message.text.strip())
        assert 0 <= foiz <= 99
    except (ValueError, AssertionError):
        await update.message.reply_text("Foiz 0 dan 99 gacha raqam bo'lsin:")
        return P_SKIDKA
    p = context.user_data["p"]
    p["skidka_foizi"] = foiz
    if foiz > 0:
        narx = p["narxi"]
        yakuniy = narx - (narx * foiz / 100)
        p["yakuniy_narx"] = yakuniy
        await update.message.reply_text(
            f"Asosiy narx: {narx:,.0f} som, Skidka: {foiz}% → "
            f"Yakuniy narx: {yakuniy:,.0f} som"
        )
        return await _ask_muddat(update)
    p["skidka_muddati"] = None
    p["yakuniy_narx"] = None
    return await _ask_miqdor(update)


async def p_back_to_narx(update, context):
    return await _ask_narx(update)


async def p_muddat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip().lower()
    p = context.user_data["p"]
    if matn in ("yo'q", "yoq", "yok", "нет"):
        p["skidka_muddati"] = None
        return await _ask_miqdor(update)
    try:
        sana = datetime.strptime(matn, "%d.%m.%Y")
        tz = ZoneInfo(daily.LOCAL_TZ)
        muddat = datetime.combine(
            sana.date(), time(23, 59), tzinfo=tz
        ).astimezone(timezone.utc)
        if muddat < datetime.now(timezone.utc):
            await update.message.reply_text(
                "Bu sana o'tib ketgan. Kelajakdagi sanani kiriting yoki 'yo'q':"
            )
            return P_MUDDAT
        p["skidka_muddati"] = muddat.isoformat()
    except ValueError:
        await update.message.reply_text(
            "Sana formati noto'g'ri. Masalan: 31.07.2026 — yoki 'yo'q' yozing:"
        )
        return P_MUDDAT
    return await _ask_miqdor(update)


async def p_back_to_skidka(update, context):
    return await _ask_skidka(update)


async def p_miqdor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip().lower()
    p = context.user_data["p"]
    if matn in ("yo'q", "yoq", "yok"):
        p["miqdor"] = None
    else:
        try:
            p["miqdor"] = int(matn)
            assert p["miqdor"] >= 0
        except (ValueError, AssertionError):
            await update.message.reply_text(
                "Raqam kiriting (dona) yoki cheksiz bo'lsa 'yo'q' yozing:"
            )
            return P_MIQDOR
    return await _ask_tavsif(update)


async def p_back_from_miqdor(update, context):
    """Miqdordan orqaga: chegirma bo'lsa muddatга, aks holda skidkaга."""
    p = context.user_data["p"]
    if p.get("skidka_foizi", 0) > 0:
        return await _ask_muddat(update)
    return await _ask_skidka(update)


async def p_tavsif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return P_TAVSIF
    context.user_data["p"]["tavsif"] = update.message.text.strip()
    return await _ask_korinish(update)


async def p_tavsif_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p"]["tavsif"] = None
    return await _ask_korinish(update)


async def p_back_to_miqdor(update, context):
    return await _ask_miqdor(update)


async def p_korinish_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ko'rinishдан orqaga → tavsif (inline'дан reply klaviaturaга qaytamiz)."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    return await _ask_tavsif(update)


async def p_korinish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    p = context.user_data["p"]
    p["korinish"] = query.data.replace("pkor_", "")

    # 8/8 — Yakuniy tasdiqlash xulosasi.
    foiz = p.get("skidka_foizi", 0)
    narx_txt = f"{p['narxi']:,.0f} som"
    if foiz > 0:
        narx_txt += (
            f" | Skidka: {foiz}% → Yakuniy: {p['yakuniy_narx']:,.0f} som"
        )
        if p.get("skidka_muddati"):
            sana = datetime.fromisoformat(p["skidka_muddati"]).astimezone(
                ZoneInfo(daily.LOCAL_TZ)
            )
            narx_txt += f" (muddati: {sana.strftime('%d.%m.%Y')})"
    miqdor_txt = (
        f"{p['miqdor']} dona" if p.get("miqdor") is not None else "cheksiz"
    )
    rasm_txt = f"{len(p['rasmlar'])} ta"
    if p["rasmlar"]:
        rasm_txt += f" ({p.get('rasm_nisbati', '1:1')})"
    xulosa = (
        "8/8 — Tekshirib tasdiqlang:\n\n"
        f"📦 Nomi: {p['nomi']}\n"
        f"🖼 Rasmlar: {rasm_txt}\n"
        f"💰 Narx: {narx_txt}\n"
        f"📊 Miqdor: {miqdor_txt}\n"
        f"📝 Tavsif: {p.get('tavsif') or '—'}\n"
        f"👁 Ko'rinish: {'🔒 Mahfiy' if p['korinish'] == 'mahfiy' else '🌐 Ommaviy'}"
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Saqlash", callback_data="psave_ok"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data="psave_no"),
            ],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="psave_back")],
        ]
    )
    await query.edit_message_text(xulosa, reply_markup=kb)
    return P_TASDIQ


async def p_saqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "psave_back":
        await query.edit_message_reply_markup(reply_markup=None)
        return await _ask_korinish(update)
    if query.data == "psave_no":
        context.user_data.clear()
        await query.edit_message_text("Bekor qilindi.")
        await context.bot.send_message(
            update.effective_chat.id,
            "Bosh menyu 👇",
            reply_markup=menu_markup(update.effective_user.id),
        )
        return ConversationHandler.END

    p = context.user_data["p"]
    data = {
        "nomi": p["nomi"],
        "narxi": p["narxi"],
        "skidka_foizi": p.get("skidka_foizi", 0),
        "skidka_muddati": p.get("skidka_muddati"),
        "miqdor": p.get("miqdor"),
        "tavsif": p.get("tavsif"),
        "korinish": p["korinish"],
        "rasm_urls": [f"/media/{fid}" for fid in p["rasmlar"]],
        "rasm_nisbati": p.get("rasm_nisbati", "1:1"),
    }
    r = await api.add_product(update.effective_user.id, p["store_id"], data)
    if r.status_code == 200:
        await query.edit_message_text(f"✅ '{p['nomi']}' saqlandi!")
    else:
        await query.edit_message_text(f"❌ Xatolik: {r.text[:300]}")
    context.user_data.clear()
    await context.bot.send_message(
        update.effective_chat.id,
        "Bosh menyu 👇",
        reply_markup=menu_markup(update.effective_user.id),
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 🔄 Mahsulotni tahrirlash (spec1 task_5)
# ---------------------------------------------------------------------------
EDIT_FIELDS = {
    "nomi": "📦 Nomi",
    "narx": "💰 Narxi",
    "skidka": "📉 Skidka %",
    "miqdor": "📊 Miqdor",
    "tavsif": "📝 Tavsif",
    "korinish": "👁 Ko'rinish",
    "rasm": "🖼 Rasmlar",
    "nisbat": "📐 Rasm nisbati",
}


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return ConversationHandler.END
    r = await api.list_products(update.effective_user.id, store_id)
    items = r.json() if r.status_code == 200 else []
    if not items:
        await _back_to_menu(update, "Mahsulotlar yo'q.")
        return ConversationHandler.END
    rows = [
        [
            InlineKeyboardButton(
                f"{p['nomi']} — {p['narxi']:,.0f} som",
                callback_data=f"epick_{p['id']}",
            )
        ]
        for p in items[:50]
    ]
    await update.message.reply_text(
        "Qaysi mahsulotni tahrirlaysiz?",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return E_FIELD


async def edit_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["edit_pid"] = int(query.data.replace("epick_", ""))
    rows = [
        [InlineKeyboardButton(label, callback_data=f"ef_{field}")]
        for field, label in EDIT_FIELDS.items()
    ]
    await query.edit_message_text(
        "Qaysi maydonni o'zgartirasiz?",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return E_FIELD


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("ef_", "")
    context.user_data["edit_field"] = field

    if field == "korinish":
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🌐 Ommaviy", callback_data="ekor_ommaviy"
                    ),
                    InlineKeyboardButton(
                        "🔒 Mahfiy", callback_data="ekor_mahfiy"
                    ),
                ]
            ]
        )
        await query.edit_message_text(
            "Yangi ko'rinishni tanlang:", reply_markup=kb
        )
        return E_VALUE
    if field == "nisbat":
        rows = [
            [
                InlineKeyboardButton(r, callback_data=f"enis_{r}")
                for r in RATIOS[:3]
            ],
            [
                InlineKeyboardButton(r, callback_data=f"enis_{r}")
                for r in RATIOS[3:]
            ],
        ]
        await query.edit_message_text(
            "Yangi rasm nisbatini tanlang:",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return E_VALUE
    if field == "rasm":
        context.user_data["edit_rasmlar"] = []
        await query.edit_message_text(
            "Yangi rasmlarni yuboring (eski rasmlar almashtiriladi, "
            f"maksimal 10 ta). Tugatgach '{BTN_DONE}' bosing."
        )
        await context.bot.send_message(
            update.effective_chat.id,
            "Rasm yuboring 👇",
            reply_markup=cancel_markup([BTN_DONE]),
        )
        return E_VALUE

    prompts = {
        "nomi": "Yangi nomini kiriting:",
        "narx": "Yangi narxini kiriting (som):",
        "skidka": "Yangi skidka foizini kiriting (0-99, 0 = chegirma yo'q):",
        "miqdor": "Yangi miqdorni kiriting (dona), cheksiz bo'lsa 'yo'q':",
        "tavsif": "Yangi tavsifni kiriting:",
    }
    await query.edit_message_text(prompts[field])
    await context.bot.send_message(
        update.effective_chat.id, "Kiriting 👇", reply_markup=cancel_markup()
    )
    return E_VALUE


async def _apply_edit(update: Update, context, data: dict) -> int:
    pid = context.user_data["edit_pid"]
    r = await api.update_product(update.effective_user.id, pid, data)
    msg = "✅ Yangilandi!" if r.status_code == 200 else f"❌ {r.text[:300]}"
    await _back_to_menu(update, msg)
    context.user_data.clear()
    return ConversationHandler.END


async def edit_value_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return E_VALUE
    field = context.user_data.get("edit_field")
    matn = update.message.text.strip()
    if field == "nomi":
        return await _apply_edit(update, context, {"nomi": matn})
    if field == "tavsif":
        return await _apply_edit(update, context, {"tavsif": matn})
    if field == "narx":
        try:
            narx = float(matn.replace(" ", "").replace(",", "."))
        except ValueError:
            await update.message.reply_text("Raqam kiriting:")
            return E_VALUE
        return await _apply_edit(update, context, {"narxi": narx})
    if field == "miqdor":
        if matn.lower() in ("yo'q", "yoq", "yok"):
            return await _apply_edit(update, context, {"miqdor": None})
        try:
            return await _apply_edit(update, context, {"miqdor": int(matn)})
        except ValueError:
            await update.message.reply_text("Raqam yoki 'yo'q' kiriting:")
            return E_VALUE
    if field == "skidka":
        try:
            foiz = int(matn)
            assert 0 <= foiz <= 99
        except (ValueError, AssertionError):
            await update.message.reply_text("0 dan 99 gacha raqam kiriting:")
            return E_VALUE
        context.user_data["edit_skidka"] = foiz
        if foiz > 0:
            await update.message.reply_text(
                "Chegirma qachongacha? (masalan 31.07.2026, "
                "muddatsiz bo'lsa 'yo'q'):"
            )
            return E_MUDDAT
        return await _apply_edit(
            update, context, {"skidka_foizi": 0, "skidka_muddati": None}
        )
    await update.message.reply_text("Nomalum maydon.")
    return ConversationHandler.END


async def edit_muddat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip().lower()
    foiz = context.user_data.get("edit_skidka", 0)
    if matn in ("yo'q", "yoq", "yok"):
        return await _apply_edit(
            update, context, {"skidka_foizi": foiz, "skidka_muddati": None}
        )
    try:
        sana = datetime.strptime(matn, "%d.%m.%Y")
        tz = ZoneInfo(daily.LOCAL_TZ)
        muddat = datetime.combine(
            sana.date(), time(23, 59), tzinfo=tz
        ).astimezone(timezone.utc)
    except ValueError:
        await update.message.reply_text("Masalan: 31.07.2026 — yoki 'yo'q':")
        return E_MUDDAT
    return await _apply_edit(
        update,
        context,
        {"skidka_foizi": foiz, "skidka_muddati": muddat.isoformat()},
    )


async def edit_value_korinish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    korinish = query.data.replace("ekor_", "")
    pid = context.user_data["edit_pid"]
    r = await api.update_product(
        update.effective_user.id, pid, {"korinish": korinish}
    )
    msg = "✅ Yangilandi!" if r.status_code == 200 else f"❌ {r.text[:300]}"
    await query.edit_message_text(msg)
    await context.bot.send_message(
        update.effective_chat.id,
        "Bosh menyu 👇",
        reply_markup=menu_markup(update.effective_user.id),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def edit_value_nisbat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nisbat = query.data.replace("enis_", "")
    pid = context.user_data["edit_pid"]
    r = await api.update_product(
        update.effective_user.id, pid, {"rasm_nisbati": nisbat}
    )
    msg = "✅ Yangilandi!" if r.status_code == 200 else f"❌ {r.text[:300]}"
    await query.edit_message_text(msg)
    await context.bot.send_message(
        update.effective_chat.id,
        "Bosh menyu 👇",
        reply_markup=menu_markup(update.effective_user.id),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def edit_value_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rasmlar = context.user_data.setdefault("edit_rasmlar", [])
    if len(rasmlar) >= 10:
        await update.message.reply_text("Maksimal 10 ta rasm.")
        return E_VALUE
    rasmlar.append(update.message.photo[-1].file_id)
    await update.message.reply_text(
        f"{len(rasmlar)}/10 qabul qilindi. Yana yuboring yoki '{BTN_DONE}'."
    )
    return E_VALUE


async def edit_value_photo_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rasmlar = context.user_data.get("edit_rasmlar", [])
    if not rasmlar:
        await update.message.reply_text("Hali rasm yubormadingiz.")
        return E_VALUE
    return await _apply_edit(
        update,
        context,
        {"rasm_urls": [f"/media/{fid}" for fid in rasmlar]},
    )


# ---------------------------------------------------------------------------
# 🗑 Mahsulotni o'chirish (spec1 task_5) — inline, suhbatsiz
# ---------------------------------------------------------------------------
async def del_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    r = await api.list_products(update.effective_user.id, store_id)
    items = r.json() if r.status_code == 200 else []
    if not items:
        await _back_to_menu(update, "Mahsulotlar yo'q.")
        return
    rows = [
        [
            InlineKeyboardButton(
                f"🗑 {p['nomi']} — {p['narxi']:,.0f} som",
                callback_data=f"pdel_{p['id']}",
            )
        ]
        for p in items[:50]
    ]
    await update.message.reply_text(
        "Qaysi mahsulot o'chirilsin?", reply_markup=InlineKeyboardMarkup(rows)
    )


async def del_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("pdel_", "")
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Ha", callback_data=f"pdelok_{pid}"),
                InlineKeyboardButton("❌ Yo'q", callback_data="pdelno"),
            ]
        ]
    )
    await query.edit_message_text(
        "Rostdan o'chirilsinmi?", reply_markup=kb
    )


async def del_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "pdelno":
        await query.edit_message_text("Bekor qilindi.")
        return
    pid = int(query.data.replace("pdelok_", ""))
    r = await api.delete_product(update.effective_user.id, pid)
    if r.status_code == 200:
        await query.edit_message_text("🗑 Mahsulot o'chirildi.")
    else:
        await query.edit_message_text(f"❌ {r.text[:300]}")


# ---------------------------------------------------------------------------
# 🆕 Buyurtmani tezkor qabul qilish / bekor qilish (spec2 task_1)
# ---------------------------------------------------------------------------
async def order_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = int(query.data.replace("qabul_", ""))
    r = await api.accept_order(update.effective_user.id, order_id)
    if r.status_code == 403:
        await query.answer("Bu buyurtma sizga tegishli emas.", show_alert=True)
        return
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", "Xatolik")
        except Exception:  # noqa: BLE001
            detail = "Xatolik"
        await query.answer(detail, show_alert=True)
        return
    await query.answer("Qabul qilindi!")
    d = r.json()
    vaqt = datetime.now(ZoneInfo(daily.LOCAL_TZ)).strftime("%H:%M")
    ism = update.effective_user.first_name or "admin"
    original = query.message.text or ""
    await query.edit_message_text(
        f"{original}\n\n✅ Qabul qilindi — {ism}, {vaqt}"
    )
    # Ombor ogohlantirishlari (task_2).
    for w in d.get("ogohlantirishlar", []):
        await context.bot.send_message(update.effective_chat.id, w)
    # Mijozga xabar (Savdo Boti orqali).
    await notify.send_customer(
        d.get("user_telegram_id"),
        f"✅ Buyurtmangiz qabul qilindi! Kod: {d['order']['kod']}\n"
        "Tez orada tayyorlab jo'natamiz.",
    )


async def order_reject_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["rad_order_id"] = int(query.data.replace("rad_", ""))
    await context.bot.send_message(
        update.effective_chat.id,
        "Bekor qilish sababini yozing (mijozga yuboriladi):",
        reply_markup=cancel_markup(),
    )
    return RAD_SABAB


async def order_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return RAD_SABAB
    sabab = update.message.text.strip()
    order_id = context.user_data.get("rad_order_id")
    r = await api.cancel_order(update.effective_user.id, order_id, sabab)
    if r.status_code == 403:
        await _back_to_menu(update, "⛔️ Bu buyurtma sizga tegishli emas.")
    elif r.status_code != 200:
        await _back_to_menu(update, f"❌ {r.text[:300]}")
    else:
        d = r.json()
        await notify.send_customer(
            d.get("user_telegram_id"),
            f"❌ Buyurtmangiz bekor qilindi (kod: {d['order']['kod']}).\n"
            f"Sabab: {sabab}",
        )
        await _back_to_menu(update, "Buyurtma bekor qilindi, mijozga xabar ketdi.")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 🔍 Buyurtma qidirish (spec2 task_4)
# ---------------------------------------------------------------------------
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return ConversationHandler.END
    context.user_data["search_store"] = store_id
    await update.message.reply_text(
        "6 xonali buyurtma kodini YOKI mijoz telefon/ismini kiriting:",
        reply_markup=cancel_markup(),
    )
    return Q_KIRITISH


async def search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return Q_KIRITISH
    q = update.message.text.strip()
    r = await api.search_orders(
        update.effective_user.id, context.user_data["search_store"], q
    )
    natijalar = r.json() if r.status_code == 200 else []
    if not natijalar:
        await _back_to_menu(update, "Hech narsa topilmadi.")
        return ConversationHandler.END
    lines = ["🔍 Topilgan buyurtmalar:\n"]
    for o in natijalar[:10]:
        sana = (o.get("yaratilgan_vaqt") or "")[:10]
        lines.append(
            f"• Kod: {o['kod']} | {', '.join(o['mahsulotlar'])} | "
            f"{o.get('mijoz_ism') or '—'} ({o.get('mijoz_tel') or '—'}) | "
            f"{o['holat']} | {sana}"
        )
    await _back_to_menu(update, "\n".join(lines))
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# 🏪 Do'kon ochish (spec1 task_3)
# ---------------------------------------------------------------------------
async def dokon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stores = await api.my_stores(update.effective_user.id)
    if stores:
        nomlar = ", ".join(s["nomi"] for s in stores)
        await _back_to_menu(
            update, f"Sizда allaqachon do'kon bor: {nomlar}"
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "🏪 Yangi do'kon ochamiz!\nDo'kon nomini kiriting:",
        reply_markup=cancel_markup(),
    )
    return DO_NOMI


async def dokon_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return DO_NOMI
    r = await api.create_self_store(
        update.effective_user.id, update.message.text.strip()
    )
    if r.status_code == 200:
        d = r.json()
        await _back_to_menu(
            update,
            f"✅ '{d['nomi']}' do'koni ochildi!\n\n"
            f"🔑 Mahfiy kodingiz: {d['mahfiy_kirish_kodi']}\n"
            "(Buni yozib qo'ying — mahfiy mahsulotlar shu kod bilan ochiladi.)",
        )
    else:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:  # noqa: BLE001
            detail = r.text
        await _back_to_menu(update, f"❌ {detail}")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ➕ Yangi admin qo'shish (spec1 task_4, faqat super-admin)
# ---------------------------------------------------------------------------
async def newadmin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_super(update.effective_user.id):
        await _back_to_menu(update, "⛔️ Bu amal faqat super-admin uchun.")
        return ConversationHandler.END
    stores = await api.my_stores(update.effective_user.id)
    if not stores:
        await _back_to_menu(update, "Hali do'konlar yo'q.")
        return ConversationHandler.END
    rows = [
        [
            InlineKeyboardButton(
                s["nomi"], callback_data=f"nastore_{s['id']}"
            )
        ]
        for s in stores[:50]
    ]
    await update.message.reply_text(
        "Qaysi do'konга admin qo'shasiz?",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return NA_ID


async def newadmin_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["na_store"] = int(query.data.replace("nastore_", ""))
    await query.edit_message_text(
        "Yangi adminning Telegram ID'sini kiriting:"
    )
    return NA_ID


async def newadmin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_admin = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Telegram ID raqam bo'lishi kerak:")
        return NA_ID
    store_id = context.user_data.get("na_store")
    if store_id is None:
        await _back_to_menu(update, "Avval do'konni tanlang.")
        return ConversationHandler.END
    r = await api.add_store_admin(
        update.effective_user.id, store_id, new_admin
    )
    if r.status_code == 200:
        await _back_to_menu(
            update,
            f"✅ Admin {new_admin} qo'shildi. U darhol botга kira oladi.",
        )
    else:
        await _back_to_menu(update, f"❌ {r.text[:300]}")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Oddiy ko'rish funksiyalari (mavjud mantiq — tugmalarga ulangan)
# ---------------------------------------------------------------------------
async def mahsulotlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    r = await api.list_products(update.effective_user.id, store_id)
    if r.status_code != 200:
        await update.message.reply_text(f"❌ {r.text}")
        return
    items = r.json()
    if not items:
        await update.message.reply_text("Mahsulotlar yo'q.")
        return
    lines = ["📋 *Mahsulotlar:*\n"]
    for p in items:
        belgi = "🔒" if p["korinish"] == "mahfiy" else "🌐"
        narx = f"{p['narxi']:,.0f} som"
        if (p.get("skidka_foizi") or 0) > 0 and p.get("yakuniy_narx"):
            narx = (
                f"~{p['narxi']:,.0f}~ → {p['yakuniy_narx']:,.0f} som "
                f"(-{p['skidka_foizi']}%)"
            )
        miqdor = p.get("miqdor")
        ombor = (
            " | ❌ Tugadi" if miqdor == 0
            else f" | {miqdor} dona" if miqdor is not None
            else ""
        )
        lines.append(f"{belgi} #{p['id']} {p['nomi']} — {narx}{ombor}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def buyurtmalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    r = await api.orders(update.effective_user.id, store_id)
    if r.status_code != 200:
        await update.message.reply_text(f"❌ {r.text}")
        return
    orders = r.json()
    if not orders:
        await update.message.reply_text("Buyurtmalar yo'q.")
        return
    lines = ["🧾 *Buyurtmalar:*\n"]
    for o in orders[:15]:
        lines.append(
            f"• #{o['id']} kod:`{o['kod']}` — {o['jami_narx']:,.0f} som — "
            f"_{o['holat']}_"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def tasdiqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tasdiqlash <kod> — buyurtma kodini tasdiqlash."""
    if not context.args:
        await update.message.reply_text("Foydalanish: /tasdiqlash <6 xonali kod>")
        return
    kod = context.args[0]
    r = await api.confirm_code(update.effective_user.id, kod)
    if r.status_code == 200:
        o = r.json()
        await update.message.reply_text(
            f"✅ Buyurtma #{o['id']} tasdiqlandi. Holat: {o['holat']}"
        )
    else:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:  # noqa: BLE001
            detail = r.text
        await update.message.reply_text(f"❌ {detail}")


async def mahfiy_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    r = await api.get_secret_code(update.effective_user.id, store_id)
    if r.status_code != 200:
        await update.message.reply_text(f"❌ {r.text}")
        return
    kod = r.json().get("mahfiy_kirish_kodi") or "(o'rnatilmagan)"
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Kodni yangilash", callback_data=f"refresh_{store_id}")]]
    )
    await update.message.reply_text(
        f"🔑 Do'koningizning joriy mahfiy kodi:\n\n`{kod}`\n\n"
        "Bu kodni faqat siz ko'rasiz. Mijozlar uni Mini App'да kiritib, "
        "mahfiy mahsulotlaringizni ochadi.",
        reply_markup=kb,
        parse_mode="Markdown",
    )


async def mahfiy_kod_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    store_id = int(query.data.replace("refresh_", ""))
    r = await api.refresh_secret_code(update.effective_user.id, store_id)
    if r.status_code != 200:
        await query.edit_message_text(f"❌ {r.text}")
        return
    yangi = r.json()["mahfiy_kirish_kodi"]
    await query.edit_message_text(
        f"✅ Yangi mahfiy kod:\n\n`{yangi}`\n\n"
        "⚠️ Eski kod bilan ochgan barcha mijozlar uchun mahfiy mahsulotlar "
        "avtomatik yopildi.",
        parse_mode="Markdown",
    )


async def statistika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    r = await api.stats(update.effective_user.id, store_id)
    if r.status_code != 200:
        await update.message.reply_text(f"❌ {r.text}")
        return
    s = r.json()
    await update.message.reply_text(
        f"📊 *Statistika*\n\n"
        f"Buyurtmalar: {s['umumiy_buyurtma']}\n"
        f"Tasdiqlangan: {s['tasdiqlangan_buyurtma']}\n"
        f"Tushum: {s['umumiy_tushum']:,.0f} som\n"
        f"Mahsulotlar: {s['mahsulot_soni']}",
        parse_mode="Markdown",
    )


async def top_tovarlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    r = await api.top_products(update.effective_user.id, store_id)
    if r.status_code != 200:
        await update.message.reply_text(f"❌ {r.text}")
        return
    top = r.json()
    if not top:
        await update.message.reply_text("Hali sotilgan tovar yo'q.")
        return
    lines = ["🏆 *Top tovarlar:*\n"]
    for i, t in enumerate(top, 1):
        lines.append(f"{i}. {t['nomi']} — {t['soni']} dona")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ---------------------------------------------------------------------------
# 🎟 Promo kod (tugmali)
# ---------------------------------------------------------------------------
async def promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return ConversationHandler.END
    context.user_data["promo_store"] = store_id
    await update.message.reply_text(
        "Promo kod matnini kiriting (masalan: YOZGI20):",
        reply_markup=cancel_markup(),
    )
    return PR_KOD


async def promo_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return PR_KOD
    context.user_data["promo_kod"] = update.message.text.strip()
    await update.message.reply_text("Chegirma foizini kiriting (1-100):")
    return PR_FOIZ


async def promo_foiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        foiz = int(update.message.text.strip())
        assert 1 <= foiz <= 100
    except (ValueError, AssertionError):
        await update.message.reply_text("1 dan 100 gacha raqam kiriting:")
        return PR_FOIZ
    r = await api.create_promo(
        update.effective_user.id,
        context.user_data["promo_store"],
        {"kod": context.user_data["promo_kod"], "chegirma_foizi": foiz},
    )
    if r.status_code == 200:
        await _back_to_menu(
            update,
            f"✅ Promo yaratildi: {context.user_data['promo_kod']} (-{foiz}%)",
        )
    else:
        await _back_to_menu(update, f"❌ {r.text[:300]}")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Super-admin: boshqa odamга do'kon ochish (legacy /yangi_dokon)
# ---------------------------------------------------------------------------
async def yangi_dokon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_super(update.effective_user.id):
        await _back_to_menu(update, "⛔️ Do'kon ochish faqat super-admin uchun.")
        return ConversationHandler.END
    await update.message.reply_text(
        "🏪 Yangi do'kon yaratish.\nDo'kon nomini kiriting:",
        reply_markup=cancel_markup(),
    )
    return S_NOMI


async def s_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_menu_press(update.message.text):
        await _warn_finish_first(update)
        return S_NOMI
    context.user_data["yangi_dokon_nomi"] = update.message.text
    await update.message.reply_text(
        "Yangi admin(do'kon egasi)ning Telegram ID'sini kiriting:"
    )
    return S_ADMIN_ID


async def s_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_admin = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Telegram ID raqam bo'lishi kerak:")
        return S_ADMIN_ID
    r = await api.create_store(
        update.effective_user.id,
        {
            "nomi": context.user_data["yangi_dokon_nomi"],
            "admin_telegram_id": new_admin,
        },
    )
    if r.status_code == 200:
        d = r.json()
        await _back_to_menu(
            update,
            f"✅ Do'kon yaratildi!\n\n"
            f"Nomi: {d['nomi']}\nID: {d['store_id']}\n"
            f"Admin: {new_admin}\n"
            f"Mahfiy kod: {d['mahfiy_kirish_kodi']}",
        )
    elif r.status_code == 403:
        await _back_to_menu(
            update, "⛔️ Faqat super-admin yangi do'kon qo'sha oladi."
        )
    else:
        await _back_to_menu(update, f"❌ {r.text[:300]}")
    context.user_data.clear()
    return ConversationHandler.END


# --- Super-admin: do'konni o'chirish (mavjud oqim) ---
async def dokon_ochirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_super(update.effective_user.id):
        await _back_to_menu(update, "⛔️ Do'kon o'chirish faqat super-admin uchun.")
        return
    stores = await api.my_stores(update.effective_user.id)
    if not stores:
        await update.message.reply_text("Do'konlar yo'q.")
        return
    rows = [
        [
            InlineKeyboardButton(
                f"🗑 {s['nomi']} (ID {s['id']})",
                callback_data=f"delstore_{s['id']}",
            )
        ]
        for s in stores
    ]
    await update.message.reply_text(
        "Qaysi do'konни o'chirmoqchisiz?\n"
        "⚠️ Do'kon bilan birga uning BARCHA mahsulot va buyurtmalari o'chadi!",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def dokon_ochirish_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    store_id = int(query.data.replace("delstore_", ""))
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Ha, o'chirilsin", callback_data=f"delok_{store_id}"
                ),
                InlineKeyboardButton("❌ Bekor", callback_data="delcancel"),
            ]
        ]
    )
    await query.edit_message_text(
        f"ID {store_id} do'konни butunlay o'chirishни tasdiqlaysizmi?\n"
        "Bu amalni ORTGA QAYTARIB BO'LMAYDI.",
        reply_markup=kb,
    )


async def dokon_ochirish_tasdiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    store_id = int(query.data.replace("delok_", ""))
    r = await api.delete_store(update.effective_user.id, store_id)
    if r.status_code == 200:
        d = r.json()
        await query.edit_message_text(
            f"🗑 '{d['nomi']}' do'koni butunlay o'chirildi."
        )
    elif r.status_code == 403:
        await query.edit_message_text(
            "⛔️ Faqat super-admin do'kon o'chira oladi."
        )
    else:
        await query.edit_message_text(f"❌ Xatolik: {r.text[:300]}")


async def dokon_ochirish_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Bekor qilindi — hech narsa o'chirilmadi.")


# ---------------------------------------------------------------------------
# Application yig'ish
# ---------------------------------------------------------------------------
def _conv(entry_points, states, name: str) -> ConversationHandler:
    return ConversationHandler(
        entry_points=entry_points,
        states=states,
        fallbacks=[
            MessageHandler(filters.Regex(f"^{BTN_HOME}$"), bekor),
            MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), bekor),
            CommandHandler("bekor", bekor),
        ],
        allow_reentry=True,
        name=name,
    )


def build_application(token: str) -> Application:
    app = Application.builder().token(token).updater(None).build()

    TXT = filters.TEXT & ~filters.COMMAND

    # 📦 Mahsulot qo'shish (kengaytirilgan, spec1 task_2)
    add_conv = _conv(
        [
            MessageHandler(filters.Regex(f"^{BTN_ADD}$"), add_start),
            CommandHandler("mahsulot_qoshish", add_start),
        ],
        {
            P_NOMI: [MessageHandler(TXT, p_nomi)],
            P_RASM: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), p_back_to_nomi),
                MessageHandler(filters.PHOTO, p_rasm),
                MessageHandler(filters.Regex(f"^{BTN_DONE}$"), p_rasm_done),
                MessageHandler(filters.Regex(f"^{BTN_SKIP}$"), p_rasm_skip),
            ],
            P_NISBAT: [CallbackQueryHandler(p_nisbat, pattern="^nis_")],
            P_NARX: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), p_back_from_narx),
                MessageHandler(filters.PHOTO, p_stray_photo),
                MessageHandler(TXT, p_narx),
            ],
            P_SKIDKA: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), p_back_to_narx),
                MessageHandler(TXT, p_skidka),
            ],
            P_MUDDAT: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), p_back_to_skidka),
                MessageHandler(TXT, p_muddat),
            ],
            P_MIQDOR: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), p_back_from_miqdor),
                MessageHandler(TXT, p_miqdor),
            ],
            P_TAVSIF: [
                MessageHandler(filters.Regex(f"^{BTN_BACK}$"), p_back_to_miqdor),
                MessageHandler(filters.Regex(f"^{BTN_SKIP}$"), p_tavsif_skip),
                MessageHandler(TXT, p_tavsif),
            ],
            P_KORINISH: [
                CallbackQueryHandler(p_korinish_back, pattern="^pkor_back$"),
                CallbackQueryHandler(p_korinish, pattern="^pkor_"),
            ],
            P_TASDIQ: [CallbackQueryHandler(p_saqlash, pattern="^psave_")],
        },
        "add_product",
    )

    # 🔄 Tahrirlash
    edit_conv = _conv(
        [
            MessageHandler(filters.Regex(f"^{BTN_EDIT}$"), edit_start),
            CommandHandler("mahsulot_yangilash", edit_start),
        ],
        {
            E_FIELD: [
                CallbackQueryHandler(edit_pick, pattern="^epick_"),
                CallbackQueryHandler(edit_field, pattern="^ef_"),
            ],
            E_VALUE: [
                CallbackQueryHandler(edit_value_korinish, pattern="^ekor_"),
                CallbackQueryHandler(edit_value_nisbat, pattern="^enis_"),
                MessageHandler(filters.PHOTO, edit_value_photo),
                MessageHandler(
                    filters.Regex(f"^{BTN_DONE}$"), edit_value_photo_done
                ),
                MessageHandler(TXT, edit_value_text),
            ],
            E_MUDDAT: [MessageHandler(TXT, edit_muddat)],
        },
        "edit_product",
    )

    # 🎟 Promo
    promo_conv = _conv(
        [
            MessageHandler(filters.Regex(f"^{BTN_PROMO}$"), promo_start),
            CommandHandler("promo_yaratish", promo_start),
        ],
        {
            PR_KOD: [MessageHandler(TXT, promo_kod)],
            PR_FOIZ: [MessageHandler(TXT, promo_foiz)],
        },
        "promo",
    )

    # 🔍 Qidirish
    search_conv = _conv(
        [
            MessageHandler(filters.Regex(f"^{BTN_SEARCH}$"), search_start),
            CommandHandler("qidirish", search_start),
        ],
        {Q_KIRITISH: [MessageHandler(TXT, search_query)]},
        "search",
    )

    # ➕ Yangi admin (super)
    newadmin_conv = _conv(
        [MessageHandler(filters.Regex(f"^{BTN_NEWADMIN}$"), newadmin_start)],
        {
            NA_ID: [
                CallbackQueryHandler(newadmin_store, pattern="^nastore_"),
                MessageHandler(TXT, newadmin_id),
            ]
        },
        "new_admin",
    )

    # 🏪 Yangi do'kon (faqat super) — nom + admin ID so'raydi
    store_conv = _conv(
        [
            MessageHandler(filters.Regex(f"^{BTN_NEWSTORE}$"), yangi_dokon),
            CommandHandler("yangi_dokon", yangi_dokon),
        ],
        {
            S_NOMI: [MessageHandler(TXT, s_nomi)],
            S_ADMIN_ID: [MessageHandler(TXT, s_admin_id)],
        },
        "super_store",
    )

    # ❌ Buyurtmani bekor qilish (sabab bilan)
    reject_conv = _conv(
        [CallbackQueryHandler(order_reject_start, pattern="^rad_")],
        {RAD_SABAB: [MessageHandler(TXT, order_reject_reason)]},
        "reject_order",
    )

    app.add_handler(CommandHandler("start", start))
    # 🏠 Bosh menyu — jarayondan tashqarida bosilса menyuni ko'rsatadi
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_HOME}$"), start))
    app.add_handler(add_conv)
    app.add_handler(edit_conv)
    app.add_handler(promo_conv)
    app.add_handler(search_conv)
    app.add_handler(newadmin_conv)
    app.add_handler(store_conv)
    app.add_handler(reject_conv)

    # Bir bosishli tugmalar / buyruqlar
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_DEL}$"), del_start))
    app.add_handler(CommandHandler("mahsulot_ochirish", del_start))
    app.add_handler(
        MessageHandler(filters.Regex(f"^{BTN_SECRET}$"), mahfiy_kod)
    )
    app.add_handler(CommandHandler("mahfiy_kod", mahfiy_kod))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_STATS}$"), statistika))
    app.add_handler(CommandHandler("statistika", statistika))
    app.add_handler(
        MessageHandler(filters.Regex(f"^{BTN_ORDERS}$"), buyurtmalar)
    )
    app.add_handler(CommandHandler("buyurtmalar", buyurtmalar))
    app.add_handler(CommandHandler("mahsulotlar", mahsulotlar))
    app.add_handler(CommandHandler("tasdiqlash", tasdiqlash))
    app.add_handler(CommandHandler("top_tovarlar", top_tovarlar))
    # 🗑 Do'kon o'chirish (faqat super-admin)
    app.add_handler(
        MessageHandler(filters.Regex(f"^{BTN_DELSTORE}$"), dokon_ochirish)
    )
    app.add_handler(CommandHandler("dokon_ochirish", dokon_ochirish))

    # Inline callbacklar
    app.add_handler(CallbackQueryHandler(order_accept, pattern="^qabul_"))
    app.add_handler(CallbackQueryHandler(del_pick, pattern="^pdel_\\d"))
    app.add_handler(CallbackQueryHandler(del_confirm, pattern="^pdelok_"))
    app.add_handler(CallbackQueryHandler(del_confirm, pattern="^pdelno$"))
    app.add_handler(CallbackQueryHandler(mahfiy_kod_refresh, pattern="^refresh_"))
    app.add_handler(
        CallbackQueryHandler(dokon_ochirish_tanlash, pattern="^delstore_")
    )
    app.add_handler(
        CallbackQueryHandler(dokon_ochirish_tasdiq, pattern="^delok_")
    )
    app.add_handler(
        CallbackQueryHandler(dokon_ochirish_bekor, pattern="^delcancel$")
    )
    return app
