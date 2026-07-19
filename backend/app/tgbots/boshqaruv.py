"""Boshqaruv Boti handlerlari — webhook rejimi (adminlar uchun, phase 8).

bots/boshqaruv_bot/bot.py bilan bir xil mantiq, bulutда ishlaydi.
Har amal backend'да check_store_access orqali tekshiriladi (rule 7).
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .client import api

# ConversationHandler holatlari.
(
    P_NOMI,
    P_NARX,
    P_KORINISH,
    S_NOMI,
    S_ADMIN_ID,
) = range(5)


async def _resolve_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminning do'konini aniqlaydi; ruxsat yo'q bo'lsa xabar beradi."""
    admin_id = update.effective_user.id
    stores = await api.my_stores(admin_id)
    if not stores:
        await update.effective_message.reply_text(
            "⛔️ Sizда ruxsat yo'q. Super-admin bilan bog'laning."
        )
        return None
    if len(stores) == 1:
        return stores[0]["id"]
    context.user_data["stores"] = stores
    return stores[0]["id"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = update.effective_user.id
    stores = await api.my_stores(admin_id)
    if not stores:
        await update.message.reply_text(
            "⛔️ Sizда ruxsat yo'q, super-admin bilan bog'laning.\n"
            "(Telegram ID'ingiz hech qaysi do'konга biriktirilmagan.)"
        )
        return
    lines = ["✅ Xush kelibsiz, admin!\n\nSizning do'konlaringiz:"]
    for s in stores:
        lines.append(f"• {s['nomi']} (ID: {s['id']}, holat: {s['holat']})")
    lines.append(
        "\nBuyruqlar: /mahsulot_qoshish, /mahsulotlar, /buyurtmalar, "
        "/tasdiqlash, /mahfiy_kod, /statistika, /top_tovarlar, /promo_yaratish"
    )
    await update.message.reply_text("\n".join(lines))


# --- Mahsulot qo'shish (ConversationHandler) ---
async def mahsulot_qoshish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return ConversationHandler.END
    context.user_data["store_id"] = store_id
    await update.message.reply_text("Mahsulot nomini kiriting:")
    return P_NOMI


async def p_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nomi"] = update.message.text
    await update.message.reply_text("Narxini kiriting (faqat raqam, so'mда):")
    return P_NARX


async def p_narx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["narxi"] = float(update.message.text.replace(" ", ""))
    except ValueError:
        await update.message.reply_text("Narx noto'g'ri. Faqat raqam kiriting:")
        return P_NARX
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Ommaviy", callback_data="kor_ommaviy"),
                InlineKeyboardButton("Mahfiy", callback_data="kor_mahfiy"),
            ]
        ]
    )
    await update.message.reply_text("Ko'rinishini tanlang:", reply_markup=kb)
    return P_KORINISH


async def p_korinish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    korinish = query.data.replace("kor_", "")
    admin_id = update.effective_user.id
    r = await api.add_product(
        admin_id,
        context.user_data["store_id"],
        {
            "nomi": context.user_data["nomi"],
            "narxi": context.user_data["narxi"],
            "korinish": korinish,
        },
    )
    if r.status_code == 200:
        await query.edit_message_text(
            f"✅ '{context.user_data['nomi']}' qo'shildi ({korinish})."
        )
    else:
        await query.edit_message_text(f"❌ Xatolik: {r.text}")
    return ConversationHandler.END


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
        lines.append(f"{belgi} #{p['id']} {p['nomi']} — {p['narxi']:,.0f} so'm")
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
            f"• #{o['id']} kod:`{o['kod']}` — {o['jami_narx']:,.0f} so'm — "
            f"_{o['holat']}_"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def tasdiqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tasdiqlash <kod> — buyurtma kodini tasdiqlash (phase 3.3)."""
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
    """Joriy mahfiy kodni ko'rsatish + yangilash tugmasi (rule 4, 6)."""
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
        f"Tushum: {s['umumiy_tushum']:,.0f} so'm\n"
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
        await update.message.reply_text("Hali sotilган tovar yo'q.")
        return
    lines = ["🏆 *Top tovarlar:*\n"]
    for i, t in enumerate(top, 1):
        lines.append(f"{i}. {t['nomi']} — {t['soni']} dona")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def promo_yaratish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/promo_yaratish <kod> <foiz> — promo kod (phase 8.4)."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Foydalanish: /promo_yaratish <KOD> <chegirma_foizi>"
        )
        return
    store_id = await _resolve_store(update, context)
    if store_id is None:
        return
    try:
        foiz = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Foiz raqam bo'lishi kerak.")
        return
    r = await api.create_promo(
        update.effective_user.id,
        store_id,
        {"kod": context.args[0], "chegirma_foizi": foiz},
    )
    if r.status_code == 200:
        await update.message.reply_text(
            f"✅ Promo yaratildi: {context.args[0]} (-{foiz}%)"
        )
    else:
        await update.message.reply_text(f"❌ {r.text}")


# --- Super-admin: yangi do'kon (rule 11) ---
async def yangi_dokon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏪 Yangi do'kon yaratish.\nDo'kon nomini kiriting (/bekor — bekor qilish):"
    )
    return S_NOMI


async def s_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(
            f"✅ Do'kon yaratildi!\n\n"
            f"Nomi: {d['nomi']}\nID: {d['store_id']}\n"
            f"Admin: {new_admin}\n"
            f"Mahfiy kod: `{d['mahfiy_kirish_kodi']}`\n\n"
            "Yangi admin darhol Boshqaruv Botiga kira oladi.",
            parse_mode="Markdown",
        )
    elif r.status_code == 403:
        await update.message.reply_text(
            "⛔️ Faqat super-admin yangi do'kon qo'sha oladi."
        )
    else:
        await update.message.reply_text(f"❌ {r.text}")
    return ConversationHandler.END


async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END


def build_application(token: str) -> Application:
    app = Application.builder().token(token).updater(None).build()

    product_conv = ConversationHandler(
        entry_points=[CommandHandler("mahsulot_qoshish", mahsulot_qoshish)],
        states={
            P_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_nomi)],
            P_NARX: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_narx)],
            P_KORINISH: [CallbackQueryHandler(p_korinish, pattern="^kor_")],
        },
        fallbacks=[CommandHandler("bekor", bekor)],
    )
    store_conv = ConversationHandler(
        entry_points=[CommandHandler("yangi_dokon", yangi_dokon)],
        states={
            S_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, s_nomi)],
            S_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, s_admin_id)],
        },
        fallbacks=[CommandHandler("bekor", bekor)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(product_conv)
    app.add_handler(store_conv)
    app.add_handler(CommandHandler("mahsulotlar", mahsulotlar))
    app.add_handler(CommandHandler("buyurtmalar", buyurtmalar))
    app.add_handler(CommandHandler("tasdiqlash", tasdiqlash))
    app.add_handler(CommandHandler("mahfiy_kod", mahfiy_kod))
    app.add_handler(CallbackQueryHandler(mahfiy_kod_refresh, pattern="^refresh_"))
    app.add_handler(CommandHandler("statistika", statistika))
    app.add_handler(CommandHandler("top_tovarlar", top_tovarlar))
    app.add_handler(CommandHandler("promo_yaratish", promo_yaratish))
    return app
